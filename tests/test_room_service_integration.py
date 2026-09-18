import os
import unittest

from dotenv import load_dotenv

from database.db import get_session
from services import hotel_service


load_dotenv()


class RoomServiceAstraIntegrationTest(unittest.TestCase):
    """Kiểm tra AC QLKS-05 trực tiếp trên Cassandra/Astra DB."""

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

    # Test này chạy trên AstraDB THẬT — cùng database mà dashboard đang thống kê.
    # Không dọn thì mấy phòng test nằm lại vĩnh viễn và bị đếm vào "tổng số phòng"
    # với "phòng đang thuê" trên báo cáo, làm số liệu lệch mà không ai lần ra.
    TEST_HOTELS = ("H_QLKS05_TEST_A", "H_QLKS05_TEST_B")

    @classmethod
    def tearDownClass(cls):
        session = getattr(cls, "session", None)
        if session is None:
            return
        for hotel_id in cls.TEST_HOTELS:
            try:
                session.execute(
                    "DELETE FROM rooms_by_hotel WHERE hotel_id = %s;", (hotel_id,)
                )
            except Exception as error:
                print(f"⚠️ Không dọn được phòng test của {hotel_id}: {error}")

    def test_create_and_get_rooms_from_only_requested_hotel_partition(self):
        hotel_a, hotel_b = self.TEST_HOTELS

        self.assertTrue(
            hotel_service.create_room(
                hotel_a, "A501", "Deluxe", "2500000", True
            )
        )
        self.assertTrue(
            hotel_service.create_room(
                hotel_a, "A502", "Standard", "1800000", False
            )
        )
        self.assertTrue(
            hotel_service.create_room(
                hotel_b, "B901", "Suite", "4200000", True
            )
        )

        rooms = hotel_service.get_rooms_by_hotel(hotel_a)
        room_numbers = {room.room_number for room in rooms}

        self.assertTrue(rooms, "Không đọc được phòng của khách sạn chỉ định")
        self.assertTrue(all(room.hotel_id == hotel_a for room in rooms))
        self.assertTrue({"A501", "A502"}.issubset(room_numbers))
        self.assertNotIn(
            "B901",
            room_numbers,
            "Kết quả chứa phòng thuộc partition của khách sạn khác",
        )


if __name__ == "__main__":
    unittest.main()
