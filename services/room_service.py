# ====================================================================
# SERVICES: QUẢN LÝ PHÒNG (MỞ RỘNG NOS-10) — CHI TIẾT, SỬA, TRẠNG THÁI
# PHỤ TRÁCH: NHƯ
#
# File riêng, KHÔNG chỉnh sửa services/hotel_service.py của Định.
# Dùng chung bảng rooms_by_hotel (đã ALTER thêm cột status/capacity/bed_type/
# description trong cql/schema.cql) nhưng đọc/ghi đầy đủ cột hơn để phục vụ
# trang chi tiết + sửa phòng.
# ====================================================================

import time
from decimal import Decimal, InvalidOperation
from types import SimpleNamespace

from database.db import get_session
from services import room_stats_service

# Trạng thái phòng: value lưu trong Cassandra (text) -> nhãn hiển thị tiếng Việt
ROOM_STATUSES = [
    ("AVAILABLE", "Đang trống"),
    ("OCCUPIED", "Đang cho thuê"),
    ("MAINTENANCE", "Đang bảo trì"),
]
ROOM_STATUS_LABELS = dict(ROOM_STATUSES)
VALID_STATUSES = {value for value, _ in ROOM_STATUSES}

# Ma trận chuyển trạng thái hợp lệ: {trạng thái hiện tại: {các trạng thái được phép chuyển tới}}
# - Đang cho thuê chỉ được trả về Đang trống (không được nhảy thẳng sang Bảo trì).
# - Đang bảo trì chỉ được mở lại về Đang trống (không được nhận khách trực tiếp từ bảo trì).
ALLOWED_TRANSITIONS = {
    "AVAILABLE": {"OCCUPIED", "MAINTENANCE"},
    "OCCUPIED": {"AVAILABLE"},
    "MAINTENANCE": {"AVAILABLE"},
}

# Hành động THỦ CÔNG mà nhân viên được phép bấm trên trang chi tiết phòng.
# LƯU Ý QUAN TRỌNG: "Đang cho thuê" (AVAILABLE -> OCCUPIED) KHÔNG nằm trong danh
# sách này — nhân viên không được tự tay đánh dấu phòng đang cho thuê, vì trạng
# thái này phải là HỆ QUẢ TỰ ĐỘNG của một booking thật (khách nhận phòng), không
# phải lựa chọn thủ công. Transition này vẫn được phép ở ALLOWED_TRANSITIONS phía
# trên và change_room_status() vẫn xử lý được — để module Đặt phòng (booking_service.py,
# phụ trách bởi Quân) có thể tự động gọi change_room_status(hotel_id, room_number,
# 'OCCUPIED') ngay sau khi tạo booking thành công, chứ không lộ ra UI cho lễ tân.
MANUAL_STATUS_ACTIONS = {
    "AVAILABLE": {"MAINTENANCE"},
    "OCCUPIED": {"AVAILABLE"},
    "MAINTENANCE": {"AVAILABLE"},
}

# Nhãn hành động hiển thị cho từng cặp chuyển trạng thái (dùng cho nút bấm ở trang chi tiết)
STATUS_ACTION_LABELS = {
    ("AVAILABLE", "OCCUPIED"): "Đánh dấu đang cho thuê",
    ("AVAILABLE", "MAINTENANCE"): "Chuyển sang bảo trì",
    ("OCCUPIED", "AVAILABLE"): "Trả phòng (chuyển về Đang trống)",
    ("MAINTENANCE", "AVAILABLE"): "Mở lại phòng (Đang trống)",
}


def get_status_actions(current_status):
    """
    Danh sách (status_value, nhãn nút) các hành động THỦ CÔNG nhân viên được bấm
    từ trạng thái hiện tại — dùng MANUAL_STATUS_ACTIONS (không phải ALLOWED_TRANSITIONS)
    nên "Đánh dấu đang cho thuê" sẽ không bao giờ xuất hiện trên UI.
    """
    return [
        (target, STATUS_ACTION_LABELS.get((current_status, target), f"Chuyển sang {ROOM_STATUS_LABELS[target]}"))
        for target in MANUAL_STATUS_ACTIONS.get(current_status, set())
    ]


