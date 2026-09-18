# Note gửi Như — những gì Quân đã chỉnh trong phần của Như

**Ngày:** 18/09/2026
**Base:** `44d7c5b` (Merge PR #15) — đã pull đủ 3 PR mới của Như: #13, #14, #15
**Người sửa:** Quân (trong lúc làm QLKS-13 / QLKS-14)

Mình pull code của Như về rồi merge với nhánh mình đang làm. Có mấy chỗ phải sửa vào file
của Như để app chạy được, nên note lại đầy đủ để Như nắm và đối chiếu. Phần nào mình
không chắc thì có ghi rõ ở cuối.

---

## 1. VIỆC CẦN NHƯ LÀM NGAY (quan trọng nhất)

Chạy 2 lệnh này trên **AstraDB CQL Console**, nếu keyspace của Như chưa có 2 cột:

```sql
ALTER TABLE rooms_by_hotel ADD current_guest_name text;
ALTER TABLE rooms_by_hotel ADD current_booking_id text;
```

**Lý do:** commit `5a501e1` ("Cập nhật thêm tên khách đang thuê trong chi tiết phòng") có
`SELECT ... current_guest_name, current_booking_id` ở `services/room_service.py` trong cả
`get_rooms_by_hotel()` và `get_room()`, nhưng `cql/schema.cql` thì **chưa khai báo 2 cột đó**.

Nghĩa là code chỉ chạy được trên đúng database mà Như đã `ALTER TABLE` bằng tay. Ai
tạo keyspace mới từ `schema.cql` (mình, Định, hoặc thầy khi chấm) thì Cassandra trả
`InvalidRequest: Undefined column name current_guest_name` → `get_rooms_by_hotel()` rơi vào
`except`, trả về list rỗng → **trang Quản lý Phòng trống trơn, trang chi tiết phòng 404**.

Mình đã bổ sung 2 cột vào `cql/schema.cql:39-41` (trong `CREATE TABLE`) và thêm 2 dòng
`ALTER TABLE` vào khối "LỆNH MIGRATION" có sẵn ở `cql/schema.cql:51-52`. Từ giờ ai dựng DB
mới từ file này là có đủ cột.

> Lần sau thêm cột thì nhớ commit kèm `schema.cql` nha, không thì code chạy được trên máy
> mình mà chết trên máy người khác, rất khó lần ra.

---

## 2. BA LỖI CHẶN — ĐÃ SỬA

### 2.1. `/dashboard` trả về 500 (không mở được trang)

- **Chỗ lỗi:** `templates/dashboard.html:40` có `{% for value, label in period_options %}`
  nhưng `routes/dashboard_routes.py` chỉ truyền `stats`, không truyền `period_options`.
- **Vì sao chết:** Jinja2 không iterate được biến `Undefined`, nó raise `UndefinedError`
  chứ không phải render ra dropdown rỗng. Nên là 500 luôn, không phải "thiếu option".
- **Đã sửa:** truyền `period_options=dashboard_service.PERIOD_OPTIONS` ở
  `routes/dashboard_routes.py:48`.

### 2.2. Bộ lọc dashboard không có tác dụng

- **Chỗ lỗi:** `dashboard_service.get_dashboard_report(hotel_id, period, custom_start, custom_end)`
  Như viết rất đủ, nhưng route vẫn gọi `get_dashboard_stats()` — hàm này hardcode
  `hotel_id=None, period="all"` và không đọc `request.args`. Chọn khách sạn / chọn kỳ xong
  bấm "Áp dụng" thì số liệu y như cũ.
- **Đã sửa:** `routes/dashboard_routes.py:21-50` giờ đọc đúng 4 tham số mà form submit
  (`hotel_id`, `period`, `start_date`, `end_date`) rồi gọi `get_dashboard_report()`.
- **Kèm theo:** `custom_range_error` mà `resolve_period_range()` trả về trước giờ không
  ai render — nhập khoảng ngày sai thì hệ thống âm thầm đổi sang "toàn bộ thời gian" mà
  người dùng không biết. Giờ mình `flash()` nó ra.
- Ghi chú: `TODO (Như)` trong docstring của route mình thay bằng mô tả thật rồi.

### 2.3. Dashboard crash nếu có hóa đơn ngày 29/02

- **Chỗ lỗi:** dòng sort chuỗi nhãn ngày, `datetime.strptime(k, "%d/%m")`.
- **Vì sao:** `%d/%m` không có năm nên Python lấy mặc định **1900** — mà 1900 không phải
  năm nhuận (chia hết 100, không chia hết 400) → `strptime("29/02", "%d/%m")` raise
  `ValueError: day is out of range for month`.
- **Lỗi thứ hai cùng dòng:** kỳ báo cáo vắt qua năm mới thì sort sai thứ tự. Mình chạy thử:
  `['28/12','05/01','31/12','02/01']` sort ra `['02/01','05/01','28/12','31/12']` — tháng 1
  nằm trước tháng 12, biểu đồ đường đọc ngược.
- **Đã sửa:** `services/dashboard_service.py:333-350` — gom doanh thu theo **đối tượng
  `date` thật** làm khóa, sort theo `date` rồi mới lấy nhãn ra. Hết cả hai lỗi.

---

## 3. BA LỖI SỐ LIỆU ÂM THẦM — ĐÃ SỬA

### 3.1. `_in_range()` làm mất dữ liệu ở chế độ "Toàn bộ thời gian"

`services/dashboard_service.py:124` — hàm trả `False` khi `d` là `None`, kể cả lúc
**không lọc kỳ nào**. Hậu quả: mọi hóa đơn / booking bị NULL ngày sẽ biến mất khỏi luôn
cả thống kê "Toàn bộ thời gian" → doanh thu và lượt đặt bị hụt mà không có dấu hiệu gì.

Đã sửa: không lọc kỳ (`start` và `end` đều `None`) thì trả `True`, lấy tất.

### 3.2. `dict(_EMPTY_REPORT)` là shallow copy

`dict()` chỉ copy tầng ngoài, nên các list bên trong (`hotels`, `hotel_breakdown`,
`revenue_labels`, `revenue_values`) vẫn **dùng chung một object** với `_EMPTY_REPORT`.
Mình chạy thử: `r1 = dict(T); r1['hotels'].append('X')` → `T['hotels']` cũng thành `['X']`,
và mọi report tạo ra sau đó đều bị nhiễm, kéo dài suốt process.

Đã sửa thành `copy.deepcopy(_EMPTY_REPORT)` ở `services/dashboard_service.py:164`.

### 3.3. Một row dữ liệu thiếu làm sập cả khối thống kê

Code đọc thẳng `r.name`, `r.hotel_id`, `r.issue_date`... nên chỉ cần một row có cột NULL
hoặc query thiếu cột là nhảy vào `except`, **mất trắng cả danh sách** chứ không phải mất
một dòng. Mình đổi sang `getattr(r, "...", None)` ở các chỗ map row (hotels, rooms,
bookings, invoices). Khách sạn không có `name` thì hiện mã thay vì làm sập dashboard.

---

## 4. BỔ SUNG CHO KHỚP TRANG CHỦ (index.html)

`templates/index.html` đang dùng `stats.occupied_rooms`, `stats.maintenance_rooms`,
`stats.total_guests`, `stats.total_invoices` — bản `get_dashboard_report()` không trả 4 key
này, nên mấy ô số đó **hiện rỗng** (Jinja render `Undefined` thành chuỗi trắng, không báo lỗi).

Đã thêm 4 key vào report:

| Key | Cách tính |
|---|---|
| `occupied_rooms` | đếm `rooms_by_hotel` có `is_available=false` và `status != 'MAINTENANCE'` |
| `maintenance_rooms` | đếm `rooms_by_hotel` có `status = 'MAINTENANCE'` |
| `total_guests` | `SELECT guest_id FROM guests` (thêm ở `dashboard_service.py:238`) |
| `total_invoices` | `len(filtered_invoices)` — số hóa đơn trong kỳ đã lọc |

Query `rooms_by_hotel` giờ lấy thêm cột `status` (trước chỉ lấy `is_available`, không tách
được "đang thuê" với "bảo trì").

Nhân đó biểu đồ tròn trạng thái phòng trong `dashboard.html` đổi từ 2 phần
(Trống / Đã đặt) thành 3 phần (Đang trống / Đang thuê / Bảo trì) cho khớp 3 giá trị
`status` thật trong `ROOM_STATUSES`.

**Một quy ước của mình mà Như nên biết:** `total_hotels` chỉ đếm khách sạn có mã bắt đầu
bằng `MT_`, để loại mấy row test (`H_QLKS04_TEST`...) khỏi số liệu báo cáo. Nếu DB không có
row `MT_` nào thì fallback đếm tất. Xem `dashboard_service.py:194`.

---

## 5. QUY ƯỚC UI — ĐÃ BỎ TOÀN BỘ ICON

Mình bỏ hết `<i class="bi bi-...">` và emoji trong tất cả template, thay bằng chữ thuần
hoặc dot tròn nhỏ (`<span class="h-1.5 w-1.5 rounded-full bg-...">`). Gồm:
`dashboard.html`, `rooms.html`, `hotels.html`, `guests.html`, `bookings.html`, `invoices.html`.

Vì không template nào còn dùng icon font nữa, mình bỏ luôn link CDN `bootstrap-icons` trong
`templates/base.html:13` (đỡ một request). Có để lại comment: muốn thêm icon lại thì nạp CDN
ở base, đừng nhúng lẻ từng trang.

Đây là **quyết định về giao diện, không phải sửa lỗi** — nếu Như thích để icon thì nói,
nhóm chốt lại một hướng rồi sửa một lượt, chứ 2 người làm 2 kiểu thì mỗi lần merge lại
conflict đúng mấy dòng đó. Vòng merge này nó conflict ở `rooms.html` và `room_detail.html`
chính vì chuyện này.

---

## 6. PHẦN CỦA NHƯ ĐƯỢC GIỮ NGUYÊN

- `services/dashboard_service.py` và `templates/dashboard.html`: lúc merge mình lấy **y bản
  của Như**, bỏ hết phần dashboard mình đang viết dở (khoảng 200 dòng), rồi mới sửa lỗi ở trên.
- Toàn bộ route phòng trong `routes/hotel_routes.py`, ma trận `ALLOWED_TRANSITIONS` và
  `MANUAL_STATUS_ACTIONS` trong `room_service.py`: không đụng.
- `templates/room_detail.html`: giữ cách hiển thị khách đang thuê của Như
  (đọc `room.current_guest_name`), không đổi sang cách mình làm trước đó.

Trong 6 file bị conflict, mình đều chọn bên của Như. Tổng cộng bỏ 452 dòng code đang viết
dở của mình để nhường cho bản của Như.

---

## 7. CÁCH 2 MODULE NỐI VỚI NHAU

Cảm ơn Như để sẵn comment ở `room_service.py:36-42` và docstring của `is_room_bookable()` —
đọc là hiểu ngay ý định, nên mình móc vào đúng chỗ đó, không phải sửa logic gì của Như:

- **Lúc đặt phòng thành công** (`routes/booking_routes.py:538-553`): gọi
  `change_room_status(hotel_id, room_number, 'OCCUPIED', guest_name=..., booking_id=...)`.
  Trước đó mình có gọi hàm này rồi nhưng thiếu 2 tham số cuối, nên `current_guest_name`
  không bao giờ được ghi → trang chi tiết phòng luôn hiện nhánh "Chưa rõ".
- **Lúc trả phòng:** lễ tân bấm nút bên trang chi tiết phòng của Như, code Như tự xóa
  `current_guest_name` / `current_booking_id` về NULL. Mình không can thiệp.
- **Dashboard tự đồng bộ:** `change_room_status()` ghi luôn `is_available`, mà dashboard
  đếm phòng trống từ đúng cột đó.

**Một cái mình phải thêm:** `room_service.get_all_rooms()` có cache in-memory 30 giây
(phần mình viết). `change_room_status()` của Như không biết cache này tồn tại, nên đặt
phòng xong danh sách phòng vẫn hiện "Đang trống" tới 30 giây → **đặt trùng phòng được trong
cửa sổ đó**. Mình gọi `invalidate_rooms_cache()` ngay sau `change_room_status()` bên phía
`booking_routes.py` để khỏi phải sửa hàm của Như.

**Chỗ này còn hở, cần Như cho ý kiến:** đường trả phòng mới (mục 7b) đã tự hủy cache,
nhưng nút "Trả phòng" bên trang chi tiết phòng của Như thì chưa — bấm nút đó xong danh
sách phòng có thể trễ tối đa 30 giây. Hai cách: (a) thêm 1 dòng `invalidate_rooms_cache()`
vào trong `change_room_status()` để mọi nơi gọi đều đúng — gọn nhất nhưng là sửa hàm của Như;
(b) để nguyên, chịu trễ 30 giây. Như chọn hướng nào thì mình làm theo.

---

## 7b. TRẢ PHÒNG: TRƯỚC ĐÂY KHÔNG ĐÓNG ĐƯỢC BOOKING

Cái này phát sinh từ câu hỏi "khách trả phòng sớm thì sao", và hóa ra vấn đề lớn hơn:
**trong cả `booking_service.py` không có một lệnh `UPDATE bookings_by_guest` nào** — booking
tạo ra là đứng mãi ở `CONFIRMED`, không có đường nào đóng nó.

Hệ quả là 2 module nói 2 chuyện khác nhau: bấm "Trả phòng" trên trang của Như thì phòng về
`AVAILABLE`, nhưng `get_active_booking_for_room()` vẫn coi khách đó đang lưu trú (nó lọc theo
`status in ('CONFIRMED','CHECKED_IN','OCCUPIED')`). `templates/bookings.html` cũng đã có sẵn
badge `COMPLETED` → "Đã trả phòng" mà không ai ghi giá trị đó vào.

Mình thêm, toàn bộ nằm trong file của mình:
- `booking_service.complete_booking()` — BATCH update status `COMPLETED` sang cả 2 bảng
  (`bookings_by_guest` + `bookings_by_hotel_date`), cùng nguyên tắc denormalization như Q5.
- `POST /bookings/<booking_id>/checkout` — đóng booking **trước**, giải phóng phòng **sau**
  (đảo thứ tự mà bước đóng lỗi thì phòng đã trống trong khi booking vẫn "đang ở", đúng cái
  trạng thái lệch đang muốn tránh). Phòng được giải phóng qua `change_room_status()` của Như,
  và có gọi `invalidate_rooms_cache()` kèm.
- Nút "Trả phòng" trong bảng đơn đặt phòng. Đơn `PENDING` không có nút (chưa nhận phòng thì
  không có gì để trả).

**Nút "Trả phòng" của Như trên trang chi tiết phòng mình KHÔNG bỏ** — nó vẫn hữu ích khi cần
sửa trạng thái phòng bằng tay. Chỉ là nó chỉ giải phóng phòng, không đóng booking; muốn đóng
đủ cả hai thì đi qua nút bên trang Đặt phòng.

**Chính sách trả sớm (nhóm đã chốt): không giảm giá, không hoàn tiền.** Khách vẫn trả đủ số
đêm đã đặt, hóa đơn giữ nguyên `total_amount` / `deposit_amount` / `remaining_amount`. Nếu
khách đi sớm thì `check_out_date` được ghi lại là ngày trả **thực tế** (để lịch sử lưu trú
đúng), còn số đêm lệch chỉ hiện ra để ghi nhận chứ không dùng tính lại tiền. Ở quá hạn là
nghiệp vụ phụ phí khác, hiện chưa xử lý — giữ nguyên ngày dự kiến.

---

## 7c. MỘT LỖI TRONG PHẦN CỦA MÌNH (chỉ để Như biết, không cần làm gì)

Trang lịch sử đặt phòng của khách (`/bookings/guest/<id>`) đang **500 với mọi khách có đơn**.
Nguyên nhân: `bookings.html` đọc field kiểu `b.guest_name if b.guest_name is defined else
b.get('guest_name','')`. Với cassandra Row (namedtuple) thiếu cột thì nhánh `is defined` là
False, rơi xuống `.get()` — mà Row không có method `.get()` → Jinja `UndefinedError` → 500.
Bảng `bookings_by_guest` lại không có cột `guest_name` nên nhánh đó luôn bị chạm.

Nó làm chết luôn cả **Q2 và Q3** (`/bookings?guest_id=...` và `/bookings/hotel-date?...`) —
hai query chính của QLKS-09. Mình đã sửa bằng cách chuẩn hóa Q2/Q3 trả về cùng một shape dict
với `get_all_bookings()`, và bù tên khách/tên khách sạn bằng đọc **theo khóa chính**
(`WHERE guest_id = ?`), không `SELECT` cả bảng — để Q2 giữ đúng tính chất chỉ đụng 1 partition.

Ghi lại đây vì nó cùng một họ lỗi với chuyện ở mục 3.3: **đọc thẳng thuộc tính của Row rồi
giả định nó luôn tồn tại**. Chỗ nào dữ liệu đi từ Cassandra ra template thì nên chuẩn hóa ở
service trước, đừng để template đoán kiểu.

---

## 8. MỘT CHUYỆN VỀ GIT

Commit `2e0a1a1` ("Xóa tỉ lệ lấp đầy trong dashboard") có **conflict marker bị commit vào
repo** — trong `services/dashboard_service.py` còn nguyên `<<<<<<< Updated upstream` và
`=======`. Đó là dấu hiệu của một lần VS Code stash/pop bị conflict rồi commit luôn mà chưa
giải quyết.

Commit sau (`4873c1b`) đã dọn sạch nên `main` hiện tại không còn marker nào, python compile
bình thường — **không cần làm gì thêm**. Chỉ là lần sau trước khi commit, Như search nhanh
`<<<<<<<` trong file một lượt là chắc.

---

## 9. TRẠNG THÁI TEST

```
Ran 89 tests — OK (0 failure, 0 error)
```

Chạy bằng env conda `qlks` (Python 3.11). Lưu ý: `cassandra-driver==3.29.2` **không build
được trên Python 3.14** (`ez_setup.py` của nó gọi `TarFile.chown()` theo signature cũ). Như
mà gặp lỗi lúc `pip install` thì kiểm tra lại `python -V`, phải là 3.11/3.12.

Test mình đã cập nhật / thêm:
- `tests/test_booking_routes.py` — assert `guest_name` / `booking_id` được đẩy sang module
  Phòng lúc đặt phòng; thêm 4 test cho luồng trả phòng.
- `tests/test_hotel_routes.py` — viết lại test "khách đang thuê" theo cách của Như (đọc
  `room.current_guest_name`) thay vì cách cũ của mình. Thêm 1 test cho phòng OCCUPIED mà 2
  cột khách còn NULL.
- `tests/test_booking_service.py` — 4 test cho `complete_booking()`, 2 test cho shape dict
  của Q2 và 1 test chặn việc bù dữ liệu bằng full scan.
- `tests/test_dashboard_service.py` — pass cả 2.

## 9b. ĐÃ CHẠY THỬ APP THẬT — SỐ LIỆU LIVE

Mình đã chạy app với AstraDB thật và xác nhận từng thứ, không còn chỗ nào là suy luận:

- `/dashboard` giờ trả **200** (trước khi sửa mục 2.1 là 500), dropdown đủ 6 kỳ + 40 khách sạn.
- Bộ lọc ra số đúng và nhất quán:

| Lọc | Khách sạn | Phòng | Lượt đặt | Doanh thu |
|---|---|---|---|---|
| Toàn bộ thời gian | 40 | 562 | 138 | 820,350,000 |
| Năm 2026 | 40 | 562 | 124 | 753,250,000 |
| Tháng 9/2026 | 40 | 562 | 60 | 437,600,000 |
| Hôm nay | 40 | 562 | 1 | 1,350,000 |
| Chỉ MT_004 | 1 | 10 | 8 | 27,800,000 |

- Card phòng: 487 trống · 53 đang thuê · 22 bảo trì (3 con số này là phần bổ sung ở mục 4).
- Khoảng ngày ngược (30/9 → 1/9): báo đúng *"Từ ngày phải trước hoặc bằng Đến ngày"*.
- **Bug sort ngày ở mục 2.3 chứng minh được bằng data thật:** lọc 15/12/2025–15/01/2026 giờ
  ra nhãn `24/12, 25/12, 27/12, 28/12, 02/01` — tháng 12 đứng trước tháng 1. Trước khi sửa
  thì `02/01` sẽ nhảy lên đầu tiên.

**Một điểm yếu mình tìm thấy nhưng KHÔNG sửa, để Như quyết:** bộ lọc kỳ chỉ lọc theo
`check_in_date`, nên booking bắt đầu trước mốc kỳ mà còn ở trong kỳ thì bị loại hẳn. Mình
quét DB thấy 1 ca: `BK2025261089` (29/08 → 02/09) có 1 đêm thuộc tháng 9 nhưng không được
tính vào kỳ "Tháng 9". Hiện chỉ lệch 1 đêm nên chưa ảnh hưởng gì, nhưng data dày lên là lệch
nhiều. Liên quan tới chỗ này, ADR cũng đang lấy `room_nights_sold` từ bookings (lọc theo
`check_in_date`) chia cho `total_revenue` từ invoices (lọc theo `issue_date`) — hai tập khác
nhau nên con số ra khó giải thích. Như tính lại theo hướng nào thì nói mình làm.

---

## 10. TÓM LẠI, NHỜ NHƯ

**Cần làm:**
1. Chạy 2 lệnh `ALTER TABLE` ở mục 1 (hoặc dựng lại keyspace từ `schema.cql` mới). Không có
   2 cột đó thì module Phòng của Như không chạy được trên máy người khác.

**Cần Như quyết, mình làm theo:**

2. **Icon** (mục 5) — mình bỏ hết icon và bỏ luôn CDN bootstrap-icons. Đây là quyết định
   giao diện, không phải sửa lỗi. Như thích để icon thì nhóm chốt một hướng rồi sửa một
   lượt, chứ 2 người 2 kiểu thì mỗi lần merge lại conflict đúng mấy dòng đó.
3. **Cache lúc bấm "Trả phòng" bên trang của Như** (mục 7) — thêm 1 dòng
   `invalidate_rooms_cache()` vào `change_room_status()`, hay để chịu trễ 30 giây?
4. **Quy ước đếm `MT_`** (mục 4) — nếu mã khách sạn sau này không theo tiền tố đó thì mình bỏ.
5. **Bộ lọc kỳ chỉ theo `check_in_date`, và cách tính ADR** (mục 9b) — cái này là logic
   thống kê của Như, mình không tự đổi.

**Đã chốt rồi, chỉ để Như biết:** trả phòng sớm không giảm, không hoàn tiền (mục 7b).

**Xem giúp:** mình đã chạy app thật và confirm `/dashboard` + bộ lọc ra số đúng (mục 9b),
nhưng Như chạy lại trên máy mình một lượt cho chắc nha, nhất là sau khi `ALTER TABLE`.

---

*Có gì không đồng ý hoặc thấy mình sửa sai chỗ nào thì nói thẳng, mình sửa lại. Mấy chỗ mình
đụng vào file của Như đều là để app chạy được, không có ý làm lại phần của Như.*
