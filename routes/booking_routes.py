# ====================================================================
# ROUTES: ĐẶT PHÒNG & HÓA ĐƠN
# PHỤ TRÁCH: QUÂN
# ====================================================================

from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from types import SimpleNamespace
from uuid import uuid4
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from services import booking_service, hotel_service, room_service

booking_bp = Blueprint('booking', __name__)


def _get_form_context():
    """Lấy danh sách khách sạn và khách hàng phục vụ dropdown trong form/bộ lọc."""
    try:
        hotels = hotel_service.get_all_hotels()
    except Exception:
        hotels = []
    try:
        guests = hotel_service.get_all_guests()
    except Exception:
        guests = []
    return hotels, guests


# --------------------------------------------------------------------
# API LẤY DANH SÁCH PHÒNG CỦA KHÁCH SẠN (DÙNG CHO DROPDOWN FORM ĐẶT PHÒNG)
# --------------------------------------------------------------------

@booking_bp.route('/api/hotels/<hotel_id>/rooms', methods=['GET'])
def get_hotel_rooms_api(hotel_id):
    """API trả về danh sách phòng kèm trạng thái chi tiết của một khách sạn."""
    if not hotel_id:
        return jsonify({"success": False, "rooms": []})
    rooms = room_service.get_rooms_by_hotel(hotel_id)
    res = []
    for r in rooms:
        status_val = getattr(r, "status", None)
        is_avail = getattr(r, "is_available", True)
        if not status_val:
            status_val = "AVAILABLE" if is_avail else "OCCUPIED"

        price_val = getattr(r, "price_per_night", 0)
        try:
            price_float = float(price_val)
        except Exception:
            price_float = 0.0

        res.append({
            "hotel_id": str(getattr(r, "hotel_id", hotel_id)),
            "room_number": str(getattr(r, "room_number", "")),
            "room_type": getattr(r, "room_type", "Tiêu chuẩn"),
            "price_per_night": price_float,
            "is_available": bool(is_avail),
            "status": status_val,
            "capacity": getattr(r, "capacity", 2),
            "bed_type": getattr(r, "bed_type", ""),
        })
    return jsonify({
        "success": True,
        "rooms": res,
        "count": len(res)
    })


@booking_bp.route('/api/rooms/<hotel_id>/<room_number>', methods=['GET'])
def get_room_detail_api(hotel_id, room_number):
    """
    API trả về thông tin chi tiết của một phòng, bao gồm tiện ích khách sạn,
    tiện nghi phòng và thông tin khách đang lưu trú (nếu có).
    Dùng để hiển thị popup chi tiết phòng nhanh ngay trên giao diện đặt phòng.
    """
    if not hotel_id or not room_number:
        return jsonify({"success": False, "error": "Thiếu mã khách sạn hoặc số phòng"}), 400

    room = room_service.get_room(hotel_id, room_number)
    if not room:
        return jsonify({"success": False, "error": "Không tìm thấy phòng"}), 404

    # Khách sạn
    hotel = hotel_service.get_hotel_by_id(hotel_id)
    hotel_name = getattr(hotel, 'name', None) or (hotel.get('name') if isinstance(hotel, dict) else hotel_id)
    hotel_address = getattr(hotel, 'address', '') or (hotel.get('address', '') if isinstance(hotel, dict) else '')
    hotel_city = getattr(hotel, 'city', '') or (hotel.get('city', '') if isinstance(hotel, dict) else '')
    hotel_phone = getattr(hotel, 'phone', '') or (hotel.get('phone', '') if isinstance(hotel, dict) else '')
    raw_amenities = getattr(hotel, 'amenities', None) or (hotel.get('amenities') if isinstance(hotel, dict) else [])
    hotel_amenities = list(raw_amenities) if raw_amenities else []

    status_val = getattr(room, 'status', None)
    is_avail = getattr(room, 'is_available', True)
    if not status_val:
        status_val = "AVAILABLE" if is_avail else "OCCUPIED"

    price_val = getattr(room, 'price_per_night', 0)
    try:
        price_float = float(price_val)
    except Exception:
        price_float = 0.0

    description = getattr(room, 'description', '') or ''
    room_type = getattr(room, 'room_type', 'Tiêu chuẩn') or ''

    # Tiện nghi trong phòng nhận diện từ mô tả & loại phòng
    desc_lower = f"{description} {room_type}".lower()
    room_features = []
    if 'ban công' in desc_lower:
        room_features.append('Ban công ngắm cảnh')
    if 'bồn tắm' in desc_lower or 'jacuzzi' in desc_lower:
        room_features.append('Bồn tắm nằm cao cấp')
    if 'biển' in desc_lower:
        room_features.append('Hướng biển / View biển')
    if 'bếp' in desc_lower:
        room_features.append('Bếp nhỏ / Kitchenette')
    if 'panorama' in desc_lower:
        room_features.append('Cửa sổ Panorama')
    if 'king' in desc_lower:
        room_features.append('Giường King-size cao cấp')
    elif 'twin' in desc_lower:
        room_features.append('2 Giường Twin đơn')
    elif 'single' in desc_lower:
        room_features.append('Giường Single êm ái')

    # Bổ sung các tiện nghi tiêu chuẩn
    standard_features = ['Điều hòa 2 chiều', 'Wifi tốc độ cao', 'Smart TV LED', 'Két sắt an toàn', 'Máy sấy tóc & Vệ sinh cá nhân']
    for sf in standard_features:
        if sf not in room_features:
            room_features.append(sf)

    # Active booking nếu phòng đang có khách thuê
    active_b = None
    if status_val == 'OCCUPIED' or not is_avail:
        try:
            active_b = booking_service.get_active_booking_for_room(hotel_id, room_number)
            if active_b and isinstance(active_b, dict):
                for k in ('check_in_date', 'check_out_date'):
                    if k in active_b and active_b[k]:
                        active_b[k] = str(active_b[k])
        except Exception as e:
            print(f"⚠️ [Lỗi lấy thông tin khách thuê phòng]: {e}")

    return jsonify({
        "success": True,
        "room": {
            "hotel_id": str(hotel_id),
            "hotel_name": hotel_name,
            "hotel_address": hotel_address,
            "hotel_city": hotel_city,
            "hotel_phone": hotel_phone,
            "room_number": str(getattr(room, 'room_number', room_number)),
            "room_type": room_type,
            "price_per_night": price_float,
            "formatted_price": f"{price_float:,.0f} đ",
            "capacity": getattr(room, 'capacity', 2),
            "bed_type": getattr(room, 'bed_type', 'King'),
            "status": status_val,
            "is_available": is_avail,
            "description": description or f"Phòng {room_type} sang trọng, đầy đủ tiện nghi cao cấp tiêu chuẩn Mường Thanh.",
            "hotel_amenities": hotel_amenities,
            "room_features": room_features,
            "active_booking": active_b
        }
    })


