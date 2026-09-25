"""
Đồng bộ bảng counter room_status_counts_by_hotel với dữ liệu thật trong rooms_by_hotel.

Khi nào cần chạy:
  - Lần đầu, sau khi tạo bảng counter (nạp số liệu ban đầu cho các phòng có sẵn).
  - Sau khi chạy các script seed / dọn dữ liệu ghi thẳng vào rooms_by_hotel
    (không đi qua room_service nên counter không được cập nhật).
  - Khi nghi ngờ số phòng trên dashboard bị lệch.

    python scripts/sync_room_status_counts.py           # đồng bộ (tạo bảng nếu chưa có)
    python scripts/sync_room_status_counts.py --check   # chỉ báo lệch, không ghi gì

Chạy nhiều lần vẫn an toàn: mỗi lần chỉ cộng/trừ đúng phần chênh lệch.
Exit code 0 = khớp (hoặc đã đồng bộ xong), 1 = --check phát hiện lệch / lỗi kết nối.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db import get_session
from services import room_stats_service

CREATE_TABLE_CQL = """
    CREATE TABLE IF NOT EXISTS room_status_counts_by_hotel (
        hotel_id text,
        total_rooms counter,
        available_rooms counter,
        occupied_rooms counter,
        maintenance_rooms counter,
        PRIMARY KEY (hotel_id)
    );
"""


def main():
    check_only = "--check" in sys.argv
    session = get_session()
    if not session:
        print("❌ Không kết nối được AstraDB. Kiểm tra .env (và database có đang hibernate không).")
        return 1

    if not check_only:
        session.execute(CREATE_TABLE_CQL)

    drifted, orphans = room_stats_service.reconcile(session, apply=not check_only)

    if not drifted and not orphans:
        print("✅ Counter khớp hoàn toàn với rooms_by_hotel.")
        return 0

    verb = "Lệch" if check_only else "Đã chỉnh"
    for hid, delta in sorted(drifted):
        changes = ", ".join(f"{k} {v:+d}" for k, v in delta.items() if v)
        print(f"   {verb} {hid}: {changes}")
    if orphans:
        print(f"   {'Thừa' if check_only else 'Đã xóa'} counter của khách sạn không còn tồn tại: {orphans}")

    if check_only:
        print(f"⚠️ {len(drifted)} khách sạn lệch, {len(orphans)} counter thừa. "
              "Chạy lại không có --check để đồng bộ.")
        return 1

    print(f"✅ Đã đồng bộ {len(drifted)} khách sạn, xóa {len(orphans)} counter thừa.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
