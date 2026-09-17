# ====================================================================
# ROUTES: KHÁCH SẠN, PHÒNG & KHÁCH HÀNG
# PHỤ TRÁCH: ĐỊNH
# ====================================================================

from uuid import uuid4
from decimal import Decimal, InvalidOperation
import re

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for

from services import hotel_service, location_service

hotel_bp = Blueprint('hotel', __name__)

PHONE_REGEX = r'^0\d{9}$'
ID_CARD_REGEX = r'^\d{12}$|^[A-Za-z]\d{7,8}$'


def is_valid_phone(phone: str) -> bool:
    """Kiểm tra số điện thoại Việt Nam hợp lệ: 10 chữ số, bắt đầu bằng 0."""
    return bool(re.fullmatch(PHONE_REGEX, (phone or '').strip()))


def is_valid_id_card(id_card: str) -> bool:
    """Kiểm tra CCCD (12 chữ số) hoặc Hộ chiếu (1 chữ cái + 7-8 chữ số, VD: B1234567) hợp lệ."""
    return bool(re.fullmatch(ID_CARD_REGEX, (id_card or '').strip()))


# --------------------------------------------------------------------
# API ĐỊA CHỈ & TỈNH THÀNH (Dữ liệu từ docs/provinces.json)
# --------------------------------------------------------------------

@hotel_bp.route('/api/provinces', methods=['GET'])
def get_provinces_api():
    """API trả về danh sách 34 tỉnh thành sau sáp nhập."""
    provinces = location_service.get_all_provinces()
    return jsonify(provinces)


@hotel_bp.route('/api/provinces/<province_code>/wards', methods=['GET'])
def get_wards_api(province_code):
    """API trả về danh sách phường/xã theo mã tỉnh."""
    wards = location_service.get_wards_by_province(province_code)
    return jsonify(wards)


# --------------------------------------------------------------------
# ROUTE KHÁCH SẠN (CRUD)
# --------------------------------------------------------------------

@hotel_bp.route('/hotels', methods=['GET'])
def list_hotels():
    """Hiển thị form thêm mới và danh sách khách sạn."""
    hotels = hotel_service.get_all_hotels()
    provinces = location_service.get_all_provinces()
    return render_template(
        'hotels.html',
        hotels=hotels,
        provinces=provinces,
        form_data={},
        errors={},
    )