# --------------------------------------------------------------------
# ROUTE ĐẶT PHÒNG (Gồm BATCH INSERT Q5 & BỘ LỌC Q2, Q3)
# --------------------------------------------------------------------

@booking_bp.route('/bookings', methods=['GET'])
def list_bookings():
    """
    Quản lý đặt phòng & Khám phá phòng trống:
    - Tab 1: Khám phá & Đặt phòng trống (lọc theo Chi nhánh, Loại phòng, Loại giường, Sức chứa, Tiện nghi, Khoảng giá)
    - Tab 2: Danh sách đơn đặt phòng đã tạo
    - Bố cục mở rộng thoáng đãng, hỗ trợ nút Đặt phòng ngay trên từng phòng trống
    """
    tab = request.args.get('tab', '').strip()
    guest_id = request.args.get('guest_id', '').strip()
    hotel_id = request.args.get('hotel_id', '').strip()
    check_in_date = request.args.get('check_in_date', '').strip()
    check_out_date = request.args.get('check_out_date', '').strip()
    room_type = request.args.get('room_type', '').strip()
    bed_type = request.args.get('bed_type', '').strip()
    capacity = request.args.get('capacity', '').strip()
    amenity = request.args.get('amenity', '').strip()
    price_range = request.args.get('price_range', '').strip()
    room_status = request.args.get('room_status', 'AVAILABLE').strip()
    q = request.args.get('q', '').strip()

    hotels, guests = _get_form_context()
    hotel_map = {
        (getattr(h, 'hotel_id', None) or (h.get('hotel_id') if isinstance(h, dict) else '')):
        (getattr(h, 'name', None) or (h.get('name') if isinstance(h, dict) else ''))
        for h in hotels
    }

    if not tab:
        if guest_id or (q and not hotel_id and not room_type and not bed_type and not amenity):
            tab = 'orders'
        else:
            tab = 'rooms'

    hotel_amenities_map = {}
    for h in hotels:
        h_id = getattr(h, 'hotel_id', None) or (h.get('hotel_id') if isinstance(h, dict) else '')
        h_ams = getattr(h, 'amenities', None) or (h.get('amenities') if isinstance(h, dict) else set())
        hotel_amenities_map[h_id] = set(h_ams or [])

    # Lấy các tag tiện ích thực tế, ngắn gọn từ các chi nhánh khách sạn
    hotel_tags = [
        'Hồ bơi',
        'Phòng Gym',
        'Spa & Sauna',
        'Bãi đỗ xe',
        'Phòng họp hội thảo',
        'Executive Lounge',
        'Sân Tennis',
        'Karaoke & Bar',
        'Khu vui chơi trẻ em'
    ]

    room_features = [
        ('ban công', 'Ban công ngắm cảnh'),
        ('bồn tắm', 'Bồn tắm nằm / Jacuzzi'),
        ('biển', 'Hướng biển / View biển'),
        ('bếp', 'Bếp nhỏ / Kitchenette'),
        ('panorama', 'Kính Panorama trọn cảnh'),
    ]

    amenity_groups = [
        {
            'group': 'Tiện ích chi nhánh (từ Khách Sạn)',
            'options': [(t, t) for t in hotel_tags]
        },
        {
            'group': 'Tiện nghi trong phòng',
            'options': room_features
        }
    ]

    quick_amenities = [(t, t) for t in hotel_tags[:6]] + [('ban công', 'Ban công'), ('bồn tắm', 'Bồn tắm nằm'), ('biển', 'View biển')]

    # 1. Lọc danh sách phòng phục vụ tiếp tân tìm phòng cho khách (Room Discovery)
    raw_rooms = room_service.get_filtered_rooms(
        hotel_id=hotel_id,
        room_type=room_type,
        bed_type=bed_type,
        capacity=capacity,
        amenity=amenity,
        price_range=price_range,
        status=room_status,
        limit=120,
        hotel_amenities_map=hotel_amenities_map
    )
    filtered_rooms = []
    for r in raw_rooms:
        r_dict = SimpleNamespace(
            hotel_id=r.hotel_id,
            hotel_name=hotel_map.get(r.hotel_id, r.hotel_id),
            room_number=str(r.room_number),
            room_type=r.room_type or "Tiêu chuẩn",
            price_per_night=float(r.price_per_night or 0),
            is_available=r.is_available,
            status=r.status or ("AVAILABLE" if r.is_available else "OCCUPIED"),
            capacity=r.capacity or 2,
            bed_type=r.bed_type or "King",
            description=r.description or ""
        )
        filtered_rooms.append(r_dict)

    # 2. Lấy danh sách đơn đặt phòng đã tạo (Bookings / Orders)
    bookings = []
    search_type = None

    if guest_id and not hotel_id and not check_in_date and not q:
        bookings = booking_service.get_bookings_by_guest(guest_id)
        search_type = 'guest'
    elif hotel_id and check_in_date and not guest_id and not q and not room_type:
        bookings = booking_service.get_bookings_by_hotel_date(hotel_id, check_in_date)
        search_type = 'hotel_date'
    else:
        bookings = booking_service.get_all_bookings(
            hotel_id=hotel_id,
            guest_id=guest_id,
            check_in_date=check_in_date,
            q=q,
            limit=200
        )
        if guest_id or hotel_id or check_in_date or q:
            search_type = 'filter'

    is_filtered = bool(
        guest_id or hotel_id or check_in_date or q or 
        (room_type and room_type != 'ALL') or 
        (bed_type and bed_type != 'ALL') or 
        (capacity and capacity != 'ALL') or 
        (amenity and amenity != 'ALL') or 
        (price_range and price_range != 'ALL')
    )

    room_types = [
        'Deluxe King', 'Deluxe Twin', 'Executive Suite', 'Family Suite', 
        'Superior Single', 'Standard', 'Suite', 'Royal Presidential Suite'
    ]
    bed_types = ['King', 'Twin', 'Double', 'Single']
    capacities = [
        ('1', '1 người (Đơn)'),
        ('2', '2 người (Đôi)'),
        ('4', '4 người (Gia đình)')
    ]
    price_ranges = [
        ('under_1m', 'Dưới 1.000.000 đ'),
        ('1m_2m', 'Từ 1 - 2 triệu đ'),
        ('above_2m', 'Trên 2 triệu đ')
    ]

    return render_template(
        'bookings.html',
        tab=tab,
        filtered_rooms=filtered_rooms,
        room_types=room_types,
        bed_types=bed_types,
        capacities=capacities,
        price_ranges=price_ranges,
        amenity_groups=amenity_groups,
        quick_amenities=quick_amenities,
        room_type=room_type,
        bed_type=bed_type,
        capacity=capacity,
        amenity=amenity,
        price_range=price_range,
        room_status=room_status,
        bookings=bookings,
        hotels=hotels,
        guests=guests,
        search_type=search_type,
        guest_id=guest_id,
        hotel_id=hotel_id,
        check_in_date=check_in_date,
        check_out_date=check_out_date,
        q=q,
        is_filtered=is_filtered,
        active_tab='bookings'
    )


