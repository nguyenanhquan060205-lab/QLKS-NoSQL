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

    def test_create_and_get_invoice_q4(self):
        """
        QLKS-10 Integration Test:
        1. Gọi create_invoice(...) lưu bản ghi vào bảng invoices_by_booking trên AstraDB.
        2. Gọi get_invoice_by_booking(booking_id) kiểm tra truy vấn Query Q4 theo Partition Key.
        3. Assert kiểm tra tính toàn vẹn của các trường dữ liệu.
        """
        test_suffix = datetime.now().strftime("%m%d%H%M%S")
        booking_id = f"BK_INV_TEST_{test_suffix}"
        invoice_id = f"INV_INT_{test_suffix}"
        guest_name = "Trần Thị Test"
        hotel_id = "H001"
        issue_date = "2026-09-16"
        payment_method = "CREDIT_CARD"
        payment_status = "PAID"
        total_amount = 4200000

        # 1. Gọi create_invoice ghi vào AstraDB
        created_invoice_id = booking_service.create_invoice(
            booking_id=booking_id,
            invoice_id=invoice_id,
            guest_name=guest_name,
            hotel_id=hotel_id,
            issue_date=issue_date,
            payment_method=payment_method,
            payment_status=payment_status,
            total_amount=total_amount,
        )
        self.assertEqual(created_invoice_id, invoice_id, "create_invoice không trả về đúng invoice_id")

        # 2. Truy vấn Q4 bằng get_invoice_by_booking
        invoice = booking_service.get_invoice_by_booking(booking_id)
        self.assertIsNotNone(invoice, "Không tìm thấy hóa đơn theo booking_id trên AstraDB")

        # Hỗ trợ cả Row object lẫn dict
        get_val = lambda key: invoice[key] if isinstance(invoice, dict) else getattr(invoice, key, None)

        self.assertEqual(get_val("booking_id"), booking_id)
        self.assertEqual(get_val("invoice_id"), invoice_id)
        self.assertEqual(get_val("guest_name"), guest_name)
        self.assertEqual(get_val("hotel_id"), hotel_id)
        self.assertEqual(get_val("payment_method"), payment_method)
        self.assertEqual(get_val("payment_status"), payment_status)
        self.assertEqual(float(get_val("total_amount")), float(total_amount))

        print(f"🎉 TÍCH HỢP ASTRADB THÀNH CÔNG: Hóa đơn {invoice_id} cho Booking {booking_id} được lưu và đọc chính xác (Query Q4)!")


if __name__ == "__main__":
    unittest.main()
