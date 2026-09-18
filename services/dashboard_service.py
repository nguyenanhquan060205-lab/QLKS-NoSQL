# ====================================================================
# SERVICES: TRANG CHỦ & DASHBOARD THỐNG KÊ
# PHỤ TRÁCH: NHƯ
# ====================================================================

import calendar
from datetime import date, datetime
from types import SimpleNamespace

from database.db import get_session

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
    "total_bookings": 0,
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


def _in_range(d, start, end):
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
      - rooms_by_hotel: đếm tổng phòng & phòng trống, group theo hotel_id
      - bookings_by_guest: có đủ hotel_id + check_in_date + check_out_date + total_amount
        nên dùng để tính lượt đặt và tỷ lệ lấp đầy (occupancy) theo kỳ
      - invoices_by_booking: dùng để tính doanh thu thực tế theo kỳ (theo issue_date)

    Tỷ lệ lấp đầy (Occupancy Rate) = (số đêm phòng đã bán trong kỳ) /
    (tổng số phòng x số ngày trong kỳ) x 100%. Chỉ tính được khi có kỳ cụ thể
    (period khác 'all'), vì 'toàn bộ thời gian' không có mẫu số ngày rõ ràng.
    """
    session = get_session()
    start_date, end_date, period_label, custom_range_error = resolve_period_range(period, custom_start, custom_end)

    if not session:
        report = dict(_EMPTY_REPORT)
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
    bookings = []
    invoices = []

    try:
        hotel_rows = session.execute("SELECT hotel_id, name FROM hotels;")
        hotels = [{"hotel_id": r.hotel_id, "name": r.name} for r in hotel_rows]
    except Exception as error:
        print(f"❌ [Dashboard] Lỗi lấy danh sách khách sạn: {error}")

    try:
        room_rows = session.execute("SELECT hotel_id, is_available FROM rooms_by_hotel;")
        for r in room_rows:
            rooms_total[r.hotel_id] = rooms_total.get(r.hotel_id, 0) + 1
            if r.is_available:
                rooms_available[r.hotel_id] = rooms_available.get(r.hotel_id, 0) + 1
    except Exception as error:
        print(f"❌ [Dashboard] Lỗi lấy danh sách phòng: {error}")

    try:
        booking_rows = session.execute(
            "SELECT booking_id, hotel_id, check_in_date, check_out_date, total_amount "
            "FROM bookings_by_guest;"
        )
        # Row của cassandra-driver bất biến (namedtuple) nên không sửa được thuộc tính
        # trực tiếp -> tạo bản sao SimpleNamespace, đồng thời chuẩn hóa ngày tháng.
        bookings = [
            SimpleNamespace(
                booking_id=r.booking_id,
                hotel_id=r.hotel_id,
                check_in_date=_to_date(r.check_in_date),
                check_out_date=_to_date(r.check_out_date),
                total_amount=r.total_amount,
            )
            for r in booking_rows
        ]
    except Exception as error:
        print(f"❌ [Dashboard] Lỗi lấy danh sách đặt phòng: {error}")

    try:
        invoice_rows = session.execute(
            "SELECT invoice_id, booking_id, hotel_id, issue_date, total_amount "
            "FROM invoices_by_booking;"
        )
        invoices = [
            SimpleNamespace(
                invoice_id=r.invoice_id,
                booking_id=r.booking_id,
                hotel_id=r.hotel_id,
                issue_date=_to_date(r.issue_date),
                total_amount=r.total_amount,
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
        total_hotels = 1 if hotel_id in hotel_name_map else 0
    else:
        scoped_bookings = bookings
        scoped_invoices = invoices
        total_rooms = sum(rooms_total.values())
        available_rooms = sum(rooms_available.values())
        total_hotels = len(hotels)

    filtered_bookings = [b for b in scoped_bookings if _in_range(b.check_in_date, start_date, end_date)]
    filtered_invoices = [i for i in scoped_invoices if _in_range(i.issue_date, start_date, end_date)]

    total_bookings = len(filtered_bookings)
    total_revenue = sum(float(i.total_amount) for i in filtered_invoices if i.total_amount is not None)

    # Số đêm phòng đã bán trong kỳ (cắt phần booking nằm ngoài khoảng lọc)
    room_nights_sold = 0
    for b in filtered_bookings:
        check_in, check_out = b.check_in_date, b.check_out_date
        if not check_in or not check_out or check_out <= check_in:
            continue
        window_start = max(check_in, start_date) if start_date else check_in
        window_end = min(check_out, end_date) if end_date else check_out
        nights = (window_end - window_start).days
        if nights > 0:
            room_nights_sold += nights

    adr = None
    if room_nights_sold:
        adr = round(total_revenue / room_nights_sold, 0)

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

    revenue_series = {}
    for inv in filtered_invoices:
        if not inv.issue_date or inv.total_amount is None:
            continue
        key = inv.issue_date.strftime("%d/%m") if bucket_by_day else inv.issue_date.strftime("%m/%Y")
        revenue_series[key] = revenue_series.get(key, 0) + float(inv.total_amount)

    sort_key = (lambda k: datetime.strptime(k, "%d/%m")) if bucket_by_day else (lambda k: datetime.strptime(k, "%m/%Y"))
    revenue_labels = sorted(revenue_series.keys(), key=sort_key)
    revenue_values = [round(revenue_series[k]) for k in revenue_labels]

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
        "total_bookings": total_bookings,
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
