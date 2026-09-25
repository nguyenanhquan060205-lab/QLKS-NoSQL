# ====================================================================
# SERVICES: TRANG CHỦ & DASHBOARD THỐNG KÊ
# PHỤ TRÁCH: NHƯ
# ====================================================================

import calendar
import copy
from datetime import date, datetime, timedelta
from types import SimpleNamespace

from database.db import get_session
from services import room_stats_service

_EMPTY_REPORT = {
    "hotels": [],
    "selected_hotel_id": None,
    "selected_hotel_name": None,
    "period": "all",
    "period_label": "Toàn bộ thời gian",
    "custom_start": "",
    "custom_end": "",
    "custom_range_error": None,
    "total_hotels": 0,
    "total_rooms": 0,
    "available_rooms": 0,
    "occupied_rooms": 0,
    "maintenance_rooms": 0,
    "total_bookings": 0,
    "total_guests": 0,
    "total_invoices": 0,
    "total_revenue": 0,
    "adr": None,
    "hotel_breakdown": [],
    "revenue_labels": [],
    "revenue_values": [],
    "bucket_by_day": True,
}

PERIOD_OPTIONS = [
    ("all", "Toàn bộ thời gian"),
    ("today", "Hôm nay"),
    ("month", "Tháng này"),
    ("quarter", "Quý này"),
    ("year", "Năm này"),
    ("custom", "Tùy chọn khoảng ngày"),
]


def _to_date(value):
    """
    Chuẩn hóa giá trị cột kiểu 'date' đọc TỪ Cassandra về datetime.date thuần.

    cassandra-driver không trả về datetime.date cho cột CQL 'date' mà trả về
    cassandra.util.Date (vì CQL date hỗ trợ khoảng giá trị rộng hơn Python date).
    Lớp này KHÔNG hỗ trợ phép trừ giữa 2 Date (Date - Date sẽ TypeError), nên phải
    gọi .date() để lấy datetime.date thật trước khi làm phép tính/so sánh ngày tháng.
    """
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if hasattr(value, "date"):
        try:
            return value.date()
        except (OverflowError, ValueError, TypeError):
            return None
    return value


