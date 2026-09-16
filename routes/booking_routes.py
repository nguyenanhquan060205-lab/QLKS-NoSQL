# ====================================================================
# ROUTES: ĐẶT PHÒNG & HÓA ĐƠN
# PHỤ TRÁCH: QUÂN
# ====================================================================

from flask import Blueprint, render_template, request, redirect, url_for, flash
from services import booking_service, hotel_service

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
# ROUTE ĐẶT PHÒNG (Gồm BATCH INSERT Q5 & BỘ LỌC Q2, Q3)
# --------------------------------------------------------------------

@booking_bp.route('/bookings', methods=['GET'])
def list_bookings():
    """
    [QUÂN - TASK QLKS-11]
    Hiển thị trang quản lý đặt phòng:
    - Form tạo đặt phòng mới (BATCH INSERT Q5)
    - Bộ lọc tra cứu theo Khách hàng (Q2) hoặc Khách sạn & Ngày (Q3)
    - Bảng danh sách kết quả kèm nút xem Hóa đơn (Q4)
    """
    guest_id = request.args.get('guest_id', '').strip()
    hotel_id = request.args.get('hotel_id', '').strip()
    check_in_date = request.args.get('check_in_date', '').strip()

    hotels, guests = _get_form_context()
    bookings = []
    search_type = None

    if guest_id:
        bookings = booking_service.get_bookings_by_guest(guest_id)
        search_type = 'guest'
    elif hotel_id and check_in_date:
        bookings = booking_service.get_bookings_by_hotel_date(hotel_id, check_in_date)
        search_type = 'hotel_date'

    return render_template(
        'bookings.html',
        bookings=bookings,
        hotels=hotels,
        guests=guests,
        search_type=search_type,
        guest_id=guest_id,
        hotel_id=hotel_id,
        check_in_date=check_in_date
    )


@booking_bp.route('/bookings/create', methods=['POST'])
def create_booking():
    """
    [QUÂN - TASK QLKS-08 & QLKS-11]
    Route xử lý tạo Đặt phòng dùng BATCH INSERT Q5:
    - Ghi đồng thời vào bookings_by_guest và bookings_by_hotel_date
    - Tự động tạo bản ghi Hóa đơn trong invoices_by_booking
    - Điều hướng người dùng trực tiếp đến trang Hóa đơn (hoàn tất luồng Đặt phòng ➡️ Xem HĐ)
    """
    guest_id = request.form.get('guest_id', '').strip()
    guest_name = request.form.get('guest_name', '').strip()
    hotel_id = request.form.get('hotel_id', '').strip()
    room_number = request.form.get('room_number', '').strip()
    check_in_date = request.form.get('check_in_date', '').strip()
    check_out_date = request.form.get('check_out_date', '').strip()
    total_amount = request.form.get('total_amount', 0)
    status = request.form.get('status', 'CONFIRMED').strip()
    payment_method = request.form.get('payment_method', 'TIỀN MẶT').strip()

    # Tự động điền guest_name nếu khách hàng chọn guest_id từ dropdown
    if not guest_name and guest_id:
        try:
            for g in hotel_service.get_all_guests():
                g_id = g.guest_id if hasattr(g, 'guest_id') else g.get('guest_id')
                if g_id == guest_id:
                    guest_name = g.full_name if hasattr(g, 'full_name') else g.get('full_name', '')
                    break
        except Exception:
            pass

    if not guest_id or not hotel_id or not room_number or not check_in_date or not check_out_date:
        flash("Vui lòng điền đầy đủ các trường thông tin bắt buộc!", "error")
        return redirect(url_for('booking.list_bookings'))

    try:
        # 1. BATCH INSERT ghi đồng thời vào cả 2 bảng (Query Q5)
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

        # 2. Tự động tạo hóa đơn tương ứng cho booking (Query Q4)
        booking_service.create_invoice(
            booking_id=booking_id,
            guest_name=guest_name,
            hotel_id=hotel_id,
            issue_date=check_in_date,
            payment_method=payment_method,
            payment_status="PAID" if status in ("CONFIRMED", "COMPLETED") else "UNPAID",
            total_amount=total_amount
        )

        flash(f"Đặt phòng thành công (BATCH Q5)! Mã Booking: {booking_id}. Hóa đơn đã được khởi tạo tự động.", "success")
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
        guest_id=guest_id
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
        check_in_date=check_in_date
    )


# --------------------------------------------------------------------
# ROUTE HÓA ĐƠN (QUERY Q4)
# --------------------------------------------------------------------

@booking_bp.route('/invoices/<booking_id>', methods=['GET'])
def view_invoice(booking_id):
    """
    [QUÂN - TASK QLKS-10 & QLKS-11] - Query Q4 trong PDF:
    Hiển thị chi tiết phiếu hóa đơn thanh toán cho mã đặt phòng.
    """
    invoice = booking_service.get_invoice_by_booking(booking_id)
    return render_template('invoices.html', invoice=invoice, booking_id=booking_id)


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

