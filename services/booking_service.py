# ====================================================================
# SERVICES: QUẢN LÝ ĐẶT PHÒNG & HÓA ĐƠN
# PHỤ TRÁCH: QUÂN
# ====================================================================

import uuid
import time
from datetime import datetime, date
from decimal import Decimal
from database.db import get_session

# Kho lưu trữ bộ nhớ tạm (Mock store khi chưa nạp chứng chỉ AstraDB)
_mock_bookings_by_guest = []
_mock_bookings_by_hotel_date = []
_mock_invoices = []

# In-memory cache cho danh sách hóa đơn (TTL 30s)
_invoice_cache = {"data": None, "timestamp": 0}

# In-memory cache cho danh sách đặt phòng (TTL 30s)
_booking_cache = {"data": None, "timestamp": 0}


def invalidate_invoice_cache():
    """Hủy cache danh sách hóa đơn khi có phát sinh giao dịch mới."""
    _invoice_cache["data"] = None
    _invoice_cache["timestamp"] = 0


def invalidate_booking_cache():
    """Hủy cache danh sách đặt phòng khi có phát sinh giao dịch mới."""
    _booking_cache["data"] = None
    _booking_cache["timestamp"] = 0


# --------------------------------------------------------------------
# 1. ĐẶT PHÒNG VỚI BATCH INSERT (TRỌNG TÂM CASSANDRA - QUERY Q5)
# --------------------------------------------------------------------

def create_booking_batch(guest_id, guest_name, hotel_id, room_number, 
                         check_in_date, check_out_date, status="CONFIRMED", 
                         total_amount=0, booking_id=None):
    """
    [QUÂN - TASK QLKS-08] - Query Q5 trong đề cương PDF:
    Theo nguyên lý thiết kế Cassandra (Query-First & Denormalization):
    Dữ liệu đặt phòng được lưu đồng thời ở 2 bảng:
      - bookings_by_guest (phục vụ tra cứu lịch sử theo khách - Query Q2)
      - bookings_by_hotel_date (phục vụ tra cứu danh sách theo KS và ngày check-in - Query Q3)

    Sử dụng BATCH STATEMENT để đảm bảo tính nhất quán (Atomic Batch):
      BEGIN BATCH
        INSERT INTO bookings_by_guest (guest_id, booking_id, hotel_id, room_number, check_in_date, check_out_date, status, total_amount)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        INSERT INTO bookings_by_hotel_date (hotel_id, check_in_date, booking_id, guest_id, guest_name, room_number, status)
        VALUES (?, ?, ?, ?, ?, ?, ?);
      APPLY BATCH;
    """
    # 1. Khởi tạo mã booking_id nếu chưa truyền vào
    if not booking_id:
        booking_id = f"BK{datetime.now().strftime('%Y%m%d%H%M%S')}"

    # 2. Chuẩn hóa kiểu dữ liệu date cho Cassandra DateType
    if isinstance(check_in_date, str):
        in_date = datetime.strptime(check_in_date.strip(), "%Y-%m-%d").date()
    else:
        in_date = check_in_date

    if isinstance(check_out_date, str):
        out_date = datetime.strptime(check_out_date.strip(), "%Y-%m-%d").date()
    else:
        out_date = check_out_date

    amount = Decimal(str(total_amount))
    status_val = status or "CONFIRMED"

    session = get_session()

    if session:
        # Khi đã kết nối AstraDB thành công: Sử dụng BatchStatement chính thức
        from cassandra.query import BatchStatement

        batch = BatchStatement()

        # Câu lệnh 1: Insert vào bảng bookings_by_guest (Partition: guest_id, Cluster: booking_id)
        stmt_guest = session.prepare("""
            INSERT INTO bookings_by_guest (
                guest_id, booking_id, hotel_id, room_number, 
                check_in_date, check_out_date, status, total_amount
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """)
        batch.add(stmt_guest, (
            guest_id, booking_id, hotel_id, str(room_number), 
            in_date, out_date, status_val, amount
        ))

        # Câu lệnh 2: Insert vào bảng bookings_by_hotel_date (Partition: (hotel_id, check_in_date), Cluster: booking_id)
        stmt_hotel_date = session.prepare("""
            INSERT INTO bookings_by_hotel_date (
                hotel_id, check_in_date, booking_id, 
                guest_id, guest_name, room_number, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?);
        """)
        batch.add(stmt_hotel_date, (
            hotel_id, in_date, booking_id, 
            guest_id, guest_name, str(room_number), status_val
        ))

        # Thực thi BATCH ghi đồng thời
        session.execute(batch)
        print(f"✅ [AstraDB] Đã thực thi BATCH INSERT Q5 thành công! Mã Booking: {booking_id}")
    else:
        # Chế độ dự phòng giả lập (Mock Store khi đang phát triển chưa có Token AstraDB)
        record_guest = {
            "guest_id": guest_id,
            "booking_id": booking_id,
            "hotel_id": hotel_id,
            "room_number": str(room_number),
            "check_in_date": in_date,
            "check_out_date": out_date,
            "status": status_val,
            "total_amount": amount
        }
        record_hotel_date = {
            "hotel_id": hotel_id,
            "check_in_date": in_date,
            "booking_id": booking_id,
            "guest_id": guest_id,
            "guest_name": guest_name,
            "room_number": str(room_number),
            "status": status_val
        }
        _mock_bookings_by_guest.append(record_guest)
        _mock_bookings_by_hotel_date.append(record_hotel_date)
        print(f"🔶 [MOCK MODE] Đã ghi đồng thời vào cả 2 bảng tạm. Mã Booking: {booking_id}")

    invalidate_invoice_cache()
    invalidate_booking_cache()
    return booking_id


# --------------------------------------------------------------------
# 2. TRA CỨU ĐẶT PHÒNG THEO KHÁCH HÀNG (QUERY Q2 TRONG PDF)
# --------------------------------------------------------------------

def _row_value(row, field, default=None):
    """Đọc 1 trường từ bản ghi, không cần biết nó là cassandra Row hay dict."""
    if isinstance(row, dict):
        return row.get(field, default)
    value = getattr(row, field, default)
    return default if value is None else value


def _lookup_by_pk(session, query, keys):
    """
    Đọc nhiều bản ghi theo KHÓA CHÍNH, mỗi khóa một lần — cố tình KHÔNG
    'SELECT * FROM <bảng>' rồi lọc ở Python, để Q2/Q3 giữ đúng tính chất chỉ
    đụng vào partition cần thiết. Số khóa ở đây luôn nhỏ (1 khách, vài khách sạn).
    """
    out = {}
    if not session or not keys:
        return out
    try:
        stmt = session.prepare(query)
        for key in keys:
            rows = list(session.execute(stmt, (key,)))
            if rows:
                out[key] = rows[0]
    except Exception as error:
        print(f"⚠️ [Booking] Không bù được thông tin tham chiếu: {error}")
    return out