def _build_room(row):
    """
    Chuyển Row (namedtuple BẤT BIẾN do cassandra-driver trả về) thành SimpleNamespace
    có thể gán lại thuộc tính, đồng thời suy ra status cho các phòng cũ (tạo trước khi
    có cột status) từ is_available. Gán trực tiếp row.status = ... trên Row thật sẽ
    lỗi "can't set attribute" vì namedtuple không cho sửa thuộc tính.
    """
    room = SimpleNamespace(
        hotel_id=row.hotel_id,
        room_number=row.room_number,
        room_type=row.room_type,
        price_per_night=row.price_per_night,
        is_available=row.is_available,
        status=getattr(row, "status", None),
        capacity=getattr(row, "capacity", None),
        bed_type=getattr(row, "bed_type", None),
        description=getattr(row, "description", None),
        current_guest_name=getattr(row, "current_guest_name", None),
        current_booking_id=getattr(row, "current_booking_id", None),
    )
    if room.status not in VALID_STATUSES:
        room.status = "AVAILABLE" if room.is_available else "OCCUPIED"
    return room


# Mock store cho phòng khi chạy ở chế độ offline/chưa cấu hình AstraDB
_mock_rooms = {
    "H001": [
        SimpleNamespace(hotel_id="H001", room_number="101", room_type="Deluxe Twin", price_per_night=Decimal("1350000"), is_available=True, status="AVAILABLE", capacity=2, bed_type="2 Single Beds", description="Phòng tiêu chuẩn 2 giường đơn view thành phố"),
        SimpleNamespace(hotel_id="H001", room_number="102", room_type="Deluxe King", price_per_night=Decimal("1450000"), is_available=True, status="AVAILABLE", capacity=2, bed_type="1 King Bed", description="Phòng tiêu chuẩn 1 giường lớn view biển"),
        SimpleNamespace(hotel_id="H001", room_number="201", room_type="Executive Suite", price_per_night=Decimal("2600000"), is_available=True, status="AVAILABLE", capacity=3, bed_type="1 King Bed + 1 Sofa", description="Phòng cao cấp kèm phòng khách riêng"),
        SimpleNamespace(hotel_id="H001", room_number="301", room_type="Grand Suite", price_per_night=Decimal("3800000"), is_available=False, status="MAINTENANCE", capacity=4, bed_type="2 King Beds", description="Phòng Tổng thống đang bảo trì hệ thống điều hòa"),
    ],
    "H002": [
        SimpleNamespace(hotel_id="H002", room_number="401", room_type="Deluxe Ocean", price_per_night=Decimal("1650000"), is_available=True, status="AVAILABLE", capacity=2, bed_type="1 King Bed", description="View trực diện vịnh Nha Trang"),
        SimpleNamespace(hotel_id="H002", room_number="501", room_type="Executive Suite", price_per_night=Decimal("2800000"), is_available=True, status="AVAILABLE", capacity=3, bed_type="1 King Bed + Sofa", description="Phòng Suite ban công rộng"),
    ],
    "H003": [
        SimpleNamespace(hotel_id="H003", room_number="105", room_type="Superior King", price_per_night=Decimal("950000"), is_available=True, status="AVAILABLE", capacity=2, bed_type="1 King Bed", description="Phòng tiêu chuẩn Hà Nội"),
        SimpleNamespace(hotel_id="H003", room_number="205", room_type="Deluxe King", price_per_night=Decimal("1250000"), is_available=True, status="AVAILABLE", capacity=2, bed_type="1 King Bed", description="Phòng Deluxe view hồ Linh Đàm"),
    ],
    "H004": [
        SimpleNamespace(hotel_id="H004", room_number="601", room_type="Deluxe King", price_per_night=Decimal("1600000"), is_available=True, status="AVAILABLE", capacity=2, bed_type="1 King Bed", description="Phòng trung tâm Sài Gòn"),
    ],
}


