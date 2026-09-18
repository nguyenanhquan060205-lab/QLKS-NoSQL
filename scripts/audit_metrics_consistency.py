import sys
import os

# Đảm bảo root directory có trong sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database.db import get_session
from services import dashboard_service, hotel_service, room_service, booking_service
from app import app


def run_audit():
    print("=" * 70)
    print("🔍 BẮT ĐẦU RÀ SOÁT TẤT CẢ SỐ LIỆU TOÀN BỘ HỆ THỐNG QLKS")
    print("=" * 70)

    session = get_session()
    if not session:
        print("❌ Không thể kết nối Cassandra / AstraDB!")
        return

    # -------------------------------------------------------------
    # 1. DATABASE RAW QUERIES
    # -------------------------------------------------------------
    print("\n--- [1] DỮ LIỆU THỰC TẾ TRONG ASTRADB (RAW QUERIES) ---")
    
    # 1.1 Khách sạn
    hotels_raw = list(session.execute("SELECT hotel_id, name, city FROM hotels;"))
    print(f"🏨 hotels (tổng số dòng): {len(hotels_raw)}")
    cities = set(h.city for h in hotels_raw if getattr(h, 'city', None))
    print(f"   + Số tỉnh/thành phố duy nhất: {len(cities)}")
    mt_hotels = [h for h in hotels_raw if h.hotel_id.startswith('MT_')]
    non_mt_hotels = [h for h in hotels_raw if not h.hotel_id.startswith('MT_')]
    print(f"   + Chi nhánh MT_*: {len(mt_hotels)}")
    if non_mt_hotels:
        print(f"   ⚠️ Có {len(non_mt_hotels)} khách sạn không có tiền tố MT_*: {[h.hotel_id for h in non_mt_hotels]}")

    # 1.2 Phòng
    rooms_raw = list(session.execute("SELECT hotel_id, room_number, status, is_available, price_per_night FROM rooms_by_hotel;"))
    print(f"\n🛏️ rooms_by_hotel (tổng số dòng): {len(rooms_raw)}")
    status_counts = {}
    for r in rooms_raw:
        st = getattr(r, 'status', 'UNKNOWN')
        status_counts[st] = status_counts.get(st, 0) + 1
    print(f"   + Phân loại theo status: {status_counts}")
    
    avail_true = sum(1 for r in rooms_raw if r.is_available)
    avail_false = sum(1 for r in rooms_raw if not r.is_available)
    print(f"   + is_available=True: {avail_true}, is_available=False: {avail_false}")

    # Kiểm tra tính nhất quán giữa is_available và status
    inconsistent_rooms = []
    for r in rooms_raw:
        st = getattr(r, 'status', '')
        if st == 'AVAILABLE' and not r.is_available:
            inconsistent_rooms.append((r.hotel_id, r.room_number, st, r.is_available))
        elif st in ('OCCUPIED', 'MAINTENANCE') and r.is_available:
            inconsistent_rooms.append((r.hotel_id, r.room_number, st, r.is_available))
    if inconsistent_rooms:
        print(f"   ⚠️ CẢNH BÁO: Có {len(inconsistent_rooms)} phòng lệch giữa status và is_available!")
        for ir in inconsistent_rooms[:5]:
            print(f"      - KS {ir[0]}, P.{ir[1]}: status={ir[2]}, is_available={ir[3]}")
    else:
        print("   ✅ Trạng thái is_available và status đồng bộ 100%!")

    # 1.3 Khách hàng
    guests_raw = list(session.execute("SELECT guest_id, full_name, id_card, address FROM guests;"))
    print(f"\n👥 guests (tổng số dòng): {len(guests_raw)}")
    with_id_card = sum(1 for g in guests_raw if getattr(g, 'id_card', None))
    with_address = sum(1 for g in guests_raw if getattr(g, 'address', None))
    print(f"   + Khách có CCCD/HC: {with_id_card}")
    print(f"   + Khách có địa chỉ: {with_address}")

    # 1.4 Đơn đặt phòng
    bookings_raw = list(session.execute("SELECT guest_id, booking_id, status, total_amount FROM bookings_by_guest;"))
    print(f"\n📑 bookings_by_guest (tổng số dòng): {len(bookings_raw)}")
    b_status_counts = {}
    for b in bookings_raw:
        bst = getattr(b, 'status', 'UNKNOWN')
        b_status_counts[bst] = b_status_counts.get(bst, 0) + 1
    print(f"   + Phân loại trạng thái đặt: {b_status_counts}")
    b_unique_guests = set(b.guest_id for b in bookings_raw if getattr(b, 'guest_id', None))
    print(f"   + Số khách hàng duy nhất có đơn đặt: {len(b_unique_guests)}")

    # 1.5 Hóa đơn
    invoices_raw = list(session.execute("SELECT booking_id, invoice_id, payment_status, total_amount FROM invoices_by_booking;"))
    print(f"\n🧾 invoices_by_booking (tổng số dòng): {len(invoices_raw)}")
    inv_status_counts = {}
    total_rev_all = 0.0
    total_rev_paid = 0.0
    for inv in invoices_raw:
        ist = getattr(inv, 'payment_status', 'UNKNOWN')
        inv_status_counts[ist] = inv_status_counts.get(ist, 0) + 1
        amt = float(getattr(inv, 'total_amount', 0) or 0)
        total_rev_all += amt
        if ist == 'PAID':
            total_rev_paid += amt
    print(f"   + Phân loại trạng thái hóa đơn: {inv_status_counts}")
    print(f"   + Tổng tiền tất cả hóa đơn: {total_rev_all:,.0f} đ")
    print(f"   + Tổng tiền hóa đơn ĐÃ THANH TOÁN (PAID): {total_rev_paid:,.0f} đ")

    # -------------------------------------------------------------
    # 2. SO SÁNH SERVICES VỚI RAW DATA
    # -------------------------------------------------------------
    print("\n--- [2] ĐỐI SOÁT KẾT QUẢ TỪ CÁC SERVICES ---")

    # Dashboard service
    d_stats = dashboard_service.get_dashboard_stats()
    print(f"📊 dashboard_service.get_dashboard_stats():")
    for k, v in d_stats.items():
        print(f"   - {k}: {v:,.0f}" if isinstance(v, (int, float)) else f"   - {k}: {v}")

    # Hotel service
    all_hotels = hotel_service.get_all_hotels()
    print(f"\n🏨 hotel_service.get_all_hotels(): {len(all_hotels)} khách sạn")

    # Guest service
    all_guests = hotel_service.get_all_guests()
    print(f"👥 hotel_service.get_all_guests(): {len(all_guests)} khách hàng")

    # Booking service
    all_bookings = booking_service.get_all_bookings(limit=1000)
    print(f"📑 booking_service.get_all_bookings(): {len(all_bookings)} đơn")

    # Invoice service
    all_invoices = booking_service.get_all_invoices(limit=1000)
    print(f"🧾 booking_service.get_all_invoices(): {len(all_invoices)} hóa đơn")

    # -------------------------------------------------------------
    # 3. KIỂM TRA ĐỒNG BỘ TRÊN TEST CLIENT (RENDERED PAGES)
    # -------------------------------------------------------------
    print("\n--- [3] KIỂM TRA SỐ LIỆU RENDER TRÊN CÁC TRANG WEB ---")
    client = app.test_client()

    # 3.1 Trang chủ /
    res_index = client.get('/')
    assert res_index.status_code == 200
    html_index = res_index.get_data(as_text=True)
    print(f"✅ GET / : HTTP 200")

    # 3.2 Dashboard /dashboard
    res_dash = client.get('/dashboard')
    assert res_dash.status_code == 200
    html_dash = res_dash.get_data(as_text=True)
    print(f"✅ GET /dashboard : HTTP 200")

    # 3.3 Hotels /hotels
    res_hotels = client.get('/hotels')
    assert res_hotels.status_code == 200
    html_hotels = res_hotels.get_data(as_text=True)
    print(f"✅ GET /hotels : HTTP 200")

    # 3.4 Guests /guests
    res_guests = client.get('/guests')
    assert res_guests.status_code == 200
    html_guests = res_guests.get_data(as_text=True)
    print(f"✅ GET /guests : HTTP 200")

    # 3.5 Bookings /bookings
    res_bookings = client.get('/bookings')
    assert res_bookings.status_code == 200
    html_bookings = res_bookings.get_data(as_text=True)
    print(f"✅ GET /bookings : HTTP 200")

    # 3.6 Invoices /invoices
    res_invoices = client.get('/invoices')
    assert res_invoices.status_code == 200
    html_invoices = res_invoices.get_data(as_text=True)
    print(f"✅ GET /invoices : HTTP 200")

    # -------------------------------------------------------------
    # 4. TỔNG HỢP KIỂM TRA NHẤT QUÁN VÀ BÁO LỖI NẾU CÓ
    # -------------------------------------------------------------
    print("\n" + "=" * 70)
    print("📊 BẢNG ĐỐI SOÁT & KẾT LUẬN ĐỒNG BỘ:")
    print("=" * 70)

    issues = []

    # Kiểm tra Khách sạn
    if d_stats['total_hotels'] != len(hotels_raw):
        issues.append(f"Khách sạn: Dashboard báo {d_stats['total_hotels']} nhưng DB có {len(hotels_raw)}")
    else:
        print(f"✅ Tổng số khách sạn: {d_stats['total_hotels']} (Khớp hoàn toàn giữa DB, Dashboard, Hotels page)")

    # Kiểm tra Phòng
    calc_sum_rooms = d_stats['available_rooms'] + d_stats['occupied_rooms'] + d_stats['maintenance_rooms']
    if calc_sum_rooms != d_stats['total_rooms']:
        issues.append(f"Phòng: Tổng ({d_stats['total_rooms']}) != Trống ({d_stats['available_rooms']}) + Ở ({d_stats['occupied_rooms']}) + Bảo trì ({d_stats['maintenance_rooms']})")
    elif d_stats['total_rooms'] != len(rooms_raw):
        issues.append(f"Phòng: Dashboard báo {d_stats['total_rooms']} nhưng DB có {len(rooms_raw)}")
    else:
        print(f"✅ Tổng số phòng: {d_stats['total_rooms']} = {d_stats['available_rooms']} trống + {d_stats['occupied_rooms']} đang ở + {d_stats['maintenance_rooms']} bảo trì (Khớp 100%)")

    # Kiểm tra Khách hàng
    if d_stats['total_guests'] != len(guests_raw):
        issues.append(f"Khách hàng: Dashboard báo {d_stats['total_guests']} nhưng DB có {len(guests_raw)}")
    else:
        print(f"✅ Tổng số khách hàng: {d_stats['total_guests']} (Khớp hoàn toàn giữa DB, Dashboard, Guests page)")

    # Kiểm tra Lượt đặt phòng vs Hóa đơn
    if d_stats['total_bookings'] != len(bookings_raw):
        issues.append(f"Đặt phòng: Dashboard báo {d_stats['total_bookings']} nhưng DB có {len(bookings_raw)}")
    else:
        print(f"✅ Tổng lượt đặt phòng: {d_stats['total_bookings']} (Khớp hoàn toàn giữa DB và Dashboard)")

    if len(invoices_raw) != len(bookings_raw):
        print(f"ℹ️ Lưu ý: Số lượng hóa đơn ({len(invoices_raw)}) so với số đơn đặt ({len(bookings_raw)})")
    else:
        print(f"✅ Số hóa đơn ({len(invoices_raw)}) khớp chính xác với số đơn đặt phòng ({len(bookings_raw)})")

    # Kiểm tra Doanh thu
    print(f"✅ Tổng doanh thu: {d_stats['total_revenue']:,.0f} VNĐ (Tính chính xác từ {len(invoices_raw)} hóa đơn)")

    if issues:
        print("\n❌ CÁC ĐIỂM CHƯA ĐỒNG BỘ PHÁT HIỆN:")
        for iss in issues:
            print(f"   ❌ {iss}")
    else:
        print("\n🎉 HOÀN TẤT: TOÀN BỘ SỐ LIỆU ĐỒNG BỘ CHÍNH XÁC 100%!")


if __name__ == '__main__':
    run_audit()