@booking_bp.route('/bookings/create', methods=['POST'])
def create_booking():
    """
    [QUÂN - TASK QLKS-08 & QLKS-11]
    Route xử lý tạo Đặt phòng dùng BATCH INSERT Q5:
    - Hỗ trợ chọn khách hàng có sẵn HOẶC tự động tạo hồ sơ khách hàng mới (AstraDB)
    - Kiểm tra khách sạn, phòng, khách hàng tồn tại hợp lệ
    - Kiểm tra ràng buộc ngày Check-out > Check-in
    - CHẶN đặt phòng nếu phòng đang BẢO TRÌ (MAINTENANCE) hoặc ĐÃ CHO THUÊ (OCCUPIED)
    - Tự động tính tiền theo số đêm và giá phòng
    - Ghi đồng thời vào bookings_by_guest và bookings_by_hotel_date (BATCH Q5)
    - TỰ ĐỘNG CHUYỂN TRẠNG THÁI PHÒNG SANG 'OCCUPIED' (is_available = False)
    - Tự động tạo hóa đơn trong invoices_by_booking
    """
    guest_id = request.form.get('guest_id', '').strip()
    guest_name = request.form.get('guest_name', '').strip()
    guest_phone = request.form.get('guest_phone', '').strip()
    guest_id_card = request.form.get('guest_id_card', '').strip()
    guest_email = request.form.get('guest_email', '').strip()
    hotel_id = request.form.get('hotel_id', '').strip()
    room_number = request.form.get('room_number', '').strip()
    check_in_date = request.form.get('check_in_date', '').strip()
    check_out_date = request.form.get('check_out_date', '').strip()
    total_amount = request.form.get('total_amount', '').strip()
    status = request.form.get('status', 'CONFIRMED').strip()
    payment_method = request.form.get('payment_method', 'TIỀN MẶT').strip()

    # XỬ LÝ KHÁCH HÀNG MỚI (TỰ ĐỘNG TẠO HỒ SƠ KHÁCH NẾU CHƯA CÓ TRÊN HỆ THỐNG)
    new_guest_created = False
    if (not guest_id or guest_id == 'NEW') and guest_name:
        try:
            all_guests = hotel_service.get_all_guests() or []
            matched_guest = None
            for g in all_guests:
                g_phone = getattr(g, 'phone', '') or (g.get('phone') if isinstance(g, dict) else '')
                g_id_card = getattr(g, 'id_card', '') or (g.get('id_card') if isinstance(g, dict) else '')
                g_name = getattr(g, 'full_name', '') or (g.get('full_name') if isinstance(g, dict) else '')
                if guest_phone and g_phone == guest_phone:
                    matched_guest = g
                    break
                if guest_id_card and g_id_card == guest_id_card:
                    matched_guest = g
                    break
                if not guest_phone and not guest_id_card and g_name.strip().lower() == guest_name.lower():
                    matched_guest = g
                    break

            if matched_guest:
                guest_id = getattr(matched_guest, 'guest_id', '') or matched_guest.get('guest_id')
                if not guest_name:
                    guest_name = getattr(matched_guest, 'full_name', '') or matched_guest.get('full_name')
            else:
                guest_id = f"G{uuid4().hex[:8].upper()}"
                hotel_service.create_guest(
                    guest_id=guest_id,
                    full_name=guest_name,
                    email=guest_email,
                    phone=guest_phone,
                    id_card=guest_id_card,
                    address=""
                )
                new_guest_created = True
        except Exception as g_err:
            print(f"⚠️ Lỗi tự động tạo hồ sơ khách: {g_err}")
            if not guest_id or guest_id == 'NEW':
                guest_id = f"G{uuid4().hex[:8].upper()}"

    # 1. Kiểm tra trường bắt buộc
    if not guest_id or not hotel_id or not room_number or not check_in_date or not check_out_date:
        flash("Vui lòng chọn hoặc nhập đầy đủ thông tin khách hàng và các trường bắt buộc!", "error")
        return redirect(url_for('booking.list_bookings'))

    # 2. Tự động tìm tên khách hàng nếu chưa có
    if not guest_name and guest_id:
        try:
            for g in hotel_service.get_all_guests():
                g_id = g.guest_id if hasattr(g, 'guest_id') else g.get('guest_id')
                if g_id == guest_id:
                    guest_name = g.full_name if hasattr(g, 'full_name') else g.get('full_name', '')
                    break
        except Exception:
            pass

    # 3. Kiểm tra ngày Check-in và Check-out
    try:
        in_date = datetime.strptime(check_in_date, "%Y-%m-%d").date()
        out_date = datetime.strptime(check_out_date, "%Y-%m-%d").date()
    except ValueError:
        flash("Định dạng ngày nhận/trả phòng không hợp lệ (YYYY-MM-DD)!", "error")
        return redirect(url_for('booking.list_bookings'))

    if out_date <= in_date:
        flash("Ngày trả phòng (Check-out) phải sau ngày nhận phòng (Check-in) ít nhất 1 đêm!", "error")
        return redirect(url_for('booking.list_bookings'))

    nights = (out_date - in_date).days

    # 4. Kiểm tra phòng tồn tại và TRẠNG THÁI PHÒNG
    room = room_service.get_room(hotel_id, room_number)
    if not room:
        flash(f"Phòng số {room_number} không tồn tại tại khách sạn này!", "error")
        return redirect(url_for('booking.list_bookings'))

    room_status = getattr(room, 'status', 'AVAILABLE')
    room_available = getattr(room, 'is_available', True)

    # CHẶN ĐẶT PHÒNG KHI ĐANG BẢO TRÌ HOẶC ĐÃ CHO THUÊ
    if room_status == 'MAINTENANCE':
        flash(f"Phòng {room_number} hiện đang ở trạng thái ĐANG BẢO TRÌ! Hệ thống không cho phép đặt phòng bảo trì.", "error")
        return redirect(url_for('booking.list_bookings'))

    if room_status == 'OCCUPIED' or not room_available:
        flash(f"Phòng {room_number} hiện ĐÃ CÓ KHÁCH THUÊ (OCCUPIED)! Vui lòng chọn phòng khác.", "error")
        return redirect(url_for('booking.list_bookings'))

    # 5. Tính toán / Kiểm tra số tiền
    price = getattr(room, 'price_per_night', Decimal("0"))
    calculated_amount = Decimal(str(price)) * nights
    try:
        amt = Decimal(str(total_amount)) if total_amount else calculated_amount
        if amt <= 0:
            amt = calculated_amount
    except Exception:
        amt = calculated_amount

    if amt <= 0:
        amt = calculated_amount if calculated_amount > 0 else Decimal("1000000")

    # 6. Chuẩn hóa trạng thái đặt phòng và hình thức thanh toán (Đủ 100%, Đặt cọc một phần, Chưa thanh toán)
    valid_statuses = {'CONFIRMED', 'CHECKED_IN', 'PENDING'}
    if status not in valid_statuses:
        status = 'CONFIRMED'

    payment_type = request.form.get('payment_type', 'FULL').strip().upper()
    deposit_amount_raw = request.form.get('deposit_amount', '').strip()

    if payment_type == 'DEPOSIT':
        try:
            deposit_amt = Decimal(deposit_amount_raw) if deposit_amount_raw else (amt / Decimal("2"))
        except Exception:
            deposit_amt = amt / Decimal("2")

        if deposit_amt >= amt:
            deposit_amt = amt
            rem_amt = Decimal("0")
            payment_status = "PAID"
        elif deposit_amt <= 0:
            deposit_amt = Decimal("0")
            rem_amt = amt
            payment_status = "UNPAID"
        else:
            rem_amt = max(Decimal("0"), amt - deposit_amt)
            payment_status = "PARTIAL"
    elif payment_type == 'LATER':
        deposit_amt = Decimal("0")
        rem_amt = amt
        payment_status = "UNPAID"
    else:  # 'FULL': Thanh toán đủ 100%
        deposit_amt = amt
        rem_amt = Decimal("0")
        payment_status = "PAID"

    try:
        # 7. BATCH INSERT ghi đồng thời vào cả 2 bảng (Query Q5)
        booking_id = booking_service.create_booking_batch(
            guest_id=guest_id,
            guest_name=guest_name,
            hotel_id=hotel_id,
            room_number=room_number,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            status=status,
            total_amount=amt
        )

        # 8. Tự động tạo hóa đơn tương ứng cho booking (Query Q4) kèm thông tin cọc
        booking_service.create_invoice(
            booking_id=booking_id,
            guest_name=guest_name,
            hotel_id=hotel_id,
            issue_date=check_in_date,
            payment_method=payment_method,
            payment_status=payment_status,
            total_amount=amt,
            deposit_amount=deposit_amt,
            remaining_amount=rem_amt
        )

        # 9. TỰ ĐỘNG CHUYỂN TRẠNG THÁI PHÒNG SANG "OCCUPIED" (ĐÃ ĐẶT / ĐANG CHO THUÊ)
        # Truyền kèm guest_name/booking_id theo đúng seam mà room_service chừa sẵn cho
        # module Đặt phòng: trang chi tiết phòng đọc 2 cột này để hiện "ai đang thuê",
        # và change_room_status() tự xóa chúng về NULL khi lễ tân bấm "Trả phòng".
        try:
            status_res = room_service.change_room_status(
                hotel_id, room_number, 'OCCUPIED',
                guest_name=guest_name, booking_id=booking_id
            )
            if isinstance(status_res, tuple) and not status_res[0]:
                print(f"⚠️ Cảnh báo chuyển trạng thái phòng: {status_res[1]}")
            else:
                # Danh sách phòng có cache in-memory 30s -> phải hủy ngay, nếu không
                # phòng vừa đặt vẫn hiện "Đang trống" và có thể bị đặt trùng.
                room_service.invalidate_rooms_cache()
        except Exception as st_err:
            print(f"⚠️ Không thể cập nhật trạng thái phòng: {st_err}")

        success_msg = f"Đặt phòng thành công (BATCH Q5)! Mã Booking: {booking_id}."
        if new_guest_created:
            success_msg += f" Đã tự động tạo hồ sơ khách hàng mới [{guest_name}] (Mã: {guest_id})."
        success_msg += f" Phòng {room_number} đã chuyển sang trạng thái ĐÃ ĐẶT (OCCUPIED)."
        flash(success_msg, "success")
        return redirect(url_for('booking.view_invoice', booking_id=booking_id))
    except Exception as e:
        flash(f"Lỗi khi đặt phòng: {str(e)}", "error")
        return redirect(url_for('booking.list_bookings'))


