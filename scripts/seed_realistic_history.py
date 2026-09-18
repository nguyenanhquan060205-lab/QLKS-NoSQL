#!/usr/bin/env python3
"""
Seed script: Khách hàng thực tế, Lịch sử đặt phòng 1 năm (2025 - 2026) và Đồng bộ trạng thái phòng
- Dọn dẹp khách sạn / đặt phòng rác thử nghiệm (H_QLKS04_TEST, H_INT_...).
- Nạp 50 khách hàng thực tế (tiếng Việt phong phú + vài khách quốc tế).
- Nạp ~135 đơn đặt phòng & hóa đơn trải dài 1 năm (10/2025 -> 09/2026):
  * Quá khứ: ~70 đơn đã hoàn tất (CHECKED_OUT / CONFIRMED).
  * Đang lưu trú hôm nay (18/09/2026): ~50 đơn đang ở.
  * Tương lai: ~15 đơn đặt trước.
- ĐỒNG BỘ CHÍNH XÁC 100% TRẠNG THÁI PHÒNG:
  * Số phòng OCCUPIED = Đúng số đơn đang ở hôm nay (50 phòng).
  * Số phòng MAINTENANCE = ~22 phòng bảo trì định kỳ.
  * Số phòng AVAILABLE = 561 - 50 - 22 = 489 phòng trống.
  * Tổng số: 561 phòng.
"""

import sys
import os
import random
from datetime import date, datetime, timedelta
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from database.db import get_session

TODAY = date(2026, 9, 18)

