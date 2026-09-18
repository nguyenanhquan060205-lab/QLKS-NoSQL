# Báo cáo rà soát hệ thống — nhóm QLKS NoSQL

**Cập nhật:** 18/09/2026, sau khi gộp toàn bộ công việc của 3 thành viên lên `main`.
**Commit tại thời điểm rà soát:** `1b5694a`

Bản trước của tài liệu này kết luận "hệ thống vận hành trơn tru, không có bất kỳ lỗi
route" và chấm mọi trang là "hoàn hảo". Kết luận đó **sai**. Lúc viết, `/dashboard` đang
trả về 500, hai truy vấn Q2 và Q3 cũng 500, và mọi phòng đang thuê đều không hiện được
tên khách. Bản này viết lại theo đúng những gì đã kiểm chứng bằng cách chạy thật.

---

## 1. Phân công (theo README_JIRA.md)

| Người | Task | Phạm vi |
|---|---|---|
| **Định** (9 SP) | QLKS-04 | Service CQL `hotels`, `guests` |
| | QLKS-05 | Service CQL Query Q1 `rooms_by_hotel` |
| | QLKS-06 | Route + giao diện Khách sạn, Khách hàng |
| **Như** (13 SP) | QLKS-01 | Keyspace `hotel_ks` + DDL schema |
| | QLKS-02 | Module kết nối `database/db.py` |
| | QLKS-03 | Khung layout Tailwind, navbar, footer |
| | QLKS-07 | Route + giao diện Quản lý phòng |
| | QLKS-12 | Dashboard thống kê + trang chủ |
| **Quân** (13 SP) | QLKS-08 | BATCH INSERT đặt phòng (Q5) |
| | QLKS-09 | Tra cứu lịch sử Q2, Q3 |
| | QLKS-10 | Hóa đơn + đặt cọc (Q4) |
| | QLKS-11 | Giao diện Đặt phòng, Hóa đơn |
| **Cả nhóm** | QLKS-13 | Kiểm thử tích hợp E2E |
| | QLKS-14 | Bắt lỗi ngoại lệ + tinh chỉnh UI |

---

## 2. Những lỗi đã tìm ra và đã sửa

### 2.1. Lỗi làm trang không mở được

| Lỗi | Hậu quả | Nguyên nhân |
|---|---|---|
| `/dashboard` trả 500 | Không mở được dashboard | `dashboard.html` lặp `period_options` nhưng route không truyền. Jinja2 không iterate được `Undefined` nên raise chứ không render rỗng |
| Bộ lọc dashboard không có tác dụng | Chọn kỳ/khách sạn xong số liệu không đổi | Route gọi `get_dashboard_stats()` (hardcode `period="all"`) thay vì `get_dashboard_report()`, và không đọc `request.args` |
| Q2 và Q3 trả 500 | Lịch sử đặt phòng của **mọi khách có đơn** đều chết | Template đọc field kiểu `b.x if b.x is defined else b.get('x')`. Với cassandra `Row` thiếu cột thì rơi xuống `.get()` — mà `Row` không có method đó |
| Đổi trạng thái phòng luôn báo "Lỗi kết nối AstraDB" | Không trả phòng / chuyển bảo trì được | `is_available` được dùng mà không bao giờ được gán → `UnboundLocalError`, bị `except` nuốt rồi gán nhãn sai thành lỗi kết nối |
| Thiếu 2 cột trong `schema.cql` | DB dựng mới từ schema sẽ làm trang Quản lý phòng rỗng | `room_service` `SELECT current_guest_name, current_booking_id` nhưng schema chưa khai báo |

### 2.2. Lỗi số liệu âm thầm (không báo lỗi, chỉ ra số sai)

- **Crash khi có hóa đơn ngày 29/02**: `strptime(k, "%d/%m")` lấy năm mặc định 1900, không phải năm nhuận.
- **Biểu đồ sai thứ tự khi kỳ vắt qua năm mới**: cùng dòng đó, `05/01` bị xếp trước `28/12`. Đã sửa bằng cách gom theo đối tượng `date` thật rồi mới lấy nhãn.
- **`_in_range()` làm mất dữ liệu**: trả `False` cho ngày `NULL` ngay cả khi không lọc kỳ → mọi hóa đơn thiếu ngày biến mất khỏi cả thống kê "toàn bộ thời gian".
- **`dict(_EMPTY_REPORT)` là shallow copy**: các list bên trong dùng chung object với template toàn process.
- **Trang chủ hiện ô rỗng**: `index.html` dùng 4 key (`occupied_rooms`, `maintenance_rooms`, `total_guests`, `total_invoices`) mà report không trả.
- **Đọc thẳng `r.name` / `r.hotel_id`**: một dòng dữ liệu `NULL` là mất trắng cả danh sách qua `except`, không phải mất một dòng.