# --------------------------------------------------------------------
# ROUTE TRA CỨU THEO KHÁCH HÀNG (QUERY Q2)
# --------------------------------------------------------------------

@booking_bp.route('/bookings/guest/<guest_id>', methods=['GET'])
def history_by_guest(guest_id):
    """
    [QUÂN - TASK QLKS-09 & QLKS-11] - Query Q2 trong PDF:
    Xem toàn bộ lịch sử đặt phòng của một khách hàng.
    """
    hotels, guests = _get_form_context()
    bookings = booking_service.get_bookings_by_guest(guest_id)
    return render_template(
        'bookings.html',
        bookings=bookings,
        hotels=hotels,
        guests=guests,
        search_type='guest',
        guest_id=guest_id,
        active_tab='bookings'
    )


# --------------------------------------------------------------------
# ROUTE TRA CỨU THEO KHÁCH SẠN VÀ NGÀY (QUERY Q3)
# --------------------------------------------------------------------

@booking_bp.route('/bookings/hotel-date', methods=['GET'])
def search_by_hotel_date():
    """
    [QUÂN - TASK QLKS-09 & QLKS-11] - Query Q3 trong PDF:
    Xem danh sách đặt phòng theo Khách sạn và Ngày Check-in.
    """
    hotel_id = request.args.get('hotel_id', '').strip()
    check_in_date = request.args.get('check_in_date', '').strip()
    hotels, guests = _get_form_context()
    bookings = booking_service.get_bookings_by_hotel_date(hotel_id, check_in_date) if (hotel_id and check_in_date) else []
    return render_template(
        'bookings.html',
        bookings=bookings,
        hotels=hotels,
        guests=guests,
        search_type='hotel_date',
        hotel_id=hotel_id,
        check_in_date=check_in_date,
        active_tab='bookings'
    )


