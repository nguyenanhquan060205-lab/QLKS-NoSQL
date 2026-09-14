# 🏨 ĐỒ ÁN MÔN HỌC: QUẢN LÝ KHÁCH SẠN (NoSQL - APACHE CASSANDRA / ASTRADB)

> **Công nghệ:** Python Flask, Apache Cassandra / DataStax AstraDB, Tailwind CSS v4.  
> **Thời hạn nộp:** Thứ 6 (Chốt hoàn tất toàn bộ: **24h00 Thứ 5, ngày 17/09/2026**).  
> **Số lượng thành viên:** 3 người (Làm việc song song).

---

## 👥 BẢNG PHÂN CHIA NHIỆM VỤ 3 THÀNH VIÊN

| Thành viên | Phụ trách nghiệp vụ | Bảng Cassandra (CQL) | File Code Backend & Frontend |
| :--- | :--- | :--- | :--- |
| **Định** | **Khách sạn, Phòng & Khách hàng**<br>- Xem & thêm khách sạn<br>- Xem & thêm phòng theo KS (**Query Q1**)<br>- Quản lý hồ sơ khách hàng | `hotels`<br>`rooms_by_hotel`<br>`guests` | - `services/hotel_service.py`<br>- `routes/hotel_routes.py`<br>- `templates/hotels.html`<br>- `templates/rooms.html`<br>- `templates/guests.html` |
| **Quân** | **Đặt phòng & Hóa đơn**<br>- Đặt phòng BATCH (**Query Q5**)<br>- Lịch sử đặt theo khách (**Query Q2**)<br>- Lịch sử theo KS & ngày (**Query Q3**)<br>- Tra cứu hóa đơn (**Query Q4**) | `bookings_by_guest`<br>`bookings_by_hotel_date`<br>`invoices_by_booking` | - `services/booking_service.py`<br>- `routes/booking_routes.py`<br>- `templates/bookings.html`<br>- `templates/invoices.html` |
| **Như** | **Hạ tầng, Giao diện chung & Thống kê**<br>- Tạo Keyspace & Tables trên AstraDB<br>- Kết nối AstraDB (`database/db.py`)<br>- Layout chung (Navbar, Footer)<br>- Trang chủ & Dashboard thống kê | Keyspace: `hotel_ks`<br>(Chạy `cql/schema.cql`) | - `database/db.py`<br>- `services/dashboard_service.py`<br>- `routes/dashboard_routes.py`<br>- `templates/base.html`<br>- `templates/index.html`<br>- `templates/dashboard.html`<br>- `static/css/style.css`<br>- `static/js/main.js` |

👉 **Xem chi tiết kế hoạch quản lý tiến độ Sprint:** [README_JIRA.md](README_JIRA.md) (Gồm Story Points, Tiêu chuẩn chấp nhận AC, Biểu đồ Gantt).

---

## 📂 CẤU TRÚC THƯ MỤC DỰ ÁN

```text
QLKS-NoSQL/
├── app.py                         # File chạy chính của Flask (Đăng ký Blueprints)
├── requirements.txt               # Danh sách thư viện cần cài đặt
├── .env.example                   # Mẫu cấu hình môi trường AstraDB
├── cql/
│   └── schema.cql                 # Toàn bộ script DDL tạo bảng & dữ liệu mẫu (PDF)
│
├── database/
│   ├── __init__.py
│   └── db.py                      # [Như] Khung hàm kết nối AstraDB
│
├── services/                      # Tầng xử lý logic & truy vấn CQL
│   ├── __init__.py
│   ├── hotel_service.py           # [Định] Khung hàm CQL Khách sạn, Phòng, Khách
│   ├── booking_service.py         # [Quân] Khung hàm CQL Đặt phòng BATCH, Hóa đơn
│   └── dashboard_service.py       # [Như] Khung hàm tính toán thống kê
│
├── routes/                        # Tầng điều hướng Flask Blueprint
│   ├── __init__.py
│   ├── hotel_routes.py            # [Định] Route xem/thêm Khách sạn, Phòng, Khách
│   ├── booking_routes.py          # [Quân] Route Đặt phòng, Tìm kiếm, Hóa đơn
│   └── dashboard_routes.py        # [Như] Route Trang chủ & Dashboard
│
├── templates/                     # Giao diện HTML (Jinja2)
│   ├── base.html                  # [Như] Khung layout chung (Navbar, Tailwind CSS v4)
│   ├── index.html                 # [Như] Khung trang chủ
│   ├── hotels.html                # [Định] Khung danh sách khách sạn
│   ├── rooms.html                 # [Định] Khung danh sách phòng (Query Q1)
│   ├── guests.html                # [Định] Khung danh sách khách hàng
│   ├── bookings.html              # [Quân] Khung đặt phòng & tra cứu (Q2, Q3, Q5)
│   ├── invoices.html              # [Quân] Khung hóa đơn thanh toán (Query Q4)
│   └── dashboard.html             # [Như] Khung biểu đồ / thẻ thống kê
│
└── static/
    ├── css/
    │   └── style.css              # [Như] File CSS tùy chỉnh
    └── js/
        └── main.js                # [Như] File Javascript tùy chỉnh
```

