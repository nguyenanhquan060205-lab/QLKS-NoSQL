# ====================================================================
# ROUTES: TRANG CHỦ & DASHBOARD THỐNG KÊ
# PHỤ TRÁCH: NHƯ
# ====================================================================

from flask import Blueprint, render_template
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
    TODO (Như):
    1. Gọi dashboard_service.get_dashboard_stats()
    2. Truyền các thông số thống kê sang dashboard.html để hiển thị biểu đồ/card
    """
    stats = dashboard_service.get_dashboard_stats()
    return render_template('dashboard.html', stats=stats)