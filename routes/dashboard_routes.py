# ====================================================================
# ROUTES: TRANG CHỦ & DASHBOARD THỐNG KÊ
# PHỤ TRÁCH: NHƯ
# ====================================================================

from flask import Blueprint, render_template, request
from services import dashboard_service

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/', methods=['GET'])
def index():
    """
    Trang chủ giới thiệu hệ thống + dải số liệu nhanh (lấy chung từ dashboard_service).
    """
    stats = dashboard_service.get_dashboard_stats()
    return render_template('index.html', stats=stats)


@dashboard_bp.route('/dashboard', methods=['GET'])
def dashboard():
    """
    Đọc bộ lọc (khách sạn, kỳ báo cáo, khoảng ngày tùy chọn) từ query string
    và truyền xuống dashboard_service để tính báo cáo tương ứng.
    """
    hotel_id = request.args.get('hotel_id') or None
    period = request.args.get('period') or 'all'
    start_date = request.args.get('start_date') or None
    end_date = request.args.get('end_date') or None

    stats = dashboard_service.get_dashboard_report(
        hotel_id=hotel_id,
        period=period,
        custom_start=start_date,
        custom_end=end_date,
    )
    return render_template(
        'dashboard.html',
        stats=stats,
        period_options=dashboard_service.PERIOD_OPTIONS,
    )