# ====================================================================
# ROUTES: KHÁCH SẠN, PHÒNG & KHÁCH HÀNG
# PHỤ TRÁCH: ĐỊNH
# ====================================================================

from flask import Blueprint, render_template, request, redirect, url_for, flash
from services import hotel_service

hotel_bp = Blueprint('hotel', __name__)

# --------------------------------------------------------------------
# ROUTE KHÁCH SẠN
# --------------------------------------------------------------------

@hotel_bp.route('/hotels', methods=['GET'])
def list_hotels():
    """
    TODO (Định):
    1. Gọi hotel_service.get_all_hotels() để lấy danh sách khách sạn
    2. Truyền danh sách qua template hotels.html
    """
    hotels = hotel_service.get_all_hotels()
    return render_template('hotels.html', hotels=hotels)


@hotel_bp.route('/hotels/add', methods=['POST'])
def add_hotel():
    """
    TODO (Định):
    1. Lấy dữ liệu từ form (name, phone, address, city, country, amenities)
    2. Gọi hotel_service.create_hotel(...) để lưu vào AstraDB
    3. Chuyển hướng về trang danh sách /hotels
    """
    # Xử lý form thêm khách sạn tại đây
    return redirect(url_for('hotel.list_hotels'))


# --------------------------------------------------------------------
# ROUTE PHÒNG (QUERY Q1: Tìm phòng theo khách sạn)
# --------------------------------------------------------------------

@hotel_bp.route('/hotels/<hotel_id>/rooms', methods=['GET'])
def list_rooms(hotel_id):
    """
    TODO (Định):
    1. Gọi hotel_service.get_rooms_by_hotel(hotel_id) (Thực hiện Query Q1)
    2. Truyền danh sách phòng qua template rooms.html
    """
    rooms = hotel_service.get_rooms_by_hotel(hotel_id)
    return render_template('rooms.html', hotel_id=hotel_id, rooms=rooms)


@hotel_bp.route('/hotels/<hotel_id>/rooms/add', methods=['POST'])
def add_room(hotel_id):
    """
    TODO (Định):
    1. Lấy dữ liệu phòng từ form (room_number, room_type, price_per_night, is_available)
    2. Gọi hotel_service.create_room(...) để lưu
    3. Chuyển hướng lại trang danh sách phòng
    """
    return redirect(url_for('hotel.list_rooms', hotel_id=hotel_id))


# --------------------------------------------------------------------
# ROUTE KHÁCH HÀNG
# --------------------------------------------------------------------

@hotel_bp.route('/guests', methods=['GET'])
def list_guests():
    """
    TODO (Định):
    1. Gọi hotel_service.get_all_guests()
    2. Truyền danh sách qua template guests.html
    """
    guests = hotel_service.get_all_guests()
    return render_template('guests.html', guests=guests)


@hotel_bp.route('/guests/add', methods=['POST'])
def add_guest():
    """
    TODO (Định):
    1. Lấy dữ liệu từ form (full_name, email, phone, id_card)
    2. Gọi hotel_service.create_guest(...)
    3. Chuyển hướng lại trang /guests
    """
    return redirect(url_for('hotel.list_guests'))
