# ====================================================================
# SERVICES: QUẢN LÝ KHÁCH SẠN, PHÒNG, KHÁCH HÀNG
# PHỤ TRÁCH: ĐỊNH
# ====================================================================

from decimal import Decimal
from types import SimpleNamespace

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


def get_hotel_by_id(hotel_id):
    """
    Lấy thông tin một khách sạn theo hotel_id (Partition Key).
    """
    session = get_session()
    if not session or not hotel_id:
        return None

    try:
        query = session.prepare("""
            SELECT hotel_id, name, phone, address, city, country, amenities
            FROM hotels
            WHERE hotel_id = ?;
        """)
        rows = session.execute(query, (hotel_id,))
        row_list = list(rows)
        return row_list[0] if row_list else None
    except Exception as error:
        print(f"Error fetching hotel {hotel_id}: {error}")
        return None


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


def update_hotel(hotel_id, name, phone, address, city, country, amenities):
    """
    Cập nhật thông tin khách sạn trong bảng hotels theo hotel_id.
    """
    session = get_session()
    if not session or not hotel_id:
        return False

    try:
        if isinstance(amenities, str):
            amenities = {
                amenity.strip()
                for amenity in amenities.split(",")
                if amenity.strip()
            }
        else:
            amenities = set(amenities or [])

        query = session.prepare("""
            UPDATE hotels
            SET name = ?, phone = ?, address = ?, city = ?, country = ?, amenities = ?
            WHERE hotel_id = ?;
        """)
        session.execute(query, (
            name,
            phone,
            address,
            city,
            country,
            amenities,
            hotel_id,
        ))
        return True
    except Exception as error:
        print(f"Error updating hotel {hotel_id}: {error}")
        return False


def delete_hotel(hotel_id):
    """
    Xóa khách sạn và dọn dẹp các phòng thuộc khách sạn trong bảng rooms_by_hotel.
    """
    session = get_session()
    if not session or not hotel_id:
        return False

    try:
        # Xóa các phòng thuộc khách sạn trong partition hotel_id
        try:
            delete_rooms_query = session.prepare("""
                DELETE FROM rooms_by_hotel WHERE hotel_id = ?;
            """)
            session.execute(delete_rooms_query, (hotel_id,))
        except Exception as e:
            print(f"Warning: could not delete rooms for hotel {hotel_id}: {e}")

        # Xóa bản ghi khách sạn
        query = session.prepare("""
            DELETE FROM hotels WHERE hotel_id = ?;
        """)
        session.execute(query, (hotel_id,))
        return True
    except Exception as error:
        print(f"Error deleting hotel {hotel_id}: {error}")
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
    Lấy toàn bộ khách hàng từ bảng guests kèm địa chỉ cư trú (address).
    Hỗ trợ fallback an toàn nếu cột address chưa tồn tại trên AstraDB.
    """
    session = get_session()
    if not session:
        return []

    try:
        try:
            query = """
                SELECT guest_id, full_name, email, phone, id_card, address
                FROM guests;
            """
            rows = session.execute(query)
            return list(rows)
        except Exception:
            # Fallback nếu bảng guests chưa chạy ALTER TABLE ADD address
            query = """
                SELECT guest_id, full_name, email, phone, id_card
                FROM guests;
            """
            rows = session.execute(query)
            result = []
            for r in rows:
                if not hasattr(r, "address"):
                    result.append(SimpleNamespace(
                        guest_id=r.guest_id,
                        full_name=r.full_name,
                        email=r.email,
                        phone=r.phone,
                        id_card=r.id_card,
                        address="",
                    ))
                else:
                    result.append(r)
            return result
    except Exception as error:
        print(f"Error fetching guests: {error}")
        return []


def get_guest_by_id(guest_id):
    """
    Lấy thông tin chi tiết một khách hàng theo guest_id.
    """
    session = get_session()
    if not session or not guest_id:
        return None

    try:
        try:
            query = session.prepare("""
                SELECT guest_id, full_name, email, phone, id_card, address
                FROM guests
                WHERE guest_id = ?;
            """)
            rows = session.execute(query, (guest_id,))
        except Exception:
            query = session.prepare("""
                SELECT guest_id, full_name, email, phone, id_card
                FROM guests
                WHERE guest_id = ?;
            """)
            rows = session.execute(query, (guest_id,))

        row_list = list(rows)
        if not row_list:
            return None
        row = row_list[0]
        if not hasattr(row, "address"):
            return SimpleNamespace(
                guest_id=row.guest_id,
                full_name=row.full_name,
                email=row.email,
                phone=row.phone,
                id_card=row.id_card,
                address="",
            )
        return row
    except Exception as error:
        print(f"Error fetching guest {guest_id}: {error}")
        return None


def create_guest(guest_id, full_name, email, phone, id_card, address=""):
    """
    Thêm một khách hàng vào bảng guests bằng prepared statement.
    """
    session = get_session()
    if not session:
        return False

    try:
        try:
            query = session.prepare("""
                INSERT INTO guests (
                    guest_id, full_name, email, phone, id_card, address
                ) VALUES (?, ?, ?, ?, ?, ?);
            """)
            session.execute(query, (
                guest_id,
                full_name,
                email,
                phone,
                id_card,
                address or "",
            ))
        except Exception:
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


def update_guest(guest_id, full_name, email, phone, id_card, address=""):
    """
    Cập nhật thông tin khách hàng trong bảng guests.
    """
    session = get_session()
    if not session or not guest_id:
        return False

    try:
        try:
            query = session.prepare("""
                UPDATE guests
                SET full_name = ?, email = ?, phone = ?, id_card = ?, address = ?
                WHERE guest_id = ?;
            """)
            session.execute(query, (
                full_name,
                email,
                phone,
                id_card,
                address or "",
                guest_id,
            ))
        except Exception:
            query = session.prepare("""
                UPDATE guests
                SET full_name = ?, email = ?, phone = ?, id_card = ?
                WHERE guest_id = ?;
            """)
            session.execute(query, (
                full_name,
                email,
                phone,
                id_card,
                guest_id,
            ))
        return True
    except Exception as error:
        print(f"Error updating guest {guest_id}: {error}")
        return False


def delete_guest(guest_id):
    """
    Xóa khách hàng theo guest_id.
    """
    session = get_session()
    if not session or not guest_id:
        return False

    try:
        query = session.prepare("""
            DELETE FROM guests WHERE guest_id = ?;
        """)
        session.execute(query, (guest_id,))
        return True
    except Exception as error:
        print(f"Error deleting guest {guest_id}: {error}")
        return False
