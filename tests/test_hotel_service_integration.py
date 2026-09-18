import os
import unittest

from dotenv import load_dotenv

from database.db import get_session
from services import hotel_service


load_dotenv()


class HotelServiceAstraIntegrationTest(unittest.TestCase):
    """Kiểm tra AC QLKS-04 trực tiếp trên Cassandra/Astra DB."""

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

        cls.session = get_session()
        if cls.session is None:
            raise RuntimeError("Không thể kết nối Cassandra/Astra DB")

    def test_create_and_get_hotel(self):
        hotel_id = "H_QLKS04_TEST"

        created = hotel_service.create_hotel(
            hotel_id,
            "QLKS-04 Integration Test Hotel",
            "0900000000",
            "QLKS-04 Test Address",
            "Da Nang",
            "Vietnam",
            {"Wifi", "Parking"},
        )

        self.assertTrue(created, "Không insert được dữ liệu vào bảng hotels")
        hotel_ids = {hotel.hotel_id for hotel in hotel_service.get_all_hotels()}
        self.assertIn(
            hotel_id,
            hotel_ids,
            "Không đọc lại được khách sạn vừa insert từ bảng hotels",
        )

    def test_create_and_get_guest(self):
        guest_id = "G_QLKS04_TEST"

        created = hotel_service.create_guest(
            guest_id,
            "QLKS-04 Integration Test Guest",
            "qlks04-test@example.com",
            "0911111111",
            "QLKS04TEST",
        )

        self.assertTrue(created, "Không insert được dữ liệu vào bảng guests")
        guest_ids = {guest.guest_id for guest in hotel_service.get_all_guests()}
        self.assertIn(
            guest_id,
            guest_ids,
            "Không đọc lại được khách hàng vừa insert từ bảng guests",
        )

    @classmethod
    def tearDownClass(cls):
        try:
            hotel_service.delete_hotel("H_QLKS04_TEST")
            hotel_service.delete_guest("G_QLKS04_TEST")
        except Exception:
            pass


if __name__ == "__main__":
    unittest.main()