def _normalize_bookings(rows, session=None):
    """
    Đưa bản ghi booking của Q2/Q3 về CÙNG shape dict mà get_all_bookings() trả ra.

    VÌ SAO CẦN: templates/bookings.html đọc field theo kiểu
    `b.guest_name if b.guest_name is defined else b.get('guest_name', '')`.
    Với cassandra Row (namedtuple) thiếu cột thì nhánh `is defined` là False,
    rơi xuống `.get()` — mà Row KHÔNG có method .get() -> Jinja raise
    UndefinedError -> cả trang 500. Bảng bookings_by_guest lại không có cột
    guest_name, nên trước đây MỌI khách có đơn đều làm trang lịch sử chết.

    Thay vì sửa template cho chịu được 2 kiểu dữ liệu, chuẩn hóa ngay ở service
    để cả 3 đường (Q2, Q3, get_all_bookings) trả về một shape duy nhất.
    """
    rows = list(rows or [])
    if not rows:
        return []

    guest_ids = {str(_row_value(r, "guest_id", "")) for r in rows}
    guest_ids.discard("")
    hotel_ids = {str(_row_value(r, "hotel_id", "")) for r in rows}
    hotel_ids.discard("")

    guest_map = _lookup_by_pk(
        session,
        "SELECT guest_id, full_name, phone, id_card FROM guests WHERE guest_id = ?;",
        guest_ids,
    )
    hotel_map = _lookup_by_pk(
        session,
        "SELECT hotel_id, name, city FROM hotels WHERE hotel_id = ?;",
        hotel_ids,
    )

    normalized = []
    for r in rows:
        g_id = str(_row_value(r, "guest_id", "") or "")
        h_id = str(_row_value(r, "hotel_id", "") or "")
        g_info = guest_map.get(g_id)
        h_info = hotel_map.get(h_id)

        check_in = _row_value(r, "check_in_date")
        check_out = _row_value(r, "check_out_date")

        nights = 1
        if check_in and check_out:
            try:
                d_in = date(check_in.year, check_in.month, check_in.day) if hasattr(check_in, "year") else check_in
                d_out = date(check_out.year, check_out.month, check_out.day) if hasattr(check_out, "year") else check_out
                nights = max(1, (d_out - d_in).days)
            except Exception:
                nights = 1

        amount = _row_value(r, "total_amount")
        try:
            amount = float(amount) if amount is not None else 0.0
        except (TypeError, ValueError):
            amount = 0.0

        # guest_name: ưu tiên bản ghi tự có (bảng bookings_by_hotel_date của Q3 có
        # sẵn cột này), sau đó mới tới hồ sơ khách, cuối cùng fallback về mã khách.
        guest_name = _row_value(r, "guest_name", "") or _row_value(g_info, "full_name", "") or g_id or "Khách vãng lai"

        normalized.append({
            "booking_id": _row_value(r, "booking_id", ""),
            "guest_id": g_id,
            "guest_name": guest_name,
            "guest_phone": _row_value(g_info, "phone", "") if g_info else "",
            "guest_id_card": _row_value(g_info, "id_card", "") if g_info else "",
            "hotel_id": h_id,
            "hotel_name": _row_value(h_info, "name", h_id) if h_info else h_id,
            "hotel_city": _row_value(h_info, "city", "") if h_info else "",
            "room_number": str(_row_value(r, "room_number", "") or ""),
            "check_in_date": check_in,
            "check_out_date": check_out,
            "nights": nights,
            "status": _row_value(r, "status", "") or "CONFIRMED",
            "total_amount": amount,
        })

    return normalized


def get_bookings_by_guest(guest_id):
    """
    [QUÂN - TASK QLKS-09] - Query Q2 trong đề cương PDF:
    Tra cứu toàn bộ lịch sử đặt phòng của khách hàng theo mã khách hàng (guest_id).
    
    Nguyên lý NoSQL Cassandra:
    - Bảng bookings_by_guest có Partition Key là guest_id, Clustering Key là booking_id.
    - Truy vấn WHERE guest_id = ? định tuyến trực tiếp đến Partition duy nhất trên node,
      đạt tốc độ truy vấn O(1) mà không cần scan toàn bộ bảng.
    """
    if not guest_id:
        return []

    guest_id_str = str(guest_id).strip()
    session = get_session()

    if session:
        try:
            stmt = session.prepare("""
                SELECT guest_id, booking_id, hotel_id, room_number, 
                       check_in_date, check_out_date, status, total_amount
                FROM bookings_by_guest
                WHERE guest_id = ?;
            """)
            rows = session.execute(stmt, (guest_id_str,))
            return _normalize_bookings(rows, session)
        except Exception as error:
            print(f"❌ [Lỗi truy vấn Q2 - bookings_by_guest]: {error}")
            return []

    # Mock fallback
    return _normalize_bookings(
        [b for b in _mock_bookings_by_guest if b["guest_id"] == guest_id_str]
    )


# --------------------------------------------------------------------
# 3. TRA CỨU ĐẶT PHÒNG THEO KHÁCH SẠN VÀ NGÀY (QUERY Q3 TRONG PDF)
# --------------------------------------------------------------------

def get_bookings_by_hotel_date(hotel_id, check_in_date):
    """
    [QUÂN - TASK QLKS-09] - Query Q3 trong đề cương PDF:
    Tra cứu danh sách khách check-in tại khách sạn trong ngày chỉ định.

    Nguyên lý NoSQL Cassandra:
    - Bảng bookings_by_hotel_date có Composite Partition Key là ((hotel_id, check_in_date)),
      Clustering Key là booking_id.
    - Bắt buộc phải cung cấp đủ cả hotel_id VÀ check_in_date để Cassandra tính toán hash partition,
      giúp hệ thống tìm kiếm siêu tốc trên cụm dữ liệu phân tán.
    """
    if not hotel_id or not check_in_date:
        return []

    hotel_id_str = str(hotel_id).strip()

    # Chuẩn hóa kiểu dữ liệu date cho Cassandra DateType
    if isinstance(check_in_date, str):
        try:
            in_date = datetime.strptime(check_in_date.strip(), "%Y-%m-%d").date()
        except ValueError:
            print(f"❌ [Lỗi định dạng ngày Q3]: {check_in_date} không đúng định dạng YYYY-MM-DD")
            return []
    else:
        in_date = check_in_date

    session = get_session()

    if session:
        try:
            stmt = session.prepare("""
                SELECT hotel_id, check_in_date, booking_id, 
                       guest_id, guest_name, room_number, status
                FROM bookings_by_hotel_date
                WHERE hotel_id = ? AND check_in_date = ?;
            """)
            rows = session.execute(stmt, (hotel_id_str, in_date))
            return _normalize_bookings(rows, session)
        except Exception as error:
            print(f"❌ [Lỗi truy vấn Q3 - bookings_by_hotel_date]: {error}")
            return []

    # Mock fallback
    return _normalize_bookings([
        b for b in _mock_bookings_by_hotel_date
        if b["hotel_id"] == hotel_id_str and str(b["check_in_date"]) == str(in_date)
    ])


