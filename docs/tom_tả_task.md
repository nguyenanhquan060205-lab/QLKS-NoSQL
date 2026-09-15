# Tóm tắt task và phân tích mã nguồn hệ thống Quản lý Khách sạn NoSQL

## 1. Phạm vi đọc mã

Repository không có thư mục `src/`. Vì vậy, báo cáo này xem toàn bộ phần triển khai sau là mã nguồn của ứng dụng:

- `app.py`
- `routes/`
- `services/`
- `database/`
- `cql/schema.cql`
- `templates/`
- `static/css/` và `static/js/`
- `tests/`
- `requirements.txt` và `.env.example` để đối chiếu cấu hình chạy

File PDF trong `docs/` và các file README không được xem là mã thực thi nên không nằm trong phạm vi phân tích chi tiết.

## 2. Tóm tắt tổng quan

Đây là một ứng dụng web quản lý khách sạn được xây dựng bằng Flask, Jinja2 và Apache Cassandra/DataStax Astra DB. Dự án áp dụng cách thiết kế dữ liệu theo truy vấn (query-first) và phi chuẩn hóa dữ liệu đặt phòng thành nhiều bảng để phục vụ từng kiểu tra cứu.

Kiến trúc hiện tại chia thành ba lớp chính:

1. `routes`: nhận HTTP request và render giao diện.
2. `services`: dự kiến chứa nghiệp vụ và truy vấn Cassandra.
3. `database`: tạo và cache kết nối tới Astra DB.

Phần giao diện dùng Jinja2, Tailwind CSS từ CDN, Bootstrap Icons và Chart.js. Cấu trúc tổng thể khá rõ ràng cho một đồ án nhóm. Sau Task 4, tầng service đã có thể thêm và đọc khách sạn/khách hàng; tuy nhiên các route POST và giao diện tương ứng vẫn là placeholder. Phần phòng, đặt phòng và hóa đơn vẫn chủ yếu dừng ở khung sườn.

## Task 4: service khách sạn và khách hàng

### Yêu cầu

Triển khai bốn hàm trong `services/hotel_service.py`:

- `get_all_hotels()`
- `create_hotel()`
- `get_all_guests()`
- `create_guest()`

Acceptance Criteria: thêm và lấy dữ liệu thành công từ hai bảng Cassandra `hotels` và `guests`.

### Tư duy query-first đã áp dụng

Trước khi viết hàm, bốn access pattern được xác định rõ:

```sql
SELECT hotel_id, name, phone, address, city, country, amenities
FROM hotels;

INSERT INTO hotels (
    hotel_id, name, phone, address, city, country, amenities
) VALUES (?, ?, ?, ?, ?, ?, ?);

SELECT guest_id, full_name, email, phone, id_card
FROM guests;

INSERT INTO guests (
    guest_id, full_name, email, phone, id_card
) VALUES (?, ?, ?, ?, ?);
```

Schema hiện có dùng `hotel_id` và `guest_id` làm partition key. Thiết kế này tốt cho thao tác ghi và tra cứu theo ID. Hai truy vấn `get_all_*` là quét toàn bảng, chỉ phù hợp với dữ liệu nhỏ của đồ án. Nếu hệ thống lớn hơn, cần tạo bảng chuyên phục vụ access pattern liệt kê thay vì dựa vào full table scan.

### Nội dung đã triển khai

| Hàm | Cách xử lý | Giá trị trả về |
|---|---|---|
| `get_all_hotels` | Thực thi `SELECT` với danh sách cột tường minh | `list` Cassandra Row; lỗi trả `[]` |
| `create_hotel` | Prepared `INSERT`; chuẩn hóa tiện nghi | Thành công `True`, lỗi `False` |
| `get_all_guests` | Thực thi `SELECT` với danh sách cột tường minh | `list` Cassandra Row; lỗi trả `[]` |
| `create_guest` | Prepared `INSERT` | Thành công `True`, lỗi `False` |

Các điểm cần ghi nhớ:

- Prepared statement của `cassandra-driver` dùng placeholder `?`.
- Cassandra không có auto-increment; caller phải cung cấp `hotel_id` và `guest_id`.
- `amenities` trong schema là `set<text>`, vì vậy service chuyển chuỗi phân tách bằng dấu phẩy hoặc iterable thành Python `set`.
- Các hàm bắt lỗi từ driver để không làm route văng lỗi 500 trực tiếp.
- Thông báo lỗi dùng chuỗi ASCII để không phát sinh `UnicodeEncodeError` trên Windows console CP1252.
- Các hàm đọc giữ nguyên Cassandra Row; Jinja có thể truy cập dạng `hotel.name` hoặc `guest.full_name`.

