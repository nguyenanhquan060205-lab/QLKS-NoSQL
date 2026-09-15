# ====================================================================
# SERVICES: QUẢN LÝ KHÁCH SẠN, PHÒNG, KHÁCH HÀNG
# PHỤ TRÁCH: ĐỊNH
# ====================================================================

from database.db import get_session

# --------------------------------------------------------------------
# 1. QUẢN LÝ KHÁCH SẠN (Bảng: hotels)
# --------------------------------------------------------------------

def get_all_hotels():
    """
    Lấy toàn bộ khách sạn từ bảng hotels.

    Bảng hotels dùng hotel_id làm partition key. Truy vấn toàn bảng phù hợp
    với phạm vi dữ liệu nhỏ của đồ án; nếu dữ liệu lớn cần thiết kế thêm bảng
    chuyên phục vụ access pattern liệt kê khách sạn.
    """
    session = get_session()
    if not session:
        return []

    try:
        query = """
            SELECT hotel_id, name, phone, address, city, country, amenities
            FROM hotels;
        """
        rows = session.execute(query)
        return list(rows)
    except Exception as error:
        print(f"Error fetching hotels: {error}")
        return []


def create_hotel(hotel_id, name, phone, address, city, country, amenities):
    """
    Thêm một khách sạn vào bảng hotels bằng prepared statement.

    amenities được chuẩn hóa thành set để tương thích với kiểu set<text>
    trong Cassandra. Hàm trả về True khi ghi thành công, ngược lại trả False.
    """
    session = get_session()
    if not session:
        return False

    try:
        query = session.prepare("""
            INSERT INTO hotels (
                hotel_id, name, phone, address, city, country, amenities
            ) VALUES (?, ?, ?, ?, ?, ?, ?);
        """)

        if isinstance(amenities, str):
            amenities = {
                amenity.strip()
                for amenity in amenities.split(",")
                if amenity.strip()
            }
        else:
            amenities = set(amenities or [])

        session.execute(query, (
            hotel_id,
            name,
            phone,
            address,
            city,
            country,
            amenities,
        ))
        return True
    except Exception as error:
        print(f"Error creating hotel: {error}")
        return False


# --------------------------------------------------------------------
# 2. QUẢN LÝ PHÒNG (Bảng: rooms_by_hotel - QUERY Q1 TRONG PDF)
# --------------------------------------------------------------------

def get_rooms_by_hotel(hotel_id):
    """
    TODO (Định) - Query Q1 trong PDF:
    - Câu lệnh CQL:
      SELECT * FROM rooms_by_hotel WHERE hotel_id = ?;
    - Trả về danh sách phòng của khách sạn được chọn.
    """
    session = get_session()
    if not session:
        return []

    # query = "SELECT * FROM rooms_by_hotel WHERE hotel_id = %s;"
    # rows = session.execute(query, [hotel_id])
    # return list(rows)
    return []


def create_room(hotel_id, room_number, room_type, price_per_night, is_available=True):
    """
    TODO (Định):
    - Câu lệnh CQL:
      INSERT INTO rooms_by_hotel (hotel_id, room_number, room_type, price_per_night, is_available)
      VALUES (?, ?, ?, ?, ?);
    """
    session = get_session()
    if not session:
        return False

    # Viết code insert phòng tại đây
    pass


# --------------------------------------------------------------------
# 3. QUẢN LÝ KHÁCH HÀNG (Bảng: guests)
# --------------------------------------------------------------------

def get_all_guests():
    """
    Lấy toàn bộ khách hàng từ bảng guests.

    Tương tự hotels, đây là truy vấn toàn bảng dành cho dữ liệu đồ án nhỏ.
    """
    session = get_session()
    if not session:
        return []

    try:
        query = """
            SELECT guest_id, full_name, email, phone, id_card
            FROM guests;
        """
        rows = session.execute(query)
        return list(rows)
    except Exception as error:
        print(f"Error fetching guests: {error}")
        return []


def create_guest(guest_id, full_name, email, phone, id_card):
    """
    Thêm một khách hàng vào bảng guests bằng prepared statement.

    Hàm trả về True khi ghi thành công, ngược lại trả False.
    """
    session = get_session()
    if not session:
        return False

    try:
        query = session.prepare("""
            INSERT INTO guests (
                guest_id, full_name, email, phone, id_card
            ) VALUES (?, ?, ?, ?, ?);
        """)
        session.execute(query, (
            guest_id,
            full_name,
            email,
            phone,
            id_card,
        ))
        return True
    except Exception as error:
        print(f"Error creating guest: {error}")
        return False