# --------------------------------------------------------------------
# 4. QUẢN LÝ HÓA ĐƠN THEO MÃ ĐẶT PHÒNG (QUERY Q4 TRONG PDF)
# --------------------------------------------------------------------

def get_invoice_by_booking(booking_id):
    """
    [QUÂN - TASK QLKS-10] - Query Q4 trong đề cương PDF:
    Tra cứu hóa đơn thanh toán theo mã đặt phòng (booking_id).

    Nguyên lý NoSQL Cassandra:
    - Bảng invoices_by_booking có Partition Key là booking_id, Clustering Key là invoice_id.
    - Truy vấn WHERE booking_id = ? định tuyến trực tiếp đến Partition duy nhất trên node,
      đạt tốc độ truy vấn O(1) theo đúng thiết kế Query-First.

    Câu lệnh CQL:
      SELECT booking_id, invoice_id, guest_name, hotel_id,
             issue_date, payment_method, payment_status, total_amount
      FROM invoices_by_booking
      WHERE booking_id = ?;

    Trả về bản ghi hóa đơn (Row / dict) hoặc None nếu không tìm thấy.
    """
    if not booking_id:
        return None

    booking_id_str = str(booking_id).strip()
    session = get_session()

    if session:
        try:
            stmt = session.prepare("""
                SELECT booking_id, invoice_id, guest_name, hotel_id,
                       issue_date, payment_method, payment_status, total_amount,
                       deposit_amount, remaining_amount
                FROM invoices_by_booking
                WHERE booking_id = ?;
            """)
            rows = session.execute(stmt, (booking_id_str,))
            return rows.one() if hasattr(rows, "one") else (rows[0] if rows else None)
        except Exception as error:
            # Fallback nếu câu query 10 cột gặp lỗi driver cũ
            try:
                stmt_fallback = session.prepare("""
                    SELECT booking_id, invoice_id, guest_name, hotel_id,
                           issue_date, payment_method, payment_status, total_amount
                    FROM invoices_by_booking
                    WHERE booking_id = ?;
                """)
                rows = session.execute(stmt_fallback, (booking_id_str,))
                return rows.one() if hasattr(rows, "one") else (rows[0] if rows else None)
            except Exception as e_fb:
                print(f"❌ [Lỗi truy vấn Q4 - invoices_by_booking]: {error} / {e_fb}")
                return None

    # Mock fallback
    for inv in _mock_invoices:
        if inv.get("booking_id") == booking_id_str:
            return inv
    return None


def create_invoice(booking_id, invoice_id=None, guest_name="", hotel_id="", 
                   issue_date=None, payment_method="CASH", payment_status=None, total_amount=0,
                   deposit_amount=None, remaining_amount=None):
    """
    [QUÂN - TASK QLKS-10 & NÂNG CẤP ĐẶT CỌC]
    Tạo hóa đơn thanh toán cho mã đặt phòng (bảng invoices_by_booking).
    Hỗ trợ thanh toán toàn bộ (PAID), thanh toán cọc trước (PARTIAL), hoặc thanh toán sau (UNPAID).

    Theo mô hình dữ liệu Cassandra:
      - Partition Key: booking_id
      - Clustering Key: invoice_id
    """
    if not booking_id:
        return None

    booking_id_str = str(booking_id).strip()
    if not invoice_id:
        invoice_id = f"INV{datetime.now().strftime('%Y%m%d%H%M%S')}"
    else:
        invoice_id = str(invoice_id).strip()

    # Chuẩn hóa kiểu dữ liệu date cho Cassandra DateType
    if issue_date is None:
        in_date = date.today()
    elif isinstance(issue_date, str):
        try:
            in_date = datetime.strptime(issue_date.strip(), "%Y-%m-%d").date()
        except ValueError:
            in_date = date.today()
    elif isinstance(issue_date, datetime):
        in_date = issue_date.date()
    else:
        in_date = issue_date

    try:
        amount = Decimal(str(total_amount))
    except Exception:
        amount = Decimal("0")

    # Xử lý số tiền cọc (deposit_amount) & số tiền còn lại (remaining_amount)
    if deposit_amount is not None:
        try:
            dep_amount = Decimal(str(deposit_amount))
        except Exception:
            dep_amount = Decimal("0")
    else:
        # Tự động suy luận tiền cọc nếu không truyền trực tiếp
        if payment_status == "PAID":
            dep_amount = amount
        elif payment_status == "PARTIAL":
            dep_amount = amount / Decimal("2")
        else:
            dep_amount = Decimal("0")

    if remaining_amount is not None:
        try:
            rem_amount = Decimal(str(remaining_amount))
        except Exception:
            rem_amount = max(Decimal("0"), amount - dep_amount)
    else:
        rem_amount = max(Decimal("0"), amount - dep_amount)

    # Tự động chuẩn hóa trạng thái thanh toán
    if not payment_status:
        if amount > 0 and dep_amount >= amount:
            status_str = "PAID"
            dep_amount = amount
            rem_amount = Decimal("0")
        elif dep_amount > 0:
            status_str = "PARTIAL"
        else:
            status_str = "UNPAID"
            rem_amount = amount
    else:
        status_str = str(payment_status).strip().upper()
        if status_str == "PAID":
            dep_amount = amount
            rem_amount = Decimal("0")
        elif status_str == "UNPAID":
            dep_amount = Decimal("0")
            rem_amount = amount

    guest_name_str = str(guest_name).strip() if guest_name else ""
    hotel_id_str = str(hotel_id).strip() if hotel_id else ""
    method_str = str(payment_method).strip() if payment_method else "TIỀN MẶT"

    session = get_session()
    if session:
        try:
            stmt = session.prepare("""
                INSERT INTO invoices_by_booking (
                    booking_id, invoice_id, guest_name, hotel_id,
                    issue_date, payment_method, payment_status, total_amount,
                    deposit_amount, remaining_amount
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """)
            session.execute(stmt, (
                booking_id_str,
                invoice_id,
                guest_name_str,
                hotel_id_str,
                in_date,
                method_str,
                status_str,
                amount,
                dep_amount,
                rem_amount
            ))
            print(f"✅ [AstraDB] Đã tạo hóa đơn Q4 thành công! Mã HĐ: {invoice_id} cho Booking: {booking_id_str} (Trạng thái: {status_str}, Đã cọc: {dep_amount}, Còn lại: {rem_amount})")
            invalidate_invoice_cache()
            return invoice_id
        except Exception as error:
            # Fallback nếu insert 10 cột gặp lỗi
            try:
                stmt_fb = session.prepare("""
                    INSERT INTO invoices_by_booking (
                        booking_id, invoice_id, guest_name, hotel_id,
                        issue_date, payment_method, payment_status, total_amount
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """)
                session.execute(stmt_fb, (
                    booking_id_str,
                    invoice_id,
                    guest_name_str,
                    hotel_id_str,
                    in_date,
                    method_str,
                    status_str,
                    amount
                ))
                print(f"⚠️ [AstraDB Fallback] Đã tạo hóa đơn Q4 8 cột: {invoice_id}")
                invalidate_invoice_cache()
                return invoice_id
            except Exception as e_fb:
                print(f"❌ [Lỗi tạo hóa đơn Q4 - invoices_by_booking]: {error} / {e_fb}")
                return None
    else:
        # Mock fallback khi chưa có kết nối AstraDB
        record = {
            "booking_id": booking_id_str,
            "invoice_id": invoice_id,
            "guest_name": guest_name_str,
            "hotel_id": hotel_id_str,
            "issue_date": in_date,
            "payment_method": method_str,
            "payment_status": status_str,
            "total_amount": amount,
            "deposit_amount": dep_amount,
            "remaining_amount": rem_amount
        }
        _mock_invoices.append(record)
        print(f"🔶 [MOCK MODE] Đã lưu hóa đơn tạm. Mã HĐ: {invoice_id} ({status_str})")
        invalidate_invoice_cache()
        return invoice_id


