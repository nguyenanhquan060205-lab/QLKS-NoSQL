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
    TODO (Định):
    - Câu lệnh CQL: SELECT * FROM hotels;
    - Trả về danh sách các khách sạn.
    """
    session = get_session()
    if not session:
        return []
    
    # query = "SELECT * FROM hotels;"
    # rows = session.execute(query)
    # return list(rows)
    return []


def create_hotel(hotel_id, name, phone, address, city, country, amenities):
    """
    TODO (Định):
    - Câu lệnh CQL:
      INSERT INTO hotels (hotel_id, name, phone, address, city, country, amenities)
      VALUES (?, ?, ?, ?, ?, ?, ?);
    - Lưu ý: amenities là kiểu dữ liệu set<text> trong Cassandra.
    """
    session = get_session()
    if not session:
        return False
    
    # Viết code insert tại đây
    pass


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
    TODO (Định):
    - Câu lệnh CQL: SELECT * FROM guests;
    - Trả về danh sách khách hàng.
    """
    session = get_session()
    if not session:
        return []

    # query = "SELECT * FROM guests;"
    # rows = session.execute(query)
    # return list(rows)
    return []


def create_guest(guest_id, full_name, email, phone, id_card):
    """
    TODO (Định):
    - Câu lệnh CQL:
      INSERT INTO guests (guest_id, full_name, email, phone, id_card)
      VALUES (?, ?, ?, ?, ?);
    """
    session = get_session()
    if not session:
        return False

    # Viết code insert khách hàng tại đây
    pass
