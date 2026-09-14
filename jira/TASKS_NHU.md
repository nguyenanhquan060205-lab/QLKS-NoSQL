# 👤 NHIỆM VỤ CHI TIẾT: NHƯ
## 🏨 Module: Hạ Tầng Database AstraDB, Layout Tailwind & Dashboard Thống Kê

> **Tổng Story Points:** 11 SP  
> **Thời gian:** Bắt đầu Thứ 2 (14/09) - Setup Database cho cả nhóm ➡️ Hoàn thành trước Thứ 5.  
> **Nhiệm vụ cốt lõi:** Đảm bảo Database chạy mượt mà để Định và Quân có thể kết nối code được!

---

## 📋 CHECKLIST CÔNG VIỆC CỦA NHƯ

### 1. Hạ Tầng DataStax AstraDB (Thứ 2 - Quan trọng nhất)
- [ ] **`QLKS-01`** Đăng ký tài khoản miễn phí trên [DataStax AstraDB](https://astra.datastax.com/).
- [ ] **`QLKS-01`** Tạo Database mới:
  - Database Name: `hotel_db`
  - Keyspace Name: `hotel_ks`
  - Cloud Provider: AWS hoặc GCP (chọn khu vực Singapore hoặc gần nhất).
- [ ] **`QLKS-01`** Mở tab **CQL Console** trên AstraDB:
  - Mở file [cql/schema.cql](file:///Users/quan/HUIT_CNTT/NoSQL/QLKS-NoSQL/cql/schema.cql) trong dự án.
  - Copy toàn bộ nội dung và paste vào CQL Console để chạy tạo 6 bảng và dữ liệu mẫu.
- [ ] **`QLKS-02`** Tải **Secure Connect Bundle**:
  - Vào phần Connect ➡️ Python ➡️ Tải file zip `secure-connect-hotel-db.zip`.
  - Copy file zip này bỏ vào thư mục dự án `QLKS-NoSQL/`.
- [ ] **`QLKS-02`** Tạo **Application Token**:
  - Quyền hạn: `Database Administrator`.
  - Lưu lại mã Token (dạng `AstraCS:...`).
- [ ] **`QLKS-02`** Cấu hình file `.env`:
  ```ini
  ASTRA_DB_SECURE_BUNDLE_PATH=secure-connect-hotel-db.zip
  ASTRA_DB_TOKEN=AstraCS:your_actual_token_here
  ASTRA_DB_KEYSPACE=hotel_ks
  ```
- [ ] **`QLKS-02`** Bỏ comment và hoàn thiện hàm kết nối trong [database/db.py](file:///Users/quan/HUIT_CNTT/NoSQL/QLKS-NoSQL/database/db.py):
  ```python
  from cassandra.cluster import Cluster
  from cassandra.auth import PlainTextAuthProvider

  cloud_config = {'secure_connect_bundle': bundle_path}
  auth_provider = PlainTextAuthProvider('token', token)
  cluster = Cluster(cloud=cloud_config, auth_provider=auth_provider)
  _session = cluster.connect(keyspace)
  ```
  Chạy lệnh test: `python3 -c "from database.db import get_session; s = get_session(); print(s)"` xem có in ra Session thành công không.

---

### 2. Giao Diện Chung & Layout Tailwind CSS v4
- [ ] **`QLKS-03`** Kiểm tra và tinh chỉnh [templates/base.html](file:///Users/quan/HUIT_CNTT/NoSQL/QLKS-NoSQL/templates/base.html):
  - Đảm bảo thanh Navbar hiển thị đẹp trên cả Desktop và Mobile.
  - Các đường link dẫn đúng tới trang của Định (`/hotels`, `/guests`), Quân (`/bookings`), và Như (`/`, `/dashboard`).
- [ ] **`QLKS-12`** Hoàn thiện [templates/index.html](file:///Users/quan/HUIT_CNTT/NoSQL/QLKS-NoSQL/templates/index.html):
  - Trang chủ giới thiệu hệ thống quản lý khách sạn NoSQL.

---

### 3. Dashboard Thống Kê & Báo Cáo
- [ ] **`QLKS-12`** Viết hàm thống kê trong [services/dashboard_service.py](file:///Users/quan/HUIT_CNTT/NoSQL/QLKS-NoSQL/services/dashboard_service.py):
  - Đếm tổng số khách sạn: `SELECT count(*) FROM hotels;`
  - Đếm tổng số lượt đặt phòng: `SELECT count(*) FROM bookings_by_guest;`
  - Đếm số phòng trống và ước tính doanh thu.
- [ ] **`QLKS-12`** Hoàn thiện giao diện [templates/dashboard.html](file:///Users/quan/HUIT_CNTT/NoSQL/QLKS-NoSQL/templates/dashboard.html):
  - Dùng Tailwind CSS dựng 4 Card chỉ số (Grid 4 cột: Khách sạn, Phòng trống, Lượt đặt, Doanh thu).
  - (Tuỳ chọn thêm điểm cộng): Nhúng biểu đồ Chart.js trực quan.

---

## 🎯 TIÊU CHUẨN HOÀN THÀNH (Definition of Done)
- Cung cấp file bundle zip và token hoặc file `.env` chuẩn cho Định và Quân để 2 bạn kết nối được Database trên máy của mình.
- Chạy ứng dụng không bị lỗi kết nối DB.
- Hoàn thành chậm nhất vào **Thứ Tư (16/09)** để Thứ Năm test tổng thể cùng nhóm!
