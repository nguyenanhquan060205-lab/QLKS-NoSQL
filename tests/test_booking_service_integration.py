import os
import unittest
from datetime import datetime
from dotenv import load_dotenv

from database.db import get_session
from services import booking_service

load_dotenv()


class BookingServiceAstraIntegrationTest(unittest.TestCase):
    """Kiểm tra tích hợp thực tế QLKS-08 (BATCH) và QLKS-09 (Query Q2, Q3) trên AstraDB."""

    @classmethod
    def setUpClass(cls):
        token = os.getenv("ASTRA_DB_TOKEN")
        bundle_path = os.getenv("ASTRA_DB_SECURE_BUNDLE_PATH")

        if not token or not bundle_path:
            raise unittest.SkipTest("Chưa cấu hình ASTRA_DB_TOKEN hoặc ASTRA_DB_SECURE_BUNDLE_PATH trong .env")
        if not os.path.isfile(bundle_path):
            raise unittest.SkipTest("Không tìm thấy file Secure Connect Bundle theo đường dẫn trong .env")

        cls.session = get_session()
        if cls.session is None:
            raise unittest.SkipTest("Không thể kết nối Cassandra/AstraDB")

    def test_batch_insert_and_query_q2_q3(self):
        """
        AC Test:
        1. Gọi create_booking_batch ghi đồng thời vào 2 bảng.
        2. Query Q2: get_bookings_by_guest tìm đúng bản ghi theo guest_id.
        3. Query Q3: get_bookings_by_hotel_date tìm đúng bản ghi theo hotel_id và check_in_date.
        """
        test_suffix = datetime.now().strftime("%m%d%H%M%S")
        guest_id = f"G_INT_{test_suffix}"
        hotel_id = f"H_INT_{test_suffix}"
        room_number = "999"
        check_in = "2026-09-20"
        check_out = "2026-09-23"
        guest_name = "Nguyễn Văn Test"

        # 1. Thực hiện BATCH INSERT Q5
        booking_id = booking_service.create_booking_batch(
            guest_id=guest_id,
            guest_name=guest_name,
            hotel_id=hotel_id,
            room_number=room_number,
            check_in_date=check_in,
            check_out_date=check_out,
            status="CONFIRMED",
            total_amount=3500000,
        )
        self.assertIsNotNone(booking_id, "Lỗi BATCH INSERT không sinh được mã booking_id")

        # 2. Kiểm tra Query Q2 (bookings_by_guest)
        guest_bookings = booking_service.get_bookings_by_guest(guest_id)
        self.assertGreaterEqual(len(guest_bookings), 1, "Query Q2 không tìm thấy bản ghi theo guest_id")
        found_in_q2 = any(
            (b["booking_id"] if isinstance(b, dict) else getattr(b, "booking_id", None)) == booking_id
            for b in guest_bookings
        )
        self.assertTrue(found_in_q2, f"Mã booking {booking_id} không xuất hiện trong bảng bookings_by_guest")

        # 3. Kiểm tra Query Q3 (bookings_by_hotel_date)
        hotel_date_bookings = booking_service.get_bookings_by_hotel_date(hotel_id, check_in)
        self.assertGreaterEqual(len(hotel_date_bookings), 1, "Query Q3 không tìm thấy bản ghi theo hotel_id và check_in_date")
        found_in_q3 = any(
            (b["booking_id"] if isinstance(b, dict) else getattr(b, "booking_id", None)) == booking_id
            for b in hotel_date_bookings
        )
        self.assertTrue(found_in_q3, f"Mã booking {booking_id} không xuất hiện trong bảng bookings_by_hotel_date")

        print(f"🎉 TÍCH HỢP ASTRADB THÀNH CÔNG: Booking {booking_id} đã được lưu và đọc chính xác từ cả 2 bảng (Q2 & Q3)!")


if __name__ == "__main__":
    unittest.main()