# --------------------------------------------------------------------
# ROUTE HÓA ĐƠN (QUERY Q4)
# --------------------------------------------------------------------

@booking_bp.route('/invoices', methods=['GET'])
def list_invoices():
    """
    [QUÂN - TASK QLKS-10 & QLKS-11]
    Hiển thị danh sách toàn bộ hóa đơn trong hệ thống:
    - Bảng danh sách kèm tên người đặt, ngày nhận phòng (check-in) và ngày trả phòng (check-out)
    - Bộ lọc tìm kiếm nhanh theo từ khóa (khách, mã HĐ, mã booking, phòng)
    - Lọc theo trạng thái thanh toán (PAID / UNPAID) và chi nhánh
    - Hỗ trợ click xem phiếu hóa đơn chi tiết dạng Modal hoặc chuyển trang
    """
    query_str = request.args.get('q', '').strip().lower()
    status_filter = request.args.get('status', '').strip().upper()
    hotel_filter = request.args.get('hotel_id', '').strip()

    all_invoices = booking_service.get_all_invoices() or []
    hotels, _ = _get_form_context()

    filtered = []
    for inv in all_invoices:
        # Lọc theo trạng thái
        if status_filter and status_filter != 'ALL':
            if inv.get('payment_status', '').upper() != status_filter:
                continue
        # Lọc theo khách sạn
        if hotel_filter and hotel_filter != 'ALL':
            if inv.get('hotel_id', '') != hotel_filter:
                continue
        # Lọc theo từ khóa (search)
        if query_str:
            target = f"{inv.get('invoice_id', '')} {inv.get('booking_id', '')} {inv.get('guest_name', '')} {inv.get('room_number', '')} {inv.get('hotel_name', '')}".lower()
            if query_str not in target:
                continue
        filtered.append(inv)

    return render_template(
        'invoices.html',
        invoices=filtered,
        total_invoices_count=len(all_invoices),
        hotels=hotels,
        q=query_str,
        status_filter=status_filter,
        hotel_filter=hotel_filter,
        view_mode='list',
        active_tab='invoices'
    )


