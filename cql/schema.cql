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
    PRIMARY KEY (hotel_id, room_number)
);

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
    PRIMARY KEY (booking_id, invoice_id)
);


-- ====================================================================
-- DỮ LIỆU MẪU CHUỖI KHÁCH SẠN MƯỜNG THANH & GIÁ PHÒNG THỰC TẾ
-- ====================================================================

-- 1. Khách sạn Mường Thanh tại các tỉnh thành lớn (theo danh mục 34 tỉnh)
INSERT INTO hotels (hotel_id, name, phone, address, city, country, amenities)
VALUES ('H001', 'Mường Thanh Luxury Đà Nẵng', '02363956789', '270 Võ Nguyên Giáp, Phường Mỹ An', 'Thành phố Đà Nẵng', 'Vietnam', {'Bể bơi vô cực', 'Spa', 'Bãi biển riêng', 'Gym', 'Wifi'});

INSERT INTO hotels (hotel_id, name, phone, address, city, country, amenities)
VALUES ('H002', 'Mường Thanh Luxury Nha Trang', '02583898888', '60 Trần Phú, Phường Lộc Thọ', 'Khánh Hòa', 'Vietnam', {'Bể bơi ngoài trời', 'Trung tâm hội nghị', 'Spa', 'View biển', 'Wifi'});

INSERT INTO hotels (hotel_id, name, phone, address, city, country, amenities)
VALUES ('H003', 'Mường Thanh Grand Hà Nội', '02436408686', 'Lô CC2 Bắc Linh Đàm, Phường Đại Kim', 'Thành phố Hà Nội', 'Vietnam', {'Hồ bơi trong nhà', 'Sân tennis', 'Nhà hàng', 'Gym', 'Wifi'});

INSERT INTO hotels (hotel_id, name, phone, address, city, country, amenities)
VALUES ('H004', 'Mường Thanh Luxury Sài Gòn', '02838445678', '261 Nguyễn Văn Trỗi, Phường 10', 'Thành phố Hồ Chí Minh', 'Vietnam', {'Rooftop Bar', 'Hồ bơi sân thượng', 'Gym', 'Đưa đón sân bay', 'Wifi'});

-- 2. Phòng mẫu theo các hạng phòng và giá thực tế Mường Thanh
-- Đà Nẵng
INSERT INTO rooms_by_hotel (hotel_id, room_number, room_type, price_per_night, is_available)
VALUES ('H001', '101', 'Deluxe Twin', 1350000, true);

INSERT INTO rooms_by_hotel (hotel_id, room_number, room_type, price_per_night, is_available)
VALUES ('H001', '102', 'Deluxe King', 1450000, true);

INSERT INTO rooms_by_hotel (hotel_id, room_number, room_type, price_per_night, is_available)
VALUES ('H001', '201', 'Executive Suite', 2600000, true);

INSERT INTO rooms_by_hotel (hotel_id, room_number, room_type, price_per_night, is_available)
VALUES ('H001', '301', 'Grand Suite', 3800000, true);

-- Nha Trang
INSERT INTO rooms_by_hotel (hotel_id, room_number, room_type, price_per_night, is_available)
VALUES ('H002', '401', 'Deluxe Ocean', 1650000, true);

INSERT INTO rooms_by_hotel (hotel_id, room_number, room_type, price_per_night, is_available)
VALUES ('H002', '501', 'Executive Suite', 2800000, true);

-- Hà Nội
INSERT INTO rooms_by_hotel (hotel_id, room_number, room_type, price_per_night, is_available)
VALUES ('H003', '105', 'Superior King', 950000, true);

INSERT INTO rooms_by_hotel (hotel_id, room_number, room_type, price_per_night, is_available)
VALUES ('H003', '205', 'Deluxe King', 1250000, true);

-- Sài Gòn
INSERT INTO rooms_by_hotel (hotel_id, room_number, room_type, price_per_night, is_available)
VALUES ('H004', '601', 'Deluxe King', 1600000, true);

-- 3. Khách hàng mẫu kèm địa chỉ cư trú
INSERT INTO guests (guest_id, full_name, email, phone, id_card, address)
VALUES ('G001', 'Nguyễn Văn An', 'nguyenvanan@gmail.com', '0912345678', '079201001234', '123 Nguyễn Thị Minh Khai, Thành phố Đà Nẵng');

INSERT INTO guests (guest_id, full_name, email, phone, id_card, address)
VALUES ('G002', 'Trần Thị Mai', 'tranmai@gmail.com', '0987654321', '079201005678', '45 Hàng Bài, Phường Tràng Tiền, Thành phố Hà Nội');
