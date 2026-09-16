import unittest
from datetime import date
from unittest.mock import MagicMock, patch
from cassandra.query import PreparedStatement

from services import booking_service


class FakeSession:
    def __init__(self):
        self.calls = []
        self.prepared_queries = {}

    def prepare(self, query):
        self.calls.append(("prepare", query))
        mock_stmt = MagicMock(spec=PreparedStatement)
        self.prepared_queries[mock_stmt] = query
        return mock_stmt

    def execute(self, query_or_batch, parameters=None):
        self.calls.append(("execute", query_or_batch, parameters))

        # Nếu là BatchStatement
        if hasattr(query_or_batch, "_statements_and_parameters"):
            return []

        # Giả lập kết quả trả về cho query Q2 (bookings_by_guest)
        query_str = self.prepared_queries.get(query_or_batch, "")
        if "bookings_by_guest" in query_str:
            return [{"guest_id": parameters[0], "booking_id": "BK_TEST_01"}]

        # Giả lập kết quả trả về cho query Q3 (bookings_by_hotel_date)
        if "bookings_by_hotel_date" in query_str:
            return [{"hotel_id": parameters[0], "check_in_date": parameters[1], "booking_id": "BK_TEST_02"}]

        return []


class FailingSession(FakeSession):
    def prepare(self, query):
        raise RuntimeError("prepare query failed")

    def execute(self, query_or_batch, parameters=None):
        raise RuntimeError("execute query failed")


class BookingServiceTest(unittest.TestCase):
    def setUp(self):
        self.session = FakeSession()
        self.session_patcher = patch.object(
            booking_service,
            "get_session",
            return_value=self.session,
        )
        self.session_patcher.start()

    def tearDown(self):
        self.session_patcher.stop()

    def test_create_booking_batch_executes_batch_statement(self):
        """Kiểm tra QLKS-08: BATCH INSERT ghi đồng thời vào cả 2 bảng."""
        booking_id = booking_service.create_booking_batch(
            guest_id="G001",
            guest_name="Nguyễn Văn An",
            hotel_id="H001",
            room_number="101",
            check_in_date="2026-09-15",
            check_out_date="2026-09-18",
            status="CONFIRMED",
            total_amount=5000000,
            booking_id="BK_UNITTEST_01",
        )

        self.assertEqual(booking_id, "BK_UNITTEST_01")
        # Kiểm tra session.prepare được gọi cho cả 2 bảng
        prepared_texts = [call[1] for call in self.session.calls if call[0] == "prepare"]
        self.assertTrue(any("bookings_by_guest" in q for q in prepared_texts))
        self.assertTrue(any("bookings_by_hotel_date" in q for q in prepared_texts))

        # Kiểm tra execute được gọi với đối tượng BatchStatement
        execute_calls = [call for call in self.session.calls if call[0] == "execute"]
        self.assertGreaterEqual(len(execute_calls), 1)

    def test_get_bookings_by_guest_q2_uses_partition_key(self):
        """Kiểm tra QLKS-09: Query Q2 tra cứu theo Partition Key guest_id."""
        results = booking_service.get_bookings_by_guest("G001")

        self.assertEqual(results, [{"guest_id": "G001", "booking_id": "BK_TEST_01"}])
        prepared_queries = [call[1] for call in self.session.calls if call[0] == "prepare"]
        self.assertTrue(any("WHERE guest_id = ?" in q for q in prepared_queries))

    def test_get_bookings_by_hotel_date_q3_uses_composite_partition_key(self):
        """Kiểm tra QLKS-09: Query Q3 tra cứu theo Composite Partition Key (hotel_id, check_in_date)."""
        results = booking_service.get_bookings_by_hotel_date("H001", "2026-09-15")

        self.assertEqual(
            results,
            [{"hotel_id": "H001", "check_in_date": date(2026, 9, 15), "booking_id": "BK_TEST_02"}]
        )
        prepared_queries = [call[1] for call in self.session.calls if call[0] == "prepare"]
        self.assertTrue(any("WHERE hotel_id = ? AND check_in_date = ?" in q for q in prepared_queries))

    def test_get_bookings_empty_input_returns_empty_list(self):
        """Kiểm tra tham số đầu vào rỗng thì trả về mảng rỗng [] không báo lỗi."""
        self.assertEqual(booking_service.get_bookings_by_guest(""), [])
        self.assertEqual(booking_service.get_bookings_by_guest(None), [])
        self.assertEqual(booking_service.get_bookings_by_hotel_date("", "2026-09-15"), [])
        self.assertEqual(booking_service.get_bookings_by_hotel_date("H001", ""), [])
        self.assertEqual(booking_service.get_bookings_by_hotel_date("H001", "sai-dinh-dang-ngay"), [])

    def test_exception_handling_returns_empty_list(self):
        """Kiểm tra khi xảy ra lỗi Cassandra cluster vẫn bắt ngoại lệ và trả về [] an toàn."""
        with patch.object(booking_service, "get_session", return_value=FailingSession()):
            self.assertEqual(booking_service.get_bookings_by_guest("G001"), [])
            self.assertEqual(booking_service.get_bookings_by_hotel_date("H001", "2026-09-15"), [])


if __name__ == "__main__":
    unittest.main()