# --------------------------------------------------------------------
# 5. DANH SÁCH TOÀN BỘ HÓA ĐƠN & CHI TIẾT ĐẦY ĐỦ (QUERY Q4 MỞ RỘNG)
# --------------------------------------------------------------------

def get_all_invoices(limit=250, use_cache=True):
    """
    [QUÂN - TASK QLKS-10 & QLKS-11]
    Lấy danh sách toàn bộ hóa đơn thanh toán kèm thông tin người đặt,
    ngày check-in, check-out, số phòng, chi nhánh khách sạn để hiển thị bảng quản lý hóa đơn.
    """
    import time
    now = time.time()
    if use_cache and _invoice_cache["data"] is not None and (now - _invoice_cache["timestamp"] < 30):
        return _invoice_cache["data"]

    session = get_session()
    if session:
        try:
            try:
                inv_rows = list(session.execute(
                    f"SELECT booking_id, invoice_id, guest_name, hotel_id, issue_date, payment_method, payment_status, total_amount, deposit_amount, remaining_amount FROM invoices_by_booking LIMIT {limit};"
                ))
            except Exception:
                # Fallback nếu bảng chưa có cột mới
                inv_rows = list(session.execute(
                    f"SELECT booking_id, invoice_id, guest_name, hotel_id, issue_date, payment_method, payment_status, total_amount FROM invoices_by_booking LIMIT {limit};"
                ))

            booking_rows = list(session.execute(
                "SELECT booking_id, check_in_date, check_out_date, room_number, hotel_id, guest_id, status FROM bookings_by_guest;"
            ))
            booking_map = {b.booking_id: b for b in booking_rows}

            try:
                guest_rows = list(session.execute("SELECT guest_id, full_name, phone, id_card FROM guests;"))
                guest_map = {g.guest_id: g for g in guest_rows}
            except Exception:
                guest_map = {}

            try:
                hotel_rows = list(session.execute("SELECT hotel_id, name, address, city FROM hotels;"))
                hotel_map = {h.hotel_id: h for h in hotel_rows}
            except Exception:
                hotel_map = {}

            result = []
            for inv in inv_rows:
                b_info = booking_map.get(inv.booking_id)
                g_id = getattr(b_info, "guest_id", None) if b_info else None
                g_info = guest_map.get(g_id) if g_id else None
                h_info = hotel_map.get(inv.hotel_id)

                check_in = getattr(b_info, "check_in_date", None) if b_info else None
                check_out = getattr(b_info, "check_out_date", None) if b_info else None

                nights = 1
                if check_in and check_out:
                    try:
                        d_in = date(check_in.year, check_in.month, check_in.day) if hasattr(check_in, "year") else check_in
                        d_out = date(check_out.year, check_out.month, check_out.day) if hasattr(check_out, "year") else check_out
                        nights = max(1, (d_out - d_in).days)
                    except Exception:
                        nights = 1

                tot_amt = float(inv.total_amount) if inv.total_amount is not None else 0.0
                pay_st = (inv.payment_status or "PAID").strip().upper()
                
                # Tính toán số tiền cọc & số tiền còn thiếu (fallback an toàn cho dữ liệu cũ)
                raw_dep = getattr(inv, "deposit_amount", None)
                raw_rem = getattr(inv, "remaining_amount", None)

                if raw_dep is not None:
                    dep_val = float(raw_dep)
                else:
                    if pay_st == "PAID":
                        dep_val = tot_amt
                    elif pay_st == "PARTIAL":
                        dep_val = round(tot_amt / 2.0, 0)
                    else:
                        dep_val = 0.0

                if raw_rem is not None:
                    rem_val = float(raw_rem)
                else:
                    if pay_st == "PAID":
                        rem_val = 0.0
                    elif pay_st == "PARTIAL":
                        rem_val = max(0.0, tot_amt - dep_val)
                    else:
                        rem_val = tot_amt

                item = {
                    "booking_id": inv.booking_id,
                    "invoice_id": inv.invoice_id,
                    "guest_name": inv.guest_name or (getattr(g_info, "full_name", "") if g_info else "Khách vãng lai"),
                    "guest_id": g_id or "",
                    "guest_phone": getattr(g_info, "phone", "") if g_info else "",
                    "guest_id_card": getattr(g_info, "id_card", "") if g_info else "",
                    "hotel_id": inv.hotel_id,
                    "hotel_name": getattr(h_info, "name", inv.hotel_id) if h_info else inv.hotel_id,
                    "hotel_address": getattr(h_info, "address", "") if h_info else "",
                    "hotel_city": getattr(h_info, "city", "") if h_info else "",
                    "room_number": getattr(b_info, "room_number", "") if b_info else "",
                    "check_in_date": check_in,
                    "check_out_date": check_out,
                    "nights": nights,
                    "issue_date": inv.issue_date,
                    "payment_method": inv.payment_method or "TIỀN MẶT",
                    "payment_status": pay_st,
                    "total_amount": tot_amt,
                    "deposit_amount": dep_val,
                    "remaining_amount": rem_val,
                    "booking_status": getattr(b_info, "status", "CONFIRMED") if b_info else "CONFIRMED",
                }
                result.append(item)

            result.sort(key=lambda x: (str(x.get("issue_date") or ""), str(x.get("invoice_id") or "")), reverse=True)
            _invoice_cache["data"] = result
            _invoice_cache["timestamp"] = now
            return result
        except Exception as e:
            print(f"❌ [Lỗi get_all_invoices]: {e}")
            return []
    else:
        # Mock mode
        result = []
        booking_map = {b["booking_id"]: b for b in _mock_bookings_by_guest}
        for inv in _mock_invoices:
            b_info = booking_map.get(inv.get("booking_id"))
            inv_dict = dict(inv)
            inv_dict["check_in_date"] = b_info.get("check_in_date") if b_info else None
            inv_dict["check_out_date"] = b_info.get("check_out_date") if b_info else None
            inv_dict["room_number"] = b_info.get("room_number", "") if b_info else ""
            inv_dict["nights"] = 1
            inv_dict["hotel_name"] = inv.get("hotel_id", "")
            tot_amt = float(inv.get("total_amount", 0))
            inv_dict["total_amount"] = tot_amt
            pay_st = (inv.get("payment_status") or "PAID").upper()
            inv_dict["payment_status"] = pay_st
            
            raw_dep = inv.get("deposit_amount")
            raw_rem = inv.get("remaining_amount")
            if raw_dep is not None:
                inv_dict["deposit_amount"] = float(raw_dep)
            else:
                inv_dict["deposit_amount"] = tot_amt if pay_st == "PAID" else (round(tot_amt/2, 0) if pay_st == "PARTIAL" else 0.0)
            
            if raw_rem is not None:
                inv_dict["remaining_amount"] = float(raw_rem)
            else:
                inv_dict["remaining_amount"] = 0.0 if pay_st == "PAID" else max(0.0, tot_amt - inv_dict["deposit_amount"])
                
            inv_dict["guest_phone"] = ""
            inv_dict["guest_id_card"] = ""
            result.append(inv_dict)
        _invoice_cache["data"] = result
        _invoice_cache["timestamp"] = now
        return result


