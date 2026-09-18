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

        # Giả lập kết quả trả về cho query Q4 (invoices_by_booking)
        if "invoices_by_booking" in query_str and "SELECT" in query_str:
            return [{
                "booking_id": parameters[0],
                "invoice_id": "INV_TEST_01",
                "guest_name": "Nguyễn Văn An",
                "hotel_id": "H001",
                "issue_date": date(2026, 9, 16),
                "payment_method": "CASH",
                "payment_status": "PAID",
                "total_amount": 5000000
            }]

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

    def test_complete_booking_updates_both_tables_with_batch(self):
        """Trả phòng phải đồng bộ status COMPLETED sang cả 2 bảng denormalize."""
        ok, result = booking_service.complete_booking(
            guest_id="G001",
            booking_id="BK_CO_UT_01",
            hotel_id="H001",
            check_in_date="2026-09-15",
            actual_check_out="2026-09-18",
            planned_check_out="2026-09-18",
        )

        self.assertTrue(ok)
        self.assertEqual(result["status"], "COMPLETED")
        self.assertFalse(result["is_early_checkout"])

        prepared_texts = [call[1] for call in self.session.calls if call[0] == "prepare"]
        guest_updates = [q for q in prepared_texts if "UPDATE bookings_by_guest" in q]
        hotel_updates = [q for q in prepared_texts if "UPDATE bookings_by_hotel_date" in q]
        self.assertEqual(len(guest_updates), 1)
        self.assertEqual(len(hotel_updates), 1)
        # bookings_by_hotel_date không có cột check_out_date -> chỉ được set status
        self.assertNotIn("check_out_date", hotel_updates[0])

    def test_complete_booking_early_checkout_records_actual_date(self):
        """Trả sớm: check_out_date phải là ngày trả THỰC TẾ, không phải ngày dự kiến."""
        ok, result = booking_service.complete_booking(
            guest_id="G001",
            booking_id="BK_CO_UT_02",
            hotel_id="H001",
            check_in_date="2026-09-15",
            actual_check_out="2026-09-16",   # khách đi sớm 2 ngày
            planned_check_out="2026-09-18",
        )

        self.assertTrue(ok)
        self.assertTrue(result["is_early_checkout"])
        self.assertEqual(result["check_out_date"], "2026-09-16")
        self.assertEqual(result["nights_stayed"], 1)
        self.assertEqual(result["nights_billed"], 3)

    def test_complete_booking_late_checkout_keeps_planned_date(self):
        """Ở quá hạn là nghiệp vụ phụ phí khác -> giữ nguyên ngày dự kiến, không ghi đè."""
        ok, result = booking_service.complete_booking(
            guest_id="G001",
            booking_id="BK_CO_UT_03",
            hotel_id="H001",
            check_in_date="2026-09-15",
            actual_check_out="2026-09-20",
            planned_check_out="2026-09-18",
        )

        self.assertTrue(ok)
        self.assertFalse(result["is_early_checkout"])
        self.assertEqual(result["check_out_date"], "2026-09-18")

    def test_complete_booking_requires_identity(self):
        """Thiếu guest_id thì phải từ chối, vì khóa chính là (guest_id, booking_id)."""
        ok, reason = booking_service.complete_booking(
            guest_id="",
            booking_id="BK_CO_UT_04",
            hotel_id="H001",
            check_in_date="2026-09-15",
        )
        self.assertFalse(ok)
        self.assertIn("guest_id", reason)

    def test_get_bookings_by_guest_q2_uses_partition_key(self):
        """Kiểm tra QLKS-09: Query Q2 tra cứu theo Partition Key guest_id."""
        results = booking_service.get_bookings_by_guest("G001")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["guest_id"], "G001")
        self.assertEqual(results[0]["booking_id"], "BK_TEST_01")
        prepared_queries = [call[1] for call in self.session.calls if call[0] == "prepare"]
        self.assertTrue(any("WHERE guest_id = ?" in q for q in prepared_queries))

    def test_get_bookings_by_guest_q2_returns_template_ready_dict(self):
        """
        Q2 phải trả dict có đủ field mà bookings.html cần. Trước đây nó trả
        cassandra Row thô: Row không có .get() và bảng bookings_by_guest không có
        cột guest_name, nên trang lịch sử của MỌI khách có đơn đều 500.
        """
        results = booking_service.get_bookings_by_guest("G001")

        self.assertIsInstance(results[0], dict)
        for field in ("guest_name", "hotel_name", "room_number", "nights",
                      "status", "total_amount", "check_in_date", "check_out_date"):
            self.assertIn(field, results[0])
        # Không có hồ sơ khách thì fallback về mã khách, không để trống
        self.assertEqual(results[0]["guest_name"], "G001")
        self.assertEqual(results[0]["status"], "CONFIRMED")
        self.assertEqual(results[0]["total_amount"], 0.0)

    def test_q2_enrichment_reads_by_primary_key_not_full_scan(self):
        """
        Việc bù tên khách/tên khách sạn phải đọc theo khóa chính, không được
        'SELECT ... FROM guests' cả bảng — nếu không thì Q2 mất đúng cái tính chất
        chỉ đụng 1 partition mà QLKS-09 đang chứng minh.
        """
        booking_service.get_bookings_by_guest("G001")
        prepared = [call[1] for call in self.session.calls if call[0] == "prepare"]

        guest_queries = [q for q in prepared if "FROM guests" in q]
        hotel_queries = [q for q in prepared if "FROM hotels" in q]
        for q in guest_queries:
            self.assertIn("WHERE guest_id = ?", q)
        for q in hotel_queries:
            self.assertIn("WHERE hotel_id = ?", q)

    def test_get_bookings_by_hotel_date_q3_uses_composite_partition_key(self):
        """Kiểm tra QLKS-09: Query Q3 tra cứu theo Composite Partition Key (hotel_id, check_in_date)."""
        results = booking_service.get_bookings_by_hotel_date("H001", "2026-09-15")

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["hotel_id"], "H001")
        self.assertEqual(results[0]["booking_id"], "BK_TEST_02")
        self.assertEqual(results[0]["check_in_date"], date(2026, 9, 15))
        prepared_queries = [call[1] for call in self.session.calls if call[0] == "prepare"]
        self.assertTrue(any("WHERE hotel_id = ? AND check_in_date = ?" in q for q in prepared_queries))

    def test_get_bookings_empty_input_returns_empty_list(self):
        """Kiểm tra tham số đầu vào rỗng thì trả về mảng rỗng [] không báo lỗi."""
        self.assertEqual(booking_service.get_bookings_by_guest(""), [])
        self.assertEqual(booking_service.get_bookings_by_guest(None), [])
        self.assertEqual(booking_service.get_bookings_by_hotel_date("", "2026-09-15"), [])
        self.assertEqual(booking_service.get_bookings_by_hotel_date("H001", ""), [])
        self.assertEqual(booking_service.get_bookings_by_hotel_date("H001", "sai-dinh-dang-ngay"), [])

    def test_create_invoice_q4_executes_prepared_statement(self):
        """Kiểm tra QLKS-10: create_invoice gọi chuẩn bị và thực thi prepared statement với kiểu dữ liệu chuẩn."""
        invoice_id = booking_service.create_invoice(
            booking_id="BK_INV_01",
            invoice_id="INV_UNITTEST_01",
            guest_name="Nguyễn Văn An",
            hotel_id="H001",
            issue_date="2026-09-16",
            payment_method="CASH",
            payment_status="PAID",
            total_amount=5000000,
        )

        self.assertEqual(invoice_id, "INV_UNITTEST_01")
        prepared_queries = [call[1] for call in self.session.calls if call[0] == "prepare"]
        self.assertTrue(any("INSERT INTO invoices_by_booking" in q for q in prepared_queries))

        # Kiểm tra tham số truyền vào execute
        execute_calls = [call for call in self.session.calls if call[0] == "execute"]
        self.assertTrue(any(
            call[2] and call[2][0] == "BK_INV_01" and call[2][1] == "INV_UNITTEST_01"
            for call in execute_calls
        ))

    def test_create_invoice_auto_generates_id(self):
        """Kiểm tra QLKS-10: Tự sinh mã invoice_id dạng INV... nếu không truyền vào."""
        invoice_id = booking_service.create_invoice(
            booking_id="BK_INV_AUTO",
            guest_name="Trần Thị Mai",
            hotel_id="H002",
            total_amount=2000000,
        )
        self.assertIsNotNone(invoice_id)
        self.assertTrue(invoice_id.startswith("INV"))

    def test_get_invoice_by_booking_q4_uses_partition_key(self):
        """Kiểm tra QLKS-10: Query Q4 tra cứu hóa đơn theo Partition Key booking_id."""
        invoice = booking_service.get_invoice_by_booking("BK_INV_01")

        self.assertIsNotNone(invoice)
        self.assertEqual(invoice.get("invoice_id"), "INV_TEST_01")
        self.assertEqual(invoice.get("booking_id"), "BK_INV_01")

        prepared_queries = [call[1] for call in self.session.calls if call[0] == "prepare"]
        self.assertTrue(any("WHERE booking_id = ?" in q for q in prepared_queries))

    def test_invoice_empty_input_returns_none(self):
        """Kiểm tra tham số booking_id rỗng thì trả về None."""
        self.assertIsNone(booking_service.create_invoice(booking_id=""))
        self.assertIsNone(booking_service.create_invoice(booking_id=None))
        self.assertIsNone(booking_service.get_invoice_by_booking(""))
        self.assertIsNone(booking_service.get_invoice_by_booking(None))

    def test_exception_handling_returns_safe_fallbacks(self):
        """Kiểm tra khi xảy ra lỗi Cassandra cluster vẫn bắt ngoại lệ an toàn."""
        with patch.object(booking_service, "get_session", return_value=FailingSession()):
            self.assertEqual(booking_service.get_bookings_by_guest("G001"), [])
            self.assertEqual(booking_service.get_bookings_by_hotel_date("H001", "2026-09-15"), [])
            self.assertIsNone(booking_service.create_invoice(booking_id="BK_ERR"))
            self.assertIsNone(booking_service.get_invoice_by_booking("BK_ERR"))

    def test_invoice_mock_fallback_when_session_none(self):
        """Kiểm tra khi không có kết nối AstraDB (session=None), hệ thống fallback lưu và đọc từ mock store."""
        with patch.object(booking_service, "get_session", return_value=None):
            test_booking_id = "BK_MOCK_99"
            created_id = booking_service.create_invoice(
                booking_id=test_booking_id,
                invoice_id="INV_MOCK_99",
                guest_name="Khách Giả Lập",
                total_amount=1500000,
            )
            self.assertEqual(created_id, "INV_MOCK_99")

            fetched = booking_service.get_invoice_by_booking(test_booking_id)
            self.assertIsNotNone(fetched)
            self.assertEqual(fetched["invoice_id"], "INV_MOCK_99")
            self.assertEqual(fetched["guest_name"], "Khách Giả Lập")

    def test_get_all_invoices_mock_mode(self):
        """Kiểm tra get_all_invoices trong chế độ mock trả về danh sách hóa đơn kèm ngày check-in/out."""
        with patch.object(booking_service, "get_session", return_value=None):
            booking_service.invalidate_invoice_cache()
            booking_service.create_invoice(
                booking_id="BK_MOCK_LIST",
                invoice_id="INV_MOCK_LIST",
                guest_name="Nguyễn Văn An",
                total_amount=3000000
            )
            invoices = booking_service.get_all_invoices(use_cache=False)
            self.assertIsInstance(invoices, list)
            match = [i for i in invoices if i.get("invoice_id") == "INV_MOCK_LIST"]
            self.assertTrue(len(match) > 0)
            self.assertEqual(match[0]["guest_name"], "Nguyễn Văn An")
            self.assertEqual(match[0]["total_amount"], 3000000.0)

    def test_get_invoice_detail_enriched(self):
        """Kiểm tra get_invoice_detail_enriched trả về dict đầy đủ thông tin."""
        with patch.object(booking_service, "get_session", return_value=None):
            booking_service.create_invoice(
                booking_id="BK_ENRICHED",
                invoice_id="INV_ENRICHED",
                guest_name="Trần Văn Bình",
                total_amount=2100000
            )
            detail = booking_service.get_invoice_detail_enriched("BK_ENRICHED")
            self.assertIsNotNone(detail)
            self.assertEqual(detail["invoice_id"], "INV_ENRICHED")
            self.assertEqual(detail["guest_name"], "Trần Văn Bình")
            self.assertEqual(detail["total_amount"], 2100000.0)

    def test_create_invoice_with_partial_deposit(self):
        """Kiểm tra tạo hóa đơn đặt cọc trước: trạng thái PARTIAL, tiền cọc và tiền còn lại chuẩn xác."""
        with patch.object(booking_service, "get_session", return_value=None):
            booking_service.invalidate_invoice_cache()
            inv_id = booking_service.create_invoice(
                booking_id="BK_DEPOSIT_TEST_01",
                invoice_id="INV_DEP_01",
                guest_name="Lê Hoàng Cọc",
                total_amount=2000000,
                deposit_amount=600000,
                remaining_amount=1400000,
                payment_status="PARTIAL"
            )
            self.assertEqual(inv_id, "INV_DEP_01")

            fetched = booking_service.get_invoice_by_booking("BK_DEPOSIT_TEST_01")
            self.assertIsNotNone(fetched)
            self.assertEqual(fetched["payment_status"], "PARTIAL")
            self.assertEqual(float(fetched["deposit_amount"]), 600000.0)
            self.assertEqual(float(fetched["remaining_amount"]), 1400000.0)

    def test_settle_invoice_payment_flow(self):
        """Kiểm tra quy trình lễ tân xác nhận thu nốt số tiền còn lại (chuyển từ PARTIAL sang PAID)."""
        with patch.object(booking_service, "get_session", return_value=None):
            booking_service.invalidate_invoice_cache()
            booking_service.create_invoice(
                booking_id="BK_SETTLE_TEST_01",
                invoice_id="INV_SETTLE_01",
                guest_name="Phạm Thu Nốt",
                total_amount=3000000,
                deposit_amount=1000000,
                payment_status="PARTIAL"
            )

            # Lễ tân xác nhận thu nốt
            success, res = booking_service.settle_invoice_payment(
                booking_id="BK_SETTLE_TEST_01",
                payment_method="CHUYỂN KHOẢN"
            )
            self.assertTrue(success)
            self.assertEqual(res["payment_status"], "PAID")
            self.assertEqual(res["deposit_amount"], 3000000.0)
            self.assertEqual(res["remaining_amount"], 0.0)
            self.assertEqual(res["payment_method"], "CHUYỂN KHOẢN")

            # Kiểm tra đọc lại hóa đơn sau khi thu nốt
            fetched = booking_service.get_invoice_by_booking("BK_SETTLE_TEST_01")
            self.assertEqual(fetched["payment_status"], "PAID")


if __name__ == "__main__":
    unittest.main()