# 1. DANH SÁCH 50 KHÁCH HÀNG THỰC TẾ (VIỆT NAM & QUỐC TẾ)
REAL_GUESTS = [
    # Khách hàng Việt Nam (45 người)
    {"id": "G_001", "name": "Nguyễn Anh Quân", "email": "anhquan.nguyen@gmail.com", "phone": "0912345678", "id_card": "001201001234", "address": "Quận Hoàn Kiếm, Hà Nội"},
    {"id": "G_002", "name": "Trần Thị Mai", "email": "mai.tran@yahoo.com", "phone": "0987654321", "id_card": "001201005678", "address": "Quận Cầu Giấy, Hà Nội"},
    {"id": "G_003", "name": "Lê Hoàng Nam", "email": "nam.lehoang@fpt.com.vn", "phone": "0903112233", "id_card": "079201002345", "address": "Quận 1, TP. Hồ Chí Minh"},
    {"id": "G_004", "name": "Phạm Thu Hương", "email": "thuhuong.pham@gmail.com", "phone": "0918223344", "id_card": "048201003456", "address": "Quận Hải Châu, Đà Nẵng"},
    {"id": "G_005", "name": "Vũ Đức Đam", "email": "dam.vuduc@vinfast.vn", "phone": "0934556677", "id_card": "031201004567", "address": "Quận Hồng Bàng, Hải Phòng"},
    {"id": "G_006", "name": "Đặng Ngọc Linh", "email": "linh.dang@viettel.com.vn", "phone": "0945667788", "id_card": "046201005678", "address": "Thành phố Huế, Thừa Thiên Huế"},
    {"id": "G_007", "name": "Hoàng Minh Đức", "email": "duc.hoang@vcci.com.vn", "phone": "0967889900", "id_card": "056201006789", "address": "Thành phố Nha Trang, Khánh Hòa"},
    {"id": "G_008", "name": "Bùi Thị Xuân", "email": "xuan.bui@gmail.com", "phone": "0978990011", "id_card": "068201007890", "address": "Thành phố Đà Lạt, Lâm Đồng"},
    {"id": "G_009", "name": "Ngô Quang Hải", "email": "hai.ngoquang@vietcombank.com.vn", "phone": "0989001122", "id_card": "092201008901", "address": "Quận Ninh Kiều, Cần Thơ"},
    {"id": "G_010", "name": "Đỗ Mỹ Linh", "email": "mylinh.do@gmail.com", "phone": "0901223344", "id_card": "077201009012", "address": "Thành phố Vũng Tàu, Bà Rịa - Vũng Tàu"},
    {"id": "G_011", "name": "Dương Quốc Anh", "email": "quocanh.duong@techcombank.com.vn", "phone": "0912334455", "id_card": "012201001122", "address": "Thành phố Thái Nguyên, Thái Nguyên"},
    {"id": "G_012", "name": "Trịnh Hoài Đức", "email": "duc.trinh@gmail.com", "phone": "0923445566", "id_card": "019201002233", "address": "Thành phố Hạ Long, Quảng Ninh"},
    {"id": "G_013", "name": "Lương Thế Vinh", "email": "vinh.luongthe@hust.edu.vn", "phone": "0934556677", "id_card": "020201003344", "address": "Thành phố Nam Định, Nam Định"},
    {"id": "G_014", "name": "Phan Thanh Giản", "email": "gian.phanthanh@gmail.com", "phone": "0945667788", "id_card": "083201004455", "address": "Thành phố Bến Tre, Bến Tre"},
    {"id": "G_015", "name": "Tô Ngọc Vân", "email": "van.tongoc@finearts.edu.vn", "phone": "0956778899", "id_card": "024201005566", "address": "Thành phố Bắc Ninh, Bắc Ninh"},
    {"id": "G_016", "name": "Chu Văn An", "email": "chuvanan.edu@gmail.com", "phone": "0967889901", "id_card": "026201006677", "address": "Thành phố Vĩnh Yên, Vĩnh Phúc"},
    {"id": "G_017", "name": "Lê Quý Đôn", "email": "lequydon.research@gmail.com", "phone": "0978990012", "id_card": "034201007788", "address": "Thành phố Thái Bình, Thái Bình"},
    {"id": "G_018", "name": "Nguyễn Du", "email": "nguyendu.lit@gmail.com", "phone": "0989001123", "id_card": "042201008899", "address": "Thành phố Hà Tĩnh, Hà Tĩnh"},
    {"id": "G_019", "name": "Hồ Xuân Hương", "email": "xuanhuong.ho@gmail.com", "phone": "0901112234", "id_card": "040201009900", "address": "Thành phố Vinh, Nghệ An"},
    {"id": "G_020", "name": "Đoàn Thị Điểm", "email": "diem.doanthi@gmail.com", "phone": "0912223345", "id_card": "033201001011", "address": "Thành phố Hưng Yên, Hưng Yên"},
    {"id": "G_021", "name": "Nguyễn Trãi", "email": "nguyentrai.history@gmail.com", "phone": "0923334456", "id_card": "030201002122", "address": "Thành phố Hải Dương, Hải Dương"},
    {"id": "G_022", "name": "Trần Hưng Đạo", "email": "tranhungdao.mil@gmail.com", "phone": "0934445567", "id_card": "035201003233", "address": "Thành phố Phủ Lý, Hà Nam"},
    {"id": "G_023", "name": "Lý Thường Kiệt", "email": "lythuongkiet@gmail.com", "phone": "0945556678", "id_card": "038201004344", "address": "Thành phố Thanh Hóa, Thanh Hóa"},
    {"id": "G_024", "name": "Võ Nguyên Giáp", "email": "vonguyengiap@gmail.com", "phone": "0956667789", "id_card": "044201005455", "address": "Thành phố Đồng Hới, Quảng Bình"},
    {"id": "G_025", "name": "Phạm Nhật Vượng", "email": "vuong.pn@vingroup.net", "phone": "0967778890", "id_card": "001201006566", "address": "Khu đô thị Vinhomes Riverside, Hà Nội"},
    {"id": "G_026", "name": "Nguyễn Thị Phương Thảo", "email": "thao.ntp@vietjetair.com", "phone": "0978889901", "id_card": "079201007677", "address": "Quận 3, TP. Hồ Chí Minh"},
    {"id": "G_027", "name": "Trần Đình Long", "email": "long.td@hoaphat.com.vn", "phone": "0989990012", "id_card": "001201008788", "address": "Quận Hai Bà Trưng, Hà Nội"},
    {"id": "G_028", "name": "Hồ Hùng Anh", "email": "anh.hh@techcombank.com.vn", "phone": "0901001123", "id_card": "001201009899", "address": "Quận Tây Hồ, Hà Nội"},
    {"id": "G_029", "name": "Nguyễn Đăng Quang", "email": "quang.nd@masangroup.com", "phone": "0912112234", "id_card": "079201000910", "address": "Thành phố Thủ Đức, TP. Hồ Chí Minh"},
    {"id": "G_030", "name": "Trương Gia Bình", "email": "binh.tg@fpt.com.vn", "phone": "0923223345", "id_card": "001201001920", "address": "Quận Cầu Giấy, Hà Nội"},
    {"id": "G_031", "name": "Đặng Lê Nguyên Vũ", "email": "vu.dln@trungnguyen.com.vn", "phone": "0934334456", "id_card": "066201002930", "address": "Thành phố Buôn Ma Thuột, Đắk Lắk"},
    {"id": "G_032", "name": "Nguyễn Tuấn Dũng", "email": "tuandung@gmail.com", "phone": "0945445567", "id_card": "051201003940", "address": "Thành phố Tam Kỳ, Quảng Nam"},
    {"id": "G_033", "name": "Trần Bảo Ngọc", "email": "baongoc.tran@gmail.com", "phone": "0956556678", "id_card": "052201004950", "address": "Thành phố Quảng Ngãi, Quảng Ngãi"},
    {"id": "G_034", "name": "Lê Văn Thắng", "email": "thang.le@gmail.com", "phone": "0967667789", "id_card": "054201005960", "address": "Thành phố Quy Nhơn, Bình Định"},
    {"id": "G_035", "name": "Đỗ Hồng Nhung", "email": "hongnhung.do@gmail.com", "phone": "0978778890", "id_card": "058201006970", "address": "Thành phố Tuy Hòa, Phú Yên"},
    {"id": "G_036", "name": "Phạm Tuấn Anh", "email": "tuananh.pham@gmail.com", "phone": "0989889901", "id_card": "060201007980", "address": "Thành phố Phan Thiết, Bình Thuận"},
    {"id": "G_037", "name": "Hoàng Yến Nhi", "email": "yennhi.hoang@gmail.com", "phone": "0901990012", "id_card": "064201008990", "address": "Thành phố Pleiku, Gia Lai"},
    {"id": "G_038", "name": "Vũ Minh Tuấn", "email": "minhtuan.vu@gmail.com", "phone": "0912001123", "id_card": "062201009901", "address": "Thành phố Kon Tum, Kon Tum"},
    {"id": "G_039", "name": "Nguyễn Quỳnh Chi", "email": "quynhchi.nguyen@gmail.com", "phone": "0923112234", "id_card": "067201000912", "address": "Thành phố Gia Nghĩa, Đắk Nông"},
    {"id": "G_040", "name": "Bùi Đức Thịnh", "email": "ducthinh.bui@gmail.com", "phone": "0934223345", "id_card": "070201001923", "address": "Thành phố Đồng Xoài, Bình Phước"},
    {"id": "G_041", "name": "Trịnh Thu Trang", "email": "thutrang.trinh@gmail.com", "phone": "0945334456", "id_card": "072201002934", "address": "Thành phố Tây Ninh, Tây Ninh"},
    {"id": "G_042", "name": "Đặng Hữu Tài", "email": "huutai.dang@gmail.com", "phone": "0956445567", "id_card": "074201003945", "address": "Thành phố Thủ Dầu Một, Bình Dương"},
    {"id": "G_043", "name": "Lâm Thanh Hà", "email": "thanhha.lam@gmail.com", "phone": "0967556678", "id_card": "075201004956", "address": "Thành phố Biên Hòa, Đồng Nai"},
    {"id": "G_044", "name": "Mai Trọng Nhân", "email": "trongnhan.mai@gmail.com", "phone": "0978667789", "id_card": "080201005967", "address": "Thành phố Tân An, Long An"},
    {"id": "G_045", "name": "Đinh Quang Khải", "email": "quangkhai.dinh@gmail.com", "phone": "0989778890", "id_card": "082201006978", "address": "Thành phố Mỹ Tho, Tiền Giang"},

    # Khách quốc tế (5 người)
    {"id": "G_046", "name": "David Miller", "email": "david.miller@deloitte.co.uk", "phone": "0903889901", "id_card": "G8291047", "address": "London, United Kingdom"},
    {"id": "G_047", "name": "Emily Watson", "email": "emily.watson@sydney.edu.au", "phone": "0914990012", "id_card": "N1094821", "address": "Sydney, New South Wales, Australia"},
    {"id": "G_048", "name": "Michael Zhang", "email": "michael.zhang@dbs.com.sg", "phone": "0925001123", "id_card": "E4829103", "address": "Marina Bay, Singapore"},
    {"id": "G_049", "name": "Sarah Jenkins", "email": "sarah.jenkins@apple.com", "phone": "0936112234", "id_card": "P9381024", "address": "Cupertino, California, USA"},
    {"id": "G_050", "name": "Kenji Takahashi", "email": "kenji.takahashi@sony.co.jp", "phone": "0947223345", "id_card": "T7381920", "address": "Minato-ku, Tokyo, Japan"},
]


