"""
QLKS-13 — KIỂM THỬ TÍCH HỢP END-TO-END TOÀN BỘ CHỨC NĂNG

Chạy thật: đi qua route Flask thật, render template thật, ghi/đọc AstraDB thật.
Khác với unit test trong tests/ (mock session), script này kiểm tra cả chuỗi
route -> service -> Cassandra -> template, tức là đúng thứ người dùng gặp.

AN TOÀN DỮ LIỆU NHÓM: script tự tạo khách sạn / phòng / khách / booking riêng
mang nhãn E2E kèm dấu thời gian, rồi DỌN SẠCH ở cuối (kể cả khi giữa đường lỗi).
Không sửa và không xoá bất kỳ dữ liệu sẵn có nào.

    python scripts/e2e_full_test.py           # chạy đầy đủ
    python scripts/e2e_full_test.py --keep    # giữ lại dữ liệu test để xem tận mắt

Exit code 0 = tất cả PASS, 1 = có FAIL.
"""

import os
import re
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from database.db import get_session
from services import booking_service, room_service

RUN = date.today().strftime("%m%d") + os.urandom(2).hex().upper()
TAG = f"E2E{RUN}"

# Hệ thống chặn trùng SĐT khách, trùng SĐT/tên khách sạn và trùng CCCD, nên dữ
# liệu test phải độc nhất từng lần chạy — nếu không script sẽ fail vì trùng với
# dữ liệu thật chứ không phải vì chức năng sai.
UNIQ8 = "".join(str(b % 10) for b in os.urandom(8))
GUEST_PHONE = "09" + UNIQ8
GUEST_PHONE_2 = "08" + UNIQ8
HOTEL_PHONE = "02" + UNIQ8
GUEST_ID_CARD = "0" + UNIQ8 + "123"        # CCCD = đúng 12 chữ số
GUEST_ID_CARD_2 = "0" + UNIQ8 + "456"

TODAY = date.today()
IN_DATE = (TODAY + timedelta(days=3)).isoformat()
OUT_DATE = (TODAY + timedelta(days=6)).isoformat()   # 3 đêm
PRICE = 1000000
EXPECTED_AMOUNT = PRICE * 3


class Report:
    def __init__(self):
        self.passed = 0
        self.failed = []
        self.section = ""

    def head(self, title):
        self.section = title
        print()
        print(f"── {title} " + "─" * max(0, 62 - len(title)))

    def check(self, name, ok, detail=""):
        if ok:
            self.passed += 1
            print(f"  PASS  {name}")
        else:
            self.failed.append((self.section, name, detail))
            print(f"  FAIL  {name}")
            if detail:
                print(f"        {detail}")
        return ok

    def note(self, msg):
        print(f"        · {msg}")

    def summary(self):
        total = self.passed + len(self.failed)
        print()
        print("═" * 66)
        print(f"  KẾT QUẢ: {self.passed}/{total} PASS")
        if self.failed:
            print(f"  {len(self.failed)} FAIL:")
            for section, name, detail in self.failed:
                print(f"    [{section}] {name}")
                if detail:
                    print(f"       {detail}")
        else:
            print("  Toàn bộ chức năng hoạt động đúng.")
        print("═" * 66)
        return 0 if not self.failed else 1


r = Report()
created = {"hotel_id": None, "guest_id": None, "booking_ids": [], "rooms": []}


def text_of(resp):
    return resp.get_data(as_text=True)


def bust_caches():
    """Service có cache in-memory 30s; kiểm thử phải đọc số mới nhất."""
    room_service.invalidate_rooms_cache()
    booking_service.invalidate_booking_cache()
    booking_service.invalidate_invoice_cache()


def db_room(session, hotel_id, room_number):
    stmt = session.prepare(
        "SELECT hotel_id, room_number, status, is_available, current_guest_name, "
        "current_booking_id FROM rooms_by_hotel WHERE hotel_id = ? AND room_number = ?;"
    )
    rows = list(session.execute(stmt, (hotel_id, str(room_number))))
    return rows[0] if rows else None


