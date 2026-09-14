# ====================================================================
# SERVICES: THỐNG KÊ & BÁO CÁO DASHBOARD
# PHỤ TRÁCH: NHƯ
# ====================================================================

from database.db import get_session

def get_dashboard_stats():
    """
    TODO (Như):
    - Tổng hợp số liệu thống kê để hiển thị trên trang Dashboard:
      + Tổng số khách sạn trong hệ thống
      + Tổng số phòng & số phòng đang trống (is_available = True)
      + Tổng số lượt đặt phòng
      + Ước tính tổng doanh thu
    - Trả về dictionary chứa các chỉ số thống kê.
    """
    session = get_session()
    if not session:
        return {
            "total_hotels": 0,
            "total_rooms": 0,
            "available_rooms": 0,
            "total_bookings": 0,
            "total_revenue": 0
        }

    # Viết code tổng hợp thống kê tại đây
    return {
        "total_hotels": 0,
        "total_rooms": 0,
        "available_rooms": 0,
        "total_bookings": 0,
        "total_revenue": 0
    }
