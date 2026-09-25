-- ====================================================================
-- HỆ THỐNG QUẢN LÝ KHÁCH SẠN (CHUỖI MƯỜNG THANH) - CASSANDRA / ASTRADB
-- Phụ trách chung: Chạy file này trên CQL Console của DataStax AstraDB
-- ====================================================================

-- 1. TẠO KEYSPACE (Nếu dùng AstraDB thì Keyspace thường tạo lúc tạo DB)
CREATE KEYSPACE IF NOT EXISTS hotel_ks
WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};

USE hotel_ks;

-- ====================================================================
-- PHẦN CỦA ĐỊNH: KHÁCH SẠN, PHÒNG, KHÁCH HÀNG (QLKS-04 ĐẾN QLKS-07)
-- ====================================================================

-- Bảng 1: Thông tin Khách sạn
CREATE TABLE IF NOT EXISTS hotels (
    hotel_id text,
    name text,
    phone text,
    address text,
    city text,
    country text,
    amenities set<text>,
    PRIMARY KEY (hotel_id)
);

-- Bảng 2: Danh sách phòng theo khách sạn (Query Q1: Tìm phòng theo khách sạn)
CREATE TABLE IF NOT EXISTS rooms_by_hotel (
    hotel_id text,
    room_number text,
    room_type text,
    price_per_night decimal,
    is_available boolean,
    status text,          -- 'AVAILABLE', 'OCCUPIED', 'MAINTENANCE'
    capacity int,         -- Số khách tối đa (1-10)
    bed_type text,        -- 'Single', 'Double', 'Twin', 'King', 'Queen'
    description text,
    current_guest_name text,   -- Tên khách ĐANG lưu trú (denormalize để trang chi tiết phòng
                               -- đọc 1 lần theo khóa chính, không phải quét bookings_by_guest).
                               -- Chỉ có giá trị khi status = 'OCCUPIED', NULL ở mọi trạng thái khác.
    current_booking_id text,   -- Mã booking đang gắn với phòng, cùng vòng đời với current_guest_name
    PRIMARY KEY (hotel_id, room_number)
);

-- LỆNH MIGRATION: Nếu bảng rooms_by_hotel đã tạo từ trước thiếu các cột mới, chạy trên AstraDB CQL Console:
-- ALTER TABLE rooms_by_hotel ADD status text;
-- ALTER TABLE rooms_by_hotel ADD capacity int;
-- ALTER TABLE rooms_by_hotel ADD bed_type text;
-- ALTER TABLE rooms_by_hotel ADD description text;
-- ALTER TABLE rooms_by_hotel ADD current_guest_name text;
-- ALTER TABLE rooms_by_hotel ADD current_booking_id text;

-- Bảng 3: Hồ sơ khách hàng (Bao gồm địa chỉ cư trú)
CREATE TABLE IF NOT EXISTS guests (
    guest_id text,
    full_name text,
    email text,
    phone text,
    id_card text,
    address text,
    PRIMARY KEY (guest_id)
);

-- LỆNH MIGRATION: Nếu bảng guests đã tồn tại từ trước, chạy lệnh sau trên AstraDB Console:
-- ALTER TABLE guests ADD address text;


-- ====================================================================
-- PHẦN CỦA QUÂN: ĐẶT PHÒNG & HÓA ĐƠN
-- ====================================================================

-- Bảng 4: Lịch sử đặt phòng theo khách hàng (Query Q2: Xem lịch sử đặt phòng của khách)
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

-- Bảng 5: Đặt phòng theo khách sạn và ngày (Query Q3: Tìm đặt phòng theo KS và ngày check-in)
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

-- Bảng 6: Hóa đơn theo mã đặt phòng (Query Q4: Xem chi tiết hóa đơn theo booking)
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


-- ====================================================================
-- PHẦN CỦA NHƯ: BẢNG COUNTER CHO DASHBOARD
-- ====================================================================

-- Bảng 7: Số phòng theo trạng thái của từng khách sạn (Dashboard / Trang chủ)
-- Query: "Mỗi khách sạn có bao nhiêu phòng trống / đang thuê / bảo trì?"
-- Gộp sẵn bằng kiểu COUNTER thay vì quét toàn bảng rooms_by_hotel mỗi lần mở dashboard.
-- Quy tắc của bảng counter: mọi cột ngoài khóa chính đều phải là counter, chỉ
-- cập nhật bằng "cột = cột + n", không INSERT, và không được chung BATCH với lệnh thường.
-- Cập nhật bởi room_service.create_room() và change_room_status().
-- Nạp số liệu ban đầu / đồng bộ lại: python scripts/sync_room_status_counts.py
CREATE TABLE IF NOT EXISTS room_status_counts_by_hotel (
    hotel_id text,
    total_rooms counter,
    available_rooms counter,
    occupied_rooms counter,
    maintenance_rooms counter,
    PRIMARY KEY (hotel_id)
);


