# ====================================================================
# SERVICES: QUẢN LÝ PHÒNG (MỞ RỘNG NOS-10) — CHI TIẾT, SỬA, TRẠNG THÁI
# PHỤ TRÁCH: NHƯ
#
# File riêng, KHÔNG chỉnh sửa services/hotel_service.py của Định.
# Dùng chung bảng rooms_by_hotel (đã ALTER thêm cột status/capacity/bed_type/
# description trong cql/schema.cql) nhưng đọc/ghi đầy đủ cột hơn để phục vụ
# trang chi tiết + sửa phòng.
# ====================================================================

from decimal import Decimal, InvalidOperation
from types import SimpleNamespace

from database.db import get_session

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


def get_rooms_by_hotel(hotel_id):
    """Danh sách phòng đầy đủ thông tin (kèm sức chứa, loại giường, trạng thái) theo khách sạn."""
    session = get_session()
    if not session:
        return []
    try:
        stmt = session.prepare("""
            SELECT hotel_id, room_number, room_type, price_per_night, is_available,
                   status, capacity, bed_type, description, current_guest_name, current_booking_id
            FROM rooms_by_hotel
            WHERE hotel_id = ?;
        """)
        rows = session.execute(stmt, (hotel_id,))
        return [_build_room(row) for row in rows]
    except Exception as error:
        print(f"❌ [Phòng] Lỗi lấy danh sách phòng: {error}")
        return []


def get_room(hotel_id, room_number):
    """Thông tin chi tiết 1 phòng, trả None nếu không tồn tại."""
    session = get_session()
    if not session:
        return None
    try:
        stmt = session.prepare("""
            SELECT hotel_id, room_number, room_type, price_per_night, is_available,
                   status, capacity, bed_type, description, current_guest_name, current_booking_id
            FROM rooms_by_hotel
            WHERE hotel_id = ? AND room_number = ?;
        """)
        rows = list(session.execute(stmt, (hotel_id, room_number)))
        if not rows:
            return None
        return _build_room(rows[0])
    except Exception as error:
        print(f"❌ [Phòng] Lỗi lấy chi tiết phòng: {error}")
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
    session = get_session()
    if not session:
        return False
    try:
        price = price_per_night if isinstance(price_per_night, Decimal) else Decimal(str(price_per_night))
        cap = int(capacity)
        stmt = session.prepare("""
            INSERT INTO rooms_by_hotel (
                hotel_id, room_number, room_type, price_per_night,
                is_available, status, capacity, bed_type, description
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """)
        session.execute(stmt, (
            hotel_id, room_number, room_type, price,
            True, "AVAILABLE", cap, bed_type, description or "",
        ))
        return True
    except (InvalidOperation, ValueError, TypeError) as error:
        print(f"❌ [Phòng] Dữ liệu không hợp lệ khi tạo phòng: {error}")
        return False
    except Exception as error:
        print(f"❌ [Phòng] Lỗi tạo phòng: {error}")
        return False


def update_room(hotel_id, room_number, room_type, price_per_night, capacity, bed_type, description):
    """
    Sửa thông tin phòng — CHẶN hoàn toàn nếu phòng đang ở trạng thái Đang cho thuê
    (tránh thay đổi giá/loại phòng trong lúc khách đang lưu trú).
    Trả về (True, None) nếu thành công, (False, lý_do) nếu thất bại.
    """
    current = get_room(hotel_id, room_number)
    if not current:
        return False, "Không tìm thấy phòng."
    if current.status == "OCCUPIED":
        return False, "Phòng đang có khách thuê, không thể sửa thông tin. Vui lòng đợi khách trả phòng."

    session = get_session()
    if not session:
        return False, "Không thể kết nối AstraDB."
    try:
        price = price_per_night if isinstance(price_per_night, Decimal) else Decimal(str(price_per_night))
        cap = int(capacity)
        stmt = session.prepare("""
            UPDATE rooms_by_hotel
            SET room_type = ?, price_per_night = ?, capacity = ?, bed_type = ?, description = ?
            WHERE hotel_id = ? AND room_number = ?;
        """)
        session.execute(stmt, (room_type, price, cap, bed_type, description or "", hotel_id, room_number))
        return True, None
    except (InvalidOperation, ValueError, TypeError) as error:
        return False, f"Dữ liệu không hợp lệ: {error}"
    except Exception as error:
        print(f"❌ [Phòng] Lỗi sửa phòng: {error}")
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

    current = get_room(hotel_id, room_number)
    if not current:
        return False, "Không tìm thấy phòng."

    if new_status == current.status:
        return False, f'Phòng đã ở trạng thái "{ROOM_STATUS_LABELS[new_status]}" rồi.'

    if new_status not in ALLOWED_TRANSITIONS.get(current.status, set()):
        return False, (
            f'Không thể chuyển từ "{ROOM_STATUS_LABELS[current.status]}" '
            f'sang "{ROOM_STATUS_LABELS[new_status]}" trực tiếp.'
        )

    if new_status != "OCCUPIED":
        guest_name = None
        booking_id = None

    session = get_session()
    if not session:
        return False, "Không thể kết nối AstraDB."
    try:
        is_available = new_status == "AVAILABLE"
        stmt = session.prepare("""
            UPDATE rooms_by_hotel
            SET status = ?, is_available = ?, current_guest_name = ?, current_booking_id = ?
            WHERE hotel_id = ? AND room_number = ?;
        """)
        session.execute(stmt, (new_status, is_available, guest_name, booking_id, hotel_id, room_number))
        return True, None
    except Exception as error:
        print(f"❌ [Phòng] Lỗi đổi trạng thái phòng: {error}")
        return False, "Lỗi kết nối AstraDB, vui lòng thử lại."
