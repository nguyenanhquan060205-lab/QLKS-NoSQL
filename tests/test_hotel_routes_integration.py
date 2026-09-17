import os
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from dotenv import load_dotenv
from flask import Flask

from database.db import get_session
from routes.booking_routes import booking_bp
from routes.hotel_routes import hotel_bp
from services import hotel_service


load_dotenv()


class HotelRoutesAstraIntegrationTest(unittest.TestCase):
    """Kiểm tra AC QLKS-06 qua HTTP route và Astra DB thật."""

    @classmethod
    def setUpClass(cls):
        token = os.getenv("ASTRA_DB_TOKEN")
        bundle_path = os.getenv("ASTRA_DB_SECURE_BUNDLE_PATH")

        if not token or not bundle_path:
            raise unittest.SkipTest(
                "Chưa cấu hình ASTRA_DB_TOKEN hoặc "
                "ASTRA_DB_SECURE_BUNDLE_PATH trong .env"
            )
        if not os.path.isfile(bundle_path):
            raise unittest.SkipTest(
                "Không tìm thấy Secure Connect Bundle theo đường dẫn trong .env"
            )
        if get_session() is None:
            raise RuntimeError("Không thể kết nối Cassandra/Astra DB")

        app = Flask(__name__, template_folder="../templates")
        app.config.update(TESTING=True, SECRET_KEY="integration-test-secret")
        app.register_blueprint(hotel_bp)
        app.register_blueprint(booking_bp)
        cls.client = app.test_client()

    def setUp(self):
        # Dọn dẹp dữ liệu test cũ nếu còn lưu trong Astra DB
        hotel_service.delete_hotel("H06060606")
        hotel_service.delete_guest("G07070707")
        for h in hotel_service.get_all_hotels():
            if (h.name or "").strip().lower() == "qlks-06 web test hotel":
                hotel_service.delete_hotel(h.hotel_id)
        for g in hotel_service.get_all_guests():
            if (g.email or "").strip().lower() == "qlks06-web-test@example.com" or (g.id_card or "").strip().upper() == "079201009999":
                hotel_service.delete_guest(g.guest_id)

    def tearDown(self):
        hotel_service.delete_hotel("H06060606")
        hotel_service.delete_guest("G07070707")

    def test_user_adds_hotel_directly_from_web(self):
        fixed_uuid = SimpleNamespace(hex="06060606abcdef1234567890abcdef12")

        with patch("routes.hotel_routes.uuid4", return_value=fixed_uuid):
            response = self.client.post(
                "/hotels/add",
                data={
                    "name": "QLKS-06 Web Test Hotel",
                    "phone": "0906060606",
                    "address": "06 Test Street",
                    "city": "Da Nang",
                    "country": "Vietnam",
                    "amenities": "Wifi, Parking",
                },
                follow_redirects=True,
            )

        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Đã thêm khách sạn", body)
        self.assertIn("QLKS-06 Web Test Hotel", body)
        self.assertIn(
            "H06060606",
            {hotel.hotel_id for hotel in hotel_service.get_all_hotels()},
        )

    def test_user_adds_guest_directly_from_web(self):
        fixed_uuid = SimpleNamespace(hex="07070707abcdef1234567890abcdef12")

        with patch("routes.hotel_routes.uuid4", return_value=fixed_uuid):
            response = self.client.post(
                "/guests/add",
                data={
                    "full_name": "QLKS-06 Web Test Guest",
                    "email": "qlks06-web-test@example.com",
                    "phone": "0907070707",
                    "id_card": "079201009999",
                },
                follow_redirects=True,
            )

        body = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Đã thêm khách hàng", body)
        self.assertIn("QLKS-06 Web Test Guest", body)
        self.assertIn(
            "G07070707",
            {guest.guest_id for guest in hotel_service.get_all_guests()},
        )


if __name__ == "__main__":
    unittest.main()