### Kiểm thử

Đã thêm `tests/test_hotel_service.py` với sáu ca kiểm thử:

1. Đọc danh sách khách sạn.
2. Thêm khách sạn bằng prepared statement và kiểm tra `amenities` là `set`.
3. Đọc danh sách khách hàng.
4. Thêm khách hàng bằng prepared statement và kiểm tra thứ tự tham số.
5. Trả giá trị an toàn khi không có kết nối database.
6. Trả giá trị an toàn khi Cassandra driver ném exception.

Kết quả: `Ran 6 tests ... OK`. Kiểm tra cú pháp bằng `py_compile` cũng thành công.

Đã bổ sung `tests/test_hotel_service_integration.py` để xác nhận trực tiếp AC trên Cassandra/Astra DB. Bài test sử dụng hai ID cố định `H_QLKS04_TEST` và `G_QLKS04_TEST`, thực hiện `INSERT` qua service rồi gọi hàm `get_all_*` để xác nhận đọc lại được đúng bản ghi. ID cố định làm cho test có thể chạy lại mà không tạo thêm hàng trùng vì Cassandra thực hiện upsert theo primary key.

File `.env` cục bộ cũng đã được tạo với keyspace `hotel_ks`; token và đường dẫn bundle được để trống để người dùng điền trực tiếp trên máy. `.gitignore` đã loại trừ `.env` và `*.zip`, tránh commit thông tin bí mật.

Lần chạy hiện tại cho kết quả unit test `OK`; integration test được `skipped` có chủ đích vì chưa có `ASTRA_DB_TOKEN` và `ASTRA_DB_SECURE_BUNDLE_PATH`. QLKS-04 chỉ được xác nhận hoàn thành toàn bộ AC sau khi integration test này chạy thành công trên Astra DB thật.

## 3. Kiến trúc và luồng xử lý

Luồng request đi qua các thành phần như sau:

```text
Trình duyệt
    -> Flask route/Blueprint
        -> Service nghiệp vụ
            -> database.get_session()
                -> Cassandra/Astra DB
        -> Jinja2 template
    -> HTML trả về trình duyệt
```

### 3.1. Điểm khởi động ứng dụng

`app.py` thực hiện các công việc:

- Đọc biến môi trường bằng `python-dotenv`.
- Khởi tạo Flask app.
- Đăng ký ba Blueprint: `hotel_bp`, `booking_bp`, `dashboard_bp`.
- Chạy development server trên `0.0.0.0`, port lấy từ biến `PORT` hoặc mặc định `5000`.

Ba nhóm chức năng được phân công rõ trong code:

- Khách sạn, phòng và khách hàng: `hotel_routes.py` + `hotel_service.py`.
- Đặt phòng và hóa đơn: `booking_routes.py` + `booking_service.py`.
- Trang chủ, dashboard và kết nối dữ liệu: `dashboard_routes.py`, `dashboard_service.py`, `database/db.py`.

### 3.2. Lớp kết nối dữ liệu

`database/db.py` cung cấp duy nhất hàm `get_session()`:

- Đọc `ASTRA_DB_SECURE_BUNDLE_PATH`, `ASTRA_DB_TOKEN` và `ASTRA_DB_KEYSPACE`.
- Kiểm tra cấu hình và sự tồn tại của Secure Connect Bundle.
- Dùng `cassandra-driver` với `PlainTextAuthProvider('token', token)` để kết nối Astra DB.
- Cache `Session` trong biến module `_session` để tái sử dụng giữa các request.
- Khi lỗi, in thông báo ra console và trả về `None`.

Cách cache này phù hợp với ứng dụng demo vì Cassandra `Session` được thiết kế để tái sử dụng. Tuy nhiên, code chưa giữ tham chiếu `Cluster` để đóng kết nối khi ứng dụng dừng, chưa có retry/health check và có thể có race nhỏ nếu nhiều request đầu tiên cùng khởi tạo session.

### 3.3. Lớp route

Ứng dụng khai báo 13 endpoint:

| Method | URL | Chức năng | Trạng thái |
|---|---|---|---|
| GET | `/` | Trang chủ và số liệu nhanh | Có hoạt động |
| GET | `/dashboard` | Dashboard và biểu đồ phòng | Có hoạt động |
| GET | `/hotels` | Danh sách khách sạn | Service đã đọc DB; template chưa render danh sách |
| POST | `/hotels/add` | Thêm khách sạn | Service đã có; route chưa xử lý form |
| GET | `/hotels/<hotel_id>/rooms` | Phòng theo khách sạn, Q1 | Route có, service trả rỗng |
| POST | `/hotels/<hotel_id>/rooms/add` | Thêm phòng | Chưa xử lý form |
| GET | `/guests` | Danh sách khách hàng | Service đã đọc DB; template chưa render danh sách |
| POST | `/guests/add` | Thêm khách hàng | Service đã có; route chưa xử lý form |
| GET | `/bookings` | Danh sách đặt phòng | Luôn truyền danh sách rỗng |
| POST | `/bookings/create` | Tạo đặt phòng bằng batch, Q5 | Chưa xử lý form/chưa gọi service |
| GET | `/bookings/guest/<guest_id>` | Lịch sử theo khách, Q2 | Route có, service trả rỗng |
| GET | `/bookings/hotel-date` | Đặt phòng theo khách sạn và ngày, Q3 | Route có, service trả rỗng |
| GET | `/invoices/<booking_id>` | Hóa đơn theo booking, Q4 | Route có, service trả `None` |

Các POST route hiện chỉ redirect, không đọc `request.form`, không gọi service và không hiển thị thông báo thành công/thất bại. `flash` được import ở hai module route nhưng chưa được sử dụng.

### 3.4. Lớp service

`hotel_service.py` định nghĩa các thao tác cho ba bảng:

- `get_all_hotels`, `create_hotel`.
- `get_rooms_by_hotel`, `create_room`.
- `get_all_guests`, `create_guest`.

Bốn hàm của Task 4 (`get_all_hotels`, `create_hotel`, `get_all_guests`, `create_guest`) đã được triển khai với xử lý exception và prepared statements cho thao tác ghi. Hai hàm liên quan đến phòng (`get_rooms_by_hotel`, `create_room`) vẫn là stub.

`booking_service.py` định nghĩa:

- `create_booking_batch`: ghi cùng một booking vào hai bảng.
- `get_bookings_by_guest`: truy vấn Q2.
- `get_bookings_by_hotel_date`: truy vấn Q3.
- `get_invoice_by_booking`: truy vấn Q4.
- `create_invoice`: tạo hóa đơn.

Các hàm này cũng chưa thực thi CQL. Đặc biệt, `create_booking_batch` là nghiệp vụ trung tâm nhưng chưa tạo `booking_id`, chưa dùng `BatchStatement`, chưa cập nhật trạng thái phòng và chưa trả kết quả thành công.

`dashboard_service.py` là service hoàn chỉnh duy nhất. Hàm `get_dashboard_stats()`:

- Đếm khách sạn từ toàn bộ `hotel_id`.
- Đếm tổng phòng và phòng còn trống từ toàn bộ `is_available`.
- Đếm booking từ toàn bộ `booking_id` trong `bookings_by_guest`.
- Tính tổng doanh thu từ toàn bộ `total_amount` trong `invoices_by_booking`.
- Khi mất kết nối hoặc có exception, trả bộ số liệu 0.

## 4. Mô hình dữ liệu Cassandra

`cql/schema.cql` tạo keyspace `hotel_ks` và sáu bảng:

| Bảng | Primary key | Mục đích |
|---|---|---|
| `hotels` | `hotel_id` | Thông tin khách sạn |
| `rooms_by_hotel` | `(hotel_id, room_number)` | Q1: phòng theo khách sạn |
| `guests` | `guest_id` | Hồ sơ khách hàng |
| `bookings_by_guest` | `(guest_id, booking_id)` | Q2: lịch sử booking theo khách |
| `bookings_by_hotel_date` | `((hotel_id, check_in_date), booking_id)` | Q3: booking theo khách sạn và ngày check-in |
| `invoices_by_booking` | `(booking_id, invoice_id)` | Q4: hóa đơn theo booking |

### 4.1. Điểm hợp lý

- `rooms_by_hotel` dùng `hotel_id` làm partition key, phù hợp với truy vấn liệt kê phòng của một khách sạn.
- `bookings_by_hotel_date` dùng partition key ghép `(hotel_id, check_in_date)`, phù hợp trực tiếp với Q3.
- Booking được phi chuẩn hóa sang hai bảng để tránh JOIN, đúng hướng thiết kế phổ biến của Cassandra.
- Kiểu `set<text>` cho tiện nghi khách sạn giúp loại trùng phần tử.

### 4.2. Hạn chế của mô hình hiện tại

