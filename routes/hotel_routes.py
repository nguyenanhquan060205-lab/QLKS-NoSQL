# ====================================================================
# ROUTES: KHÁCH SẠN, PHÒNG & KHÁCH HÀNG
# PHỤ TRÁCH: ĐỊNH
# ====================================================================

from uuid import uuid4
import re

from flask import Blueprint, flash, redirect, render_template, request, url_for

from services import hotel_service

hotel_bp = Blueprint('hotel', __name__)

# --------------------------------------------------------------------
# ROUTE KHÁCH SẠN
# --------------------------------------------------------------------

@hotel_bp.route('/hotels', methods=['GET'])
def list_hotels():
    """Hiển thị form thêm mới và danh sách khách sạn."""
    hotels = hotel_service.get_all_hotels()
    return render_template('hotels.html', hotels=hotels, form_data={}, errors={})


@hotel_bp.route('/hotels/add', methods=['POST'])
def add_hotel():
    """Validate form và thêm khách sạn mới vào Cassandra/Astra DB."""
    form_data = {
        'name': request.form.get('name', '').strip(),
        'phone': request.form.get('phone', '').strip(),
        'address': request.form.get('address', '').strip(),
        'city': request.form.get('city', '').strip(),
        'country': request.form.get('country', '').strip(),
        'amenities': request.form.get('amenities', '').strip(),
    }
    field_labels = {
        'name': 'Tên khách sạn',
        'phone': 'Số điện thoại',
        'address': 'Địa chỉ',
        'city': 'Thành phố',
        'country': 'Quốc gia',
    }
    errors = {
        field: f'{label} không được để trống.'
        for field, label in field_labels.items()
        if not form_data[field]
    }

    if errors:
        flash('Vui lòng kiểm tra lại các trường bắt buộc.', 'error')
        hotels = hotel_service.get_all_hotels()
        return render_template(
            'hotels.html',
            hotels=hotels,
            form_data=form_data,
            errors=errors,
        ), 400

    hotel_id = f'H{uuid4().hex[:8].upper()}'
    created = hotel_service.create_hotel(
        hotel_id,
        form_data['name'],
        form_data['phone'],
        form_data['address'],
        form_data['city'],
        form_data['country'],
        form_data['amenities'],
    )
    if created:
        flash(f'Đã thêm khách sạn {form_data["name"]} thành công.', 'success')
        return redirect(url_for('hotel.list_hotels'))

    flash('Không thể thêm khách sạn. Vui lòng kiểm tra kết nối Astra DB.', 'error')
    hotels = hotel_service.get_all_hotels()
    return render_template(
        'hotels.html',
        hotels=hotels,
        form_data=form_data,
        errors={},
    ), 503


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
    """Hiển thị form thêm mới và danh sách khách hàng."""
    guests = hotel_service.get_all_guests()
    return render_template('guests.html', guests=guests, form_data={}, errors={})


@hotel_bp.route('/guests/add', methods=['POST'])
def add_guest():
    """Validate form và thêm khách hàng mới vào Cassandra/Astra DB."""
    form_data = {
        'full_name': request.form.get('full_name', '').strip(),
        'email': request.form.get('email', '').strip(),
        'phone': request.form.get('phone', '').strip(),
        'id_card': request.form.get('id_card', '').strip(),
    }
    field_labels = {
        'full_name': 'Họ và tên',
        'email': 'Email',
        'phone': 'Số điện thoại',
        'id_card': 'CCCD/Hộ chiếu',
    }
    errors = {
        field: f'{label} không được để trống.'
        for field, label in field_labels.items()
        if not form_data[field]
    }
    if form_data['email'] and not re.fullmatch(
        r'[^@\s]+@[^@\s]+\.[^@\s]+',
        form_data['email'],
    ):
        errors['email'] = 'Email chưa đúng định dạng.'

    if errors:
        flash('Vui lòng kiểm tra lại các trường bắt buộc.', 'error')
        guests = hotel_service.get_all_guests()
        return render_template(
            'guests.html',
            guests=guests,
            form_data=form_data,
            errors=errors,
        ), 400

    guest_id = f'G{uuid4().hex[:8].upper()}'
    created = hotel_service.create_guest(
        guest_id,
        form_data['full_name'],
        form_data['email'],
        form_data['phone'],
        form_data['id_card'],
    )
    if created:
        flash(f'Đã thêm khách hàng {form_data["full_name"]} thành công.', 'success')
        return redirect(url_for('hotel.list_guests'))

    flash('Không thể thêm khách hàng. Vui lòng kiểm tra kết nối Astra DB.', 'error')
    guests = hotel_service.get_all_guests()
    return render_template(
        'guests.html',
        guests=guests,
        form_data=form_data,
        errors={},
    ), 503