def get_all_bookings(hotel_id=None, guest_id=None, check_in_date=None, q=None, limit=250):
    """
    Lấy danh sách tất cả các đơn đặt phòng, kết hợp thông tin chi tiết (tên khách, SĐT, tên khách sạn)
    và hỗ trợ bộ lọc theo chi nhánh, khách hàng, ngày nhận phòng và từ khóa.
    Có bộ nhớ đệm in-memory (TTL 30s) đảm bảo tốc độ phản hồi cực nhanh.
    """
    now = time.time()
    cached = _booking_cache.get("data")

    data = None
    if cached and (now - _booking_cache.get("timestamp", 0) < 30):
        data = cached
    else:
        session = get_session()
        if session:
            try:
                booking_rows = list(session.execute(
                    "SELECT guest_id, booking_id, hotel_id, room_number, check_in_date, check_out_date, status, total_amount FROM bookings_by_guest;"
                ))

                try:
                    guest_rows = list(session.execute("SELECT guest_id, full_name, phone, id_card FROM guests;"))
                    guest_map = {g.guest_id: g for g in guest_rows}
                except Exception:
                    guest_map = {}

                try:
                    hotel_rows = list(session.execute("SELECT hotel_id, name, city FROM hotels;"))
                    hotel_map = {h.hotel_id: h for h in hotel_rows}
                except Exception:
                    hotel_map = {}

                enriched = []
                for b in booking_rows:
                    g_info = guest_map.get(b.guest_id)
                    h_info = hotel_map.get(b.hotel_id)

                    check_in = b.check_in_date
                    check_out = b.check_out_date

                    nights = 1
                    if check_in and check_out:
                        try:
                            d_in = date(check_in.year, check_in.month, check_in.day) if hasattr(check_in, "year") else check_in
                            d_out = date(check_out.year, check_out.month, check_out.day) if hasattr(check_out, "year") else check_out
                            nights = max(1, (d_out - d_in).days)
                        except Exception:
                            nights = 1

                    item = {
                        "booking_id": b.booking_id,
                        "guest_id": b.guest_id,
                        "guest_name": getattr(g_info, "full_name", "") if g_info else (b.guest_id or "Khách vãng lai"),
                        "guest_phone": getattr(g_info, "phone", "") if g_info else "",
                        "guest_id_card": getattr(g_info, "id_card", "") if g_info else "",
                        "hotel_id": b.hotel_id,
                        "hotel_name": getattr(h_info, "name", b.hotel_id) if h_info else b.hotel_id,
                        "hotel_city": getattr(h_info, "city", "") if h_info else "",
                        "room_number": str(b.room_number or ""),
                        "check_in_date": check_in,
                        "check_out_date": check_out,
                        "nights": nights,
                        "status": b.status or "CONFIRMED",
                        "total_amount": float(b.total_amount) if b.total_amount is not None else 0.0,
                    }
                    enriched.append(item)

                # Sắp xếp theo ngày nhận phòng giảm dần, sau đó theo mã booking
                enriched.sort(key=lambda x: (str(x.get("check_in_date") or ""), str(x.get("booking_id") or "")), reverse=True)
                _booking_cache["data"] = enriched
                _booking_cache["timestamp"] = now
                data = enriched
            except Exception as e:
                print(f"❌ [Lỗi get_all_bookings]: {e}")
                data = []
        else:
            # Mock mode
            enriched = []
            for b in _mock_bookings_by_guest:
                b_dict = dict(b)
                b_dict["guest_name"] = b.get("guest_name", b.get("guest_id", "Khách vãng lai"))
                b_dict["guest_phone"] = b.get("guest_phone", "")
                b_dict["hotel_name"] = b.get("hotel_id", "")
                b_dict["nights"] = 1
                enriched.append(b_dict)
            enriched.sort(key=lambda x: (str(x.get("check_in_date") or ""), str(x.get("booking_id") or "")), reverse=True)
            _booking_cache["data"] = enriched
            _booking_cache["timestamp"] = now
            data = enriched

    # Áp dụng bộ lọc
    res = data or []
    if guest_id:
        res = [x for x in res if x.get("guest_id") == str(guest_id).strip()]
    if hotel_id and str(hotel_id).strip().upper() not in ("", "ALL"):
        res = [x for x in res if x.get("hotel_id") == str(hotel_id).strip()]
    if check_in_date:
        res = [x for x in res if str(x.get("check_in_date") or "") == str(check_in_date).strip()]
    if q:
        q_norm = str(q).strip().lower()
        res = [
            x for x in res
            if q_norm in str(x.get("booking_id", "")).lower()
            or q_norm in str(x.get("guest_name", "")).lower()
            or q_norm in str(x.get("guest_phone", "")).lower()
            or q_norm in str(x.get("room_number", "")).lower()
            or q_norm in str(x.get("hotel_name", "")).lower()
        ]

    return res[:limit]


