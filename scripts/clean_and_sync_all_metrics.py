import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.db import get_session


def clean_and_sync():
    print("=" * 60)
    print("🧹 DỌN DẸP DỮ LIỆU RÁC TEST & ĐỒNG BỘ 100% CSDL ASTRADB")
    print("=" * 60)

    session = get_session()
    if not session:
        print("❌ Không thể kết nối AstraDB!")
        return

    # 1. Xóa các phòng rác từ integration test cũ (H001, H_QLKS05_TEST_*)
    orphan_rooms = [
        ('H001', '101'),
        ('H_QLKS05_TEST_B', 'B901'),
        ('H_QLKS05_TEST_A', 'A501'),
        ('H_QLKS05_TEST_A', 'A502'),
    ]
    for hid, rnum in orphan_rooms:
        try:
            session.execute(
                "DELETE FROM rooms_by_hotel WHERE hotel_id = %s AND room_number = %s;",
                (hid, rnum)
            )
            print(f"🗑️ Đã xóa phòng rác test: KS {hid}, P.{rnum}")
        except Exception as e:
            print(f"⚠️ Không thể xóa KS {hid}, P.{rnum}: {e}")

    # 2. Đảm bảo tất cả các phòng thuộc chuỗi Mường Thanh (MT_*) đều có status và is_available chuẩn
    mt_rooms = list(session.execute("SELECT hotel_id, room_number, status, is_available FROM rooms_by_hotel;"))
    fixed_rooms = 0
    for r in mt_rooms:
        st = getattr(r, 'status', None)
        is_av = bool(getattr(r, 'is_available', True))
        if not st:
            new_st = 'AVAILABLE' if is_av else 'OCCUPIED'
            session.execute(
                "UPDATE rooms_by_hotel SET status = %s WHERE hotel_id = %s AND room_number = %s;",
                (new_st, r.hotel_id, r.room_number)
            )
            fixed_rooms += 1
    if fixed_rooms > 0:
        print(f"✅ Đã chuẩn hóa status cho {fixed_rooms} phòng thiếu trường trạng thái.")
    else:
        print("✅ Tất cả phòng Mường Thanh đã có status đầy đủ.")

    # 3. Xóa các hóa đơn rác test (BK_INV_TEST_*)
    inv_rows = list(session.execute("SELECT booking_id FROM invoices_by_booking;"))
    test_invoices = [r.booking_id for r in inv_rows if "TEST" in str(r.booking_id)]
    deleted_invs = 0
    for b_id in test_invoices:
        try:
            session.execute(
                "DELETE FROM invoices_by_booking WHERE booking_id = %s;",
                (b_id,)
            )
            deleted_invs += 1
        except Exception as e:
            print(f"⚠️ Lỗi xóa hóa đơn rác {b_id}: {e}")
    print(f"🗑️ Đã dọn dẹp {deleted_invs} hóa đơn rác test khỏi invoices_by_booking.")

    print("\n🎉 HOÀN TẤT DỌN DẸP & ĐỒNG BỘ DỮ LIỆU!")


if __name__ == '__main__':
    clean_and_sync()