- `bookings_by_guest` sắp xếp theo `booking_id`, không theo ngày. Vì vậy lịch sử đặt phòng không tự nhiên có thứ tự thời gian và khó truy vấn theo khoảng ngày.
- `hotels` và `guests` chỉ có partition key riêng cho từng bản ghi. `SELECT *` để lập danh sách sẽ quét toàn bảng, không phù hợp khi dữ liệu lớn.
- Trạng thái phòng chỉ là một cờ `is_available`. Mô hình này không biểu diễn phòng trống theo khoảng ngày và không đủ để phát hiện hai booking bị trùng lịch.
- Không có bảng booking chuẩn duy nhất theo `booking_id`; việc cập nhật/hủy booking phải đồng bộ thủ công giữa hai bảng phi chuẩn hóa.
- Chưa có bảng hoặc trường phục vụ thống kê theo thời gian. Dashboard phải quét các bảng nghiệp vụ.
- `invoices_by_booking` cho phép nhiều hóa đơn trên một booking, nhưng service `get_invoice_by_booking()` dự kiến chỉ trả `rows.one()`. Ý nghĩa nghiệp vụ giữa “một” và “nhiều” hóa đơn chưa thống nhất.

### 4.3. Lưu ý về batch Q5

Hai bản ghi booking thuộc hai partition khác nhau: một partition theo `guest_id`, một partition theo `(hotel_id, check_in_date)`. Logged batch có thể giúp hai bản ghi được áp dụng cùng nhau, nhưng batch xuyên partition tạo thêm chi phí điều phối và không nên được dùng như cơ chế tối ưu hiệu năng. Cassandra cũng không cung cấp tính cô lập giao dịch đầy đủ giữa nhiều partition như cơ sở dữ liệu quan hệ. Với đồ án nhỏ cách này có thể chấp nhận, nhưng cần kiểm soát kích thước batch, lỗi ghi và chiến lược sửa dữ liệu nếu hai view bị lệch.

## 5. Phân tích giao diện

### 5.1. Thành phần đã hoàn thiện

- `base.html`: layout chung, navbar desktop/mobile, footer, tải CSS/JS và các CDN.
- `index.html`: hero section, liên kết nhanh và bốn chỉ số tổng quan.
- `dashboard.html`: bốn KPI và biểu đồ doughnut tỷ lệ phòng trống/đã đặt bằng Chart.js.
- `static/css/style.css`: bảo đảm footer nằm cuối trang bằng flex layout.
- `static/js/main.js`: hiện chỉ log trạng thái; menu mobile được xử lý inline trong `base.html`.

### 5.2. Thành phần chưa hoàn thiện

Các file `hotels.html`, `rooms.html`, `guests.html`, `bookings.html` và `invoices.html` mới hiển thị khung thông báo vị trí cần code. Chúng chưa có:

- Form nhập liệu.
- Bảng lặp qua dữ liệu Jinja.
- Trạng thái rỗng/lỗi cụ thể.
- Nút thao tác nghiệp vụ.
- Hiển thị validation và flash message.

Giao diện phụ thuộc internet để tải Tailwind Browser CDN, Google Fonts, Bootstrap Icons và Chart.js. Khi chạy offline hoặc CDN lỗi, trang vẫn có HTML nhưng phần lớn style/icon/chart sẽ không hoạt động như thiết kế.

## 6. Mức độ hoàn thiện chức năng

| Hạng mục | Đánh giá |
|---|---|
| Khởi tạo Flask và Blueprint | Hoàn thiện |
| Kết nối Astra DB | Có triển khai cơ bản |
| Schema và dữ liệu mẫu | Có |
| Trang chủ | Hoàn thiện ở mức demo |
| Dashboard | Có logic và giao diện |
| Service liệt kê/thêm khách sạn | Đã triển khai và có unit test |
| Route/template khách sạn | Chưa hoàn thiện |
| Liệt kê/thêm phòng | Chưa triển khai |
| Service liệt kê/thêm khách hàng | Đã triển khai và có unit test |
| Route/template khách hàng | Chưa hoàn thiện |
| Tạo và tra cứu booking | Chưa triển khai |
| Tạo và xem hóa đơn | Chưa triển khai |
| Validation và thông báo lỗi | Chưa triển khai |
| Test tự động | Có 6 unit test đạt; integration test Astra đang chờ cấu hình |
| Authentication/authorization | Không có |

Kết luận: ứng dụng hiện là skeleton có dashboard đọc thật từ database và service khách sạn/khách hàng đã có thể đọc, ghi Cassandra. Nếu Astra DB chưa được cấu hình, trang chủ và dashboard vẫn tải được với toàn bộ số liệu bằng 0; các trang nghiệp vụ vẫn chưa có đầy đủ giao diện và xử lý form.