def get_rooms_by_hotel(hotel_id):
    """Danh sách phòng đầy đủ thông tin (kèm sức chứa, loại giường, trạng thái) theo khách sạn."""
    if not hotel_id:
        return []
    hotel_id_str = str(hotel_id).strip()
    session = get_session()
    if not session:
        return _mock_rooms.get(hotel_id_str, [])
    try:
        stmt = session.prepare("""
            SELECT hotel_id, room_number, room_type, price_per_night, is_available,
                   status, capacity, bed_type, description, current_guest_name, current_booking_id
            FROM rooms_by_hotel
            WHERE hotel_id = ?;
        """)
        rows = session.execute(stmt, (hotel_id_str,))
        return [_build_room(row) for row in rows]
    except Exception as error:
        # Fallback nếu bảng chưa ALTER cột status/capacity/bed_type/description
        try:
            stmt_basic = session.prepare("""
                SELECT hotel_id, room_number, room_type, price_per_night, is_available
                FROM rooms_by_hotel
                WHERE hotel_id = ?;
            """)
            rows = session.execute(stmt_basic, (hotel_id_str,))
            return [_build_room(row) for row in rows]
        except Exception as err2:
            print(f"❌ [Phòng] Lỗi lấy danh sách phòng: {err2}")
            return _mock_rooms.get(hotel_id_str, [])


_all_rooms_cache = {"data": None, "timestamp": 0}


def invalidate_rooms_cache():
    """Hủy cache danh sách phòng khi có phát sinh thay đổi trạng thái/tạo phòng."""
    _all_rooms_cache["data"] = None
    _all_rooms_cache["timestamp"] = 0


def get_all_rooms(limit=400):
    """Lấy danh sách tất cả các phòng kèm cache in-memory 30s."""
    now = time.time()
    if _all_rooms_cache.get("data") and (now - _all_rooms_cache.get("timestamp", 0) < 30):
        return _all_rooms_cache["data"][:limit]

    session = get_session()
    if not session:
        all_mock = []
        for rooms in _mock_rooms.values():
            all_mock.extend(rooms)
        return all_mock[:limit]

    try:
        stmt = session.prepare("""
            SELECT hotel_id, room_number, room_type, price_per_night, is_available,
                   status, capacity, bed_type, description
            FROM rooms_by_hotel;
        """)
        rows = session.execute(stmt)
        res = [_build_room(row) for row in rows]
        _all_rooms_cache["data"] = res
        _all_rooms_cache["timestamp"] = now
        return res[:limit]
    except Exception as e:
        print(f"❌ [Lỗi get_all_rooms]: {e}")
        return []


def get_filtered_rooms(hotel_id=None, room_type=None, bed_type=None, capacity=None, 
                       amenity=None, price_range=None, status="AVAILABLE", limit=200,
                       hotel_amenities_map=None):
    """
    Bộ lọc tra cứu phòng trống chuẩn nghiệp vụ tiếp tân khách sạn:
    - hotel_id: Lọc theo chi nhánh khách sạn
    - room_type: Lọc theo loại phòng (Deluxe, Suite...)
    - bed_type: Lọc theo loại giường (King, Twin, Single, Double)
    - capacity: Lọc theo sức chứa khách (1, 2, 4 người)
    - amenity: Tìm kiếm tiện nghi/mô tả (bồn tắm, view biển, panorama, ban công...)
    - price_range: 'under_1m', '1m_2m', 'above_2m'
    - status: 'AVAILABLE' (mặc định), 'OCCUPIED', 'MAINTENANCE', hoặc 'ALL'
    - hotel_amenities_map: Dict mapping hotel_id -> set/list các tiện ích của khách sạn đó
    """
    if hotel_id and str(hotel_id).strip().upper() not in ("", "ALL"):
        rooms = get_rooms_by_hotel(hotel_id)
    else:
        rooms = get_all_rooms(limit=limit * 2)

    res = []
    for r in rooms:
        # Lọc trạng thái
        if status and status != "ALL":
            if r.status != status:
                continue

        # Lọc loại phòng
        if room_type and room_type != "ALL":
            if (r.room_type or "").strip().lower() != room_type.strip().lower():
                continue

        # Lọc loại giường
        if bed_type and bed_type != "ALL":
            if (r.bed_type or "").strip().lower() != bed_type.strip().lower():
                continue

        # Lọc sức chứa
        if capacity and capacity != "ALL":
            try:
                if int(r.capacity or 2) < int(capacity):
                    continue
            except Exception:
                pass

        # Lọc tiện nghi / tiện ích khách sạn / mô tả phòng
        if amenity and amenity != "ALL":
            kw = amenity.strip().lower()
            desc = (r.description or "").lower()
            rtype = (r.room_type or "").lower()
            btype = (r.bed_type or "").lower()
            rnum = str(r.room_number or "").lower()

            hotel_matched = False
            if hotel_amenities_map and r.hotel_id in hotel_amenities_map:
                hotel_ams = [str(a).lower() for a in (hotel_amenities_map[r.hotel_id] or [])]
                hotel_matched = any(kw == a or kw in a or a in kw for a in hotel_ams)

            room_matched = (kw in desc or kw in rtype or kw in btype or kw in rnum)

            if not hotel_matched and not room_matched:
                continue

        # Lọc khoảng giá
        if price_range and price_range != "ALL":
            try:
                price = float(r.price_per_night or 0)
                if price_range == "under_1m" and price >= 1000000:
                    continue
                elif price_range == "1m_2m" and (price < 1000000 or price > 2000000):
                    continue
                elif price_range == "above_2m" and price <= 2000000:
                    continue
            except Exception:
                pass

        res.append(r)

    return res[:limit]