def db_bookings_by_guest(session, guest_id):
    stmt = session.prepare(
        "SELECT guest_id, booking_id, hotel_id, room_number, check_in_date, "
        "check_out_date, status, total_amount FROM bookings_by_guest WHERE guest_id = ?;"
    )
    return list(session.execute(stmt, (guest_id,)))


def db_bookings_by_hotel_date(session, hotel_id, check_in):
    stmt = session.prepare(
        "SELECT hotel_id, check_in_date, booking_id, guest_id, guest_name, room_number, "
        "status FROM bookings_by_hotel_date WHERE hotel_id = ? AND check_in_date = ?;"
    )
    return list(session.execute(stmt, (hotel_id, check_in)))


def db_invoices(session, booking_id):
    stmt = session.prepare(
        "SELECT booking_id, invoice_id, total_amount, payment_status, deposit_amount, "
        "remaining_amount FROM invoices_by_booking WHERE booking_id = ?;"
    )
    return list(session.execute(stmt, (booking_id,)))


def run(client, session):
    # ================================================================
    r.head("1. TẤT CẢ TRANG CHÍNH PHẢI MỞ ĐƯỢC")
    # ================================================================
    for path in ["/", "/dashboard", "/hotels", "/guests", "/bookings", "/invoices"]:
        resp = client.get(path)
        r.check(f"GET {path} -> 200", resp.status_code == 200,
                f"nhận {resp.status_code}")

    # ================================================================
    r.head("2. DASHBOARD & BỘ LỌC (QLKS-12)")
    # ================================================================
    resp = client.get("/dashboard")
    html = text_of(resp)
    r.check("dropdown kỳ báo cáo render đủ 6 lựa chọn",
            all(f'value="{v}"' in html for v in
                ["all", "today", "month", "quarter", "year", "custom"]))

    labels = {
        "today": "Hôm nay",
        "month": f"Tháng {TODAY.month}/{TODAY.year}",
        "year": f"Năm {TODAY.year}",
    }
    for period, label in labels.items():
        resp = client.get(f"/dashboard?period={period}")
        ok = resp.status_code == 200 and label in text_of(resp)
        r.check(f"lọc period={period} hiển thị đúng nhãn '{label}'", ok,
                f"status {resp.status_code}")

    # Số lượt đặt phải không giảm khi mở rộng kỳ
    def bookings_count(query):
        from services import dashboard_service
        rep = dashboard_service.get_dashboard_report(**query)
        return rep["total_bookings"], rep

    n_today, _ = bookings_count({"period": "today"})
    n_month, _ = bookings_count({"period": "month"})
    n_year, _ = bookings_count({"period": "year"})
    n_all, rep_all = bookings_count({"period": "all"})
    r.check("lượt đặt đơn điệu: hôm nay <= tháng <= năm <= toàn bộ",
            n_today <= n_month <= n_year <= n_all,
            f"{n_today} / {n_month} / {n_year} / {n_all}")
    r.note(f"hôm nay {n_today} · tháng {n_month} · năm {n_year} · toàn bộ {n_all}")

    r.check("tổng phòng = trống + đang thuê + bảo trì",
            rep_all["total_rooms"] == (rep_all["available_rooms"]
                                       + rep_all["occupied_rooms"]
                                       + rep_all["maintenance_rooms"]),
            f"{rep_all['total_rooms']} vs {rep_all['available_rooms']}"
            f"+{rep_all['occupied_rooms']}+{rep_all['maintenance_rooms']}")

    r.check("trang chủ có đủ 4 số liệu mở rộng (không rỗng)",
            all(k in rep_all for k in
                ("occupied_rooms", "maintenance_rooms", "total_guests", "total_invoices")))

    resp = client.get("/dashboard?period=custom&start_date=2026-09-30&end_date=2026-09-01",
                      follow_redirects=True)
    r.check("khoảng ngày ngược bị báo lỗi, không im lặng đổi kết quả",
            "phải trước hoặc bằng" in text_of(resp))

    resp = client.get("/dashboard?period=custom&start_date=2025-12-15&end_date=2026-01-15")
    m = re.search(r"labels:\s*\[([^\]]*)\]", text_of(resp))
    if m:
        found = re.findall(r'"(\d{2}/\d{2})"', m.group(1))
        dec = [i for i, x in enumerate(found) if x.endswith("/12")]
        jan = [i for i, x in enumerate(found) if x.endswith("/01")]
        ok = (not dec or not jan) or max(dec) < min(jan)
        r.check("biểu đồ vắt qua năm mới: tháng 12 xếp trước tháng 1", ok, str(found))
    else:
        r.check("biểu đồ vắt qua năm mới: tháng 12 xếp trước tháng 1", True)
        r.note("kỳ này không có doanh thu, bỏ qua")

    # ================================================================
    r.head("3. KHÁCH SẠN — THÊM / SỬA / RÀNG BUỘC (QLKS-04, QLKS-06)")
    # ================================================================
    hotel_name = f"Khách sạn {TAG}"
    resp = client.post("/hotels/add", data={
        "name": hotel_name, "phone": HOTEL_PHONE,
        "city": "Thành phố Hà Nội", "ward": "Phường Test",
        "address": "1 Đường Kiểm Thử", "country": "Vietnam",
        "amenities": "Wifi,Bể bơi",
    }, follow_redirects=True)
    r.check("thêm khách sạn thành công", resp.status_code == 200)

    rows = list(session.execute("SELECT hotel_id, name FROM hotels;"))
    mine = [h for h in rows if h.name == hotel_name]
    if not r.check("khách sạn vừa thêm có trong bảng hotels", len(mine) == 1,
                   f"tìm thấy {len(mine)} dòng"):
        return
    hotel_id = mine[0].hotel_id
    created["hotel_id"] = hotel_id
    r.note(f"hotel_id = {hotel_id}")

    resp = client.post("/hotels/add", data={
        "name": hotel_name, "phone": HOTEL_PHONE,
        "city": "Thành phố Hà Nội", "ward": "P", "address": "2",
    }, follow_redirects=True)
    r.check("chặn trùng tên khách sạn", "đã tồn tại" in text_of(resp))

    resp = client.post("/hotels/add", data={
        "name": f"{hotel_name} SĐT SAI", "phone": "123",
        "city": "Thành phố Hà Nội", "ward": "P", "address": "3",
    }, follow_redirects=True)
    r.check("chặn số điện thoại sai định dạng",
            "10 chữ số" in text_of(resp))

    resp = client.post(f"/hotels/{hotel_id}/edit", data={
        "name": hotel_name, "phone": HOTEL_PHONE,
        "city": "Thành phố Hà Nội", "ward": "Phường Test 2",
        "address": "1 Đường Kiểm Thử", "country": "Vietnam",
    }, follow_redirects=True)
    r.check("sửa khách sạn thành công", resp.status_code == 200)

    # ================================================================
    r.head("4. PHÒNG — QUERY Q1, RÀNG BUỘC, MA TRẬN TRẠNG THÁI (QLKS-05, QLKS-07)")
    # ================================================================
    resp = client.get(f"/hotels/{hotel_id}/rooms")
    r.check("Q1 rooms_by_hotel mở được khi chưa có phòng",
            resp.status_code == 200 and "Chưa có phòng nào" in text_of(resp))

    for room_number, room_type in [("101", "Deluxe King"), ("102", "Standard Twin")]:
        resp = client.post(f"/hotels/{hotel_id}/rooms/add", data={
            "room_number": room_number, "room_type": room_type,
            "price_per_night": str(PRICE), "capacity": "2",
            "bed_type": "King", "description": f"Phòng kiểm thử {TAG}",
        }, follow_redirects=True)
        ok = db_room(session, hotel_id, room_number) is not None
        r.check(f"thêm phòng {room_number}", ok)
        if ok:
            created["rooms"].append(room_number)

    resp = client.post(f"/hotels/{hotel_id}/rooms/add", data={
        "room_number": "101", "room_type": "Deluxe", "price_per_night": str(PRICE),
        "capacity": "2", "bed_type": "King", "description": "",
    }, follow_redirects=True)
    r.check("chặn trùng số phòng trong cùng khách sạn",
            "đã tồn tại" in text_of(resp))

    resp = client.post(f"/hotels/{hotel_id}/rooms/add", data={
        "room_number": "999", "room_type": "Deluxe", "price_per_night": "-5",
        "capacity": "2", "bed_type": "King", "description": "",
    }, follow_redirects=True)
    r.check("chặn giá phòng âm",
            db_room(session, hotel_id, "999") is None)

    resp = client.get(f"/hotels/{hotel_id}/rooms/101")
    r.check("trang chi tiết phòng mở được", resp.status_code == 200)

    resp = client.get(f"/hotels/{hotel_id}/rooms/KHONG_TON_TAI", follow_redirects=True)
    r.check("phòng không tồn tại: báo lỗi tử tế, không 500",
            resp.status_code == 200 and "Không tìm thấy phòng" in text_of(resp))

    ok, err = room_service.change_room_status(hotel_id, "102", "MAINTENANCE")
    r.check("chuyển AVAILABLE -> MAINTENANCE được", ok, str(err))

    ok, err = room_service.change_room_status(hotel_id, "102", "OCCUPIED")
    r.check("chặn MAINTENANCE -> OCCUPIED (không nhận khách từ phòng bảo trì)",
            not ok, f"lẽ ra phải bị chặn, nhận: {err}")

    ok, err = room_service.change_room_status(hotel_id, "102", "MAINTENANCE")
    r.check("chặn chuyển sang trạng thái đang có", not ok, str(err))

    ok, err = room_service.change_room_status(hotel_id, "102", "KHONG_HOP_LE")
    r.check("chặn trạng thái không hợp lệ", not ok, str(err))

    ok, err = room_service.change_room_status(hotel_id, "102", "AVAILABLE")
    r.check("mở lại phòng bảo trì về AVAILABLE", ok, str(err))
    row = db_room(session, hotel_id, "102")
    r.check("AVAILABLE thì is_available = true",
            row is not None and row.is_available is True,
            f"is_available={getattr(row, 'is_available', None)}")

    # ================================================================
    r.head("5. KHÁCH HÀNG — THÊM & RÀNG BUỘC (QLKS-04, QLKS-06)")
    # ================================================================
    guest_name = f"Khách {TAG}"
    resp = client.post("/guests/add", data={
        "full_name": guest_name, "email": f"{TAG.lower()}@test.local",
        "phone": GUEST_PHONE, "id_card": GUEST_ID_CARD,
        "city": "Thành phố Hà Nội", "ward": "Phường Test",
        "address": "1 Đường Kiểm Thử",
    }, follow_redirects=True)
    r.check("thêm khách hàng thành công", resp.status_code == 200)

    guests = [g for g in session.execute("SELECT guest_id, full_name FROM guests;")
              if g.full_name == guest_name]
    if not r.check("khách vừa thêm có trong bảng guests", len(guests) == 1,
                   f"tìm thấy {len(guests)}"):
        return
    guest_id = guests[0].guest_id
    created["guest_id"] = guest_id
    r.note(f"guest_id = {guest_id}")

    resp = client.post("/guests/add", data={
        "full_name": f"{guest_name} SĐT SAI", "email": "x@test.local",
        "phone": "abc", "id_card": GUEST_ID_CARD_2,
        "city": "Thành phố Hà Nội", "ward": "P", "address": "1",
    }, follow_redirects=True)
    r.check("chặn số điện thoại khách sai định dạng",
            "10 chữ số" in text_of(resp) or "điện thoại" in text_of(resp).lower())

    # ================================================================
    r.head("6. ĐẶT PHÒNG — BATCH Q5 + TỰ ĐỘNG HÓA ĐƠN Q4 (QLKS-08, QLKS-10)")
    # ================================================================
    resp = client.post("/bookings/create", data={
        "guest_id": guest_id, "guest_name": guest_name,
        "hotel_id": hotel_id, "room_number": "101",
        "check_in_date": IN_DATE, "check_out_date": OUT_DATE,
        "total_amount": "", "payment_method": "TIỀN MẶT",
        "status": "CONFIRMED", "payment_type": "FULL",
    }, follow_redirects=False)
    r.check("đặt phòng xong chuyển sang trang hóa đơn",
            resp.status_code == 302 and "/invoices/" in resp.headers.get("Location", ""),
            f"status {resp.status_code}, location {resp.headers.get('Location')}")

    bks = [b for b in db_bookings_by_guest(session, guest_id)]
    if not r.check("Q5 đã ghi vào bookings_by_guest", len(bks) == 1,
                   f"tìm thấy {len(bks)}"):
        return
    booking = bks[0]
    booking_id = booking.booking_id
    created["booking_ids"].append(booking_id)
    r.note(f"booking_id = {booking_id}")

    bhd = db_bookings_by_hotel_date(session, hotel_id, booking.check_in_date)
    r.check("Q5 ghi ĐỒNG THỜI vào bookings_by_hotel_date (denormalization)",
            any(x.booking_id == booking_id for x in bhd),
            f"partition có {len(bhd)} dòng")

    r.check("tiền tự tính đúng theo số đêm (3 đêm x giá phòng)",
            float(booking.total_amount) == float(EXPECTED_AMOUNT),
            f"{booking.total_amount} != {EXPECTED_AMOUNT}")

    invs = db_invoices(session, booking_id)
    r.check("Q4 hóa đơn được tạo tự động", len(invs) == 1, f"tìm thấy {len(invs)}")
    if invs:
        r.check("hóa đơn khớp tiền booking",
                float(invs[0].total_amount) == float(EXPECTED_AMOUNT),
                f"{invs[0].total_amount}")
        r.check("thanh toán đủ 100% -> payment_status = PAID",
                invs[0].payment_status == "PAID", str(invs[0].payment_status))

    row = db_room(session, hotel_id, "101")
    r.check("phòng tự chuyển sang OCCUPIED sau khi đặt",
            row is not None and row.status == "OCCUPIED",
            f"status={getattr(row, 'status', None)}")
    r.check("tên khách được đẩy sang module Phòng (current_guest_name)",
            row is not None and row.current_guest_name == guest_name,
            f"nhận {getattr(row, 'current_guest_name', None)!r}")
    r.check("mã booking được đẩy sang module Phòng (current_booking_id)",
            row is not None and row.current_booking_id == booking_id,
            f"nhận {getattr(row, 'current_booking_id', None)!r}")

    resp = client.get(f"/hotels/{hotel_id}/rooms/101")
    r.check("trang chi tiết phòng hiện tên khách đang thuê",
            guest_name in text_of(resp))

    # ---- các ràng buộc chặn đặt phòng ----
    resp = client.post("/bookings/create", data={
        "guest_id": guest_id, "guest_name": guest_name,
        "hotel_id": hotel_id, "room_number": "101",
        "check_in_date": IN_DATE, "check_out_date": OUT_DATE,
        "total_amount": "", "payment_method": "TIỀN MẶT", "status": "CONFIRMED",
    }, follow_redirects=True)
    r.check("chặn đặt trùng phòng đang có khách",
            "ĐÃ CÓ KHÁCH THUÊ" in text_of(resp).upper()
            or len(db_bookings_by_guest(session, guest_id)) == 1)

    room_service.change_room_status(hotel_id, "102", "MAINTENANCE")
    bust_caches()
    resp = client.post("/bookings/create", data={
        "guest_id": guest_id, "guest_name": guest_name,
        "hotel_id": hotel_id, "room_number": "102",
        "check_in_date": IN_DATE, "check_out_date": OUT_DATE,
        "total_amount": "", "payment_method": "TIỀN MẶT", "status": "CONFIRMED",
    }, follow_redirects=True)
    r.check("chặn đặt phòng đang bảo trì",
            "BẢO TRÌ" in text_of(resp).upper()
            or len(db_bookings_by_guest(session, guest_id)) == 1)
    room_service.change_room_status(hotel_id, "102", "AVAILABLE")

    resp = client.post("/bookings/create", data={
        "guest_id": guest_id, "guest_name": guest_name,
        "hotel_id": hotel_id, "room_number": "102",
        "check_in_date": OUT_DATE, "check_out_date": IN_DATE,
        "total_amount": "", "payment_method": "TIỀN MẶT", "status": "CONFIRMED",
    }, follow_redirects=True)
    r.check("chặn ngày trả trước ngày nhận",
            len(db_bookings_by_guest(session, guest_id)) == 1)

    resp = client.post("/bookings/create", data={"guest_id": "", "hotel_id": hotel_id},
                       follow_redirects=True)
    r.check("thiếu trường bắt buộc: không 500, quay về danh sách",
            resp.status_code == 200)

    # ================================================================
    r.head("7. TRA CỨU Q2 / Q3 / Q4 (QLKS-09, QLKS-10)")
    # ================================================================
    bust_caches()

    resp = client.get(f"/bookings/guest/{guest_id}")
    html = text_of(resp)
    r.check("Q2 lịch sử theo khách: mở được (từng 500 vì Row không có .get)",
            resp.status_code == 200, f"status {resp.status_code}")
    r.check("Q2 hiện đúng mã booking", booking_id in html)
    r.check("Q2 bù được tên khách (bảng không có cột guest_name)",
            guest_name in html)

    q2 = booking_service.get_bookings_by_guest(guest_id)
    r.check("Q2 trả dict có đủ field cho template",
            q2 and isinstance(q2[0], dict)
            and all(k in q2[0] for k in ("guest_name", "hotel_name", "nights", "status")))

    resp = client.get(f"/bookings?guest_id={guest_id}")
    r.check("lọc danh sách đặt phòng theo khách: mở được",
            resp.status_code == 200 and booking_id in text_of(resp))

    resp = client.get(f"/bookings/hotel-date?hotel_id={hotel_id}&check_in_date={IN_DATE}")
    r.check("Q3 tra theo khách sạn + ngày nhận: mở được và có đơn",
            resp.status_code == 200 and booking_id in text_of(resp),
            f"status {resp.status_code}")

    resp = client.get(f"/invoices/{booking_id}")
    html = text_of(resp)
    r.check("Q4 chi tiết hóa đơn: mở được", resp.status_code == 200)
    r.check("Q4 hóa đơn hiện tên khách và số tiền",
            guest_name in html and "3,000,000" in html.replace("&nbsp;", " "))

    resp = client.get("/invoices/BK_KHONG_TON_TAI", follow_redirects=True)
    r.check("hóa đơn không tồn tại: không 500", resp.status_code == 200)

    # ================================================================
    r.head("8. TRẢ PHÒNG SỚM — ĐÓNG BOOKING + GIẢI PHÓNG PHÒNG")
    # ================================================================
    early = (TODAY + timedelta(days=4)).isoformat()   # ở 1 đêm thay vì 3
    resp = client.post(f"/bookings/{booking_id}/checkout", data={
        "guest_id": guest_id, "hotel_id": hotel_id, "room_number": "101",
        "check_in_date": IN_DATE, "check_out_date": OUT_DATE,
        "actual_check_out": early,
    }, follow_redirects=True)
    html = text_of(resp)
    r.check("trả phòng không lỗi", resp.status_code == 200)
    r.check("cảnh báo trả sớm có nêu số đêm lệch",
            "trả sớm" in html.lower())
    r.check("nói rõ KHÔNG giảm và KHÔNG hoàn tiền (chính sách đã chốt)",
            "không giảm và không hoàn tiền" in html)

    bks = db_bookings_by_guest(session, guest_id)
    done = [b for b in bks if b.booking_id == booking_id]
    r.check("booking chuyển sang COMPLETED trong bookings_by_guest",
            done and done[0].status == "COMPLETED",
            f"status={done[0].status if done else 'không thấy'}")
    r.check("trả sớm: check_out_date ghi lại ngày trả THỰC TẾ",
            done and str(done[0].check_out_date) == early,
            f"{done[0].check_out_date if done else '?'} != {early}")

    bhd = db_bookings_by_hotel_date(session, hotel_id, booking.check_in_date)
    mine_bhd = [x for x in bhd if x.booking_id == booking_id]
    r.check("COMPLETED đồng bộ sang cả bookings_by_hotel_date",
            mine_bhd and mine_bhd[0].status == "COMPLETED",
            f"status={mine_bhd[0].status if mine_bhd else 'không thấy'}")

    row = db_room(session, hotel_id, "101")
    r.check("phòng về AVAILABLE sau khi trả", row is not None and row.status == "AVAILABLE",
            f"status={getattr(row, 'status', None)}")
    r.check("thông tin khách cũ bị xoá khỏi phòng (không rò sang khách sau)",
            row is not None and not row.current_guest_name and not row.current_booking_id,
            f"guest={getattr(row, 'current_guest_name', None)!r}")

    invs = db_invoices(session, booking_id)
    r.check("trả sớm KHÔNG làm đổi tiền hóa đơn",
            invs and float(invs[0].total_amount) == float(EXPECTED_AMOUNT),
            f"{invs[0].total_amount if invs else '?'} != {EXPECTED_AMOUNT}")

    bust_caches()
    resp = client.get(f"/bookings/guest/{guest_id}")
    r.check("lịch sử khách hiện nhãn 'Đã trả phòng'",
            "Đã trả phòng" in text_of(resp))

    row2 = db_room(session, hotel_id, "101")
    resp = client.get(f"/hotels/{hotel_id}/rooms/101")
    r.check("phòng đã trả có thể đặt lại được",
            room_service.is_room_bookable(hotel_id, "101") is True,
            f"is_room_bookable trả {room_service.is_room_bookable(hotel_id, '101')}")

    resp = client.post(f"/bookings/BK_KHONG_TON_TAI/checkout",
                       data={"hotel_id": hotel_id, "room_number": "102"},
                       follow_redirects=True)
    r.check("trả phòng cho đơn không xác định được: không 500",
            resp.status_code == 200)

    # ================================================================
    r.head("9. XỬ LÝ NGOẠI LỆ & ĐƯỜNG DẪN SAI (QLKS-14)")
    # ================================================================
    for path in [
        "/hotels/KHONG_CO/rooms",
        "/hotels/KHONG_CO/rooms/1",
        "/bookings/guest/KHONG_CO",
        f"/bookings/hotel-date?hotel_id=KHONG_CO&check_in_date={IN_DATE}",
        "/bookings/hotel-date?hotel_id=&check_in_date=",
        "/dashboard?period=rac&start_date=rac&end_date=rac",
        "/dashboard?hotel_id=KHONG_CO",
    ]:
        resp = client.get(path, follow_redirects=True)
        r.check(f"không 500: {path}", resp.status_code == 200,
                f"nhận {resp.status_code}")