### 2.3. Lỗi nghiệp vụ

**Không có đường nào đóng booking.** Trong cả `booking_service.py` không tồn tại một lệnh
`UPDATE bookings_by_guest` nào, nên booking đứng mãi ở `CONFIRMED`. Bấm "Trả phòng" chỉ
giải phóng phòng, còn `get_active_booking_for_room()` vẫn coi khách đang lưu trú — hai
module tự mâu thuẫn. `bookings.html` đã có sẵn badge `COMPLETED` mà không ai ghi vào.

Đã bổ sung `complete_booking()` (BATCH cập nhật cả 2 bảng) và route
`POST /bookings/<id>/checkout`, đóng booking trước rồi mới giải phóng phòng.

**Cửa sổ đặt trùng phòng 30 giây.** `get_all_rooms()` có cache in-memory 30s, mà
`change_room_status()` không biết cache đó tồn tại. Đặt phòng xong danh sách vẫn hiện
"Đang trống" đủ lâu để đặt trùng.

### 2.4. Vệ sinh kiểm thử

**Unit test ghi thẳng vào database production.** `tests/test_booking_routes.py` patch
`get_room` nhưng không patch `change_room_status`, mà hàm đó tự mở kết nối AstraDB.

Kiểm chứng: xoá `H001/101`, chạy đúng một test, phòng mọc lại ngay với
`current_booking_id='BK_NEW_123'`. Phòng rác đó bị đếm vào "tổng số phòng" và "phòng đang
thuê" trên dashboard. Nó cũng là lý do riêng test đó mất 16 giây.

Đã chặn ở `setUp`, và thêm `tearDownClass` cho `test_room_service_integration.py` vốn
không dọn gì. Sau khi vá: chạy đủ 94 test rồi kiểm tra lại, **0 dòng rác còn sót**.

---

## 3. Hiện trạng kiểm thử

Môi trường: conda env `qlks`, Python 3.11. Lưu ý `cassandra-driver==3.29.2` **không build
được trên Python 3.14**.

### 3.1. Unit test + integration test

| File | Số test | Phụ trách gốc |
|---|---:|---|
| `test_hotel_service.py` | 11 | Định |
| `test_hotel_service_integration.py` | 2 | Định |
| `test_room_service.py` | 9 | Định & Như |
| `test_room_service_integration.py` | 1 | Định & Như |
| `test_hotel_routes.py` | 18 | Định & Như |
| `test_hotel_routes_integration.py` | 2 | Định |
| `test_dashboard_service.py` | 2 | Như |
| `test_booking_routes.py` | 27 | Quân |
| `test_booking_service.py` | 20 | Quân |
| `test_booking_service_integration.py` | 2 | Quân |
| **Tổng** | **94** | |

```bash
PYTHONPATH=. python -m unittest discover -s tests
# Ran 94 tests — OK
```

### 3.2. Kiểm thử E2E (QLKS-13)

`scripts/e2e_full_test.py` — **79 kiểm tra**, đi qua route Flask thật, template thật và
AstraDB thật. Khác unit test (mock session), script này bắt được lỗi ở chỗ nối giữa các
tầng, đúng loại lỗi vừa nêu ở mục 2.1.

Phạm vi: 6 trang chính · dashboard và bộ lọc kỳ · khách sạn thêm/sửa và ràng buộc · phòng
Q1 và toàn bộ ma trận chuyển trạng thái · khách hàng · đặt phòng BATCH Q5 ghi cả 2 bảng,
tự tạo hóa đơn Q4, tự đẩy tên khách sang module Phòng · tra cứu Q2 Q3 Q4 · trả phòng sớm ·
7 đường dẫn rác không được trả 500.

Script tự tạo dữ liệu riêng mang nhãn `E2E` rồi dọn trong `finally`, tự kiểm tra lại là
không còn sót. Đã chạy nhiều lần, số liệu nhóm giữ nguyên.

```bash
python scripts/e2e_full_test.py          # 79/79 PASS
python scripts/e2e_full_test.py --keep   # giữ dữ liệu test để xem tận mắt
```

