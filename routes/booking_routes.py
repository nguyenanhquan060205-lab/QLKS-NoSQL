# ====================================================================
# ROUTES: ĐẶT PHÒNG & HÓA ĐƠN
# PHỤ TRÁCH: QUÂN
# ====================================================================

from flask import Blueprint, render_template, request, redirect, url_for, flash
from services import booking_service

booking_bp = Blueprint('booking', __name__)

# --------------------------------------------------------------------
# ROUTE ĐẶT PHÒNG (Gồm BATCH INSERT Q5)
# --------------------------------------------------------------------

@booking_bp.route('/bookings', methods=['GET'])
def list_bookings():
    """
    TODO (Quân):
    1. Hiển thị danh sách hoặc bộ lọc tìm kiếm đặt phòng
    2. Render template bookings.html
    """
    return render_template('bookings.html', bookings=[])


@booking_bp.route('/bookings/create', methods=['POST'])
def create_booking():
    """
    [QUÂN - TASK QLKS-08] - Route xử lý tạo Đặt phòng dùng BATCH INSERT Q5
    """
    guest_id = request.form.get('guest_id')
    guest_name = request.form.get('guest_name')
    hotel_id = request.form.get('hotel_id')
    room_number = request.form.get('room_number')
    check_in_date = request.form.get('check_in_date')
    check_out_date = request.form.get('check_out_date')
    total_amount = request.form.get('total_amount', 0)
    status = request.form.get('status', 'CONFIRMED')

    try:
        booking_id = booking_service.create_booking_batch(
            guest_id=guest_id,
            guest_name=guest_name,
            hotel_id=hotel_id,
            room_number=room_number,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            status=status,
            total_amount=total_amount
        )
        flash(f"Đặt phòng thành công (BATCH INSERT)! Mã Booking: {booking_id}", "success")
    except Exception as e:
        flash(f"Lỗi khi đặt phòng: {str(e)}", "error")

    return redirect(url_for('booking.list_bookings'))


# --------------------------------------------------------------------
# ROUTE TRA CỨU THEO KHÁCH HÀNG (QUERY Q2)
# --------------------------------------------------------------------

@booking_bp.route('/bookings/guest/<guest_id>', methods=['GET'])
def history_by_guest(guest_id):
    """
    TODO (Quân) - Query Q2 trong PDF:
    1. Gọi booking_service.get_bookings_by_guest(guest_id)
    2. Render kết quả tra cứu lịch sử của khách hàng
    """
    bookings = booking_service.get_bookings_by_guest(guest_id)
    return render_template('bookings.html', bookings=bookings, search_type='guest', guest_id=guest_id)


# --------------------------------------------------------------------
# ROUTE TRA CỨU THEO KHÁCH SẠN VÀ NGÀY (QUERY Q3)
# --------------------------------------------------------------------

@booking_bp.route('/bookings/hotel-date', methods=['GET'])
def search_by_hotel_date():
    """
    TODO (Quân) - Query Q3 trong PDF:
    1. Lấy hotel_id và check_in_date từ request.args
    2. Gọi booking_service.get_bookings_by_hotel_date(hotel_id, check_in_date)
    3. Render kết quả danh sách đặt phòng theo ngày
    """
    hotel_id = request.args.get('hotel_id')
    check_in_date = request.args.get('check_in_date')
    bookings = booking_service.get_bookings_by_hotel_date(hotel_id, check_in_date) if (hotel_id and check_in_date) else []
    return render_template('bookings.html', bookings=bookings, search_type='hotel_date')


# --------------------------------------------------------------------
# ROUTE HÓA ĐƠN (QUERY Q4)
# --------------------------------------------------------------------

@booking_bp.route('/invoices/<booking_id>', methods=['GET'])
def view_invoice(booking_id):
    """
    TODO (Quân) - Query Q4 trong PDF:
    1. Gọi booking_service.get_invoice_by_booking(booking_id)
    2. Render template invoices.html hiển thị hóa đơn thanh toán
    """
    invoice = booking_service.get_invoice_by_booking(booking_id)
    return render_template('invoices.html', invoice=invoice, booking_id=booking_id)
