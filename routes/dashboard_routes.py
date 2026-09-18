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
    Dashboard thống kê có lọc theo khách sạn và theo kỳ báo cáo.

    Form lọc trong dashboard.html submit bằng GET với 4 tham số: hotel_id, period,
    start_date, end_date — route đọc đúng 4 tham số đó rồi đẩy xuống service, nên
    chọn filter là số liệu đổi theo.

    period_options BẮT BUỘC phải truyền: dashboard.html có `{% for value, label in
    period_options %}`, mà Jinja2 không iterate được biến Undefined -> thiếu nó là
    trang trả 500 (UndefinedError) chứ không phải render ra dropdown rỗng.
    """
    stats = dashboard_service.get_dashboard_report(
        hotel_id=(request.args.get('hotel_id') or '').strip() or None,
        period=(request.args.get('period') or 'all').strip(),
        custom_start=request.args.get('start_date'),
        custom_end=request.args.get('end_date'),
    )

    # Khoảng ngày tùy chọn không hợp lệ thì service tự lùi về "toàn bộ thời gian" và
    # trả kèm lý do trong stats.custom_range_error. KHÔNG flash() nữa: dashboard.html
    # đã hiện lỗi đó ngay dưới khung filter — đúng chỗ người dùng đang nhìn — nên
    # flash thêm sẽ ra thông báo trùng 2 lần.
    return render_template(
        'dashboard.html',
        stats=stats,
        period_options=dashboard_service.PERIOD_OPTIONS,
    )