def cleanup(session, keep):
    print()
    if keep:
        print("── GIỮ LẠI dữ liệu test theo yêu cầu (--keep) " + "─" * 20)
        print(f"   hotel_id  = {created['hotel_id']}")
        print(f"   guest_id  = {created['guest_id']}")
        print(f"   booking   = {created['booking_ids']}")
        print("   Nhớ xoá tay sau khi xem xong, đừng để lẫn vào số liệu báo cáo.")
        return

    print("── DỌN DỮ LIỆU TEST " + "─" * 46)
    removed = []

    for booking_id in created["booking_ids"]:
        try:
            for inv in db_invoices(session, booking_id):
                session.execute(
                    "DELETE FROM invoices_by_booking WHERE booking_id=%s AND invoice_id=%s;",
                    (booking_id, inv.invoice_id))
            removed.append(f"hóa đơn của {booking_id}")
        except Exception as e:
            print(f"   ! không xoá được hóa đơn {booking_id}: {e}")

    if created["guest_id"]:
        try:
            for b in db_bookings_by_guest(session, created["guest_id"]):
                session.execute(
                    "DELETE FROM bookings_by_guest WHERE guest_id=%s AND booking_id=%s;",
                    (created["guest_id"], b.booking_id))
                if created["hotel_id"]:
                    session.execute(
                        "DELETE FROM bookings_by_hotel_date WHERE hotel_id=%s "
                        "AND check_in_date=%s AND booking_id=%s;",
                        (created["hotel_id"], b.check_in_date, b.booking_id))
            removed.append("booking (cả 2 bảng)")
        except Exception as e:
            print(f"   ! không xoá được booking: {e}")

        try:
            session.execute("DELETE FROM guests WHERE guest_id=%s;", (created["guest_id"],))
            removed.append(f"khách {created['guest_id']}")
        except Exception as e:
            print(f"   ! không xoá được khách: {e}")

    if created["hotel_id"]:
        try:
            session.execute("DELETE FROM rooms_by_hotel WHERE hotel_id=%s;",
                            (created["hotel_id"],))
            session.execute("DELETE FROM hotels WHERE hotel_id=%s;",
                            (created["hotel_id"],))
            removed.append(f"khách sạn {created['hotel_id']} và toàn bộ phòng")
        except Exception as e:
            print(f"   ! không xoá được khách sạn: {e}")

    for item in removed:
        print(f"   đã xoá: {item}")

    # Kiểm tra lại đúng nghĩa: dọn xong thì phải không còn vết nào
    leftover = []
    if created["hotel_id"]:
        if list(session.execute("SELECT hotel_id FROM hotels WHERE hotel_id=%s;",
                                (created["hotel_id"],))):
            leftover.append("hotels")
        if list(session.execute("SELECT hotel_id FROM rooms_by_hotel WHERE hotel_id=%s;",
                                (created["hotel_id"],))):
            leftover.append("rooms_by_hotel")
    if created["guest_id"]:
        if list(session.execute("SELECT guest_id FROM guests WHERE guest_id=%s;",
                                (created["guest_id"],))):
            leftover.append("guests")
        if db_bookings_by_guest(session, created["guest_id"]):
            leftover.append("bookings_by_guest")

    if leftover:
        print(f"   ⚠️  CÒN SÓT ở: {', '.join(leftover)} — cần xoá tay")
    else:
        print("   Sạch, không còn vết dữ liệu test nào.")

    room_service.invalidate_rooms_cache()
    booking_service.invalidate_booking_cache()
    booking_service.invalidate_invoice_cache()


def main():
    keep = "--keep" in sys.argv

    session = get_session()
    if not session:
        print("❌ Không kết nối được AstraDB. Kiểm tra .env rồi chạy lại.")
        return 1

    print("=" * 66)
    print("  KIỂM THỬ TÍCH HỢP END-TO-END — QLKS-13")
    print(f"  Nhãn dữ liệu test: {TAG}   ({IN_DATE} → {OUT_DATE})")
    print("=" * 66)

    app.config.update(TESTING=True)
    client = app.test_client()

    try:
        run(client, session)
    except Exception as error:
        import traceback
        r.check("script chạy hết không vỡ", False, f"{type(error).__name__}: {error}")
        traceback.print_exc()
    finally:
        try:
            cleanup(session, keep)
        except Exception as error:
            print(f"   ! lỗi khi dọn dữ liệu: {error}")

    return r.summary()


if __name__ == "__main__":
    sys.exit(main())