def get_invoice_detail_enriched(booking_id):
    """
    Lấy thông tin chi tiết đầy đủ của một hóa đơn cho popup modal hoặc trang chi tiết:
    Gồm hóa đơn, khách hàng, khách sạn, số phòng, ngày check-in/check-out.
    """
    if not booking_id:
        return None
    b_id_str = str(booking_id).strip()

    # Tìm trong cache get_all_invoices trước nếu có
    if _invoice_cache["data"]:
        for item in _invoice_cache["data"]:
            if item.get("booking_id") == b_id_str:
                return dict(item)

    inv = get_invoice_by_booking(b_id_str)
    if not inv:
        return None

    session = get_session()
    booking_info = None
    if session:
        try:
            b_row = session.execute(
                "SELECT booking_id, check_in_date, check_out_date, room_number, hotel_id, guest_id, status FROM bookings_by_guest WHERE booking_id = ? ALLOW FILTERING;",
                (b_id_str,)
            ).one()
            booking_info = b_row
        except Exception:
            pass

    inv_id = getattr(inv, "invoice_id", None) or (inv.get("invoice_id") if isinstance(inv, dict) else "")
    g_name = getattr(inv, "guest_name", None) or (inv.get("guest_name") if isinstance(inv, dict) else "")
    h_id = getattr(inv, "hotel_id", None) or (inv.get("hotel_id") if isinstance(inv, dict) else "")
    issue_d = getattr(inv, "issue_date", None) or (inv.get("issue_date") if isinstance(inv, dict) else None)
    pay_m = getattr(inv, "payment_method", None) or (inv.get("payment_method") if isinstance(inv, dict) else "TIỀN MẶT")
    pay_s = getattr(inv, "payment_status", None) or (inv.get("payment_status") if isinstance(inv, dict) else "PAID")
    total_amt = getattr(inv, "total_amount", None) or (inv.get("total_amount") if isinstance(inv, dict) else 0)

    check_in = getattr(booking_info, "check_in_date", None) if booking_info else None
    check_out = getattr(booking_info, "check_out_date", None) if booking_info else None
    room_num = getattr(booking_info, "room_number", "") if booking_info else ""

    nights = 1
    if check_in and check_out:
        try:
            d_in = date(check_in.year, check_in.month, check_in.day) if hasattr(check_in, "year") else check_in
            d_out = date(check_out.year, check_out.month, check_out.day) if hasattr(check_out, "year") else check_out
            nights = max(1, (d_out - d_in).days)
        except Exception:
            nights = 1

    tot_amt = float(total_amt) if total_amt is not None else 0.0
    p_status = (pay_s or "PAID").strip().upper()
    raw_dep = getattr(inv, "deposit_amount", None) or (inv.get("deposit_amount") if isinstance(inv, dict) else None)
    raw_rem = getattr(inv, "remaining_amount", None) or (inv.get("remaining_amount") if isinstance(inv, dict) else None)

    if raw_dep is not None:
        dep_val = float(raw_dep)
    else:
        if p_status == "PAID":
            dep_val = tot_amt
        elif p_status == "PARTIAL":
            dep_val = round(tot_amt / 2.0, 0)
        else:
            dep_val = 0.0

    if raw_rem is not None:
        rem_val = float(raw_rem)
    else:
        if p_status == "PAID":
            rem_val = 0.0
        elif p_status == "PARTIAL":
            rem_val = max(0.0, tot_amt - dep_val)
        else:
            rem_val = tot_amt

    return {
        "booking_id": b_id_str,
        "invoice_id": str(inv_id),
        "guest_name": g_name or "Khách vãng lai",
        "guest_id": getattr(booking_info, "guest_id", "") if booking_info else "",
        "guest_phone": "",
        "guest_id_card": "",
        "hotel_id": str(h_id),
        "hotel_name": str(h_id),
        "room_number": str(room_num),
        "check_in_date": check_in,
        "check_out_date": check_out,
        "nights": nights,
        "issue_date": issue_d,
        "payment_method": pay_m,
        "payment_status": p_status,
        "total_amount": tot_amt,
        "deposit_amount": dep_val,
        "remaining_amount": rem_val,
    }


def get_active_booking_for_room(hotel_id, room_number):
    """
    [QUÂN - TASK QLKS-11]
    Tìm thông tin đặt phòng và khách hàng đang lưu trú tại một phòng cụ thể (hotel_id, room_number).
    Dùng để hiển thị danh tính khách hàng, liên hệ, thời gian lưu trú và hóa đơn trên trang chi tiết phòng.
    """
    if not hotel_id or not room_number:
        return None

    h_id = str(hotel_id).strip()
    r_num = str(room_number).strip()

    session = get_session()
    booking_match = None
    if session:
        try:
            rows = list(session.execute(
                "SELECT guest_id, booking_id, hotel_id, room_number, check_in_date, check_out_date, status, total_amount FROM bookings_by_guest;"
            ))
            matches = [
                r for r in rows
                if r.hotel_id == h_id and str(r.room_number) == r_num
            ]
            if matches:
                active_matches = [m for m in matches if m.status in ("CONFIRMED", "CHECKED_IN", "OCCUPIED")]
                if active_matches:
                    active_matches.sort(key=lambda x: str(x.check_in_date or ""), reverse=True)
                    booking_match = active_matches[0]
                else:
                    matches.sort(key=lambda x: str(x.check_in_date or ""), reverse=True)
                    booking_match = matches[0]
        except Exception as e:
            print(f"❌ [Lỗi get_active_booking_for_room]: {e}")
            return None
    else:
        # Mock mode
        matches = [
            b for b in _mock_bookings_by_guest
            if b.get("hotel_id") == h_id and str(b.get("room_number")) == r_num
        ]
        if matches:
            matches.sort(key=lambda x: str(x.get("check_in_date") or ""), reverse=True)
            booking_match = matches[0]

    if not booking_match:
        return None

    b_id = booking_match.booking_id if hasattr(booking_match, "booking_id") else booking_match.get("booking_id")
    g_id = booking_match.guest_id if hasattr(booking_match, "guest_id") else booking_match.get("guest_id")
    c_in = booking_match.check_in_date if hasattr(booking_match, "check_in_date") else booking_match.get("check_in_date")
    c_out = booking_match.check_out_date if hasattr(booking_match, "check_out_date") else booking_match.get("check_out_date")
    total_amt = booking_match.total_amount if hasattr(booking_match, "total_amount") else booking_match.get("total_amount", 0)
    booking_status = booking_match.status if hasattr(booking_match, "status") else booking_match.get("status", "CONFIRMED")

    guest_name = "Khách vãng lai"
    guest_phone = ""
    guest_id_card = ""
    guest_email = ""
    guest_address = ""

    if session and g_id:
        try:
            stmt = session.prepare("SELECT full_name, phone, id_card, email, address FROM guests WHERE guest_id = ?;")
            g_row = session.execute(stmt, (str(g_id),)).one()
            if g_row:
                guest_name = g_row.full_name or guest_name
                guest_phone = g_row.phone or ""
                guest_id_card = g_row.id_card or ""
                guest_email = g_row.email or ""
                guest_address = getattr(g_row, "address", "") or ""
        except Exception as ge:
            print(f"⚠️ [Lỗi lấy thông tin khách]: {ge}")

    # Lấy thông tin hóa đơn
    inv = get_invoice_by_booking(b_id) if b_id else None
    if inv:
        inv_g_name = getattr(inv, "guest_name", None) or (inv.get("guest_name") if isinstance(inv, dict) else "")
        if inv_g_name and guest_name == "Khách vãng lai":
            guest_name = inv_g_name
    inv_id = getattr(inv, "invoice_id", None) or (inv.get("invoice_id") if isinstance(inv, dict) else "")
    pay_status = getattr(inv, "payment_status", None) or (inv.get("payment_status") if isinstance(inv, dict) else "PAID")
    pay_method = getattr(inv, "payment_method", None) or (inv.get("payment_method") if isinstance(inv, dict) else "TIỀN MẶT")

    tot_val = float(total_amt) if total_amt is not None else 0.0
    pay_st_up = (pay_status or "PAID").strip().upper()
    raw_dep = getattr(inv, "deposit_amount", None) or (inv.get("deposit_amount") if isinstance(inv, dict) else None)
    raw_rem = getattr(inv, "remaining_amount", None) or (inv.get("remaining_amount") if isinstance(inv, dict) else None)

    if raw_dep is not None:
        dep_val = float(raw_dep)
    else:
        dep_val = tot_val if pay_st_up == "PAID" else (round(tot_val / 2.0, 0) if pay_st_up == "PARTIAL" else 0.0)

    if raw_rem is not None:
        rem_val = float(raw_rem)
    else:
        rem_val = 0.0 if pay_st_up == "PAID" else max(0.0, tot_val - dep_val)

    if pay_st_up == "PAID":
        status_text = "ĐÃ THANH TOÁN (100%)"
    elif pay_st_up == "PARTIAL":
        status_text = f"ĐÃ CỌC {dep_val:,.0f} đ (CÒN {rem_val:,.0f} đ)"
    else:
        status_text = "CHƯA THANH TOÁN"

    nights = 1
    if c_in and c_out:
        try:
            d_in = date(c_in.year, c_in.month, c_in.day) if hasattr(c_in, "year") else c_in
            d_out = date(c_out.year, c_out.month, c_out.day) if hasattr(c_out, "year") else c_out
            nights = max(1, (d_out - d_in).days)
        except Exception:
            nights = 1

    return {
        "booking_id": b_id,
        "invoice_id": inv_id,
        "guest_id": g_id,
        "guest_name": guest_name,
        "guest_phone": guest_phone,
        "guest_id_card": guest_id_card,
        "guest_email": guest_email,
        "guest_address": guest_address,
        "hotel_id": h_id,
        "room_number": r_num,
        "check_in_date": c_in,
        "check_out_date": c_out,
        "nights": nights,
        "total_amount": tot_val,
        "deposit_amount": dep_val,
        "remaining_amount": rem_val,
        "status": booking_status,
        "payment_status": pay_st_up,
        "payment_status_text": status_text,
        "payment_method": pay_method,
    }