def get_room(hotel_id, room_number):
    """Thông tin chi tiết 1 phòng, trả None nếu không tồn tại."""
    if not hotel_id or not room_number:
        return None
    hotel_id_str = str(hotel_id).strip()
    room_number_str = str(room_number).strip()
    session = get_session()
    if not session:
        for r in _mock_rooms.get(hotel_id_str, []):
            if str(r.room_number) == room_number_str:
                return r
        return None
    try:
        stmt = session.prepare("""
            SELECT hotel_id, room_number, room_type, price_per_night, is_available,
                   status, capacity, bed_type, description, current_guest_name, current_booking_id
            FROM rooms_by_hotel
            WHERE hotel_id = ? AND room_number = ?;
        """)
        rows = list(session.execute(stmt, (hotel_id_str, room_number_str)))
        if not rows:
            return None
        return _build_room(rows[0])
    except Exception as error:
        # Fallback nếu bảng chưa có cột mở rộng
        try:
            stmt_basic = session.prepare("""
                SELECT hotel_id, room_number, room_type, price_per_night, is_available
                FROM rooms_by_hotel
                WHERE hotel_id = ? AND room_number = ?;
            """)
            rows = list(session.execute(stmt_basic, (hotel_id_str, room_number_str)))
            if not rows:
                return None
            return _build_room(rows[0])
        except Exception as err2:
            print(f"❌ [Phòng] Lỗi lấy chi tiết phòng: {err2}")
            for r in _mock_rooms.get(hotel_id_str, []):
                if str(r.room_number) == room_number_str:
                    return r
            return None


def is_room_bookable(hotel_id, room_number):
    """
    Kiểm tra phòng có đang ở trạng thái sẵn sàng nhận đặt (AVAILABLE) hay không.

    Dùng cho module Đặt phòng (booking_service.py/booking_routes.py, phụ trách bởi
    Quân) gọi TRƯỚC KHI tạo booking mới — chặn đặt phòng đang bảo trì hoặc đang có
    khách khác thuê (double-booking), mà không cần biết các giá trị status nội bộ.

    Trả về:
      - True  : phòng đang trống, đặt được.
      - False : phòng tồn tại nhưng đang OCCUPIED/MAINTENANCE, không đặt được.
      - None  : không tìm thấy phòng (hotel_id/room_number sai) — nên coi là lỗi
                "phòng không tồn tại" chứ không phải "phòng đang bận".
    """
    room = get_room(hotel_id, room_number)
    if room is None:
        return None
    return room.status == "AVAILABLE"