---

## 🚀 HƯỚNG DẪN CHẠY DỰ ÁN

### 1. Cài đặt thư viện
```bash
pip install -r requirements.txt
```

### 2. Khởi chạy ứng dụng Flask
```bash
python app.py
```
Truy cập trình duyệt: **http://127.0.0.1:5000**

---

## 📋 HƯỚNG DẪN CHI TIẾT TỪNG THÀNH VIÊN

### 👤 Định:
1. Mở file [cql/schema.cql](file:///Users/quan/HUIT_CNTT/NoSQL/QLKS-NoSQL/cql/schema.cql) để xem cấu trúc 3 bảng: `hotels`, `rooms_by_hotel`, `guests`.
2. Mở file [services/hotel_service.py](file:///Users/quan/HUIT_CNTT/NoSQL/QLKS-NoSQL/services/hotel_service.py) và viết code thực thi các câu lệnh CQL tương ứng trong từng hàm.
3. Mở file [routes/hotel_routes.py](file:///Users/quan/HUIT_CNTT/NoSQL/QLKS-NoSQL/routes/hotel_routes.py) để gọi các hàm từ service và xử lý dữ liệu form gửi lên.
4. Mở các file giao diện tương ứng trong `templates/` (`hotels.html`, `rooms.html`, `guests.html`) để dựng form nhập liệu và bảng hiển thị.

### 👤 Quân:
1. Mở file [cql/schema.cql](file:///Users/quan/HUIT_CNTT/NoSQL/QLKS-NoSQL/cql/schema.cql) để xem cấu trúc bảng: `bookings_by_guest`, `bookings_by_hotel_date`, `invoices_by_booking`.
2. Mở file [services/booking_service.py](file:///Users/quan/HUIT_CNTT/NoSQL/QLKS-NoSQL/services/booking_service.py):
   - Viết hàm `create_booking_batch` dùng `BEGIN BATCH ... APPLY BATCH;` ghi đồng thời vào cả 2 bảng đặt phòng (Query Q5).
   - Viết các hàm tra cứu theo khách (Q2), tra cứu theo khách sạn & ngày (Q3), lấy hóa đơn (Q4).
3. Mở file [routes/booking_routes.py](file:///Users/quan/HUIT_CNTT/NoSQL/QLKS-NoSQL/routes/booking_routes.py) để kết nối request từ giao diện với service.
4. Mở các file `templates/bookings.html` và `templates/invoices.html` để thiết kế giao diện đặt phòng và xem hóa đơn.

### 👤 Như:
1. Đăng ký tài khoản DataStax AstraDB, tạo Database và Keyspace `hotel_ks`.
2. Mở CQL Console trên AstraDB, copy toàn bộ nội dung trong [cql/schema.cql](file:///Users/quan/HUIT_CNTT/NoSQL/QLKS-NoSQL/cql/schema.cql) để chạy tạo bảng và insert dữ liệu mẫu.
3. Tải file `secure-connect-*.zip` và tạo `Token (Database Administrator)`.
4. Cấu hình file `.env` và hoàn thiện hàm `get_session()` trong [database/db.py](file:///Users/quan/HUIT_CNTT/NoSQL/QLKS-NoSQL/database/db.py).
5. Hoàn thiện [templates/base.html](file:///Users/quan/HUIT_CNTT/NoSQL/QLKS-NoSQL/templates/base.html), [templates/index.html](file:///Users/quan/HUIT_CNTT/NoSQL/QLKS-NoSQL/templates/index.html), và xây dựng trang [templates/dashboard.html](file:///Users/quan/HUIT_CNTT/NoSQL/QLKS-NoSQL/templates/dashboard.html).