-- ====================================================================
-- DỮ LIỆU MẪU CHUỖI KHÁCH SẠN MƯỜNG THANH HOSPITALITY (MT_001 - MT_005)
-- ====================================================================

-- 1. Các chi nhánh tiêu biểu phủ các tỉnh thành
INSERT INTO hotels (hotel_id, name, phone, address, city, country, amenities)
VALUES ('MT_001', 'Mường Thanh Luxury Hà Nội Centre', '02439428686', 'Số 78 Thợ Nhuộm, Phường Trần Hưng Đạo, Hoàn Kiếm', 'Thành phố Hà Nội', 'Vietnam', {'Hồ bơi trong nhà', 'Trầm Spa & Massage', 'Nhà hàng Bát Tràng', 'Phòng tập thể thao', 'Phòng hội nghị'});

INSERT INTO hotels (hotel_id, name, phone, address, city, country, amenities)
VALUES ('MT_002', 'Mường Thanh Grand Hà Nội', '02436408686', 'Lô CC2, Khu đô thị Bắc Linh Đàm, Đại Kim, Hoàng Mai', 'Thành phố Hà Nội', 'Vietnam', {'Hồ bơi bốn mùa', 'Phòng gym', 'Nhà hàng Cầu Gỗ', 'Bar sân thượng', 'Wifi tốc độ cao'});

INSERT INTO hotels (hotel_id, name, phone, address, city, country, amenities)
VALUES ('MT_003', 'Mường Thanh Grand Điện Biên Phủ', '02153810056', 'Số 514 Đường Võ Nguyên Giáp, Phường Him Lam', 'Điện Biên', 'Vietnam', {'Hồ bơi ngoài trời', 'Nhà hàng Mường Phăng ẩm thực Tây Bắc', 'Hoa Ban Spa', 'Sân tennis'});

INSERT INTO hotels (hotel_id, name, phone, address, city, country, amenities)
VALUES ('MT_004', 'Mường Thanh Luxury Sông Hàn', '02363656166', 'Số 115 Nguyễn Văn Linh, Phường Nam Dương, Hải Châu', 'Thành phố Đà Nẵng', 'Vietnam', {'Hồ bơi ngoài trời view cầu Rồng', 'D’Lusso Spa & Massage', 'Nhà hàng Camellia', 'Sky Bar'});

INSERT INTO hotels (hotel_id, name, phone, address, city, country, amenities)
VALUES ('MT_005', 'Mường Thanh Luxury Sài Gòn', '02838445678', 'Số 261 Nguyễn Văn Trỗi, Phường 10, Phú Nhuận', 'Thành phố Hồ Chí Minh', 'Vietnam', {'Hồ bơi vô cực tầng thượng', 'Nhà hàng Phú Nhuận', 'Chăm sóc sức khỏe hoa Sen', 'Phòng tập gym'});

-- 2. Phòng mẫu theo tiêu chuẩn chuỗi Mường Thanh
INSERT INTO rooms_by_hotel (hotel_id, room_number, room_type, price_per_night, is_available, status, capacity, bed_type, description)
VALUES ('MT_001', '101', 'Deluxe King', 1850000, true, 'AVAILABLE', 2, '1 Giường King', 'Phòng cao cấp hướng phố, trang bị bồn tắm nằm sang trọng');

INSERT INTO rooms_by_hotel (hotel_id, room_number, room_type, price_per_night, is_available, status, capacity, bed_type, description)
VALUES ('MT_001', '102', 'Deluxe Twin', 1850000, true, 'AVAILABLE', 2, '2 Giường Twin', 'Phòng hai giường đơn tiện nghi cao cấp');

INSERT INTO rooms_by_hotel (hotel_id, room_number, room_type, price_per_night, is_available, status, capacity, bed_type, description)
VALUES ('MT_001', '201', 'Executive Suite', 3600000, false, 'OCCUPIED', 3, '1 Giường King lớn', 'Phòng Suite thượng hạng phòng khách riêng biệt view toàn cảnh');

-- 3. Khách hàng mẫu kèm địa chỉ cư trú
INSERT INTO guests (guest_id, full_name, email, phone, id_card, address)
VALUES ('G001', 'Nguyễn Văn An', 'nguyenvanan@gmail.com', '0912345678', '079201001234', '123 Nguyễn Thị Minh Khai, Thành phố Đà Nẵng');

INSERT INTO guests (guest_id, full_name, email, phone, id_card, address)
VALUES ('G002', 'Trần Thị Mai', 'tranmai@gmail.com', '0987654321', '079201005678', '45 Hàng Bài, Phường Tràng Tiền, Thành phố Hà Nội');
