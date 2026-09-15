# ====================================================================
# SERVICES: THỐNG KÊ & BÁO CÁO DASHBOARD
# PHỤ TRÁCH: NHƯ
# ====================================================================

from database.db import get_session

_EMPTY_STATS = {
    "total_hotels": 0,
    "total_rooms": 0,
    "available_rooms": 0,
    "total_bookings": 0,
    "total_revenue": 0,
}


def get_dashboard_stats():
    """
    Tổng hợp số liệu thống kê cho trang Dashboard & Trang chủ:
      + Tổng số khách sạn (bảng hotels)
      + Tổng số phòng & số phòng đang trống (bảng rooms_by_hotel, is_available)
      + Tổng số lượt đặt phòng (bảng bookings_by_guest)
      + Tổng doanh thu (tổng total_amount trong bảng invoices_by_booking)

    Lưu ý: vì các bảng này khá nhỏ (dữ liệu demo), ta SELECT toàn bộ cột cần
    thiết rồi đếm/tính tổng ở phía Python, tránh phải dùng ALLOW FILTERING
    hay aggregate function của CQL (vốn không tối ưu và dễ lỗi khi bảng lớn).
    """
    session = get_session()
    if not session:
        return dict(_EMPTY_STATS)

    try:
        hotel_rows = list(session.execute("SELECT hotel_id FROM hotels;"))
        total_hotels = len(hotel_rows)

        room_rows = list(session.execute("SELECT is_available FROM rooms_by_hotel;"))
        total_rooms = len(room_rows)
        available_rooms = sum(1 for r in room_rows if r.is_available)

        booking_rows = list(session.execute("SELECT booking_id FROM bookings_by_guest;"))
        total_bookings = len(booking_rows)

        invoice_rows = list(session.execute("SELECT total_amount FROM invoices_by_booking;"))
        total_revenue = sum(
            float(r.total_amount) for r in invoice_rows if r.total_amount is not None
        )

        return {
            "total_hotels": total_hotels,
            "total_rooms": total_rooms,
            "available_rooms": available_rooms,
            "total_bookings": total_bookings,
            "total_revenue": total_revenue,
        }
    except Exception as e:
        print(f"❌ Lỗi khi lấy thống kê dashboard: {e}")
        return dict(_EMPTY_STATS)