def _parse_date(value):
    """Chuyển chuỗi 'YYYY-MM-DD' (hoặc date có sẵn) thành đối tượng date, trả None nếu không hợp lệ."""
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return datetime.strptime(value.strip(), "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


def resolve_period_range(period, custom_start=None, custom_end=None):
    """
    Quy đổi lựa chọn kỳ báo cáo (period) thành khoảng ngày cụ thể [start, end].
    Trả về (start_date, end_date, nhãn hiển thị, thông_báo_lỗi). start/end = None nghĩa là
    không giới hạn (áp dụng cho 'Toàn bộ thời gian' hoặc khi khoảng tùy chọn không hợp lệ).
    thông_báo_lỗi = None nếu không có lỗi gì cần báo cho người dùng.
    """
    today = date.today()

    if period == "today":
        return today, today, "Hôm nay", None

    if period == "month":
        start = today.replace(day=1)
        last_day = calendar.monthrange(today.year, today.month)[1]
        return start, today.replace(day=last_day), f"Tháng {today.month}/{today.year}", None

    if period == "quarter":
        quarter = (today.month - 1) // 3 + 1
        start_month = (quarter - 1) * 3 + 1
        end_month = start_month + 2
        start = date(today.year, start_month, 1)
        end = date(today.year, end_month, calendar.monthrange(today.year, end_month)[1])
        return start, end, f"Quý {quarter}/{today.year}", None

    if period == "year":
        return date(today.year, 1, 1), date(today.year, 12, 31), f"Năm {today.year}", None

    if period == "custom":
        start = _parse_date(custom_start)
        end = _parse_date(custom_end)
        if start and end and start <= end:
            return start, end, f"{start.strftime('%d/%m/%Y')} - {end.strftime('%d/%m/%Y')}", None
        if not custom_start and not custom_end:
            # Chưa chọn gì cả (vừa chuyển sang "Tùy chọn") -> không tính là lỗi, chỉ chưa lọc.
            return None, None, "Toàn bộ thời gian (chưa chọn khoảng ngày)", None
        if start and end and start > end:
            return None, None, "Toàn bộ thời gian", '"Từ ngày" phải trước hoặc bằng "Đến ngày". Đã hiển thị toàn bộ thời gian.'
        return None, None, "Toàn bộ thời gian", 'Khoảng ngày chưa hợp lệ. Đã hiển thị toàn bộ thời gian.'

    return None, None, "Toàn bộ thời gian", None


def _stay_overlaps(check_in, check_out, start, end):
    """
    Booking thuộc kỳ khi thời gian LƯU TRÚ giao với kỳ, không chỉ khi ngày nhận phòng
    rơi vào kỳ. Đêm lưu trú là [check_in, check_out) — ngày trả phòng không tính đêm.
    Ví dụ: 29/08 -> 02/09 có đêm 01/09 nên phải được tính vào kỳ "Tháng 9".
    """
    if not start and not end:
        return True
    if not check_in:
        return False
    # Thiếu ngày trả phòng thì coi như lưu trú đúng 1 đêm check_in.
    last_night = check_out if check_out and check_out > check_in else check_in + timedelta(days=1)
    if end and check_in > end:
        return False
    if start and last_night <= start:
        return False
    return True


def _nights_in_window(check_in, check_out, start, end):
    """Số đêm của booking nằm trong kỳ [start, end] (end tính trọn ngày cuối kỳ)."""
    if not check_in or not check_out or check_out <= check_in:
        return 0
    window_start = max(check_in, start) if start else check_in
    window_end = min(check_out, end + timedelta(days=1)) if end else check_out
    return max(0, (window_end - window_start).days)


def _in_range(d, start, end):
    # Không lọc kỳ nào (period="all") thì lấy TẤT, kể cả bản ghi thiếu ngày. Nếu trả
    # False cho d=None ngay cả khi không lọc thì mọi hóa đơn/booking bị NULL ngày sẽ
    # âm thầm biến mất khỏi luôn cả thống kê "Toàn bộ thời gian" — sai số liệu mà
    # không có dấu hiệu gì để lần ra.
    if not start and not end:
        return True
    if not d:
        return False
    if start and d < start:
        return False
    if end and d > end:
        return False
    return True


def get_dashboard_report(hotel_id=None, period="all", custom_start=None, custom_end=None):
    """
    Báo cáo thống kê có thể lọc theo khách sạn (hotel_id) và theo kỳ (period).

    Nguồn dữ liệu (đều SELECT toàn bảng, không WHERE, nên không cần ALLOW FILTERING —
    phù hợp với quy mô dữ liệu đồ án; xem ghi chú ở dashboard_service cũ về việc tránh
    ALLOW FILTERING trên cột không phải khóa):
      - hotels: danh sách khách sạn
      - room_status_counts_by_hotel (bảng COUNTER): số phòng theo trạng thái của
        từng khách sạn; chưa có bảng thì lùi về đếm từ rooms_by_hotel
      - bookings_by_guest: có đủ hotel_id + check_in_date + check_out_date + total_amount
        nên dùng để tính lượt đặt, số đêm phòng đã bán và ADR theo kỳ. Booking thuộc
        kỳ khi thời gian lưu trú giao với kỳ (_stay_overlaps), bỏ qua đơn CANCELLED.
      - invoices_by_booking: dùng để tính doanh thu thực tế theo kỳ (theo issue_date)
    """
    session = get_session()
    start_date, end_date, period_label, custom_range_error = resolve_period_range(period, custom_start, custom_end)

    if not session:
        # deepcopy chứ không phải dict(): dict() chỉ copy tầng ngoài nên các list
        # ("hotels", "hotel_breakdown", "revenue_labels"...) vẫn là CHUNG một object
        # với _EMPTY_REPORT — ai append vào report trả về là bẩn luôn template toàn process.
        report = copy.deepcopy(_EMPTY_REPORT)
        report.update({
            "period": period,
            "period_label": period_label,
            "custom_start": custom_start or "",
            "custom_end": custom_end or "",
            "custom_range_error": custom_range_error,
        })
        return report

    hotels = []
    rooms_total = {}
    rooms_available = {}
    rooms_occupied = {}
    rooms_maintenance = {}
    bookings = []
    invoices = []
    total_guests = 0

    try:
        hotel_rows = session.execute("SELECT hotel_id, name FROM hotels;")
        # getattr thay vì r.name: khách sạn có name NULL thì vẫn hiện được mã, chứ
        # không làm sập cả dashboard vì một row dữ liệu thiếu.
        hotels = [
            {"hotel_id": r.hotel_id, "name": getattr(r, "name", None) or r.hotel_id}
            for r in hotel_rows
        ]
        # Đếm MỌI khách sạn trong bảng hotels. Không lọc theo tiền tố mã "MT_": khách
        # sạn thêm từ giao diện được cấp mã "H" + uuid (hotel_routes.add_hotel), lọc
        # theo tiền tố sẽ làm mọi chi nhánh mới biến mất khỏi thống kê.
    except Exception as error:
        print(f"❌ [Dashboard] Lỗi lấy danh sách khách sạn: {error}")

    # Số phòng theo trạng thái: đọc từ bảng COUNTER room_status_counts_by_hotel
    # (1 dòng / khách sạn, cập nhật ngay khi phòng đổi trạng thái) thay vì quét
    # toàn bảng rooms_by_hotel. Bảng counter chưa tạo / chưa có dữ liệu thì lùi về
    # quét bảng phòng như cũ, để dashboard không bao giờ trắng số.
    # Chỉ lấy khách sạn còn tồn tại: bỏ phòng/counter mồ côi của khách sạn đã xóa.
    known_hotel_ids = {h["hotel_id"] for h in hotels}
    try:
        room_counts = room_stats_service.get_counts(session)
        if room_counts is None:
            room_counts = room_stats_service.count_from_rooms(session)
        for hid, counts in room_counts.items():
            if known_hotel_ids and hid not in known_hotel_ids:
                continue
            rooms_total[hid] = counts["total_rooms"]
            rooms_available[hid] = counts["available_rooms"]
            rooms_occupied[hid] = counts["occupied_rooms"]
            rooms_maintenance[hid] = counts["maintenance_rooms"]
    except Exception as error:
        print(f"❌ [Dashboard] Lỗi lấy số phòng: {error}")

    try:
        booking_rows = session.execute(
            "SELECT booking_id, hotel_id, check_in_date, check_out_date, status, total_amount "
            "FROM bookings_by_guest;"
        )
        # Row của cassandra-driver bất biến (namedtuple) nên không sửa được thuộc tính
        # trực tiếp -> tạo bản sao SimpleNamespace, đồng thời chuẩn hóa ngày tháng.
        bookings = [
            SimpleNamespace(
                booking_id=getattr(r, "booking_id", None),
                hotel_id=getattr(r, "hotel_id", None),
                check_in_date=_to_date(getattr(r, "check_in_date", None)),
                check_out_date=_to_date(getattr(r, "check_out_date", None)),
                total_amount=getattr(r, "total_amount", None),
            )
            for r in booking_rows
            # Đơn đã hủy không chiếm phòng và không phát sinh doanh thu tiền phòng.
            if (getattr(r, "status", None) or "").upper() != "CANCELLED"
        ]
    except Exception as error:
        print(f"❌ [Dashboard] Lỗi lấy danh sách đặt phòng: {error}")

    try:
        guest_rows = session.execute("SELECT guest_id FROM guests;")
        total_guests = sum(1 for _ in guest_rows)
    except Exception as error:
        print(f"❌ [Dashboard] Lỗi đếm khách hàng: {error}")

    try:
        invoice_rows = session.execute(
            "SELECT invoice_id, booking_id, hotel_id, issue_date, total_amount "
            "FROM invoices_by_booking;"
        )
        invoices = [
            SimpleNamespace(
                invoice_id=getattr(r, "invoice_id", None),
                booking_id=getattr(r, "booking_id", None),
                hotel_id=getattr(r, "hotel_id", None),
                issue_date=_to_date(getattr(r, "issue_date", None)),
                total_amount=getattr(r, "total_amount", None),
            )
            for r in invoice_rows
        ]
    except Exception as error:
        print(f"❌ [Dashboard] Lỗi lấy danh sách hóa đơn: {error}")

    hotel_name_map = {h["hotel_id"]: h["name"] for h in hotels}
    selected_hotel_name = hotel_name_map.get(hotel_id) if hotel_id else None

    if hotel_id:
        scoped_bookings = [b for b in bookings if b.hotel_id == hotel_id]
        scoped_invoices = [i for i in invoices if i.hotel_id == hotel_id]
        total_rooms = rooms_total.get(hotel_id, 0)
        available_rooms = rooms_available.get(hotel_id, 0)
        occupied_rooms = rooms_occupied.get(hotel_id, 0)
        maintenance_rooms = rooms_maintenance.get(hotel_id, 0)
        total_hotels = 1 if hotel_id in hotel_name_map else 0
    else:
        scoped_bookings = bookings
        scoped_invoices = invoices
        total_rooms = sum(rooms_total.values())
        available_rooms = sum(rooms_available.values())
        occupied_rooms = sum(rooms_occupied.values())
        maintenance_rooms = sum(rooms_maintenance.values())
        total_hotels = len(hotels)

    filtered_bookings = [
        b for b in scoped_bookings
        if _stay_overlaps(b.check_in_date, b.check_out_date, start_date, end_date)
    ]
    filtered_invoices = [i for i in scoped_invoices if _in_range(i.issue_date, start_date, end_date)]

    total_bookings = len(filtered_bookings)
    total_revenue = sum(float(i.total_amount) for i in filtered_invoices if i.total_amount is not None)

    # ADR = doanh thu tiền phòng của các đêm trong kỳ / số đêm phòng đã bán trong kỳ.
    # Tử số và mẫu số lấy từ CÙNG một tập booking: tiền của mỗi booking chia đều cho
    # số đêm của nó, rồi chỉ cộng phần đêm nằm trong kỳ. Không dùng total_revenue
    # (theo issue_date của hóa đơn) vì đó là tập khác — trộn hai tập làm ADR sai.
    room_nights_sold = 0
    room_revenue = 0.0
    for b in filtered_bookings:
        nights_in_period = _nights_in_window(b.check_in_date, b.check_out_date, start_date, end_date)
        if not nights_in_period:
            continue
        room_nights_sold += nights_in_period
        total_nights = (b.check_out_date - b.check_in_date).days
        if b.total_amount is not None:
            room_revenue += float(b.total_amount) * nights_in_period / total_nights

    adr = None
    if room_nights_sold:
        adr = round(room_revenue / room_nights_sold, 0)

    # So sánh giữa các khách sạn — chỉ có ý nghĩa khi đang xem "Tất cả khách sạn"
    hotel_breakdown = []
    if not hotel_id:
        for h in hotels:
            hid = h["hotel_id"]
            h_bookings = [b for b in filtered_bookings if b.hotel_id == hid]
            h_invoices = [i for i in filtered_invoices if i.hotel_id == hid]
            h_revenue = sum(float(i.total_amount) for i in h_invoices if i.total_amount is not None)
            hotel_breakdown.append({
                "hotel_id": hid,
                "name": h["name"],
                "total_rooms": rooms_total.get(hid, 0),
                "available_rooms": rooms_available.get(hid, 0),
                "total_bookings": len(h_bookings),
                "total_revenue": h_revenue,
            })
        hotel_breakdown.sort(key=lambda item: item["total_revenue"], reverse=True)

    # Chuỗi doanh thu theo thời gian cho biểu đồ đường: theo NGÀY nếu kỳ ngắn (<= 62 ngày),
    # theo THÁNG nếu kỳ dài hơn (quý/năm/toàn bộ) — tránh biểu đồ quá rối khi kỳ dài.
    if start_date and end_date:
        span_days = (end_date - start_date).days
    else:
        issue_dates = [i.issue_date for i in filtered_invoices if i.issue_date]
        span_days = (max(issue_dates) - min(issue_dates)).days if len(issue_dates) >= 2 else 0
    bucket_by_day = span_days <= 62

    # Gom doanh thu theo mốc thời gian. Khóa gom là ĐỐI TƯỢNG date thật, không phải
    # chuỗi nhãn, vì sắp xếp lại chuỗi "%d/%m" bằng strptime có 2 lỗi:
    #   1. strptime("29/02", "%d/%m") -> ValueError, do năm mặc định 1900 không nhuận;
    #   2. kỳ vắt qua năm mới thì "05/01" bị xếp trước "28/12" (mất năm nên so sai).
    # Sort theo date rồi mới lấy nhãn ra là hết cả hai.
    revenue_series = {}
    for inv in filtered_invoices:
        if not inv.issue_date or inv.total_amount is None:
            continue
        if bucket_by_day:
            bucket = inv.issue_date
            label = inv.issue_date.strftime("%d/%m")
        else:
            bucket = date(inv.issue_date.year, inv.issue_date.month, 1)
            label = inv.issue_date.strftime("%m/%Y")
        entry = revenue_series.setdefault(bucket, [label, 0.0])
        entry[1] += float(inv.total_amount)

    ordered_buckets = sorted(revenue_series.items())
    revenue_labels = [label for _, (label, _) in ordered_buckets]
    revenue_values = [round(total) for _, (_, total) in ordered_buckets]

    return {
        "hotels": hotels,
        "selected_hotel_id": hotel_id,
        "selected_hotel_name": selected_hotel_name,
        "period": period,
        "period_label": period_label,
        "custom_start": custom_start or "",
        "custom_end": custom_end or "",
        "custom_range_error": custom_range_error,
        "total_hotels": total_hotels,
        "total_rooms": total_rooms,
        "available_rooms": available_rooms,
        "occupied_rooms": occupied_rooms,
        "maintenance_rooms": maintenance_rooms,
        "total_bookings": total_bookings,
        "total_guests": total_guests,
        "total_invoices": len(filtered_invoices),
        "total_revenue": total_revenue,
        "adr": adr,
        "hotel_breakdown": hotel_breakdown,
        "revenue_labels": revenue_labels,
        "revenue_values": revenue_values,
        "bucket_by_day": bucket_by_day,
    }


def get_dashboard_stats():
    """Giữ tương thích ngược: thống kê tổng quan không lọc (dùng cho trang chủ)."""
    return get_dashboard_report(hotel_id=None, period="all")
