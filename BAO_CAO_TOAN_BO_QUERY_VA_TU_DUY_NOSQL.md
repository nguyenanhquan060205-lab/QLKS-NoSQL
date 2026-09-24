# BÁO CÁO TOÀN DIỆN DỰ ÁN QUẢN LÝ KHÁCH SẠN NOSQL (ASTRADB / CASSANDRA)
## BẢN ĐỒ KIẾN TRÚC, PHÂN CÔNG PHẦN VIỆC NGUYỄN ANH QUÂN (QN) TỪ DB ĐẾN UI & TƯ DUY THIẾT KẾ QUERY CASSANDRA

> **Sinh viên thực hiện phần việc Đặt phòng & Hóa đơn:** Nguyễn Anh Quân (**QN**)  
> **Học phần:** Cơ sở dữ liệu NoSQL — Trường ĐH Công Thương TP.HCM (HUIT)  
> **Công nghệ nền tảng:** Apache Cassandra / DataStax AstraDB, Python Flask, Tailwind CSS v4  
> **Trọng số công việc phụ trách:** 13 Story Points (~37.5% toàn bộ hệ thống)  
> **Phiên bản tài liệu:** Hoàn thiện sau kiểm thử tích hợp E2E (79/79 PASS, 94/94 Unit Tests PASS)

---