@booking_bp.route('/invoices/<booking_id>', methods=['GET'])
def view_invoice(booking_id):
    """
    [QUÂN - TASK QLKS-10 & QLKS-11] - Query Q4 trong PDF:
    Hiển thị chi tiết phiếu hóa đơn thanh toán cho mã đặt phòng.
    """
    invoice = booking_service.get_invoice_detail_enriched(booking_id) or booking_service.get_invoice_by_booking(booking_id)
    return render_template(
        'invoices.html',
        invoice=invoice,
        booking_id=booking_id,
        view_mode='detail',
        active_tab='invoices'
    )


@booking_bp.route('/api/invoices/<booking_id>', methods=['GET'])
def get_invoice_api(booking_id):
    """API JSON trả về chi tiết hóa đơn phục vụ hiển thị Modal tức thì ở Client."""
    if not booking_id:
        return jsonify({"success": False, "message": "Thiếu mã đặt phòng"}), 400
    inv = booking_service.get_invoice_detail_enriched(booking_id)
    if not inv:
        return jsonify({"success": False, "message": "Không tìm thấy hóa đơn"}), 404

    res = dict(inv)
    if res.get("check_in_date"):
        res["check_in_date"] = str(res["check_in_date"])
    if res.get("check_out_date"):
        res["check_out_date"] = str(res["check_out_date"])
    if res.get("issue_date"):
        res["issue_date"] = str(res["issue_date"])

    return jsonify({"success": True, "invoice": res})


