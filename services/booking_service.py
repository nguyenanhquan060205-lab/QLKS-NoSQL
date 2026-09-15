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
    [QUÂN - TASK QLKS-09] - Query Q2 trong PDF:
    - Câu lệnh CQL:
      SELECT * FROM bookings_by_guest WHERE guest_id = ?;
    - Trả về toàn bộ lịch sử đặt phòng của khách hàng.
    """
    session = get_session()
    if session:
        query = "SELECT * FROM bookings_by_guest WHERE guest_id = %s;"
        rows = session.execute(query, (guest_id,))
        return list(rows)
    return [b for b in _mock_bookings_by_guest if b["guest_id"] == guest_id]


# --------------------------------------------------------------------
# 3. TRA CỨU ĐẶT PHÒNG THEO KHÁCH SẠN VÀ NGÀY (QUERY Q3 TRONG PDF)
# --------------------------------------------------------------------

def get_bookings_by_hotel_date(hotel_id, check_in_date):
    """
    [QUÂN - TASK QLKS-09] - Query Q3 trong PDF:
    - Câu lệnh CQL:
      SELECT * FROM bookings_by_hotel_date 
      WHERE hotel_id = ? AND check_in_date = ?;
    - Trả về danh sách khách check-in tại khách sạn trong ngày chỉ định.
    """
    if isinstance(check_in_date, str):
        in_date = datetime.strptime(check_in_date.strip(), "%Y-%m-%d").date()
    else:
        in_date = check_in_date

    session = get_session()
    if session:
        query = "SELECT * FROM bookings_by_hotel_date WHERE hotel_id = %s AND check_in_date = %s;"
        rows = session.execute(query, (hotel_id, in_date))
        return list(rows)
    return [
        b for b in _mock_bookings_by_hotel_date 
        if b["hotel_id"] == hotel_id and str(b["check_in_date"]) == str(in_date)
    ]


# --------------------------------------------------------------------
# 4. QUẢN LÝ HÓA ĐƠN THEO MÃ ĐẶT PHÒNG (QUERY Q4 TRONG PDF)
# --------------------------------------------------------------------

def get_invoice_by_booking(booking_id):
    """
    TODO (Quân) - Query Q4 trong PDF:
    - Câu lệnh CQL:
      SELECT * FROM invoices_by_booking WHERE booking_id = ?;
    - Trả về thông tin hóa đơn gắn liền với mã đặt phòng.
    """
    session = get_session()
    if not session:
        return None

    # query = "SELECT * FROM invoices_by_booking WHERE booking_id = %s;"
    # rows = session.execute(query, [booking_id])
    # return rows.one()
    return None


def create_invoice(booking_id, invoice_id, guest_name, hotel_id, 
                   issue_date, payment_method, payment_status, total_amount):
    """
    TODO (Quân):
    - Câu lệnh CQL:
      INSERT INTO invoices_by_booking (booking_id, invoice_id, guest_name, hotel_id,
                                       issue_date, payment_method, payment_status, total_amount)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?);
    """
    session = get_session()
    if not session:
        return False

    # Viết code tạo hóa đơn tại đây
    pass
