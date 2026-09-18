# Cách gỡ conflict nhánh `Nhu` với `main`

`main` giờ ở `09421b0`, nhánh `Nhu` ở `82b76dd`. Mình thử merge rồi: **chỉ 1 file conflict**.

## Chỉ cần làm 3 lệnh

```bash
git checkout Nhu
git merge main
git checkout --theirs routes/dashboard_routes.py   # lấy bản trên main
git add routes/dashboard_routes.py templates/dashboard.html
```

Sau đó xoá icon ở `templates/dashboard.html` dòng ~60:

```
- <i class="bi bi-exclamation-triangle-fill"></i> {{ stats.custom_range_error }}
+ {{ stats.custom_range_error }}
```

Rồi `git commit`.

## Vì sao lấy bản trên main cho `dashboard_routes.py`

Hai bên fix **giống hệt nhau** — cả hai đều đọc `request.args` và truyền `period_options`.
Khác duy nhất: bản trên main có thêm `.strip()` và một dòng `flash(custom_range_error)`.

Mà Như đã hiện lỗi khoảng ngày **inline ngay trong khung filter** (dashboard.html dòng 58) —
cách đó tốt hơn flash vì nó nằm đúng chỗ người dùng đang nhìn. Nên `flash()` thành thừa,
giữ cả hai thì lỗi hiện 2 lần. Lấy bản trên main là xong, không mất gì của Như.

## `templates/dashboard.html` không conflict

Git tự merge sạch: phân trang của Như và phần sửa của mình nằm ở 2 vùng khác nhau. Sau merge
giữ được cả:
- phân trang bảng so sánh khách sạn (của Như)
- biểu đồ tròn tách 3 trạng thái Đang trống / Đang thuê / Bảo trì (cần 2 key
  `occupied_rooms`, `maintenance_rooms` mà mình mới thêm vào `get_dashboard_report`)

## Còn cái icon

Mình đã bỏ toàn bộ icon trong template và bỏ luôn link CDN `bootstrap-icons` trong
`base.html`. Commit mới của Như thêm lại một `<i class="bi bi-exclamation-triangle-fill">`,
mà không còn CDN nên nó **không hiện ra gì cả** — chỉ là ô trống.

Nên mới có bước xoá icon ở trên. Nếu Như muốn giữ icon thì nói, mình nạp lại CDN vào
`base.html`, nhưng nhóm chốt một hướng thôi chứ 2 người 2 kiểu thì lần merge nào cũng đụng
đúng mấy dòng đó.

## Đã kiểm tra

Mình làm thử đúng các bước trên trong worktree riêng: compile sạch, **82 test pass**.
Không có marker `<<<<<<<` nào sót lại.

Chi tiết những chỗ mình đã sửa trong phần của Như thì xem `NOTE_GUI_NHU_18-09.md` — nhớ chạy
2 lệnh `ALTER TABLE` ở mục 1 nha, không có 2 cột đó thì module Phòng không chạy được.
