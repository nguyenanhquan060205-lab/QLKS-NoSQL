# ====================================================================
# SERVICES: QUẢN LÝ KHÁCH SẠN, PHÒNG, KHÁCH HÀNG
# PHỤ TRÁCH: ĐỊNH
# ====================================================================

from decimal import Decimal

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
    Lấy danh sách phòng của một khách sạn theo Query Q1.

    hotel_id là partition key của bảng rooms_by_hotel, vì vậy truy vấn chỉ
    đọc đúng partition của khách sạn được chọn và không quét toàn bảng.
    """
    session = get_session()
    if not session:
        return []

    try:
        query = session.prepare("""
            SELECT hotel_id, room_number, room_type,
                   price_per_night, is_available
            FROM rooms_by_hotel
            WHERE hotel_id = ?;
        """)
        rows = session.execute(query, (hotel_id,))
        return list(rows)
    except Exception as error:
        print(f"Error fetching rooms by hotel: {error}")
        return []


def create_room(hotel_id, room_number, room_type, price_per_night, is_available=True):
    """
    Thêm một phòng vào partition của khách sạn bằng prepared statement.

    price_per_night được chuẩn hóa thành Decimal để khớp kiểu decimal và
    is_available được chuẩn hóa thành boolean để khớp schema Cassandra.
    """
    session = get_session()
    if not session:
        return False

    try:
        normalized_price = (
            price_per_night
            if isinstance(price_per_night, Decimal)
            else Decimal(str(price_per_night))
        )
        if isinstance(is_available, str):
            normalized_availability = is_available.strip().lower() in {
                "1",
                "true",
                "yes",
                "on",
            }
        else:
            normalized_availability = bool(is_available)

        query = session.prepare("""
            INSERT INTO rooms_by_hotel (
                hotel_id, room_number, room_type,
                price_per_night, is_available
            ) VALUES (?, ?, ?, ?, ?);
        """)
        session.execute(query, (
            hotel_id,
            room_number,
            room_type,
            normalized_price,
            normalized_availability,
        ))
        return True
    except Exception as error:
        print(f"Error creating room: {error}")
        return False


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
