# ====================================================================
# ENTRYPOINT CHÍNH CỦA ỨNG DỤNG FLASK
# QUẢN LÝ VÀ ĐĂNG KÝ BLUEPRINT CHO 3 THÀNH VIÊN
# ====================================================================

import os
from flask import Flask
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "qlks-secret-key-2026")

# 1. Đăng ký Blueprint của ĐỊNH (Khách sạn, Phòng, Khách hàng)
from routes.hotel_routes import hotel_bp
app.register_blueprint(hotel_bp)

# 2. Đăng ký Blueprint của QUÂN (Đặt phòng, Hóa đơn)
from routes.booking_routes import booking_bp
app.register_blueprint(booking_bp)

# 3. Đăng ký Blueprint của NHƯ (Trang chủ, Thống kê Dashboard)
from routes.dashboard_routes import dashboard_bp
app.register_blueprint(dashboard_bp)

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    print("=" * 55)
    print("  🏨 HỆ THỐNG QUẢN LÝ KHÁCH SẠN - CASSANDRA / ASTRADB")
    print(f"  🚀 Server đang chạy tại: http://127.0.0.1:{port}")
    print("=" * 55)
    app.run(host='0.0.0.0', port=port, debug=True)