def seed_realistic_data():
    session = get_session()
    if not session:
        print("❌ Không thể kết nối AstraDB!")
        return

    print("=================================================================")
    print("🚀 BẮT ĐẦU SEED KHÁCH HÀNG & LỊCH SỬ ĐẶT PHÒNG 1 NĂM (ASTRADB)")
    print("=================================================================")

    # 1. DỌN DẸP DỮ LIỆU RÁC CŨ / TEST DƯ THỪA
    print("\n[Bước 1/5] Dọn dẹp rác test và chuẩn hóa danh mục khách sạn...")
    try:
        session.execute("DELETE FROM hotels WHERE hotel_id = 'H_QLKS04_TEST';")
        session.execute("DELETE FROM rooms_by_hotel WHERE hotel_id = 'H_QLKS04_TEST';")
        session.execute("DELETE FROM hotels WHERE hotel_id = 'H001';")
        session.execute("DELETE FROM hotels WHERE hotel_id = 'H002';")
        print("   ✅ Đã xóa khách sạn test H_QLKS04_TEST và H001/H002.")
    except Exception as e:
        print(f"   ⚠️ Lỗi dọn test hotels: {e}")

    # 2. NẠP 50 KHÁCH HÀNG THỰC TẾ VÀO BẢNG 'guests'
    print("\n[Bước 2/5] Nạp 50 khách hàng thực tế (Việt Nam & Quốc tế) vào bảng 'guests'...")
    try:
        insert_guest_stmt = session.prepare("""
            INSERT INTO guests (guest_id, full_name, email, phone, id_card, address)
            VALUES (?, ?, ?, ?, ?, ?);
        """)
        for g in REAL_GUESTS:
            session.execute(insert_guest_stmt, (
                g["id"], g["name"], g["email"], g["phone"], g["id_card"], g["address"]
            ))
        print(f"   ✅ Đã nạp thành công {len(REAL_GUESTS)} khách hàng vào AstraDB.")
    except Exception as e:
        print(f"   ❌ Lỗi nạp guests: {e}")
        return

    # 3. LẤY TOÀN BỘ PHÒNG THỰC TẾ TRONG 40 CHI NHÁNH MƯỜNG THANH
    print("\n[Bước 3/5] Đọc danh mục 40 khách sạn và 561 phòng từ AstraDB...")
    hotels_res = list(session.execute("SELECT hotel_id, name, city FROM hotels;"))
    mt_hotels = [h for h in hotels_res if h.hotel_id.startswith("MT_")]
    mt_hotels.sort(key=lambda x: x.hotel_id)
    print(f"   Đã tìm thấy {len(mt_hotels)} chi nhánh Mường Thanh hợp lệ.")

    all_rooms = list(session.execute("SELECT hotel_id, room_number, room_type, price_per_night FROM rooms_by_hotel;"))
    all_rooms = [r for r in all_rooms if r.hotel_id.startswith("MT_")]
    print(f"   Tổng số phòng chuỗi Mường Thanh: {len(all_rooms)} phòng.")

    # Gom phòng theo khách sạn
    rooms_by_h = {}
    for r in all_rooms:
        rooms_by_h.setdefault(r.hotel_id, []).append(r)

    # 4. THIẾT LẬP KỊCH BẢN ĐẶT PHÒNG KHỚP 100% SỐ LIỆU THỰC TẾ
    print("\n[Bước 4/5] Lập lịch đơn đặt phòng 1 năm (10/2025 -> 09/2026) & đồng bộ phòng...")

    # A. CHỌN PHÒNG BẢO TRÌ: Chính xác 22 phòng (khoảng 1 phòng/chi nhánh cho 22 chi nhánh)
    maintenance_rooms = set()
    for h in mt_hotels[:22]:
        h_rooms = rooms_by_h.get(h.hotel_id, [])
        if h_rooms:
            # Chọn phòng cuối cùng làm bảo trì
            m_room = h_rooms[-1]
            maintenance_rooms.add((m_room.hotel_id, m_room.room_number))

    # B. CHỌN PHÒNG ĐANG LƯU TRÚ HÔM NAY (OCCUPIED): Đúng 50 phòng
    # Rải đều trên các chi nhánh
    occupied_rooms_info = []
    occupied_set = set()
    for h in mt_hotels:
        h_rooms = rooms_by_h.get(h.hotel_id, [])
        for r in h_rooms:
            if (r.hotel_id, r.room_number) not in maintenance_rooms:
                occupied_rooms_info.append(r)
                occupied_set.add((r.hotel_id, r.room_number))
                if len(occupied_rooms_info) >= 50:
                    break
        if len(occupied_rooms_info) >= 50:
            break

    print(f"   Phòng bảo trì (MAINTENANCE): {len(maintenance_rooms)} phòng.")
    print(f"   Phòng đang lưu trú hôm nay (OCCUPIED): {len(occupied_rooms_info)} phòng.")
    print(f"   Phòng trống sẵn sàng (AVAILABLE): {len(all_rooms) - len(maintenance_rooms) - len(occupied_rooms_info)} phòng.")

    # Prepared statements cho Q2, Q3, Q4
    stmt_q2 = session.prepare("""
        INSERT INTO bookings_by_guest (
            guest_id, booking_id, hotel_id, room_number,
            check_in_date, check_out_date, status, total_amount
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
    """)

    stmt_q3 = session.prepare("""
        INSERT INTO bookings_by_hotel_date (
            hotel_id, check_in_date, booking_id,
            guest_id, guest_name, room_number, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?);
    """)

    stmt_q4 = session.prepare("""
        INSERT INTO invoices_by_booking (
            booking_id, invoice_id, guest_name, hotel_id,
            issue_date, payment_method, payment_status, total_amount
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
    """)

    stmt_update_room = session.prepare("""
        UPDATE rooms_by_hotel
        SET status = ?, is_available = ?
        WHERE hotel_id = ? AND room_number = ?;
    """)

    # --- NHÓM 1: ĐƠN ĐANG LƯU TRÚ HÔM NAY (50 đơn) ---
    print("\n   -> Nạp 50 đơn đặt phòng ĐANG LƯU TRÚ HÔM NAY (18/09/2026)...")
    booking_counter = 1000
    for idx, r in enumerate(occupied_rooms_info):
        booking_counter += 1
        b_id = f"BK202609{booking_counter:04d}"
        inv_id = f"INV202609{booking_counter:04d}"
        guest = REAL_GUESTS[idx % len(REAL_GUESTS)]

        # Check-in từ 1-3 ngày trước, check-out sau 1-3 ngày nữa
        days_stayed = random.randint(1, 3)
        remaining_days = random.randint(1, 3)
        check_in = TODAY - timedelta(days=days_stayed)
        check_out = TODAY + timedelta(days=remaining_days)
        nights = (check_out - check_in).days
        price = Decimal(str(r.price_per_night or 1200000))
        total_amt = price * nights

        pay_method = random.choice(["THẺ TÍN DỤNG", "CHUYỂN KHOẢN", "TIỀN MẶT"])
        pay_status = "PAID" if random.random() < 0.9 else "UNPAID"

        # Ghi Q2
        session.execute(stmt_q2, (
            guest["id"], b_id, r.hotel_id, r.room_number,
            check_in, check_out, "CONFIRMED", total_amt
        ))
        # Ghi Q3
        session.execute(stmt_q3, (
            r.hotel_id, check_in, b_id,
            guest["id"], guest["name"], r.room_number, "CONFIRMED"
        ))
        # Ghi Q4
        session.execute(stmt_q4, (
            b_id, inv_id, guest["name"], r.hotel_id,
            check_in, pay_method, pay_status, total_amt
        ))

        # CẬP NHẬT PHÒNG SANG OCCUPIED
        session.execute(stmt_update_room, (
            "OCCUPIED", False, r.hotel_id, r.room_number
        ))

    # --- NHÓM 2: ĐƠN TRONG QUÁ KHỨ (70 đơn trải dài từ 10/2025 đến 08/2026) ---
    print("   -> Nạp 70 đơn đặt phòng LỊCH SỬ QUÁ KHỨ (10/2025 -> 08/2026)...")
    # Sinh các mốc ngày trong 1 năm qua
    for i in range(70):
        booking_counter += 1
        b_id = f"BK202526{booking_counter:04d}"
        inv_id = f"INV202526{booking_counter:04d}"
        guest = random.choice(REAL_GUESTS)
        r = random.choice(all_rooms)

        # Lùi từ 20 ngày đến 340 ngày trước
        days_ago = random.randint(20, 340)
        stay_len = random.randint(1, 4)
        check_in = TODAY - timedelta(days=days_ago)
        check_out = check_in + timedelta(days=stay_len)
        nights = stay_len
        price = Decimal(str(r.price_per_night or 1200000))
        total_amt = price * nights

        pay_method = random.choice(["CHUYỂN KHOẢN", "THẺ TÍN DỤNG", "TIỀN MẶT"])

        session.execute(stmt_q2, (
            guest["id"], b_id, r.hotel_id, r.room_number,
            check_in, check_out, "CONFIRMED", total_amt
        ))
        session.execute(stmt_q3, (
            r.hotel_id, check_in, b_id,
            guest["id"], guest["name"], r.room_number, "CONFIRMED"
        ))
        session.execute(stmt_q4, (
            b_id, inv_id, guest["name"], r.hotel_id,
            check_in, pay_method, "PAID", total_amt
        ))

    # --- NHÓM 3: ĐƠN ĐẶT TRƯỚC TƯƠNG LAI (15 đơn trong tháng 9 - 10/2026) ---
    print("   -> Nạp 15 đơn ĐẶT PHÒNG TƯƠNG LAI (cuối tháng 09 - 10/2026)...")
    for i in range(15):
        booking_counter += 1
        b_id = f"BK2026FUT{booking_counter:04d}"
        inv_id = f"INV2026FUT{booking_counter:04d}"
        guest = random.choice(REAL_GUESTS)
        # Chọn phòng đang trống
        available_candidate = random.choice([
            r for r in all_rooms
            if (r.hotel_id, r.room_number) not in occupied_set
            and (r.hotel_id, r.room_number) not in maintenance_rooms
        ])

        days_ahead = random.randint(3, 25)
        stay_len = random.randint(1, 3)
        check_in = TODAY + timedelta(days=days_ahead)
        check_out = check_in + timedelta(days=stay_len)
        price = Decimal(str(available_candidate.price_per_night or 1200000))
        total_amt = price * stay_len

        session.execute(stmt_q2, (
            guest["id"], b_id, available_candidate.hotel_id, available_candidate.room_number,
            check_in, check_out, "CONFIRMED", total_amt
        ))
        session.execute(stmt_q3, (
            available_candidate.hotel_id, check_in, b_id,
            guest["id"], guest["name"], available_candidate.room_number, "CONFIRMED"
        ))
        session.execute(stmt_q4, (
            b_id, inv_id, guest["name"], available_candidate.hotel_id,
            check_in, "CHUYỂN KHOẢN", "PAID", total_amt
        ))

    # --- NHÓM 4: ĐỒNG BỘ CÁC PHÒNG CÒN LẠI VÀO BẢNG rooms_by_hotel ---
    print("\n[Bước 5/5] Cập nhật chuẩn hóa trạng thái 561 phòng...")
    avail_count = 0
    maint_count = 0
    occ_count = 0

    for r in all_rooms:
        key = (r.hotel_id, r.room_number)
        if key in maintenance_rooms:
            session.execute(stmt_update_room, ("MAINTENANCE", False, r.hotel_id, r.room_number))
            maint_count += 1
        elif key in occupied_set:
            # Đã set ở trên
            occ_count += 1
        else:
            session.execute(stmt_update_room, ("AVAILABLE", True, r.hotel_id, r.room_number))
            avail_count += 1

    print("\n=================================================================")
    print("🎉 SEED VÀ ĐỒNG BỘ DỮ LIỆU THÀNH CÔNG RỰC RỠ!")
    print(f" - Khách hàng: {len(REAL_GUESTS)} người")
    print(f" - Tổng số đơn đặt phòng: {50 + 70 + 15} đơn (50 đang ở, 70 quá khứ 1 năm qua, 15 đặt trước)")
    print(f" - Tổng số phòng: {len(all_rooms)} phòng")
    print(f"   * Phòng trống (AVAILABLE): {avail_count} phòng")
    print(f"   * Phòng đang ở (OCCUPIED): {occ_count} phòng (Khớp 100% với 50 đơn đang ở)")
    print(f"   * Phòng bảo trì (MAINTENANCE): {maint_count} phòng")
    print("=================================================================")


if __name__ == "__main__":
    seed_realistic_data()