## 7. Các vấn đề và rủi ro kỹ thuật

### Mức cao

1. **Nhiều chức năng cốt lõi chưa hoạt động.** Service phòng/booking/invoice vẫn là stub, các POST route không xử lý dữ liệu và năm template nghiệp vụ là placeholder. Riêng service khách sạn và khách hàng đã hoàn thành ở Task 4.
2. **Không có kiểm tra xung đột lịch phòng.** Cờ `is_available` không phụ thuộc ngày, nên thiết kế hiện tại có thể nhận nhiều booking trùng phòng và trùng khoảng thời gian.
3. **Cấu hình chạy không an toàn khi triển khai.** `app.secret_key` có giá trị fallback cố định và `app.run(debug=True)` luôn bật debug, không sử dụng `FLASK_DEBUG` trong `.env.example`.

### Mức trung bình

1. **Không có validation, CSRF và chuẩn hóa dữ liệu đầu vào.** Các form POST dự kiến sẽ cần kiểm tra ID, email, ngày, số tiền, trạng thái và quyền thao tác.
2. **Dashboard quét toàn bảng.** Cách đếm ở Python phù hợp dữ liệu demo nhưng sẽ chậm và tốn tài nguyên khi dữ liệu tăng.
3. **Lỗi database bị che thành dữ liệu rỗng.** Người dùng không phân biệt được “không có dữ liệu” với “mất kết nối/lỗi truy vấn”.
4. **Thiếu quản lý vòng đời kết nối.** Không có đóng `Cluster`, retry, timeout hoặc health endpoint.
5. **Thiếu xử lý nhất quán cho dữ liệu phi chuẩn hóa.** Chưa có logic cập nhật/hủy đồng thời hai bảng booking.

### Mức thấp

1. `flash` được import nhưng chưa dùng.
2. `USE_MOCK=true` được khai báo trong `.env.example` nhưng không có code đọc biến này.
3. `FLASK_DEBUG=true` được khai báo nhưng cũng không được đọc.
4. `main.js` gần như chưa có logic; menu mobile đặt inline trong template thay vì gom vào file JS chung.
5. URL trong template được hard-code (`/hotels`, `/bookings`, ...) thay vì dùng `url_for`, làm giảm khả năng đổi route/prefix.

## 8. Thứ tự hoàn thiện được đề xuất

1. Hoàn thiện hai hàm phòng còn lại trong `hotel_service.py` và các hàm trong `booking_service.py`, tiếp tục ưu tiên prepared statements.
2. Hoàn thiện POST routes cho khách sạn/khách hàng: parse form, validate, gọi các service Task 4 và dùng flash message.
3. Hoàn thiện năm template nghiệp vụ với form, bảng dữ liệu, trạng thái rỗng và lỗi.
4. Thiết kế cơ chế kiểm tra phòng trống theo khoảng ngày trước khi cho phép tạo booking.
5. Quyết định quy tắc đồng bộ khi tạo, cập nhật hoặc hủy booking giữa các bảng phi chuẩn hóa.
6. Tắt debug theo môi trường, bắt buộc `SECRET_KEY` an toàn và bổ sung CSRF.
7. Bổ sung test unit cho service, test route Flask và test tích hợp với một môi trường Cassandra riêng.
8. Khi dữ liệu tăng, tạo các bảng tổng hợp/counter theo nhu cầu dashboard thay vì quét toàn bảng.

## 9. Kết luận

Mã nguồn có cách chia module dễ hiểu và thể hiện đúng ý tưởng query-first/denormalization của Cassandra. Schema đã hỗ trợ trực tiếp các truy vấn Q1-Q4, còn Q5 được định hướng bằng batch ghi hai bảng. Task 4 đã hoàn thiện tầng service đọc/ghi cho `hotels` và `guests`, nhưng dự án vẫn chưa phải một hệ thống quản lý khách sạn hoàn chỉnh vì route, giao diện và các nghiệp vụ phòng/booking/invoice còn TODO.

Ưu tiên tiếp theo là nối các service Task 4 vào route/template, hoàn thiện service phòng và booking, sau đó xử lý bài toán phòng trống theo khoảng ngày. Nếu chỉ điền các câu CQL đang comment mà không bổ sung kiểm tra lịch và cơ chế đồng bộ dữ liệu phi chuẩn hóa, ứng dụng có thể chạy nhưng vẫn dễ phát sinh booking trùng và dữ liệu không nhất quán.
