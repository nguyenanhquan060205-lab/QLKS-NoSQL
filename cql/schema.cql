-- ====================================================================
-- HỆ THỐNG QUẢN LÝ KHÁCH SẠN - CASSANDRA / ASTRADB SCHEMA
-- Phụ trách chung: Chạy file này trên CQL Console của DataStax AstraDB
-- ====================================================================

-- 1. TẠO KEYSPACE (Nếu dùng AstraDB thì Keyspace thường tạo lúc tạo DB)
CREATE KEYSPACE IF NOT EXISTS hotel_ks
WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};

USE hotel_ks;

-- ====================================================================
-- PHẦN CỦA ĐỊNH: KHÁCH SẠN, PHÒNG, KHÁCH HÀNG
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

-- Bảng 3: Hồ sơ khách hàng
CREATE TABLE IF NOT EXISTS guests (
    guest_id text,
    full_name text,
    email text,
    phone text,
    id_card text,
    PRIMARY KEY (guest_id)
);


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
-- DỮ LIỆU MẪU ĐỂ TEST TRUY VẤN (INSERT SAMPLE DATA)
-- ====================================================================

-- Khách sạn mẫu
INSERT INTO hotels (hotel_id, name, phone, address, city, country, amenities)
VALUES ('H001', 'Vinpearl Resort Nha Trang', '02583598100', 'Đảo Hòn Tre', 'Nha Trang', 'Vietnam', {'Bể bơi', 'Spa', 'Bãi biển riêng', 'Wifi'});

INSERT INTO hotels (hotel_id, name, phone, address, city, country, amenities)
VALUES ('H002', 'Sheraton Saigon Hotel', '02838272828', '88 Đồng Khởi, Q.1', 'Hồ Chí Minh', 'Vietnam', {'Gym', 'Hồ bơi vô cực', 'Bar sân thượng', 'Nhà hàng'});

-- Phòng mẫu
INSERT INTO rooms_by_hotel (hotel_id, room_number, room_type, price_per_night, is_available)
VALUES ('H001', '101', 'Deluxe Ocean View', 2500000, true);

INSERT INTO rooms_by_hotel (hotel_id, room_number, room_type, price_per_night, is_available)
VALUES ('H001', '102', 'Standard Garden', 1800000, true);

INSERT INTO rooms_by_hotel (hotel_id, room_number, room_type, price_per_night, is_available)
VALUES ('H002', '201', 'Executive Suite', 4200000, true);

-- Khách hàng mẫu
INSERT INTO guests (guest_id, full_name, email, phone, id_card)
VALUES ('G001', 'Nguyễn Văn An', 'nguyenvanan@gmail.com', '0912345678', '079201001234');

INSERT INTO guests (guest_id, full_name, email, phone, id_card)
VALUES ('G002', 'Trần Thị Mai', 'tranmai@gmail.com', '0987654321', '079201005678');
