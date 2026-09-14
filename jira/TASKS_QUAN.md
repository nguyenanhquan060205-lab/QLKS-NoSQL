# 👤 NHIỆM VỤ CHI TIẾT: QUÂN
## 🏨 Module: Đặt Phòng BATCH Statement & Hóa Đơn (Core Transactions)

> **Tổng Story Points:** 13 SP  
> **Thời gian:** Thứ 2 ➡️ Hoàn thành trước Thứ 5 để test E2E.  
> **Bảng Cassandra:** `bookings_by_guest` (Query Q2), `bookings_by_hotel_date` (Query Q3), `invoices_by_booking` (Query Q4).  
> **Trọng tâm đề thi NoSQL:** Query Q5 (BATCH INSERT ghi đồng thời vào 2 bảng).

---

## 📋 CHECKLIST CÔNG VIỆC CỦA QUÂN

### 1. File [services/booking_service.py](file:///Users/quan/HUIT_CNTT/NoSQL/QLKS-NoSQL/services/booking_service.py) (Viết hàm CQL & BATCH)
- [ ] **`QLKS-08`** Viết hàm `create_booking_batch(...)` (**Trọng tâm Query Q5 - BATCH INSERT**):
  ```python
  from cassandra.query import BatchStatement
  from datetime import datetime

  session = get_session()
  batch = BatchStatement()

  # 1. Insert vào bảng tra cứu theo khách (bookings_by_guest)
  insert_guest = session.prepare("""
      INSERT INTO bookings_by_guest (guest_id, booking_id, hotel_id, room_number, check_in_date, check_out_date, status, total_amount)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?);
  """)
  batch.add(insert_guest, (guest_id, booking_id, hotel_id, room_number, check_in, check_out, status, total_amount))

  # 2. Insert vào bảng tra cứu theo KS & ngày (bookings_by_hotel_date)
  insert_hotel_date = session.prepare("""
      INSERT INTO bookings_by_hotel_date (hotel_id, check_in_date, booking_id, guest_id, guest_name, room_number, status)
      VALUES (?, ?, ?, ?, ?, ?, ?);
  """)
  batch.add(insert_hotel_date, (hotel_id, check_in, booking_id, guest_id, guest_name, room_number, status))

  # Thực thi BATCH
  session.execute(batch)
  ```
- [ ] **`QLKS-09`** Viết hàm `get_bookings_by_guest(guest_id)` (**Query Q2**):
  ```python
  query = "SELECT * FROM bookings_by_guest WHERE guest_id = %s;"
  rows = session.execute(query, (guest_id,))
  return list(rows)
  ```
- [ ] **`QLKS-09`** Viết hàm `get_bookings_by_hotel_date(hotel_id, check_in_date)` (**Query Q3**):
  ```python
  query = "SELECT * FROM bookings_by_hotel_date WHERE hotel_id = %s AND check_in_date = %s;"
  rows = session.execute(query, (hotel_id, check_in_date))
  return list(rows)
  ```
- [ ] **`QLKS-10`** Viết hàm `get_invoice_by_booking(booking_id)` (**Query Q4**):
  ```python
  query = "SELECT * FROM invoices_by_booking WHERE booking_id = %s;"
  row = session.execute(query, (booking_id,)).one()
  return row
  ```
- [ ] **`QLKS-10`** Viết hàm `create_invoice(...)` để tạo hóa đơn khi khách thanh toán.

---

### 2. File [routes/booking_routes.py](file:///Users/quan/HUIT_CNTT/NoSQL/QLKS-NoSQL/routes/booking_routes.py) (Flask Blueprint)
- [ ] **`QLKS-11`** Route `GET /bookings`: Hiển thị trang đặt phòng và danh sách tìm kiếm.
- [ ] **`QLKS-08`** Route `POST /bookings/create`: Nhận thông tin form đặt phòng, tạo `booking_id` ngẫu nhiên (UUID hoặc timestamp), gọi `create_booking_batch(...)`.
- [ ] **`QLKS-09`** Route `GET /bookings/guest/<guest_id>`: Xem lịch sử của khách theo Query Q2.
- [ ] **`QLKS-09`** Route `GET /bookings/hotel-date`: Tìm kiếm khách check-in theo khách sạn và ngày theo Query Q3.
- [ ] **`QLKS-10`** Route `GET /invoices/<booking_id>`: Lấy chi tiết hóa đơn theo Query Q4 truyền sang template `invoices.html`.

---

### 3. File Giao Diện Templates (Dùng Tailwind CSS v4)
- [ ] **[templates/bookings.html](file:///Users/quan/HUIT_CNTT/NoSQL/QLKS-NoSQL/templates/bookings.html)**:
  - Form tạo đặt phòng mới (chọn Mã khách, Mã KS, Số phòng, Ngày check-in, Ngày check-out, Tổng tiền).
  - Bộ lọc tra cứu:
    - Tìm theo Khách hàng (nhập guest_id) ➡️ Gọi Q2.
    - Tìm theo Khách sạn & Ngày (chọn hotel_id và ngày) ➡️ Gọi Q3.
  - Bảng danh sách kết quả tra cứu.
  - Nút *"Xem Hóa Đơn"* dẫn sang `/invoices/{{ booking.booking_id }}`.
- [ ] **[templates/invoices.html](file:///Users/quan/HUIT_CNTT/NoSQL/QLKS-NoSQL/templates/invoices.html)**:
  - Giao diện phiếu hóa đơn thanh toán đẹp mắt (Card Tailwind, thông tin khách, số phòng, số tiền, trạng thái PAID/UNPAID, nút In hóa đơn).

---

## 🎯 TIÊU CHUẨN HOÀN THÀNH (Definition of Done)
- Khi thực hiện đặt phòng, kiểm tra trên CQL Console của AstraDB thấy cả 2 bảng `bookings_by_guest` và `bookings_by_hotel_date` đều có bản ghi mới.
- Tra cứu Query Q2, Q3 và Q4 đều hiển thị đúng thông tin.
- Hoàn thành chậm nhất vào **Thứ Tư (16/09)** để Thứ Năm test tổng thể!
