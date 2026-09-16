# ====================================================================
# SERVICES: QUẢN LÝ ĐẶT PHÒNG & HÓA ĐƠN
# PHỤ TRÁCH: QUÂN
# ====================================================================

import uuid
from datetime import datetime, date
from decimal import Decimal
from database.db import get_session

# Kho lưu trữ bộ nhớ tạm (Mock store khi chưa nạp chứng chỉ AstraDB)
_mock_bookings_by_guest = []
_mock_bookings_by_hotel_date = []
_mock_invoices = []

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

    return booking_id


# --------------------------------------------------------------------
# 2. TRA CỨU ĐẶT PHÒNG THEO KHÁCH HÀNG (QUERY Q2 TRONG PDF)
# --------------------------------------------------------------------

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
            return list(rows)
        except Exception as error:
            print(f"❌ [Lỗi truy vấn Q2 - bookings_by_guest]: {error}")
            return []

    # Mock fallback
    return [b for b in _mock_bookings_by_guest if b["guest_id"] == guest_id_str]


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
            return list(rows)
        except Exception as error:
            print(f"❌ [Lỗi truy vấn Q3 - bookings_by_hotel_date]: {error}")
            return []

    # Mock fallback
    return [
        b for b in _mock_bookings_by_hotel_date 
        if b["hotel_id"] == hotel_id_str and str(b["check_in_date"]) == str(in_date)
    ]


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
                       issue_date, payment_method, payment_status, total_amount
                FROM invoices_by_booking
                WHERE booking_id = ?;
            """)
            rows = session.execute(stmt, (booking_id_str,))
            return rows.one() if hasattr(rows, "one") else (rows[0] if rows else None)
        except Exception as error:
            print(f"❌ [Lỗi truy vấn Q4 - invoices_by_booking]: {error}")
            return None

    # Mock fallback
    for inv in _mock_invoices:
        if inv.get("booking_id") == booking_id_str:
            return inv
    return None


def create_invoice(booking_id, invoice_id=None, guest_name="", hotel_id="", 
                   issue_date=None, payment_method="CASH", payment_status="PAID", total_amount=0):
    """
    [QUÂN - TASK QLKS-10] - Tạo hóa đơn thanh toán cho mã đặt phòng (bảng invoices_by_booking).

    Theo mô hình dữ liệu Cassandra:
      - Partition Key: booking_id
      - Clustering Key: invoice_id

    Câu lệnh CQL:
      INSERT INTO invoices_by_booking (
          booking_id, invoice_id, guest_name, hotel_id,
          issue_date, payment_method, payment_status, total_amount
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);

    Trả về invoice_id nếu thành công, None nếu thất bại.
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

    guest_name_str = str(guest_name).strip() if guest_name else ""
    hotel_id_str = str(hotel_id).strip() if hotel_id else ""
    method_str = str(payment_method).strip() if payment_method else "CASH"
    status_str = str(payment_status).strip() if payment_status else "PAID"

    session = get_session()
    if session:
        try:
            stmt = session.prepare("""
                INSERT INTO invoices_by_booking (
                    booking_id, invoice_id, guest_name, hotel_id,
                    issue_date, payment_method, payment_status, total_amount
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """)
            session.execute(stmt, (
                booking_id_str,
                invoice_id,
                guest_name_str,
                hotel_id_str,
                in_date,
                method_str,
                status_str,
                amount
            ))
            print(f"✅ [AstraDB] Đã tạo hóa đơn Q4 thành công! Mã HĐ: {invoice_id} cho Booking: {booking_id_str}")
            return invoice_id
        except Exception as error:
            print(f"❌ [Lỗi tạo hóa đơn Q4 - invoices_by_booking]: {error}")
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
            "total_amount": amount
        }
        _mock_invoices.append(record)
        print(f"🔶 [MOCK MODE] Đã lưu hóa đơn tạm. Mã HĐ: {invoice_id}")
        return invoice_id