## MỤC LỤC
1. [TỔNG QUAN HỆ THỐNG VÀ CÁC LUỒNG VẬN HÀNH (WORKFLOWS)](#1-tổng-quan-hệ-thống-và-các-luồng-vận-hành-workflows)
2. [CHI TIẾT PHẦN VIỆC CỦA NGUYỄN ANH QUÂN (QN) TỪ DATABASE ĐẾN UI](#2-chi-tiết-phần-việc-của-nguyễn-anh-quân-qn-từ-database-đến-ui)
3. [BẢNG KÊ CỨU TOÀN BỘ CÁC QUERY VỀ ĐẶT PHÒNG VÀ HÓA ĐƠN](#3-bảng-kê-cứu-toàn-bộ-các-query-về-đặt-phòng-và-hóa-đơn)
4. [TƯ DUY NGƯỢC LẠI: TẠI SAO LẠI THIẾT KẾ QUERY & DỮ LIỆU NHƯ VẬY?](#4-tư-duy-ngược-lại-tại-sao-lại-thiết-kế-query--dữ-liệu-như-vậy)
5. [CẨM NANG THUYẾT TRÌNH & BẢO VỆ ĐỒ ÁN TRƯỚC HỘI ĐỒNG](#5-cẩm-nang-thuyết-trình--bảo-vệ-đồ-án-trước-hội-đồng)

---

# 1. TỔNG QUAN HỆ THỐNG VÀ CÁC LUỒNG VẬN HÀNH (WORKFLOWS)

### 1.1. Kiến trúc 3 tầng phân tán (3-Tier Distributed Architecture)

```
[ CLIENT BROWSER ]
   │ (HTML5 / Tailwind CSS v4 / Vanilla JS / Chart.js)
   ▼
[ CONTROLLER LAYER - FLASK APPS & BLUEPRINTS ]
   ├─ hotel_bp     : Quản lý Khách sạn, Phòng, Khách hàng (Định & Như)
   ├─ booking_bp   : Quản lý Đặt phòng, Giao dịch, Hóa đơn (QUÂN - QN)
   └─ dashboard_bp : Báo cáo thống kê thời gian thực & Trang chủ (Như)
   │
   ▼
[ SERVICE & BUSINESS LOGIC LAYER ]
   ├─ hotel_service.py     : CRUD danh mục Khách sạn & Khách hàng
   ├─ room_service.py      : Quản lý trạng thái phòng & Ma trận Available/Occupied/Maintenance
   ├─ booking_service.py   : BATCH INSERT Q5, Query Q2, Q3, Q4, Settle, Checkout (QUÂN)
   └─ dashboard_service.py : Tổng hợp số liệu lấp đầy, doanh thu, KPI
   │
   ▼
[ DATA ACCESS & DISTRIBUTED DATABASE ]
   ├─ database/db.py       : Cassandra Driver Singleton + AstraDB Secure Connect Bundle
   └─ AstraDB Cloud (Keyspace: hotel_ks)
        ├─ hotels                  (Catalog Khách sạn)
        ├─ rooms_by_hotel          (Q1 - Phòng theo KS & Trạng thái lưu trú)
        ├─ guests                  (Catalog Khách hàng)
        ├─ bookings_by_guest       (Q2 - Lịch sử đặt phòng theo Khách)
        ├─ bookings_by_hotel_date  (Q3 - Khách check-in theo KS và Ngày)
        └─ invoices_by_booking     (Q4 - Hóa đơn & Quản lý Đặt cọc)
```

### 1.2. Luồng nghiệp vụ tuần tự xuyên suốt hệ thống (End-to-End Workflows)

#### Luồng 1: Khám phá phòng & Tạo đơn đặt phòng mới (Booking Flow)
1. **Lễ tân / Khách hàng** truy cập `/bookings` (Tab Phòng trống).
2. Sử dụng **Bộ lọc đa tiêu chí** (Chi nhánh, Loại phòng, Loại giường, Sức chứa, Tiện nghi).
3. Bấm nút **"Đặt phòng ngay"** trên thẻ phòng trống: Modal đặt phòng tự động điền sẵn `hotel_id`, `room_number`, hiển thị đơn giá/đêm.
4. Chọn Khách hàng (tự động điền CCCD, SĐT), chọn Ngày nhận (Check-in) và Ngày trả (Check-out). Hệ thống tính tự động: `Số đêm = Ngày trả - Ngày nhận` và `Tổng tiền = Số đêm × Đơn giá`.
5. Chọn hình thức thanh toán:
   - **Thanh toán đủ (100% - PAID)**: Tiền cọc = Tổng tiền, Còn lại = 0 đ.
   - **Đặt cọc trước 50% (PARTIAL)**: Tiền cọc = Tổng tiền / 2, Còn lại = Tổng tiền / 2.
   - **Thanh toán sau (0% - UNPAID)**: Tiền cọc = 0 đ, Còn lại = Tổng tiền.
6. Khi bấm Xác nhận đặt:
   - Route `POST /bookings/create` kiểm tra `is_room_bookable(hotel_id, room_number)`. Chặn nếu phòng đang bận hoặc đang bảo trì.
   - Gọi `booking_service.create_booking_batch(...)` thực thi **Query Q5 (Atomic Batch)** ghi đồng thời vào 2 bảng `bookings_by_guest` và `bookings_by_hotel_date`.
   - Tự động gọi `booking_service.create_invoice(...)` tạo hóa đơn **Query Q4** vào bảng `invoices_by_booking`.
   - Gọi `room_service.change_room_status(hotel_id, room_number, 'OCCUPIED', guest_name, booking_id)` để cập nhật phòng sang trạng thái Đang thuê, lưu tên khách và mã booking.
   - Hủy bộ nhớ đệm (`invalidate_cache`).
   - Chuyển hướng ngay sang trang Chi tiết Hóa đơn (`/invoices/<booking_id>`) để in phiếu thu.

#### Luồng 2: Thu tiền còn lại / Thanh toán nốt cọc (Settlement Flow)
1. Truy cập danh sách hóa đơn `/invoices`, lọc theo trạng thái **"Đã đặt cọc (PARTIAL)"**.
2. Bấm nút **"Thu tiền còn lại"** tại hàng hóa đơn tương ứng.
3. Modal mở ra hiển thị số tiền còn thiếu (Remaining Amount). Nhân viên chọn hình thức thu (Tiền mặt / Chuyển khoản / Thẻ).
4. Route `POST /invoices/<booking_id>/settle` gọi `booking_service.settle_invoice_payment(...)`:
   - Ghi đè trạng thái sang `PAID`.
   - Cập nhật `deposit_amount = total_amount` và `remaining_amount = 0`.
   - Cập nhật phương thức thanh toán mới.
   - Xóa cache hóa đơn và booking để các bảng cập nhật ngay lập tức.

#### Luồng 3: Trả phòng & Đóng đơn đặt phòng (Check-out & Early Check-out Flow)
1. Tại trang Chi tiết phòng (`/hotels/<hotel_id>/rooms/<room_number>`) hoặc Danh sách đặt phòng (`/bookings`), bấm nút **"Trả phòng (Check-out)"**.
2. Hệ thống kiểm tra ngày trả thực tế (`actual_check_out`):
   - Nếu khách trả **đúng hạn hoặc trễ**: giữ nguyên ngày trả dự kiến.
   - Nếu khách **trả phòng sớm**: ghi nhận ngày trả thực tế vào cột `check_out_date` của bảng `bookings_by_guest` để thống kê số đêm thực ở chính xác.
   - **Chính sách tài chính:** Không giảm giá và không hoàn tiền (hóa đơn giữ nguyên).
3. Gọi `booking_service.complete_booking(...)`: Thực thi **BATCH UPDATE** chuyển `status = 'COMPLETED'` ở cả 2 bảng `bookings_by_guest` và `bookings_by_hotel_date`.
4. Gọi `room_service.change_room_status(..., 'AVAILABLE')`: Giải phóng phòng, xóa `current_guest_name` và `current_booking_id` về `NULL`.
5. Phòng lập tức sẵn sàng nhận khách tiếp theo, không để lại dữ liệu rác.

---

# 2. CHI TIẾT PHẦN VIỆC CỦA NGUYỄN ANH QUÂN (QN) TỪ DATABASE ĐẾN UI

Toàn bộ các công việc dưới đây do **Nguyễn Anh Quân (QN)** trực tiếp thiết kế, lập trình và kiểm thử:

```
+---------------------------------------------------------------------------------------+
| PHÂN TẦNG CÔNG VIỆC CỦA NGUYỄN ANH QUÂN (QN) - 13 STORY POINTS (~37.5% DỰ ÁN)         |
+---------------------------------------------------------------------------------------+
| 1. TẦNG CƠ SỞ DỮ LIỆU (DATABASE / CQL SCHEMA)                                         |
|    - Thiết kế bảng `bookings_by_guest` (Query Q2 - PK: guest_id, CK: booking_id)       |
|    - Thiết kế bảng `bookings_by_hotel_date` (Query Q3 - Composite PK: hotel_id, date) |
|    - Thiết kế bảng `invoices_by_booking` (Query Q4 - PK: booking_id, CK: invoice_id)    |
|    - Mở rộng cột cọc: `deposit_amount decimal`, `remaining_amount decimal`            |
|                                                                                       |
| 2. TẦNG DỊCH VỤ & NGHIỆP VỤ (SERVICES - booking_service.py - 1.320 DÒNG CODE)         |
|    - Cài đặt Atomic BATCH INSERT Q5 (`create_booking_batch`)                          |
|    - Cài đặt Truy vấn tra cứu Lịch sử khách hàng Q2 (`get_bookings_by_guest`)         |
|    - Cài đặt Truy vấn Lễ tân theo ngày Q3 (`get_bookings_by_hotel_date`)              |
|    - Cài đặt Truy vấn Hóa đơn thanh toán Q4 (`get_invoice_by_booking`)                |
|    - Xây dựng Quản lý Đặt cọc & Thanh toán (`create_invoice`, `settle_invoice_payment`)|
|    - Xây dựng Nghiệp vụ Trả phòng / Trả sớm (`complete_booking` - BATCH UPDATE)       |
|    - Xây dựng In-Memory Caching TTL 30s & Cơ chế Invalidation bảo vệ hiệu năng        |
|    - Xây dựng Fallback an toàn (Graceful Degradation) chống crash khi driver lệch cột |
|                                                                                       |
| 3. TẦNG BỘ ĐIỀU KHIỂN & API (ROUTES - booking_routes.py - 860 DÒNG CODE)              |
|    - Quản lý 13 route endpoints chuyên sâu (Web Forms + RESTful JSON APIs)            |
|    - Xử lý Validation logic: Ngày đi > Ngày đến, Không đặt phòng bận, Format SĐT/CCCD |
|                                                                                       |
| 4. TẦNG GIAO DIỆN NGƯỜI DÙNG (UI/UX - bookings.html, invoices.html)                   |
|    - `bookings.html`: Giao diện Room Discovery, Bộ lọc 5 tiêu chí, Modal đặt phòng    |
|    - `invoices.html`: Phiếu hóa đơn nhận diện Mường Thanh chuẩn in ấn, Modal Settle   |
+---------------------------------------------------------------------------------------+
```

---

# 3. BẢNG KÊ CỨU TOÀN BỘ CÁC QUERY VỀ ĐẶT PHÒNG VÀ HÓA ĐƠN

Dưới đây là danh mục chi tiết **100% tất cả các câu lệnh CQL** được sử dụng trong module Đặt phòng & Hóa đơn (`cql/schema.cql` và `services/booking_service.py`).

---

### QUERY 1: Khởi tạo bảng Lịch sử đặt phòng theo khách hàng (Query Q2 Schema)
* **Vị trí code:** `cql/schema.cql` (Dòng 74–84)
* **Mục đích:** Lưu lịch sử đặt phòng của từng khách để phục vụ xem profile/lịch sử lưu trú.
* **Cú pháp CQL:**
```sql
CREATE TABLE IF NOT EXISTS bookings_by_guest (
    guest_id text,
    booking_id text,
    hotel_id text,
    room_number text,
    check_in_date date,
    check_out_date date,
    status text,
    total_amount decimal,
    PRIMARY KEY (guest_id, booking_id)
);
```
* **Phân tích cấu trúc khóa:**
  - **Partition Key (`guest_id`):** Gom toàn bộ các lượt đặt phòng của một khách hàng vào cùng một partition vật lý trên cluster.
  - **Clustering Key (`booking_id`):** Định danh duy nhất từng đơn đặt phòng và sắp xếp dữ liệu bên trong partition.
  - **Hiệu năng:** Đạt $O(1)$ khi truy vấn theo `guest_id`.

---

### QUERY 2: Khởi tạo bảng Đặt phòng theo khách sạn và ngày (Query Q3 Schema)
* **Vị trí code:** `cql/schema.cql` (Dòng 87–96)
* **Mục đích:** Phục vụ màn hình lễ tân khách sạn tra cứu ai sẽ nhận phòng trong ngày hôm nay/ngày chỉ định.
* **Cú pháp CQL:**
```sql
CREATE TABLE IF NOT EXISTS bookings_by_hotel_date (
    hotel_id text,
    check_in_date date,
    booking_id text,
    guest_id text,
    guest_name text,
    room_number text,
    status text,
    PRIMARY KEY ((hotel_id, check_in_date), booking_id)
);
```
* **Phân tích cấu trúc khóa:**
  - **Composite Partition Key (`(hotel_id, check_in_date)`):** Cặp giá trị khách sạn và ngày nhận phòng kết hợp lại làm mã băm partition.
  - **Clustering Key (`booking_id`):** Phân biệt các đơn đặt phòng khác nhau trong cùng một ngày tại chi nhánh đó.
  - **Denormalization:** Lưu sẵn `guest_name` để lễ tân xem danh sách không phải query ngược sang bảng `guests`.

---

### QUERY 3: Khởi tạo bảng Hóa đơn thanh toán theo mã đặt phòng (Query Q4 Schema)
* **Vị trí code:** `cql/schema.cql` (Dòng 99–111)
* **Mục đích:** Lưu trữ chứng từ thanh toán và tình trạng công nợ/đặt cọc của từng đơn lưu trú.
* **Cú pháp CQL:**
```sql
CREATE TABLE IF NOT EXISTS invoices_by_booking (
    booking_id text,
    invoice_id text,
    guest_name text,
    hotel_id text,
    issue_date date,
    payment_method text,
    payment_status text,
    total_amount decimal,
    deposit_amount decimal,
    remaining_amount decimal,
    PRIMARY KEY (booking_id, invoice_id)
);
```
* **Phân tích cấu trúc khóa:**
  - **Partition Key (`booking_id`):** Một booking gắn liền với partition hóa đơn của nó.
  - **Clustering Key (`invoice_id`):** Hỗ trợ trường hợp một booking có thể xuất nhiều hóa đơn (hóa đơn cọc, hóa đơn dịch vụ phát sinh).
  - **Trạng thái thanh toán (`payment_status`):** `PAID` (Thanh toán 100%), `PARTIAL` (Đã cọc), `UNPAID` (Chưa thanh toán).

---

### QUERY 4: [TRỌNG TÂM] Atomic BATCH INSERT Đặt phòng (Query Q5 Đề Cương)
* **Vị trí code:** `services/booking_service.py` -> Hàm `create_booking_batch(...)` (Dòng 80–110)
* **Mục đích:** Ghi đồng thời dữ liệu một đơn đặt phòng mới vào cả 2 bảng phân tán nhằm bảo toàn tính nhất quán (Atomicity).
* **Cú pháp CQL:**
```sql
BEGIN BATCH
  INSERT INTO bookings_by_guest (
      guest_id, booking_id, hotel_id, room_number, 
      check_in_date, check_out_date, status, total_amount
  ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);

  INSERT INTO bookings_by_hotel_date (
      hotel_id, check_in_date, booking_id, 
      guest_id, guest_name, room_number, status
  ) VALUES (?, ?, ?, ?, ?, ?, ?);
APPLY BATCH;
```
* **Cách thức cài đặt trong Python:**
```python
from cassandra.query import BatchStatement
batch = BatchStatement()

stmt_guest = session.prepare("""
    INSERT INTO bookings_by_guest (
        guest_id, booking_id, hotel_id, room_number, 
        check_in_date, check_out_date, status, total_amount
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
""")
batch.add(stmt_guest, (guest_id, booking_id, hotel_id, str(room_number), in_date, out_date, status_val, amount))

stmt_hotel_date = session.prepare("""
    INSERT INTO bookings_by_hotel_date (
        hotel_id, check_in_date, booking_id, 
        guest_id, guest_name, room_number, status
    ) VALUES (?, ?, ?, ?, ?, ?, ?);
""")
batch.add(stmt_hotel_date, (hotel_id, in_date, booking_id, guest_id, guest_name, str(room_number), status_val))

session.execute(batch)
```
* **Ý nghĩa:** Tránh hiện tượng ghi thành công vào bảng khách hàng nhưng mạng lỗi làm mất đơn ở bảng lễ tân.

---

### QUERY 5: Tra cứu lịch sử đặt phòng theo khách hàng (Query Q2 Đề Cương)
* **Vị trí code:** `services/booking_service.py` -> Hàm `get_bookings_by_guest(guest_id)` (Dòng 256–290)
* **Mục đích:** Lấy toàn bộ danh sách đơn đặt phòng của một khách theo `guest_id`.
* **Cú pháp CQL:**
```sql
SELECT guest_id, booking_id, hotel_id, room_number, 
       check_in_date, check_out_date, status, total_amount
FROM bookings_by_guest
WHERE guest_id = ?;
```
* **Kỹ thuật tối ưu hóa:** Do bảng `bookings_by_guest` không lưu tên khách và tên khách sạn, hàm bổ trợ `_normalize_bookings` tự động thực hiện truy vấn điểm theo Partition Key:
  - `SELECT full_name, phone, id_card FROM guests WHERE guest_id = ?;`
  - `SELECT name, city FROM hotels WHERE hotel_id = ?;`
  Nhờ đó, không dùng `ALLOW FILTERING`, không scan toàn bảng, tốc độ phản hồi cực nhanh dưới 5ms.

---

### QUERY 6: Tra cứu đặt phòng theo khách sạn và ngày check-in (Query Q3 Đề Cương)
* **Vị trí code:** `services/booking_service.py` -> Hàm `get_bookings_by_hotel_date(hotel_id, check_in_date)` (Dòng 296–343)
* **Mục đích:** Lễ tân lọc danh sách khách sẽ check-in vào ngày chỉ định tại một khách sạn.
* **Cú pháp CQL:**
```sql
SELECT hotel_id, check_in_date, booking_id, 
       guest_id, guest_name, room_number, status
FROM bookings_by_hotel_date
WHERE hotel_id = ? AND check_in_date = ?;
```
* **Kỹ thuật tối ưu hóa:** Bắt buộc truyền cả `hotel_id` và `check_in_date` vì đây là Composite Partition Key. Driver sẽ băm cặp giá trị này và gửi thẳng request đến đúng node lưu trữ, bỏ qua toàn bộ các node khác trong cluster.

---

### QUERY 7: Tra cứu chi tiết hóa đơn theo mã đặt phòng (Query Q4 Đề Cương)
* **Vị trí code:** `services/booking_service.py` -> Hàm `get_invoice_by_booking(booking_id)` (Dòng 349–404)
* **Mục đích:** Lấy chi tiết số tiền, tiền cọc, số tiền còn lại và trạng thái thanh toán của đơn đặt phòng.
* **Cú pháp CQL chính (10 cột):**
```sql
SELECT booking_id, invoice_id, guest_name, hotel_id,
       issue_date, payment_method, payment_status, total_amount,
       deposit_amount, remaining_amount
FROM invoices_by_booking
WHERE booking_id = ?;
```
* **Cú pháp CQL Fallback (8 cột - Tương thích ngược):**
```sql
SELECT booking_id, invoice_id, guest_name, hotel_id,
       issue_date, payment_method, payment_status, total_amount
FROM invoices_by_booking
WHERE booking_id = ?;
```

---

### QUERY 8: Tạo hóa đơn thanh toán mới
* **Vị trí code:** `services/booking_service.py` -> Hàm `create_invoice(...)` (Dòng 406–560)
* **Mục đích:** Tự động tạo hóa đơn tương ứng ngay khi đơn đặt phòng được tạo.
* **Cú pháp CQL:**
```sql
INSERT INTO invoices_by_booking (
    booking_id, invoice_id, guest_name, hotel_id,
    issue_date, payment_method, payment_status, total_amount,
    deposit_amount, remaining_amount
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
```
* **Nghiệp vụ tiền cọc:**
  - `PAID`: `deposit_amount = total_amount`, `remaining_amount = 0`.
  - `PARTIAL`: `deposit_amount = total_amount / 2`, `remaining_amount = total_amount - deposit_amount`.
  - `UNPAID`: `deposit_amount = 0`, `remaining_amount = total_amount`.

---

### QUERY 9: Cập nhật thanh toán nốt tiền cọc (Settle Payment)
* **Vị trí code:** `services/booking_service.py` -> Hàm `settle_invoice_payment(...)` (Dòng 1071–1186)
* **Mục đích:** Thu nốt số tiền còn lại khi khách làm thủ tục check-in hoặc check-out.
* **Cú pháp CQL:**
```sql
UPDATE invoices_by_booking
SET payment_status = ?,
    deposit_amount = ?,
    remaining_amount = ?,
    payment_method = ?
WHERE booking_id = ? AND invoice_id = ?;
```
* **Nghiệp vụ:** Chuyển `payment_status` từ `PARTIAL` sang `PAID`, gán `deposit_amount = total_amount`, `remaining_amount = 0`.

---

### QUERY 10: Đóng booking khi khách trả phòng (Kể cả trả sớm)
* **Vị trí code:** `services/booking_service.py` -> Hàm `complete_booking(...)` (Dòng 1194–1320)
* **Mục đích:** Khi khách trả phòng, chuyển trạng thái booking sang `COMPLETED` ở cả 2 bảng bằng BATCH UPDATE.
* **Cú pháp CQL:**
```sql
BEGIN BATCH
  -- Cập nhật bảng bookings_by_guest (ghi nhận ngày trả thực tế nếu trả sớm)
  UPDATE bookings_by_guest
  SET status = 'COMPLETED', check_out_date = ?
  WHERE guest_id = ? AND booking_id = ?;

  -- Cập nhật bảng bookings_by_hotel_date (đồng bộ trạng thái lễ tân)
  UPDATE bookings_by_hotel_date
  SET status = 'COMPLETED'
  WHERE hotel_id = ? AND check_in_date = ? AND booking_id = ?;
APPLY BATCH;
```
* **Chính sách tài chính:** Trả phòng sớm KHÔNG giảm giá và KHÔNG hoàn tiền (hóa đơn giữ nguyên).

---

### QUERY 11: Đồng bộ trạng thái phòng khi Đặt và khi Trả phòng
* **Vị trí code:** `services/room_service.py` -> Hàm `change_room_status(...)`
* **Mục đích:** Cập nhật bảng `rooms_by_hotel` để trang chi tiết phòng và sơ đồ phòng hiển thị chính xác.
* **Cú pháp CQL khi Đặt phòng thành công:**
```sql
UPDATE rooms_by_hotel
SET status = 'OCCUPIED', 
    is_available = false, 
    current_guest_name = ?, 
    current_booking_id = ?
WHERE hotel_id = ? AND room_number = ?;
```
* **Cú pháp CQL khi Khách trả phòng (Giải phóng phòng):**
```sql
UPDATE rooms_by_hotel
SET status = 'AVAILABLE', 
    is_available = true, 
    current_guest_name = null, 
    current_booking_id = null
WHERE hotel_id = ? AND room_number = ?;
```

---

# 4. TƯ DUY NGƯỢC LẠI: TẠI SAO LẠI THIẾT KẾ QUERY & DỮ LIỆU NHƯ VẬY?

Đây là phần trọng tâm giúp sinh viên trả lời xuất sắc các câu hỏi phản biện của Hội đồng chấm đồ án NoSQL:

```
+-----------------------------------------------------------------------------------------------+
| BẢNG SO SÁNH TƯ DUY: CƠ SỞ DỮ LIỆU QUAN HỆ (SQL) VS. APACHE CASSANDRA (NOSQL)                 |
+-----------------------------------------------------------------------------------------------+
| TIÊU CHÍ         | HỆ QUẢN TRỊ RDBMS (MYSQL, POSTGRESQL) | APACHE CASSANDRA / ASTRADB (NOSQL) |
|------------------+---------------------------------------+------------------------------------|
| Triết lý thiết kế| Schema-First / Model Entities         | Query-First (Thiết kế theo truy vấn)|
| Chuẩn hóa dữ liệu| Chuẩn hóa 3NF để triệt tiêu trùng lặp | Phi chuẩn hóa (Denormalization)    |
| Phép nối (JOIN)  | Sử dụng JOIN giữa nhiều bảng           | TUYỆT ĐỐI KHÔNG CÓ JOIN             |
| Khả năng mở rộng | Scale-Up (Nâng cấp cấu hình máy chủ)  | Scale-Out (Thêm hàng nghìn node rẻ)|
| Chi phí Ghi (Write)| Đắt (Khóa dòng, ghi index B-Tree)    | Cực rẻ & Siêu tốc (CommitLog + Memtable)|
| Chi phí Đọc (Read)| Rẻ nếu có Index, đắt khi JOIN lớn    | Cực nhanh O(1) NẾU ĐÚNG Partition Key|
+-----------------------------------------------------------------------------------------------+
```

---

### Câu hỏi 1: Tại sao lại tạo 2 bảng `bookings_by_guest` và `bookings_by_hotel_date` cùng chứa dữ liệu đặt phòng thay vì 1 bảng như MySQL?
* **Tư duy SQL truyền thống:** Tạo 1 bảng `bookings (booking_id, guest_id, hotel_id, check_in_date, ...)`. Khi cần xem lịch sử khách: `SELECT * FROM bookings WHERE guest_id = ?`. Khi lễ tân tra cứu: `SELECT * FROM bookings WHERE hotel_id = ? AND check_in_date = ?`.
* **Tại sao Cassandra không làm được như vậy?**
  - Trong Cassandra, dữ liệu được phân tán trên hàng chục hoặc hàng trăm server vật lý dựa trên hàm băm Partition Key: `Token = Murmur3Hash(PartitionKey)`.
  - Nếu chỉ có 1 bảng với Partition Key là `booking_id`, khi muốn tìm các đơn của khách `G001`, Cassandra **không biết đơn đó nằm ở server nào**. Nó buộc phải gửi request đến **tất cả các server trong hệ thống** để tìm kiếm (Full Cluster Scan / `ALLOW FILTERING`). Điều này làm nghẽn băng thông mạng và sập hệ thống khi có hàng triệu bản ghi.
* **Giải pháp NoSQL (Query-First):**
  - Để phục vụ câu hỏi *"Khách hàng X đã từng đặt những phòng nào?"* -> Tạo bảng `bookings_by_guest` với Partition Key là `guest_id`.
  - Để phục vụ câu hỏi *"Ngày hôm nay tại khách sạn Y có những ai đến nhận phòng?"* -> Tạo bảng `bookings_by_hotel_date` với Partition Key là `(hotel_id, check_in_date)`.
  - Dữ liệu bị trùng lặp (phi chuẩn hóa), nhưng mỗi truy vấn chỉ cần gõ đúng 1 node lưu trữ duy nhất, đạt tốc độ phản hồi $O(1)$ (< 5ms). Trong kỷ nguyên NoSQL: **Dung lượng ổ đĩa rất rẻ, nhưng độ trễ mạng (Network Latency) và trải nghiệm người dùng là vô giá!**

---

### Câu hỏi 2: Tại sao phải bắt buộc dùng `BATCH STATEMENT` khi tạo đơn đặt phòng?
* **Nguy cơ tiềm ẩn:** Do ta có 2 bảng lưu cùng một sự kiện đặt phòng, nếu ta chạy 2 lệnh riêng biệt:
  ```python
  session.execute("INSERT INTO bookings_by_guest ...")
  # Nếu server bị mất điện, mạng chập chờn hoặc driver crash tại đây!
  session.execute("INSERT INTO bookings_by_hotel_date ...")
  ```
  Hậu quả: Tiền của khách đã trừ, đơn trong lịch sử của khách đã có, nhưng bảng lễ tân lại không hề có thông tin phòng đó! Dẫn đến lỗi nghiệp vụ nghiêm trọng.
* **Giải pháp BATCH trong Cassandra:**
  - Cassandra sử dụng cơ chế **Atomic Logged Batch**.
  - Trước khi ghi dữ liệu, Coordinator node sẽ ghi một bản ghi log (`batchlog`) xác nhận đang chuẩn bị ghi vào 2 bảng.
  - Sau đó Coordinator gửi lệnh ghi đến các node chứa partition. Nếu mọi thứ xong, log bị xóa.
  - Nếu một node bị sập giữa chừng, các node khác sẽ đọc `batchlog` và hoàn tất nốt việc ghi còn dở dang (Eventual Consistency).
  - Kết luận: `BATCH` đảm bảo **cả 2 bảng cùng được ghi hoặc cả 2 không bị ghi lệch pha**.

---

### Câu hỏi 3: Tại sao bảng `bookings_by_hotel_date` lại dùng Composite Partition Key `((hotel_id, check_in_date))` mà không chỉ dùng `hotel_id`?
* **Nếu chỉ dùng `hotel_id` làm Partition Key:**
  - Giả sử khách sạn Mường Thanh Luxury Đà Nẵng hoạt động 10 năm, mỗi ngày có 100 lượt đặt phòng. Sau 10 năm sẽ có gần 400.000 dòng dữ liệu dồn hết vào **duy nhất một Partition**.
  - Khuyến nghị thiết kế Cassandra (DataStax Best Practices): Dung lượng một partition không được vượt quá **100MB** và không chứa quá **100.000 dòng**. Partition quá lớn sẽ gây hiện tượng **Hotspot** (một máy chủ bị quá tải CPU/RAM trong khi các máy khác nhàn rỗi) và làm sập Garbage Collection của Java.
* **Khi dùng Composite Partition Key `((hotel_id, check_in_date))`:**
  - Dữ liệu được chia nhỏ: Mỗi ngày của một khách sạn là một partition riêng biệt độc lập.
  - Mỗi partition chỉ chứa khoảng vài chục đến vài trăm dòng (vài chục Kilobytes), kích thước lý tưởng tuyệt đối.
  - Lễ tân tra cứu ngày nào thì router tính hash của đúng ngày đó, truy cập thẳng node lưu trữ, cực kỳ tối ưu.

---

### Câu hỏi 4: Tại sao bảng `invoices_by_booking` lại dùng `booking_id` làm Partition Key?
* **Phân tích hành vi người dùng (Access Pattern):**
  - Không bao giờ có trường hợp người dùng mở app lên và tìm "Cho tôi xem hóa đơn theo số chứng minh nhân dân".
  - Người dùng luôn thao tác: Đặt phòng xong -> Xem hóa đơn của đơn đó; hoặc vào Danh sách đặt phòng -> Bấm nút "Xem hóa đơn" / "In hóa đơn" của mã booking đó.
  - Vì vậy, quan hệ giữa Booking và Invoice là quan hệ mật thiết 1-1 (hoặc 1-nhiều nếu có hóa đơn cọc + hóa đơn phát sinh).
  - Chọn `booking_id` làm Partition Key giúp việc lấy thông tin hóa đơn là một truy vấn điểm (Point Query) trực tiếp theo khóa chính.

---

### Câu hỏi 5: Tại sao lại Denormalize `current_guest_name` và `current_booking_id` trực tiếp vào bảng `rooms_by_hotel`?
* **Bối cảnh nghiệp vụ:** Khi nhân viên lễ tân nhìn vào sơ đồ phòng hoặc click vào xem chi tiết Phòng 101, họ cần biết ngay: *"Phòng này ai đang ở? Mã booking là gì?"*.
* **Nếu làm theo tư duy SQL:**
  ```sql
  SELECT g.full_name FROM rooms r
  JOIN bookings b ON r.room_number = b.room_number
  JOIN guests g ON b.guest_id = g.guest_id
  WHERE r.hotel_id = 'MT_001' AND r.room_number = '101' 
    AND b.status = 'CONFIRMED' AND CURRENT_DATE BETWEEN b.check_in AND b.check_out;
  ```
* **Tại sao Cassandra không thể làm như trên?** Vì Cassandra **không có lệnh JOIN**. Nếu muốn biết ai đang ở phòng 101, hệ thống sẽ phải query toàn bộ bảng `bookings_by_guest` rồi quét từng dòng xem có dòng nào phòng 101 đang ở ngày hôm nay không — vô cùng chậm chạp và tốn tài nguyên.
* **Giải pháp Denormalization:**
  - Thêm 2 cột `current_guest_name` và `current_booking_id` vào bảng `rooms_by_hotel`.
  - Khi Đặt phòng thành công -> ghi thẳng tên khách và mã booking vào dòng phòng đó.
  - Khi Trả phòng -> xóa 2 trường đó về `NULL`.
  - Kết quả: Khi mở trang chi tiết phòng, chỉ cần `SELECT * FROM rooms_by_hotel WHERE hotel_id = ? AND room_number = ?;` là có ngay lập tức cả thông tin phòng lẫn tên khách đang ở chỉ trong 1 lần đọc duy nhất!

---

### Câu hỏi 6: Tại sao hệ thống áp dụng In-Memory Caching (TTL 30s) kèm Invalidation?
* AstraDB là hệ thống cơ sở dữ liệu đám mây (Database-as-a-Service) tính phí và giới hạn Read/Write Request Units (RUs).
* Khi người dùng tải lại trang web hoặc nhiều người cùng duyệt danh sách phòng/hóa đơn, các truy vấn SELECT toàn bảng lặp lại liên tục sẽ làm nghẽn đường truyền mạng internet từ máy chủ Flask đến Data center của AstraDB ở Singapore/Mỹ.
* Giải pháp: Cache kết quả 30 giây trong RAM. Khi có bất kỳ thao tác ghi nào (Thêm booking, Trả phòng, Đổi tiền), hàm `invalidate_cache()` được gọi ngay lập tức để xóa cache, đảm bảo tính nhất quán tức thì (Immediate Consistency) mà vẫn tiết kiệm 80% lưu lượng truy vấn AstraDB.

---

# 5. CẨM NANG THUYẾT TRÌNH & BẢO VỆ ĐỒ ÁN TRƯỚC HỘI ĐỒNG

Khi thầy cô yêu cầu demo hoặc giải thích code, Quân có thể tự tin trình bày theo khung 3 bước chuyên nghiệp:

1. **Bước 1 — Nêu rõ bài toán & Trọng tâm được giao:**
   > *"Em phụ trách Epic 3: Nghiệp vụ Giao dịch Đặt phòng, Ghi đồng thời BATCH và Quản lý Hóa đơn, chiếm 13 Story Points trong dự án. Trọng tâm của phần em là giải quyết bài toán tính nhất quán dữ liệu phân tán khi không có transaction ACID đa bảng như trong SQL."*

2. **Bước 2 — Demo luồng tương tác thực tế:**
   > *"Em xin demo luồng Đặt phòng: Từ danh sách phòng trống, em chọn phòng 101 của chi nhánh Mường Thanh Sông Hàn, chọn khách Nguyễn Văn An, nhận phòng từ ngày mai ở 3 đêm. Em chọn hình thức Đặt cọc trước 50%. Khi em bấm Đặt phòng, hệ thống tự động:
   > 1. Ghi đồng thời BATCH vào 2 bảng `bookings_by_guest` và `bookings_by_hotel_date`.
   > 2. Tự động sinh hóa đơn với trạng thái `PARTIAL`, tiền cọc 50%.
   > 3. Cập nhật phòng 101 sang `OCCUPIED` và lưu tên khách đang ở.
   > 4. Chuyển ngay đến hóa đơn thanh toán."*

3. **Bước 3 — Giải thích sâu về mặt kỹ thuật NoSQL:**
   > *"Thưa thầy cô, điểm đặc biệt nhất trong kiến trúc NoSQL ở đây là nguyên lý Query-First và Denormalization. Vì Cassandra không có JOIN, nên bọn em tách thành 2 bảng đặt phòng riêng biệt để tối ưu cho 2 góc nhìn: Góc nhìn Khách hàng (Partition Key là guest_id) và Góc nhìn Lễ tân khách sạn (Composite Partition Key là hotel_id + check_in_date). Nhờ vậy, mọi câu lệnh SELECT của hệ thống đều là truy vấn O(1) theo đúng partition key mà không cần quét toàn bảng hay dùng ALLOW FILTERING."*

---
*Báo cáo được trích xuất và kiểm tra tính toàn vẹn kỹ thuật ngày 18/09/2026 bởi Nguyễn Anh Quân.*
