# ====================================================================
# SERVICES: QUẢN LÝ ĐẶT PHÒNG & HÓA ĐƠN
# PHỤ TRÁCH: QUÂN
# ====================================================================

from database.db import get_session

# --------------------------------------------------------------------
# 1. ĐẶT PHÒNG VỚI BATCH INSERT (TRỌNG TÂM CASSANDRA - QUERY Q5)
# --------------------------------------------------------------------

def create_booking_batch(guest_id, guest_name, hotel_id, room_number, 
                         check_in_date, check_out_date, status, total_amount):
    """
    TODO (Quân) - QUAN TRỌNG:
    Theo nguyên lý thiết kế Cassandra trong PDF (Mục 3.3 & Query Q5):
    Dữ liệu đặt phòng được phi chuẩn hóa (denormalize) lưu ở 2 bảng:
      - bookings_by_guest (để phục vụ tra cứu theo khách)
      - bookings_by_hotel_date (để phục vụ tra cứu theo khách sạn & ngày)

    Nhiệm vụ: Sử dụng BATCH STATEMENT để ghi đồng thời vào cả 2 bảng:
      BEGIN BATCH
        INSERT INTO bookings_by_guest (...) VALUES (...);
        INSERT INTO bookings_by_hotel_date (...) VALUES (...);
      APPLY BATCH;
    """
    session = get_session()
    if not session:
        return False

    # Viết code Batch Statement tại đây
    pass


# --------------------------------------------------------------------
# 2. TRA CỨU ĐẶT PHÒNG THEO KHÁCH HÀNG (QUERY Q2 TRONG PDF)
# --------------------------------------------------------------------

def get_bookings_by_guest(guest_id):
    """
    TODO (Quân) - Query Q2 trong PDF:
    - Câu lệnh CQL:
      SELECT * FROM bookings_by_guest WHERE guest_id = ?;
    - Trả về toàn bộ lịch sử đặt phòng của khách hàng.
    """
    session = get_session()
    if not session:
        return []

    # query = "SELECT * FROM bookings_by_guest WHERE guest_id = %s;"
    # rows = session.execute(query, [guest_id])
    # return list(rows)
    return []


# --------------------------------------------------------------------
# 3. TRA CỨU ĐẶT PHÒNG THEO KHÁCH SẠN VÀ NGÀY (QUERY Q3 TRONG PDF)
# --------------------------------------------------------------------

def get_bookings_by_hotel_date(hotel_id, check_in_date):
    """
    TODO (Quân) - Query Q3 trong PDF:
    - Câu lệnh CQL:
      SELECT * FROM bookings_by_hotel_date 
      WHERE hotel_id = ? AND check_in_date = ?;
    - Trả về danh sách khách check-in tại khách sạn trong ngày chỉ định.
    """
    session = get_session()
    if not session:
        return []

    # query = "SELECT * FROM bookings_by_hotel_date WHERE hotel_id = %s AND check_in_date = %s;"
    # rows = session.execute(query, [hotel_id, check_in_date])
    # return list(rows)
    return []


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