def create_room(hotel_id, room_number, room_type, price_per_night, capacity, bed_type, description=""):
    """Thêm phòng mới, mặc định trạng thái Đang trống (AVAILABLE)."""
    hotel_id_str = str(hotel_id).strip()
    room_number_str = str(room_number).strip()
    try:
        price = price_per_night if isinstance(price_per_night, Decimal) else Decimal(str(price_per_night))
        cap = int(capacity) if capacity else 2
    except (InvalidOperation, ValueError, TypeError) as error:
        print(f"❌ [Phòng] Dữ liệu không hợp lệ khi tạo phòng: {error}")
        return False

    session = get_session()
    if not session:
        # Mock fallback
        if hotel_id_str not in _mock_rooms:
            _mock_rooms[hotel_id_str] = []
        new_r = SimpleNamespace(
            hotel_id=hotel_id_str,
            room_number=room_number_str,
            room_type=room_type,
            price_per_night=price,
            is_available=True,
            status="AVAILABLE",
            capacity=cap,
            bed_type=bed_type or "1 Double Bed",
            description=description or "",
        )
        _mock_rooms[hotel_id_str].append(new_r)
        invalidate_rooms_cache()
        return True

    try:
        stmt = session.prepare("""
            INSERT INTO rooms_by_hotel (
                hotel_id, room_number, room_type, price_per_night,
                is_available, status, capacity, bed_type, description
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """)
        session.execute(stmt, (
            hotel_id_str, room_number_str, room_type, price,
            True, "AVAILABLE", cap, bed_type or "1 Double Bed", description or "",
        ))
        invalidate_rooms_cache()
        room_stats_service.record_room_created(session, hotel_id_str, "AVAILABLE")
        return True
    except Exception as error:
        # Fallback nếu bảng chưa có cột mở rộng
        try:
            stmt_basic = session.prepare("""
                INSERT INTO rooms_by_hotel (
                    hotel_id, room_number, room_type, price_per_night, is_available
                ) VALUES (?, ?, ?, ?, ?);
            """)
            session.execute(stmt_basic, (
                hotel_id_str, room_number_str, room_type, price, True
            ))
            invalidate_rooms_cache()
            room_stats_service.record_room_created(session, hotel_id_str, "AVAILABLE")
            return True
        except Exception as err2:
            print(f"❌ [Phòng] Lỗi tạo phòng: {err2}")
            return False


def update_room(hotel_id, room_number, room_type, price_per_night, capacity, bed_type, description):
    """
    Sửa thông tin phòng — CHẶN hoàn toàn nếu phòng đang ở trạng thái Đang cho thuê
    (tránh thay đổi giá/loại phòng trong lúc khách đang lưu trú).
    Trả về (True, None) nếu thành công, (False, lý_do) nếu thất bại.
    """
    hotel_id_str = str(hotel_id).strip()
    room_number_str = str(room_number).strip()
    current = get_room(hotel_id_str, room_number_str)
    if not current:
        return False, "Không tìm thấy phòng."
    if current.status == "OCCUPIED":
        return False, "Phòng đang có khách thuê, không thể sửa thông tin. Vui lòng đợi khách trả phòng."

    try:
        price = price_per_night if isinstance(price_per_night, Decimal) else Decimal(str(price_per_night))
        cap = int(capacity) if capacity else 2
    except (InvalidOperation, ValueError, TypeError) as error:
        return False, f"Dữ liệu không hợp lệ: {error}"

    session = get_session()
    if not session:
        # Mock fallback
        current.room_type = room_type
        current.price_per_night = price
        current.capacity = cap
        current.bed_type = bed_type
        current.description = description or ""
        invalidate_rooms_cache()
        return True, None

    try:
        stmt = session.prepare("""
            UPDATE rooms_by_hotel
            SET room_type = ?, price_per_night = ?, capacity = ?, bed_type = ?, description = ?
            WHERE hotel_id = ? AND room_number = ?;
        """)
        session.execute(stmt, (room_type, price, cap, bed_type, description or "", hotel_id_str, room_number_str))
        invalidate_rooms_cache()
        return True, None
    except Exception as error:
        try:
            stmt_basic = session.prepare("""
                UPDATE rooms_by_hotel
                SET room_type = ?, price_per_night = ?
                WHERE hotel_id = ? AND room_number = ?;
            """)
            session.execute(stmt_basic, (room_type, price, hotel_id_str, room_number_str))
            invalidate_rooms_cache()
            return True, None
        except Exception as err2:
            print(f"❌ [Phòng] Lỗi sửa phòng: {err2}")
            return False, "Lỗi kết nối AstraDB, vui lòng thử lại."