@booking_bp.route('/invoices/create', methods=['POST'])
def create_invoice_route():
    """
    [QUÂN - TASK QLKS-10 & QLKS-11]
    Tạo bổ sung hóa đơn cho một mã đặt phòng chưa có hóa đơn.
    """
    booking_id = request.form.get('booking_id', '').strip()
    guest_name = request.form.get('guest_name', '').strip()
    hotel_id = request.form.get('hotel_id', '').strip()
    payment_method = request.form.get('payment_method', 'TIỀN MẶT').strip()
    payment_status = request.form.get('payment_status', 'PAID').strip()
    total_amount = request.form.get('total_amount', 0)

    if not booking_id:
        flash("Mã đặt phòng không hợp lệ!", "error")
        return redirect(url_for('booking.list_bookings'))

    # Kiểm tra chặn tạo trùng hóa đơn cho cùng 1 booking
    existing_inv = booking_service.get_invoice_by_booking(booking_id)
    if existing_inv:
        flash(f"Mã đặt phòng '{booking_id}' đã có hóa đơn thanh toán rồi! Hệ thống không cho phép tạo hóa đơn trùng.", "warning")
        return redirect(url_for('booking.view_invoice', booking_id=booking_id))

    try:
        inv_id = booking_service.create_invoice(
            booking_id=booking_id,
            guest_name=guest_name,
            hotel_id=hotel_id,
            payment_method=payment_method,
            payment_status=payment_status,
            total_amount=total_amount
        )
        if inv_id:
            flash(f"Đã tạo hóa đơn {inv_id} thành công cho mã đặt phòng {booking_id}!", "success")
        else:
            flash(f"Không thể tạo hóa đơn cho booking {booking_id}", "error")
    except Exception as e:
        flash(f"Lỗi khi tạo hóa đơn: {str(e)}", "error")

    return redirect(url_for('booking.view_invoice', booking_id=booking_id))


@booking_bp.route('/api/invoices/<booking_id>/settle', methods=['POST'])
def settle_invoice_api(booking_id):
    """
    [QUÂN - TÍNH NĂNG ĐẶT CỌC & THU TIỀN CÒN LẠI]
    API xác nhận thu nốt số tiền còn lại cho hóa đơn đặt cọc.
    Hỗ trợ AJAX gọi từ Modal hiển thị tức thì không cần reload toàn bộ trang.
    """
    if not booking_id:
        return jsonify({"success": False, "message": "Thiếu mã đặt phòng"}), 400

    payment_method = request.form.get('payment_method')
    amount_paid = request.form.get('amount_paid')

    if not payment_method and request.is_json:
        req_json = request.get_json(silent=True) or {}
        payment_method = req_json.get('payment_method')
        amount_paid = req_json.get('amount_paid')

    success, data = booking_service.settle_invoice_payment(
        booking_id=booking_id,
        amount_paid=amount_paid,
        payment_method=payment_method
    )

    if success:
        return jsonify({
            "success": True,
            "message": "Đã xác nhận thu tiền thành công! Hóa đơn đã được thanh toán đủ 100%.",
            "invoice": data
        })
    else:
        return jsonify({"success": False, "message": str(data)}), 400


@booking_bp.route('/invoices/<booking_id>/settle', methods=['POST'])
def settle_invoice_form(booking_id):
    """
    [QUÂN - TÍNH NĂNG ĐẶT CỌC & THU TIỀN CÒN LẠI]
    Form POST xác nhận thu nốt số tiền còn lại (hỗ trợ trang chi tiết và fallback an toàn).
    """
    if not booking_id:
        flash("Mã đặt phòng không hợp lệ!", "error")
        return redirect(url_for('booking.list_invoices'))

    payment_method = request.form.get('payment_method', 'TIỀN MẶT')
    amount_paid = request.form.get('amount_paid')

    success, data = booking_service.settle_invoice_payment(
        booking_id=booking_id,
        amount_paid=amount_paid,
        payment_method=payment_method
    )

    if success:
        flash(f"Đã xác nhận thu nốt tiền cho mã đặt phòng '{booking_id}' thành công! Trạng thái hóa đơn: ĐÃ THANH TOÁN (100%).", "success")
    else:
        flash(f"Lỗi khi thu tiền: {data}", "error")

    redirect_target = request.form.get('redirect_to', 'detail')
    if redirect_target == 'list':
        return redirect(url_for('booking.list_invoices'))
    return redirect(url_for('booking.view_invoice', booking_id=booking_id))