def settle_invoice_payment(booking_id, invoice_id=None, amount_paid=None, payment_method=None):
    """
    [QUÂN - TÍNH NĂNG ĐẶT CỌC & THU TIỀN CÒN LẠI]
    Xác nhận thu nốt số tiền còn lại cho một đơn đặt phòng / hóa đơn.
    - Nếu amount_paid không truyền hoặc >= remaining_amount: thanh toán đủ 100% (chuyển sang PAID).
    - Cập nhật trực tiếp trên AstraDB bảng invoices_by_booking.
    - Invalidate cache để đồng bộ tức thì.
    """
    if not booking_id:
        return False, "Thiếu mã đặt phòng"

    b_id_str = str(booking_id).strip()
    inv = get_invoice_by_booking(b_id_str)
    if not inv:
        return False, f"Không tìm thấy hóa đơn cho mã đặt phòng {b_id_str}"

    inv_id = invoice_id or getattr(inv, "invoice_id", None) or (inv.get("invoice_id") if isinstance(inv, dict) else "")
    if not inv_id:
        return False, "Không tìm thấy mã hóa đơn"

    try:
        total_amt = Decimal(str(getattr(inv, "total_amount", 0) or (inv.get("total_amount", 0) if isinstance(inv, dict) else 0)))
    except Exception:
        total_amt = Decimal("0")

    raw_dep = getattr(inv, "deposit_amount", None) or (inv.get("deposit_amount") if isinstance(inv, dict) else None)
    raw_rem = getattr(inv, "remaining_amount", None) or (inv.get("remaining_amount") if isinstance(inv, dict) else None)
    current_status = getattr(inv, "payment_status", "PAID") or (inv.get("payment_status", "PAID") if isinstance(inv, dict) else "PAID")

    try:
        if raw_dep is not None:
            current_dep = Decimal(str(raw_dep))
        else:
            current_dep = total_amt if current_status == "PAID" else (total_amt / Decimal("2") if current_status == "PARTIAL" else Decimal("0"))
    except Exception:
        current_dep = Decimal("0")

    try:
        if raw_rem is not None:
            current_rem = Decimal(str(raw_rem))
        else:
            current_rem = Decimal("0") if current_status == "PAID" else max(Decimal("0"), total_amt - current_dep)
    except Exception:
        current_rem = max(Decimal("0"), total_amt - current_dep)

    # Tính toán số tiền thu thêm
    if amount_paid is None:
        add_amount = current_rem
    else:
        try:
            add_amount = Decimal(str(amount_paid))
        except Exception:
            add_amount = current_rem

    new_dep = min(total_amt, current_dep + add_amount) if total_amt > 0 else (current_dep + add_amount)
    new_rem = max(Decimal("0"), total_amt - new_dep)
    new_status = "PAID" if new_rem <= 0 else "PARTIAL"

    existing_method = getattr(inv, "payment_method", "TIỀN MẶT") or (inv.get("payment_method") if isinstance(inv, dict) else "TIỀN MẶT")
    new_method = str(payment_method).strip() if payment_method else existing_method

    session = get_session()
    if session:
        try:
            stmt = session.prepare("""
                UPDATE invoices_by_booking
                SET payment_status = ?,
                    deposit_amount = ?,
                    remaining_amount = ?,
                    payment_method = ?
                WHERE booking_id = ? AND invoice_id = ?;
            """)
            session.execute(stmt, (
                new_status,
                new_dep,
                new_rem,
                new_method,
                b_id_str,
                str(inv_id)
            ))
            print(f"✅ [AstraDB] Đã cập nhật thanh toán hóa đơn {inv_id}: Trạng thái = {new_status}, Đã cọc = {new_dep}, Còn lại = {new_rem}")
            invalidate_invoice_cache()
            invalidate_booking_cache()
            return True, {
                "booking_id": b_id_str,
                "invoice_id": str(inv_id),
                "payment_status": new_status,
                "deposit_amount": float(new_dep),
                "remaining_amount": float(new_rem),
                "total_amount": float(total_amt),
                "payment_method": new_method
            }
        except Exception as error:
            print(f"❌ [Lỗi settle_invoice_payment trên AstraDB]: {error}")
            return False, f"Lỗi cập nhật AstraDB: {error}"
    else:
        # Mock mode
        for m_inv in _mock_invoices:
            if m_inv.get("booking_id") == b_id_str:
                m_inv["payment_status"] = new_status
                m_inv["deposit_amount"] = new_dep
                m_inv["remaining_amount"] = new_rem
                m_inv["payment_method"] = new_method
                break
        invalidate_invoice_cache()
        invalidate_booking_cache()
        return True, {
            "booking_id": b_id_str,
            "invoice_id": str(inv_id),
            "payment_status": new_status,
            "deposit_amount": float(new_dep),
            "remaining_amount": float(new_rem),
            "total_amount": float(total_amt),
            "payment_method": new_method
        }