def change_room_status(hotel_id, room_number, new_status, guest_name=None, booking_id=None):
    """
    Chuyển trạng thái phòng theo đúng ma trận ALLOWED_TRANSITIONS.

    guest_name/booking_id: CHỈ có ý nghĩa khi new_status='OCCUPIED' — dùng để lưu lại
    "ai đang thuê phòng này" cho trang chi tiết hiển thị (module Đặt phòng của Quân
    truyền vào khi gọi tự động sau khi tạo booking thành công). Với mọi trạng thái
    khác (AVAILABLE, MAINTENANCE), 2 trường này luôn được xóa về NULL — đặc biệt là
    khi "trả phòng" (OCCUPIED -> AVAILABLE), thông tin khách cũ phải mất đi ngay.

    Trả về (True, None) nếu thành công, (False, lý_do) nếu bị chặn.
    """
    if new_status not in VALID_STATUSES:
        return False, "Trạng thái không hợp lệ."

    hotel_id_str = str(hotel_id).strip()
    room_number_str = str(room_number).strip()
    current = get_room(hotel_id_str, room_number_str)
    if not current:
        return False, f"Không tìm thấy phòng số {room_number_str} tại khách sạn này."

    if new_status == current.status:
        return False, f'Phòng {room_number_str} đã ở trạng thái "{ROOM_STATUS_LABELS[new_status]}" rồi.'

    if new_status not in ALLOWED_TRANSITIONS.get(current.status, set()):
        return False, (
            f'Không thể chuyển từ "{ROOM_STATUS_LABELS[current.status]}" '
            f'sang "{ROOM_STATUS_LABELS[new_status]}" trực tiếp.'
        )

    if new_status != "OCCUPIED":
        guest_name = None
        booking_id = None

    # Gán TRƯỚC khi rẽ nhánh session: cả nhánh mock lẫn 2 câu UPDATE bên dưới đều
    # dùng biến này. Trước đó nó bị thiếu nên mọi lần đổi trạng thái đều nổ
    # UnboundLocalError, rơi vào except rồi báo sai thành "Lỗi kết nối AstraDB".
    is_available = new_status == "AVAILABLE"

    session = get_session()
    if not session:
        # Mock fallback
        current.status = new_status
        current.is_available = is_available
        print(f"🔶 [MOCK] Đã chuyển phòng {hotel_id_str}-{room_number_str} sang {new_status} (is_available={is_available})")
        return True, None

    try:
        stmt = session.prepare("""
            UPDATE rooms_by_hotel
            SET status = ?, is_available = ?, current_guest_name = ?, current_booking_id = ?
            WHERE hotel_id = ? AND room_number = ?;
        """)
        session.execute(stmt, (new_status, is_available, guest_name, booking_id, hotel_id_str, room_number_str))
        invalidate_rooms_cache()
        # Ghi counter SAU khi UPDATE phòng thành công (counter không được chung BATCH
        # với lệnh thường). Lỗi counter chỉ cảnh báo, không làm hỏng việc đổi trạng thái.
        room_stats_service.record_status_change(session, hotel_id_str, current.status, new_status)
        return True, None
    except Exception as error:
        # Fallback cho database cũ chưa có cột status / current_guest_name
        print(f"⚠️ [Phòng] UPDATE đầy đủ thất bại, thử lại bản tối giản: {error}")
        try:
            stmt_basic = session.prepare("""
                UPDATE rooms_by_hotel SET is_available = ?
                WHERE hotel_id = ? AND room_number = ?;
            """)
            session.execute(stmt_basic, (is_available, hotel_id_str, room_number_str))
            invalidate_rooms_cache()
            room_stats_service.record_status_change(session, hotel_id_str, current.status, new_status)
            print(f"✅ [AstraDB Fallback] Đã cập nhật is_available={is_available} cho phòng {room_number_str}")
            return True, None
        except Exception as err2:
            print(f"❌ [Phòng] Lỗi đổi trạng thái phòng: {err2}")
            # Nói đúng bản chất: không phải lúc nào cũng là lỗi kết nối. Trước đây
            # message này che mất một UnboundLocalError suốt nhiều giờ.
            return False, f"Không cập nhật được trạng thái phòng: {err2}"
