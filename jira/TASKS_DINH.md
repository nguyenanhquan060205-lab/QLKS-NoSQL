# 👤 NHIỆM VỤ CHI TIẾT: ĐỊNH
## 🏨 Module: Quản Lý Khách Sạn, Phòng & Khách Hàng (Catalog Data)

> **Tổng Story Points:** 11 SP  
> **Thời gian:** Thứ 2 ➡️ Hoàn thành trước Thứ 5 để test E2E.  
> **Bảng Cassandra:** `hotels`, `rooms_by_hotel` (Query Q1), `guests`.

---

## 📋 CHECKLIST CÔNG VIỆC CỦA ĐỊNH

### 1. File [services/hotel_service.py](file:///Users/quan/HUIT_CNTT/NoSQL/QLKS-NoSQL/services/hotel_service.py) (Viết hàm CQL)
- [ ] **`QLKS-04`** Viết hàm `get_all_hotels()`:
  ```python
  session = get_session()
  rows = session.execute("SELECT hotel_id, name, phone, address, city, country, amenities FROM hotels;")
  return list(rows)
  ```
- [ ] **`QLKS-04`** Viết hàm `create_hotel(hotel_id, name, phone, address, city, country, amenities)`:
  ```python
  # Lưu ý: amenities là set trong Cassandra, truyền dạng set/list: {'Wifi', 'Pool'}
  query = """
  INSERT INTO hotels (hotel_id, name, phone, address, city, country, amenities)
  VALUES (%s, %s, %s, %s, %s, %s, %s);
  """
  session.execute(query, (hotel_id, name, phone, address, city, country, set(amenities)))
  ```
- [ ] **`QLKS-05`** Viết hàm `get_rooms_by_hotel(hotel_id)` (**Query Q1 trong đề cương PDF**):
  ```python
  query = "SELECT hotel_id, room_number, room_type, price_per_night, is_available FROM rooms_by_hotel WHERE hotel_id = %s;"
  rows = session.execute(query, (hotel_id,))
  return list(rows)
  ```
- [ ] **`QLKS-05`** Viết hàm `create_room(hotel_id, room_number, room_type, price_per_night, is_available)`:
  ```python
  query = """
  INSERT INTO rooms_by_hotel (hotel_id, room_number, room_type, price_per_night, is_available)
  VALUES (%s, %s, %s, %s, %s);
  """
  session.execute(query, (hotel_id, room_number, room_type, price_per_night, is_available))
  ```
- [ ] **`QLKS-04`** Viết hàm `get_all_guests()` và `create_guest(guest_id, full_name, email, phone, id_card)`.

---

### 2. File [routes/hotel_routes.py](file:///Users/quan/HUIT_CNTT/NoSQL/QLKS-NoSQL/routes/hotel_routes.py) (Flask Blueprint)
- [ ] **`QLKS-06`** Route `GET /hotels`: Lấy danh sách khách sạn truyền sang template `hotels.html`.
- [ ] **`QLKS-06`** Route `POST /hotels/add`: Lấy dữ liệu `request.form`, gọi `create_hotel()`, redirect về `/hotels`.
- [ ] **`QLKS-07`** Route `GET /hotels/<hotel_id>/rooms`: Gọi `get_rooms_by_hotel(hotel_id)`, render `rooms.html`.
- [ ] **`QLKS-07`** Route `POST /hotels/<hotel_id>/rooms/add`: Nhận form thêm phòng, gọi `create_room()`.
- [ ] **`QLKS-06`** Route `GET /guests` & `POST /guests/add`: Quản lý danh sách và thêm khách hàng mới.

---

### 3. File Giao Diện Templates (Dùng Tailwind CSS v4)
- [ ] **[templates/hotels.html](file:///Users/quan/HUIT_CNTT/NoSQL/QLKS-NoSQL/templates/hotels.html)**:
  - Form thêm khách sạn (Mã KS, Tên, SĐT, Địa chỉ, Thành phố, Tiện ích).
  - Bảng hiển thị danh sách các khách sạn.
  - Nút bấm *"Xem phòng"* dẫn tới `/hotels/{{ hotel.hotel_id }}/rooms`.
- [ ] **[templates/rooms.html](file:///Users/quan/HUIT_CNTT/NoSQL/QLKS-NoSQL/templates/rooms.html)**:
  - Bảng hiển thị các phòng của khách sạn: Số phòng, Loại phòng, Giá/đêm, Trạng thái trống.
  - Form modal hoặc form inline để thêm phòng mới.
- [ ] **[templates/guests.html](file:///Users/quan/HUIT_CNTT/NoSQL/QLKS-NoSQL/templates/guests.html)**:
  - Bảng hiển thị khách hàng (Mã khách, Tên, Email, SĐT, CCCD).
  - Form thêm khách hàng mới.
  - Nút *"Xem lịch sử đặt phòng"* dẫn tới link của Quân: `/bookings/guest/{{ guest.guest_id }}`.

---

## 🎯 TIÊU CHUẨN HOÀN THÀNH (Definition of Done)
- Chạy `python app.py`, mở trình duyệt thêm được Khách sạn mới và xem được danh sách phòng.
- Query Q1 chạy đúng theo Partition Key `hotel_id` trên bảng `rooms_by_hotel`.
- Hoàn thành chậm nhất vào **Thứ Tư (16/09)** để Thứ Năm test tổng thể cùng nhóm!
