"""
Bù 2 cột current_guest_name / current_booking_id cho các phòng đang OCCUPIED.

VÌ SAO CẦN: trang chi tiết phòng đọc "ai đang thuê" từ 2 cột denormalize trên
rooms_by_hotel, do booking_routes ghi vào lúc đặt phòng thành công. Nhưng bộ dữ
liệu hiện tại được tạo bằng seed script — nó set status='OCCUPIED' trực tiếp mà
không đi qua luồng đặt phòng, nên 2 cột đó còn NULL. Kết quả là mọi phòng đang
thuê đều hiện "Chưa rõ — trạng thái này chưa được module Đặt phòng cập nhật".

Script này đọc bookings_by_guest, tìm booking đang hoạt động ứng với từng phòng
rồi ghi tên khách + mã booking vào. Chạy lại nhiều lần không sao: chỉ ghi vào
phòng nào còn thiếu.

    python scripts/backfill_room_current_guest.py            # xem trước, không ghi
    python scripts/backfill_room_current_guest.py --apply    # ghi thật
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import get_session

ACTIVE_STATUSES = ("CONFIRMED", "CHECKED_IN", "OCCUPIED")


def main():
    apply_changes = "--apply" in sys.argv

    session = get_session()
    if not session:
        print("❌ Không kết nối được AstraDB. Kiểm tra .env.")
        return 1

    rooms = list(session.execute(
        "SELECT hotel_id, room_number, status, current_guest_name FROM rooms_by_hotel;"
    ))
    occupied_missing = [
        r for r in rooms
        if r.status == "OCCUPIED" and not r.current_guest_name
    ]

    if not occupied_missing:
        print("✅ Không có phòng OCCUPIED nào thiếu thông tin khách. Không cần làm gì.")
        return 0

    guest_names = {
        g.guest_id: g.full_name
        for g in session.execute("SELECT guest_id, full_name FROM guests;")
    }

    # Gom booking đang hoạt động theo (hotel_id, room_number)
    by_room = {}
    for b in session.execute(
        "SELECT guest_id, booking_id, hotel_id, room_number, status, check_in_date "
        "FROM bookings_by_guest;"
    ):
        if b.status in ACTIVE_STATUSES:
            by_room.setdefault((b.hotel_id, str(b.room_number)), []).append(b)

    stmt = session.prepare("""
        UPDATE rooms_by_hotel
        SET current_guest_name = ?, current_booking_id = ?
        WHERE hotel_id = ? AND room_number = ?;
    """)

    updated = 0
    orphans = []

    for room in occupied_missing:
        key = (room.hotel_id, str(room.room_number))
        candidates = by_room.get(key, [])
        if not candidates:
            orphans.append(key)
            continue

        # Nhiều booking cùng phòng thì lấy lần nhận phòng gần nhất
        booking = sorted(candidates, key=lambda x: str(x.check_in_date or ""), reverse=True)[0]
        name = guest_names.get(booking.guest_id) or booking.guest_id

        if apply_changes:
            session.execute(stmt, (name, booking.booking_id, room.hotel_id, str(room.room_number)))
        updated += 1
        if updated <= 10:
            print(f"   {room.hotel_id}/{room.room_number}  <-  {name} ({booking.booking_id})")

    if updated > 10:
        print(f"   ... và {updated - 10} phòng nữa")

    print()
    print(f"{'✅ Đã ghi' if apply_changes else '🔎 Sẽ ghi (chưa ghi)'}: {updated} phòng")

    if orphans:
        print()
        print(f"⚠️  {len(orphans)} phòng đang OCCUPIED nhưng KHÔNG có booking nào đang hoạt động:")
        for hotel_id, room_number in orphans:
            print(f"   {hotel_id}/{room_number}")
        print("   Mấy phòng này nên chuyển về AVAILABLE, hoặc tạo booking cho đúng thực tế.")
        print("   Script không tự đoán, để người quyết.")

    if not apply_changes:
        print()
        print("Chạy lại với --apply để ghi thật.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
