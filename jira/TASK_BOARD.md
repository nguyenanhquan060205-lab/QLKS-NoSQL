# 📌 BẢNG THEO DÕI TIẾN ĐỘ JIRA KANBAN (TASK BOARD)
## 🏨 Đồ Án NoSQL: Quản Lý Khách Sạn (Cassandra / AstraDB)

> **Mục tiêu:** Cả 3 bạn dùng file này để theo dõi tiến độ hàng ngày. Khi hoàn thành task nào thì đổi `[ ]` thành `[x]`.  
> **Hard Deadline:** **24h00 Thứ Năm (17/09/2026)** chốt toàn bộ hệ thống!

---

## 📅 THEO DÕI THEO TỪNG NGÀY (DAILY CHECKLIST)

### 🗓️ THỨ HAI (14/09/2026): SETUP HẠ TẦNG & KHỞI TẠO
- [x] **[Chung]** Khởi tạo khung dự án Modular Flask & đẩy lên GitHub (`nguyenanhquan060205-lab/QLKS-NoSQL`).
- [ ] **`QLKS-01` [Như]** Tạo Database trên DataStax AstraDB & Keyspace `hotel_ks`.
- [ ] **`QLKS-01` [Như]** Chạy toàn bộ file `cql/schema.cql` trên CQL Console của AstraDB để tạo 6 bảng.
- [ ] **`QLKS-02` [Như]** Tải Secure Connect Bundle zip, lấy Token và cấu hình `.env` kết nối trong `database/db.py`.
- [ ] **`QLKS-04` [Định]** Khảo sát cấu trúc bảng `hotels` và `guests` trong `cql/schema.cql`.

---

### 🗓️ THỨ BA (15/09/2026): VIẾT CQL SERVICES & BATCH STATEMENT (CORE)
- [ ] **`QLKS-04` [Định]** Viết hàm `get_all_hotels()`, `create_hotel()`, `get_all_guests()`, `create_guest()` trong `services/hotel_service.py`.
- [ ] **`QLKS-05` [Định]** Viết hàm `get_rooms_by_hotel(hotel_id)` (Query Q1) và `create_room(...)` trong `services/hotel_service.py`.
- [ ] **`QLKS-08` [Quân]** Viết hàm `create_booking_batch(...)` dùng `BEGIN BATCH ... APPLY BATCH;` ghi đồng thời vào `bookings_by_guest` và `bookings_by_hotel_date` (Query Q5).
- [ ] **`QLKS-09` [Quân]** Viết hàm `get_bookings_by_guest(guest_id)` (Query Q2) và `get_bookings_by_hotel_date(...)` (Query Q3) trong `services/booking_service.py`.
- [ ] **`QLKS-03` [Như]** Hoàn thiện Navbar và Layout Tailwind CSS v4 trong `templates/base.html`.

---

### 🗓️ THỨ TƯ (16/09/2026): HOÀN THIỆN ROUTE FLASK & GIAO DIỆN TAILWIND
- [ ] **`QLKS-06` [Định]** Hoàn thiện Route `routes/hotel_routes.py` và giao diện `templates/hotels.html`, `templates/guests.html`.
- [ ] **`QLKS-07` [Định]** Hoàn thiện giao diện danh sách phòng theo khách sạn `templates/rooms.html`.
- [ ] **`QLKS-10` [Quân]** Viết hàm tra cứu hóa đơn `get_invoice_by_booking(booking_id)` (Query Q4) trong `services/booking_service.py`.
- [ ] **`QLKS-11` [Quân]** Hoàn thiện Route `routes/booking_routes.py` và giao diện đặt phòng `templates/bookings.html`, hóa đơn `templates/invoices.html`.
- [ ] **`QLKS-12` [Như]** Hoàn thiện hàm thống kê `services/dashboard_service.py`, trang chủ `templates/index.html` và dashboard `templates/dashboard.html`.

---

### 🗓️ THỨ NĂM (17/09/2026): TỔNG DUYỆT, TEST E2E & ĐÓNG DEADLINE (24H00)
- [ ] **`QLKS-13` [Cả nhóm]** Chạy kiểm thử luồng tích hợp End-to-End:
  - Thêm Khách sạn ➡️ Thêm Phòng ➡️ Thêm Khách (Định test).
  - Tạo Đặt phòng BATCH ➡️ Kiểm tra dữ liệu vào đủ 2 bảng (Quân test).
  - Tra cứu theo khách (Q2), tra cứu theo ngày (Q3) ➡️ Xem Hóa đơn (Q4).
  - Xem số liệu nhảy trên Dashboard thống kê (Như test).
- [ ] **`QLKS-14` [Cả nhóm]** Bắt các lỗi biên (Edge Cases), thông báo flash message thành công/thất bại.
- [ ] **`QLKS-15` [Cả nhóm]** Chụp ảnh màn hình giao diện web và CQL Console của AstraDB để làm báo cáo/slide.
- [ ] **[Cả nhóm]** Commit & Push toàn bộ code hoàn chỉnh lên nhánh `main` trước **24h00 Thứ Năm**.

---

## 📊 BẢNG TRẠNG THÁI TỔNG HỢP (JIRA KANBAN COLUMNS)

| Mã Ticket | Công việc | Assignee | Điểm SP | Trạng thái (To Do / In Progress / Done) |
| :--- | :--- | :---: | :---: | :---: |
| `QLKS-01` | Setup AstraDB & chạy schema CQL | **Như** | 3 SP | 📌 To Do |
| `QLKS-02` | Viết hàm kết nối AstraDB `db.py` | **Như** | 3 SP | 📌 To Do |
| `QLKS-03` | Hoàn thiện Base Layout Tailwind v4 | **Như** | 2 SP | 📌 To Do |
| `QLKS-04` | CQL Hotels & Guests Service | **Định** | 3 SP | 📌 To Do |
| `QLKS-05` | CQL Rooms by Hotel Service (Q1) | **Định** | 3 SP | 📌 To Do |
| `QLKS-06` | Route & UI Hotels / Guests | **Định** | 3 SP | 📌 To Do |
| `QLKS-07` | Route & UI Rooms by Hotel | **Định** | 2 SP | 📌 To Do |
| `QLKS-08` | BATCH INSERT Đặt phòng (Q5) | **Quân** | 5 SP | 📌 To Do |
| `QLKS-09` | Tra cứu lịch sử đặt phòng (Q2, Q3) | **Quân** | 3 SP | 📌 To Do |
| `QLKS-10` | Tra cứu Hóa đơn (Q4) | **Quân** | 2 SP | 📌 To Do |
| `QLKS-11` | Route & UI Đặt phòng + Hóa đơn | **Quân** | 3 SP | 📌 To Do |
| `QLKS-12` | Dashboard Thống kê & Trang chủ | **Như** | 3 SP | 📌 To Do |
| `QLKS-13` | Test tích hợp E2E toàn bộ luồng | **Cả 3** | 3 SP | 📌 To Do |
| `QLKS-14` | Xử lý lỗi biên & Tinh chỉnh UI | **Cả 3** | 2 SP | 📌 To Do |
| `QLKS-15` | Chụp ảnh demo, đóng gói nộp bài | **Cả 3** | 1 SP | 📌 To Do |