# --------------------------------------------------------------------
# ROUTE TRẢ PHÒNG (ĐÓNG BOOKING + GIẢI PHÓNG PHÒNG)
# --------------------------------------------------------------------

@booking_bp.route('/bookings/<booking_id>/checkout', methods=['POST'])
def checkout_booking(booking_id):
    """
    [QUÂN] Trả phòng: đóng booking (status -> COMPLETED) RỒI giải phóng phòng.

    Đây là điểm duy nhất làm đúng cả 2 việc. Nút "Trả phòng" bên trang chi tiết
    phòng chỉ gọi change_room_status() nên chỉ giải phóng phòng, booking vẫn đứng
    ở 'CONFIRMED' — dùng route này thì 2 module không lệch nhau nữa.

    Thứ tự có chủ ý: đóng booking TRƯỚC, giải phóng phòng SAU. Nếu đảo lại mà bước
    đóng booking lỗi thì phòng đã trống trong khi booking vẫn "đang ở" — đúng cái
    trạng thái lệch đang muốn tránh. Lỗi ở bước sau (phòng) thì còn sửa tay được
    trên trang chi tiết phòng.
    """
    guest_id = (request.form.get('guest_id') or '').strip()
    hotel_id = (request.form.get('hotel_id') or '').strip()
    room_number = (request.form.get('room_number') or '').strip()
    check_in_date = (request.form.get('check_in_date') or '').strip()
    planned_check_out = (request.form.get('check_out_date') or '').strip()
    actual_check_out = (request.form.get('actual_check_out') or '').strip() or None

    # Thiếu thông tin thì tự tra lại từ phòng đang được thuê.
    if (not guest_id or not check_in_date) and hotel_id and room_number:
        active = booking_service.get_active_booking_for_room(hotel_id, room_number) or {}
        guest_id = guest_id or str(active.get('guest_id') or '')
        check_in_date = check_in_date or str(active.get('check_in_date') or '')
        planned_check_out = planned_check_out or str(active.get('check_out_date') or '')

    if not guest_id or not check_in_date:
        flash('Không xác định được khách hoặc ngày nhận phòng của đơn này, chưa thể trả phòng.', 'error')
        return redirect(url_for('booking.list_bookings'))

    ok, result = booking_service.complete_booking(
        guest_id=guest_id,
        booking_id=booking_id,
        hotel_id=hotel_id,
        check_in_date=check_in_date,
        actual_check_out=actual_check_out,
        planned_check_out=planned_check_out or None,
    )

    if not ok:
        flash(f'Không thể trả phòng: {result}', 'error')
        return redirect(url_for('booking.list_bookings'))

    message = f"Đã trả phòng cho đơn {booking_id}."

    # Trả sớm chỉ là thông tin ghi nhận. Chính sách đã chốt: KHÔNG giảm, KHÔNG hoàn —
    # hóa đơn giữ nguyên số tiền của trọn kỳ đã đặt.
    if result.get('is_early_checkout'):
        message += (
            f" Khách trả sớm: ở {result['nights_stayed']} đêm trên"
            f" {result['nights_billed']} đêm đã đặt. Theo chính sách, hóa đơn giữ nguyên,"
            " không giảm và không hoàn tiền."
        )

    # Giải phóng phòng qua đúng seam mà room_service để sẵn; change_room_status()
    # tự xóa current_guest_name/current_booking_id về NULL khi chuyển AVAILABLE.
    if hotel_id and room_number:
        try:
            status_ok, status_err = room_service.change_room_status(hotel_id, room_number, 'AVAILABLE')
            if status_ok:
                room_service.invalidate_rooms_cache()
                message += f" Phòng {room_number} đã về trạng thái Đang trống."
            else:
                flash(
                    f"Đã đóng đơn {booking_id} nhưng chưa giải phóng được phòng {room_number}"
                    f" ({status_err}). Vào trang chi tiết phòng đổi trạng thái tay giúp.",
                    'error'
                )
        except Exception as room_err:
            print(f"⚠️ [Trả phòng] Không đổi được trạng thái phòng: {room_err}")

    flash(message, 'success')

    if (request.form.get('redirect_to') or '') == 'invoice':
        return redirect(url_for('booking.view_invoice', booking_id=booking_id))
    return redirect(url_for('booking.list_bookings'))