@hotel_bp.route('/hotels/add', methods=['POST'])
def add_hotel():
    """Validate form và thêm khách sạn mới vào Cassandra/Astra DB."""
    name = request.form.get('name', '').strip()
    phone = request.form.get('phone', '').strip()
    city = request.form.get('city', '').strip()
    ward = request.form.get('ward', '').strip()
    raw_address = request.form.get('address', '').strip()
    country = request.form.get('country', '').strip() or 'Vietnam'

    # Tự động ghép phường/xã vào địa chỉ chi tiết nếu có
    if ward and ward not in raw_address:
        address = f"{raw_address}, {ward}".strip(', ')
    else:
        address = raw_address

    # Tiện nghi từ danh sách checkbox hoặc chuỗi
    amenities_list = request.form.getlist('amenities')
    custom_amenity = request.form.get('custom_amenity', '').strip()
    if custom_amenity:
        amenities_list.extend([a.strip() for a in custom_amenity.split(',') if a.strip()])
    if not amenities_list and request.form.get('amenities'):
        amenities_list = [a.strip() for a in request.form.get('amenities').split(',') if a.strip()]
    amenities_str = ', '.join(amenities_list)

    form_data = {
        'name': name,
        'phone': phone,
        'address': address,
        'city': city,
        'country': country,
        'amenities': amenities_str,
        'ward': ward,
        'raw_address': raw_address,
    }

    field_labels = {
        'name': 'Tên khách sạn',
        'phone': 'Số điện thoại',
        'address': 'Địa chỉ',
        'city': 'Thành phố',
    }
    errors = {
        field: f'{label} không được để trống.'
        for field, label in field_labels.items()
        if not form_data[field]
    }

    if form_data['phone'] and not is_valid_phone(form_data['phone']):
        errors['phone'] = 'Số điện thoại phải gồm đúng 10 chữ số và bắt đầu bằng số 0 (Ví dụ: 0901234567).'

    hotels = hotel_service.get_all_hotels()
    if not errors.get('name') and form_data['name']:
        if any((h.name or '').strip().lower() == form_data['name'].strip().lower() for h in hotels):
            errors['name'] = f"Tên khách sạn '{form_data['name']}' đã tồn tại trong hệ thống."

    if errors:
        flash('Vui lòng kiểm tra lại các trường thông tin.', 'error')
        provinces = location_service.get_all_provinces()
        return render_template(
            'hotels.html',
            hotels=hotels,
            provinces=provinces,
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
    provinces = location_service.get_all_provinces()
    return render_template(
        'hotels.html',
        hotels=hotels,
        provinces=provinces,
        form_data=form_data,
        errors={},
    ), 503


@hotel_bp.route('/hotels/<hotel_id>/edit', methods=['POST'])
def edit_hotel(hotel_id):
    """Cập nhật thông tin khách sạn."""
    name = request.form.get('name', '').strip()
    phone = request.form.get('phone', '').strip()
    city = request.form.get('city', '').strip()
    ward = request.form.get('ward', '').strip()
    raw_address = request.form.get('address', '').strip()
    country = request.form.get('country', '').strip() or 'Vietnam'

    if ward and ward not in raw_address:
        address = f"{raw_address}, {ward}".strip(', ')
    else:
        address = raw_address

    amenities_list = request.form.getlist('amenities')
    custom_amenity = request.form.get('custom_amenity', '').strip()
    if custom_amenity:
        amenities_list.extend([a.strip() for a in custom_amenity.split(',') if a.strip()])
    if not amenities_list and request.form.get('amenities'):
        amenities_list = [a.strip() for a in request.form.get('amenities').split(',') if a.strip()]
    amenities_str = ', '.join(amenities_list)

    if not (name and phone and address and city):
        flash('Vui lòng điền đầy đủ các trường thông tin bắt buộc.', 'error')
        return redirect(url_for('hotel.list_hotels'))

    if not is_valid_phone(phone):
        flash('Số điện thoại cập nhật không hợp lệ (cần 10 chữ số bắt đầu bằng 0).', 'error')
        return redirect(url_for('hotel.list_hotels'))

    hotels = hotel_service.get_all_hotels()
    if any((h.name or '').strip().lower() == name.strip().lower() and h.hotel_id != hotel_id for h in hotels):
        flash(f"Tên khách sạn '{name}' đã được sử dụng bởi một cơ sở khác.", 'error')
        return redirect(url_for('hotel.list_hotels'))

    updated = hotel_service.update_hotel(
        hotel_id,
        name,
        phone,
        address,
        city,
        country,
        amenities_str,
    )
    if updated:
        flash(f'Đã cập nhật thông tin khách sạn {name} thành công.', 'success')
    else:
        flash('Cập nhật khách sạn thất bại. Vui lòng kiểm tra kết nối cơ sở dữ liệu.', 'error')

    return redirect(url_for('hotel.list_hotels'))


@hotel_bp.route('/hotels/<hotel_id>/delete', methods=['POST'])
def delete_hotel(hotel_id):
    """Xóa khách sạn và dọn dẹp các phòng thuộc khách sạn."""
    deleted = hotel_service.delete_hotel(hotel_id)
    if deleted:
        flash(f'Đã xóa khách sạn ({hotel_id}) thành công.', 'success')
    else:
        flash('Xóa khách sạn thất bại. Vui lòng kiểm tra lại.', 'error')

    return redirect(url_for('hotel.list_hotels'))


# --------------------------------------------------------------------
# ROUTE PHÒNG (QUERY Q1: Tìm phòng theo khách sạn)
# --------------------------------------------------------------------

@hotel_bp.route('/hotels/<hotel_id>/rooms', methods=['GET'])
def list_rooms(hotel_id):
    """Hiển thị form thêm phòng và danh sách phòng theo khách sạn (Query Q1)."""
    hotel = hotel_service.get_hotel_by_id(hotel_id)
    all_hotels = hotel_service.get_all_hotels()
    rooms = hotel_service.get_rooms_by_hotel(hotel_id)
    return render_template(
        'rooms.html',
        hotel_id=hotel_id,
        hotel=hotel,
        all_hotels=all_hotels,
        rooms=rooms,
        form_data={},
        errors={},
    )


@hotel_bp.route('/hotels/<hotel_id>/rooms/add', methods=['POST'])
def add_room(hotel_id):
    """Validate form và thêm phòng mới vào partition của khách sạn hotel_id."""
    form_data = {
        'room_number': request.form.get('room_number', '').strip(),
        'room_type': request.form.get('room_type', '').strip(),
        'price_per_night': request.form.get('price_per_night', '').strip(),
        'is_available': request.form.get('is_available', ''),
    }
    field_labels = {
        'room_number': 'Số phòng',
        'room_type': 'Loại phòng',
        'price_per_night': 'Giá phòng/đêm',
    }
    errors = {
        field: f'{label} không được để trống.'
        for field, label in field_labels.items()
        if not form_data[field]
    }

    if not errors.get('price_per_night') and form_data['price_per_night']:
        try:
            if Decimal(form_data['price_per_night']) <= 0:
                errors['price_per_night'] = 'Giá phòng phải lớn hơn 0.'
        except InvalidOperation:
            errors['price_per_night'] = 'Giá phòng phải là số hợp lệ.'

    if errors:
        flash('Vui lòng kiểm tra lại các trường bắt buộc.', 'error')
        hotel = hotel_service.get_hotel_by_id(hotel_id)
        all_hotels = hotel_service.get_all_hotels()
        rooms = hotel_service.get_rooms_by_hotel(hotel_id)
        return render_template(
            'rooms.html',
            hotel_id=hotel_id,
            hotel=hotel,
            all_hotels=all_hotels,
            rooms=rooms,
            form_data=form_data,
            errors=errors,
        ), 400

    is_available = form_data['is_available'].strip().lower() in {'1', 'true', 'yes', 'on'}
    created = hotel_service.create_room(
        hotel_id,
        form_data['room_number'],
        form_data['room_type'],
        form_data['price_per_night'],
        is_available,
    )
    if created:
        flash(f'Đã thêm phòng {form_data["room_number"]} thành công.', 'success')
        return redirect(url_for('hotel.list_rooms', hotel_id=hotel_id))

    flash('Không thể thêm phòng. Vui lòng kiểm tra kết nối Astra DB.', 'error')
    hotel = hotel_service.get_hotel_by_id(hotel_id)
    all_hotels = hotel_service.get_all_hotels()
    rooms = hotel_service.get_rooms_by_hotel(hotel_id)
    return render_template(
        'rooms.html',
        hotel_id=hotel_id,
        hotel=hotel,
        all_hotels=all_hotels,
        rooms=rooms,
        form_data=form_data,
        errors={},
    ), 503


# --------------------------------------------------------------------
# ROUTE KHÁCH HÀNG (CRUD)
# --------------------------------------------------------------------

@hotel_bp.route('/guests', methods=['GET'])
def list_guests():
    """Hiển thị form thêm mới và danh sách khách hàng."""
    guests = hotel_service.get_all_guests()
    provinces = location_service.get_all_provinces()
    return render_template(
        'guests.html',
        guests=guests,
        provinces=provinces,
        form_data={},
        errors={},
    )


@hotel_bp.route('/guests/add', methods=['POST'])
def add_guest():
    """Validate form và thêm khách hàng mới vào Cassandra/Astra DB."""
    full_name = request.form.get('full_name', '').strip()
    email = request.form.get('email', '').strip()
    phone = request.form.get('phone', '').strip()
    id_card = request.form.get('id_card', '').strip().upper()
    city = request.form.get('city', '').strip()
    ward = request.form.get('ward', '').strip()
    raw_address = request.form.get('address', '').strip()

    parts = []
    if raw_address:
        parts.append(raw_address)
    if ward and ward not in raw_address:
        parts.append(ward)
    if city and city not in raw_address:
        parts.append(city)
    address = ', '.join(parts) if parts else raw_address

    form_data = {
        'full_name': full_name,
        'email': email,
        'phone': phone,
        'id_card': id_card,
        'address': address,
        'city': city,
        'ward': ward,
        'raw_address': raw_address,
    }
    field_labels = {
        'full_name': 'Họ và tên',
        'email': 'Email',
        'phone': 'Số điện thoại',
        'id_card': 'Số CCCD / Hộ chiếu',
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

    if form_data['phone'] and not is_valid_phone(form_data['phone']):
        errors['phone'] = 'Số điện thoại phải gồm đúng 10 chữ số và bắt đầu bằng số 0 (Ví dụ: 0901234567).'

    if form_data['id_card'] and not is_valid_id_card(form_data['id_card']):
        errors['id_card'] = 'Số CCCD phải gồm đúng 12 chữ số hoặc Hộ chiếu gồm 1 chữ cái và 7-8 số (Ví dụ: B1234567).'

    guests = hotel_service.get_all_guests()
    # Kiểm tra trùng lặp CCCD/Hộ chiếu, Email, Số điện thoại
    if not errors.get('id_card') and form_data['id_card']:
        if any((g.id_card or '').strip().upper() == form_data['id_card'] for g in guests):
            errors['id_card'] = f"Số CCCD/Hộ chiếu '{form_data['id_card']}' đã được đăng ký cho khách hàng khác."

    if not errors.get('email') and form_data['email']:
        if any((g.email or '').strip().lower() == form_data['email'].lower() for g in guests):
            errors['email'] = f"Email '{form_data['email']}' đã tồn tại trong hệ thống."

    if not errors.get('phone') and form_data['phone']:
        if any((g.phone or '').strip() == form_data['phone'] for g in guests):
            errors['phone'] = f"Số điện thoại '{form_data['phone']}' đã được đăng ký cho khách hàng khác."

    if errors:
        flash('Vui lòng kiểm tra lại các trường thông tin.', 'error')
        provinces = location_service.get_all_provinces()
        return render_template(
            'guests.html',
            guests=guests,
            provinces=provinces,
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
        form_data['address'],
    )
    if created:
        flash(f'Đã thêm khách hàng {form_data["full_name"]} thành công.', 'success')
        return redirect(url_for('hotel.list_guests'))

    flash('Không thể thêm khách hàng. Vui lòng kiểm tra kết nối Astra DB.', 'error')
    provinces = location_service.get_all_provinces()
    return render_template(
        'guests.html',
        guests=guests,
        provinces=provinces,
        form_data=form_data,
        errors={},
    ), 503


@hotel_bp.route('/guests/<guest_id>/edit', methods=['POST'])
def edit_guest(guest_id):
    """Cập nhật thông tin hồ sơ khách hàng."""
    full_name = request.form.get('full_name', '').strip()
    email = request.form.get('email', '').strip()
    phone = request.form.get('phone', '').strip()
    id_card = request.form.get('id_card', '').strip().upper()
    city = request.form.get('city', '').strip()
    ward = request.form.get('ward', '').strip()
    raw_address = request.form.get('address', '').strip()

    parts = []
    if raw_address:
        parts.append(raw_address)
    if ward and ward not in raw_address:
        parts.append(ward)
    if city and city not in raw_address:
        parts.append(city)
    address = ', '.join(parts) if parts else raw_address

    if not (full_name and email and phone and id_card):
        flash('Vui lòng điền đầy đủ các thông tin bắt buộc.', 'error')
        return redirect(url_for('hotel.list_guests'))

    if not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', email):
        flash('Email cập nhật không đúng định dạng.', 'error')
        return redirect(url_for('hotel.list_guests'))

    if not is_valid_phone(phone):
        flash('Số điện thoại cập nhật không hợp lệ (cần 10 chữ số bắt đầu bằng 0).', 'error')
        return redirect(url_for('hotel.list_guests'))

    if not is_valid_id_card(id_card):
        flash('Số CCCD/Hộ chiếu cập nhật không hợp lệ (cần đúng 12 chữ số cho CCCD hoặc Hộ chiếu 1 chữ cái và 7-8 số, VD: B1234567).', 'error')
        return redirect(url_for('hotel.list_guests'))

    guests = hotel_service.get_all_guests()
    for g in guests:
        if getattr(g, 'guest_id', None) != guest_id:
            if (getattr(g, 'id_card', '') or '').strip().upper() == id_card:
                flash(f"Số CCCD/Hộ chiếu '{id_card}' đã được sử dụng bởi khách hàng khác.", 'error')
                return redirect(url_for('hotel.list_guests'))
            if (getattr(g, 'email', '') or '').strip().lower() == email.lower():
                flash(f"Email '{email}' đã được sử dụng bởi khách hàng khác.", 'error')
                return redirect(url_for('hotel.list_guests'))
            if (getattr(g, 'phone', '') or '').strip() == phone:
                flash(f"Số điện thoại '{phone}' đã được sử dụng bởi khách hàng khác.", 'error')
                return redirect(url_for('hotel.list_guests'))

    updated = hotel_service.update_guest(
        guest_id,
        full_name,
        email,
        phone,
        id_card,
        address,
    )
    if updated:
        flash(f'Đã cập nhật thông tin khách hàng {full_name} thành công.', 'success')
    else:
        flash('Cập nhật khách hàng thất bại. Vui lòng kiểm tra kết nối Astra DB.', 'error')

    return redirect(url_for('hotel.list_guests'))


@hotel_bp.route('/guests/<guest_id>/delete', methods=['POST'])
def delete_guest(guest_id):
    """Xóa hồ sơ khách hàng."""
    deleted = hotel_service.delete_guest(guest_id)
    if deleted:
        flash(f'Đã xóa khách hàng ({guest_id}) thành công.', 'success')
    else:
        flash('Xóa khách hàng thất bại. Vui lòng kiểm tra lại.', 'error')

    return redirect(url_for('hotel.list_guests'))