# --------------------------------------------------------------------
# 6. ĐÓNG BOOKING KHI KHÁCH TRẢ PHÒNG (KỂ CẢ TRẢ SỚM)
# --------------------------------------------------------------------

def complete_booking(guest_id, booking_id, hotel_id, check_in_date,
                     actual_check_out=None, planned_check_out=None):
    """
    [QUÂN] Đóng một booking khi khách đã trả phòng: status -> 'COMPLETED'.

    VÌ SAO CẦN HÀM NÀY: đổi trạng thái phòng về 'AVAILABLE' chỉ giải phóng PHÒNG,
    nó không nói gì về BOOKING. Nếu không đóng booking thì bản ghi đứng mãi ở
    'CONFIRMED', và hệ thống tự mâu thuẫn với chính nó:
      - trang chi tiết phòng: phòng trống;
      - get_active_booking_for_room(): vẫn coi khách đó đang lưu trú, vì hàm này
        lọc theo status in ('CONFIRMED', 'CHECKED_IN', 'OCCUPIED');
      - lịch sử đặt phòng của khách: không bao giờ có dòng nào "đã trả phòng",
        dù templates/bookings.html đã có sẵn badge cho 'COMPLETED'.

    TRẢ PHÒNG SỚM: nếu actual_check_out sớm hơn ngày dự kiến thì ghi lại ngày trả
    THỰC TẾ vào check_out_date của bookings_by_guest, để lịch sử lưu trú và các
    thống kê dựa trên số đêm (ADR) không tính những đêm khách không thực ở.

    Ghi vào cả 2 bảng bằng BATCH, cùng nguyên tắc denormalization như
    create_booking_batch (Q5): bookings_by_guest + bookings_by_hotel_date.

    CHÍNH SÁCH TIỀN (đã chốt): trả phòng sớm KHÔNG giảm giá, KHÔNG hoàn tiền —
    khách vẫn trả đủ số đêm đã đặt. Vì vậy hàm này cố tình không đụng tới hóa đơn:
    total_amount, deposit_amount, remaining_amount giữ nguyên như lúc đặt.
    nights_stayed / nights_billed trả ra chỉ để GHI NHẬN và hiển thị, không dùng
    để tính lại tiền.

    Trả về (True, payload) hoặc (False, "lý do").
    """
    if not guest_id or not booking_id:
        return False, "Thiếu guest_id hoặc booking_id để đóng booking."

    def _as_date(value):
        if isinstance(value, str) and value.strip():
            try:
                return datetime.strptime(value.strip(), "%Y-%m-%d").date()
            except ValueError:
                return None
        if hasattr(value, "date") and not isinstance(value, date):
            try:
                return value.date()
            except (TypeError, ValueError, OverflowError):
                return None
        return value if isinstance(value, date) else None

    in_date = _as_date(check_in_date)
    if not in_date:
        return False, "Ngày nhận phòng không hợp lệ, không xác định được bản ghi cần đóng."

    planned_out = _as_date(planned_check_out)
    actual_out = _as_date(actual_check_out) or date.today()

    # Không cho ghi ngày trả sớm hơn cả ngày nhận phòng
    if actual_out < in_date:
        actual_out = in_date

    # Chỉ ghi đè check_out_date khi khách trả SỚM hơn dự kiến. Ở quá hạn là một
    # nghiệp vụ khác (phụ phí), không xử lý ở đây nên giữ nguyên ngày dự kiến.
    is_early = bool(planned_out and actual_out < planned_out)
    new_check_out = actual_out if is_early else (planned_out or actual_out)

    nights_billed = (planned_out - in_date).days if planned_out else None
    nights_stayed = (actual_out - in_date).days

    b_id = str(booking_id)
    session = get_session()

    if session:
        from cassandra.query import BatchStatement

        batch = BatchStatement()

        stmt_guest = session.prepare("""
            UPDATE bookings_by_guest
            SET status = ?, check_out_date = ?
            WHERE guest_id = ? AND booking_id = ?;
        """)
        batch.add(stmt_guest, ("COMPLETED", new_check_out, guest_id, b_id))

        # bookings_by_hotel_date không có cột check_out_date -> chỉ đồng bộ status.
        # Khóa chính là ((hotel_id, check_in_date), booking_id) nên bắt buộc phải có
        # đủ hotel_id và check_in_date mới update được đúng partition.
        if hotel_id:
            stmt_hotel_date = session.prepare("""
                UPDATE bookings_by_hotel_date
                SET status = ?
                WHERE hotel_id = ? AND check_in_date = ? AND booking_id = ?;
            """)
            batch.add(stmt_hotel_date, ("COMPLETED", hotel_id, in_date, b_id))

        try:
            session.execute(batch)
        except Exception as error:
            print(f"❌ [Trả phòng] Lỗi đóng booking {b_id}: {error}")
            return False, f"Không thể đóng booking: {error}"
        print(f"✅ [AstraDB] Đã đóng booking {b_id} (COMPLETED), ngày trả: {new_check_out}")
    else:
        touched = False
        for rec in _mock_bookings_by_guest:
            if rec.get("booking_id") == b_id and rec.get("guest_id") == guest_id:
                rec["status"] = "COMPLETED"
                rec["check_out_date"] = new_check_out
                touched = True
                break
        for rec in _mock_bookings_by_hotel_date:
            if rec.get("booking_id") == b_id:
                rec["status"] = "COMPLETED"
                break
        if not touched:
            return False, f"Không tìm thấy booking {b_id} của khách {guest_id}."
        print(f"🔶 [MOCK MODE] Đã đóng booking {b_id} (COMPLETED)")

    invalidate_booking_cache()
    invalidate_invoice_cache()

    return True, {
        "booking_id": b_id,
        "guest_id": guest_id,
        "hotel_id": hotel_id,
        "status": "COMPLETED",
        "check_in_date": in_date.isoformat(),
        "check_out_date": new_check_out.isoformat() if new_check_out else None,
        "is_early_checkout": is_early,
        "nights_billed": nights_billed,
        "nights_stayed": nights_stayed,
    }