---

## 4. Số liệu cơ sở dữ liệu (đã kiểm chứng)

| Chỉ số | Giá trị |
|---|---:|
| Khách sạn | 40 |
| Phòng | 558 |
| — đang trống | 488 |
| — đang thuê | 48 |
| — bảo trì | 22 |
| Khách hàng | 53 |
| Đơn đặt phòng | 138 |
| Hóa đơn | 138 |
| Doanh thu | 818.550.000 đ |

Đã đối chiếu: `488 + 48 + 22 = 558`, và số đơn đơn điệu theo kỳ
(hôm nay 3 ≤ tháng 60 ≤ năm 124 ≤ toàn bộ 138).

**Đã dọn dữ liệu mồ côi**: 4 phòng thuộc khách sạn không tồn tại, 2 booking và 2 hóa đơn
trỏ tới khách sạn `H002` và khách `G2EA0FEED` đều đã bị xoá. Hai booking đó là rác thử
tay — số phòng `1111111`, ngày trả `08/09` trước ngày nhận `17/09`, tạo từ trước khi có
validation chặn ngày ngược. Hiện **không còn bản ghi mồ côi nào**.

---

## 5. Việc còn mở

### 5.1. Cần Như quyết (logic thống kê, không ai nên tự đổi)

1. **Bộ lọc kỳ chỉ lọc theo `check_in_date`** → booking bắt đầu trước mốc kỳ mà còn ở
   trong kỳ bị loại hẳn. Đã kiểm chứng trên dữ liệu thật: `BK2025261089` (29/08 → 02/09)
   có 1 đêm thuộc tháng 9 nhưng không được tính vào kỳ "Tháng 9".
2. **ADR trộn hai mẫu số**: số đêm phòng lấy từ `bookings` (lọc theo `check_in_date`),
   doanh thu lấy từ `invoices` (lọc theo `issue_date`) — hai tập khác nhau.
3. **Cache 30s khi bấm "Trả phòng" ở trang chi tiết phòng** chưa được hủy. Đường trả
   phòng mới đã hủy cache; nút của Như thì chưa. Thêm một dòng `invalidate_rooms_cache()`
   vào `change_room_status()` là xong, nhưng đó là hàm của Như.
4. **Quy ước đếm `MT_`**: `total_hotels` chỉ đếm khách sạn có mã bắt đầu bằng `MT_` để
   loại row test. Nếu sau này mã không theo tiền tố đó thì phải bỏ quy ước này.

### 5.2. Nợ kỹ thuật cả nhóm nên biết

- **Tiền dùng `float`** thay vì `Decimal` trong `dashboard_service` — mất chính xác trong
  một ứng dụng tính tiền.
- **Mỗi lần load dashboard là 5 lần quét toàn bảng** rồi gộp số ở Python. Tránh được
  `ALLOW FILTERING` thật, nhưng với môn NoSQL thì nguyên tắc query-first sẽ muốn một bảng
  gộp sẵn (counter table) chứ không phải quét cả bảng.
- **Ở quá hạn chưa xử lý**: mới có trả sớm, chưa có phụ phí khi khách ở quá ngày.
- **`room_detail` flash lỗi cho mọi đường dẫn không khớp** dưới `/hotels/<id>/rooms/<...>`.
  Trình duyệt tự xin `logo.png` theo đường dẫn tương đối → rơi vào route này → flash một
  thông báo mà request ảnh không bao giờ render, nên thông báo đó **rò sang trang kế tiếp**
  người dùng mở.
- **Chính sách đã chốt**: trả phòng sớm **không giảm giá, không hoàn tiền**. Hóa đơn giữ
  nguyên, chỉ ghi lại ngày trả thực tế.

---

## 6. Cách tự kiểm chứng

Đừng tin bảng số ở trên, chạy lại:

```bash
conda activate qlks

# 94 unit + integration test
PYTHONPATH=. python -m unittest discover -s tests

# 79 kiểm tra E2E trên database thật, tự dọn sau khi chạy
python scripts/e2e_full_test.py

# chạy app
python app.py        # http://127.0.0.1:5050
```

Nếu vừa dựng keyspace mới từ `cql/schema.cql`, chạy thêm:

```bash
python scripts/backfill_room_current_guest.py --apply
```

để bù `current_guest_name` cho các phòng đang `OCCUPIED` — dữ liệu do seed script tạo
không đi qua luồng đặt phòng nên hai cột này còn `NULL`.
