import unittest
from types import SimpleNamespace
from unittest.mock import patch

from flask import Flask

from routes.booking_routes import booking_bp


class BookingRoutesTest(unittest.TestCase):
    def setUp(self):
        app = Flask(__name__, template_folder="../templates")
        app.config.update(TESTING=True, SECRET_KEY="test-secret")
        app.register_blueprint(booking_bp)
        self.client = app.test_client()

        # CHỐT AN TOÀN: route đặt phòng gọi room_service.change_room_status() để tự
        # chuyển phòng sang OCCUPIED. Hàm đó tự mở kết nối AstraDB, nên nếu không
        # chặn ở đây thì unit test GHI THẲNG VÀO DATABASE THẬT của nhóm.
        #
        # Đã xảy ra rồi: test_create_booking_success_redirects_to_invoice tạo ra
        # phòng rác H001/101 (OCCUPIED, "Nguyễn Văn An", BK_NEW_123) nằm lại trong
        # AstraDB và bị đếm vào "tổng số phòng" / "phòng đang thuê" trên dashboard.
        # Chạy 1 test đó cũng mất 16 giây vì phải bắt tay với Astra.
        #
        # Test nào cần assert lời gọi này thì tự khai @patch riêng, decorator sẽ
        # đè lên bản chặn ở đây.
        for target, result in (
            ("routes.booking_routes.room_service.change_room_status", (True, None)),
            ("routes.booking_routes.room_service.invalidate_rooms_cache", None),
        ):
            patcher = patch(target, return_value=result)
            patcher.start()
            self.addCleanup(patcher.stop)

    @patch("routes.booking_routes.hotel_service.get_all_hotels", return_value=[
        SimpleNamespace(hotel_id="H001", name="Vinpearl Nha Trang")
    ])
    @patch("routes.booking_routes.hotel_service.get_all_guests", return_value=[
        SimpleNamespace(guest_id="G001", full_name="Nguyễn Văn An")
    ])
    def test_list_bookings_renders_page(self, mock_guests, mock_hotels):
        response = self.client.get("/bookings")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Quản lý Đặt phòng & Hóa đơn", html)
        self.assertIn("Vinpearl Nha Trang", html)
        self.assertIn("Nguyễn Văn An", html)

    @patch("routes.booking_routes.hotel_service.get_all_hotels", return_value=[])
    @patch("routes.booking_routes.hotel_service.get_all_guests", return_value=[])
    @patch("routes.booking_routes.booking_service.get_bookings_by_guest")
    def test_list_bookings_with_guest_filter(self, mock_get_by_guest, mock_guests, mock_hotels):
        mock_get_by_guest.return_value = [{
            "booking_id": "BK_FILTER_01",
            "guest_id": "G001",
            "hotel_id": "H001",
            "room_number": "101",
            "check_in_date": "2026-09-20",
            "status": "CONFIRMED",
            "total_amount": 2500000
        }]
        response = self.client.get("/bookings?guest_id=G001")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("BK_FILTER_01", html)
        mock_get_by_guest.assert_called_once_with("G001")

    @patch("routes.booking_routes.hotel_service.get_all_hotels", return_value=[])
    @patch("routes.booking_routes.hotel_service.get_all_guests", return_value=[])
    @patch("routes.booking_routes.room_service.get_room")
    @patch("routes.booking_routes.booking_service.create_booking_batch", return_value="BK_NEW_123")
    @patch("routes.booking_routes.booking_service.create_invoice", return_value="INV_NEW_123")
    def test_create_booking_success_redirects_to_invoice(
        self, mock_create_inv, mock_create_batch, mock_get_room, mock_guests, mock_hotels
    ):
        mock_get_room.return_value = SimpleNamespace(
            hotel_id="H001",
            room_number="101",
            room_type="Deluxe Twin",
            price_per_night=1350000,
            is_available=True,
            status="AVAILABLE"
        )
        response = self.client.post(
            "/bookings/create",
            data={
                "guest_id": "G001",
                "guest_name": "Nguyễn Văn An",
                "hotel_id": "H001",
                "room_number": "101",
                "check_in_date": "2026-09-20",
                "check_out_date": "2026-09-23",
                "total_amount": "3500000",
                "payment_method": "TIỀN MẶT",
                "status": "CONFIRMED"
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/invoices/BK_NEW_123", response.headers["Location"])
        mock_create_batch.assert_called_once()
        mock_create_inv.assert_called_once()

    def test_create_booking_missing_fields_redirects_to_list(self):
        response = self.client.post(
            "/bookings/create",
            data={
                "guest_id": "",
                "hotel_id": "H001"
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/bookings", response.headers["Location"])

    @patch("routes.booking_routes.hotel_service.get_all_hotels", return_value=[])
    @patch("routes.booking_routes.hotel_service.get_all_guests", return_value=[])
    @patch("routes.booking_routes.booking_service.get_bookings_by_guest")
    def test_history_by_guest_route(self, mock_get_by_guest, mock_guests, mock_hotels):
        mock_get_by_guest.return_value = [{
            "booking_id": "BK_HIST_01",
            "guest_id": "G001",
            "hotel_id": "H001",
            "room_number": "202",
            "check_in_date": "2026-09-22",
            "status": "CONFIRMED",
            "total_amount": 1800000
        }]
        response = self.client.get("/bookings/guest/G001")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("BK_HIST_01", html)

    @patch("routes.booking_routes.hotel_service.get_all_hotels", return_value=[])
    @patch("routes.booking_routes.hotel_service.get_all_guests", return_value=[])
    @patch("routes.booking_routes.booking_service.get_bookings_by_hotel_date")
    def test_search_by_hotel_date_route(self, mock_get_by_hd, mock_guests, mock_hotels):
        mock_get_by_hd.return_value = [{
            "booking_id": "BK_DATE_01",
            "guest_id": "G002",
            "guest_name": "Trần Thị Mai",
            "hotel_id": "H001",
            "room_number": "303",
            "check_in_date": "2026-09-25",
            "status": "CONFIRMED"
        }]
        response = self.client.get("/bookings/hotel-date?hotel_id=H001&check_in_date=2026-09-25")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("BK_DATE_01", html)

    @patch("routes.booking_routes.booking_service.get_invoice_by_booking")
    def test_view_invoice_route_found(self, mock_get_inv):
        mock_get_inv.return_value = {
            "invoice_id": "INV_20260916001",
            "booking_id": "BK_INV_01",
            "guest_name": "Nguyễn Văn An",
            "hotel_id": "H001",
            "issue_date": "2026-09-16",
            "payment_method": "TIỀN MẶT",
            "payment_status": "PAID",
            "total_amount": 4500000
        }
        response = self.client.get("/invoices/BK_INV_01")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("INV_20260916001", html)
        self.assertIn("BK_INV_01", html)
        self.assertIn("Nguyễn Văn An", html)
        self.assertIn("Đã Thanh Toán", html)

    @patch("routes.booking_routes.booking_service.get_invoice_by_booking", return_value=None)
    def test_view_invoice_route_not_found_shows_form(self, mock_get_inv):
        response = self.client.get("/invoices/BK_NONEXIST")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Chưa có hóa đơn cho mã đặt phòng", html)
        self.assertIn("BK_NONEXIST", html)

    @patch("routes.booking_routes.booking_service.create_invoice", return_value="INV_MANUAL_01")
    def test_create_invoice_route_manual(self, mock_create_inv):
        response = self.client.post(
            "/invoices/create",
            data={
                "booking_id": "BK_MANUAL_01",
                "guest_name": "Lê Văn C",
                "hotel_id": "H002",
                "payment_method": "CHUYỂN KHOẢN",
                "payment_status": "PAID",
                "total_amount": "2800000"
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/invoices/BK_MANUAL_01", response.headers["Location"])

    @patch("routes.booking_routes.booking_service.get_invoice_by_booking")
    @patch("routes.booking_routes.booking_service.create_invoice")
    def test_create_invoice_duplicate_prevented(self, mock_create_inv, mock_get_inv):
        mock_get_inv.return_value = {
            "invoice_id": "INV_EXISTING_01",
            "booking_id": "BK_DUP_01"
        }
        response = self.client.post(
            "/invoices/create",
            data={
                "booking_id": "BK_DUP_01",
                "guest_name": "Lê Văn C",
                "hotel_id": "H002",
                "payment_method": "TIỀN MẶT",
                "payment_status": "PAID",
                "total_amount": "1500000"
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/invoices/BK_DUP_01", response.headers["Location"])
        mock_create_inv.assert_not_called()

    @patch("routes.booking_routes.room_service.get_rooms_by_hotel")
    def test_get_rooms_api_route(self, mock_get_rooms):
        mock_get_rooms.return_value = [
            SimpleNamespace(
                hotel_id="H001",
                room_number="101",
                room_type="Deluxe Twin",
                price_per_night=1350000,
                is_available=True,
                status="AVAILABLE"
            ),
            SimpleNamespace(
                hotel_id="H001",
                room_number="102",
                room_type="Deluxe King",
                price_per_night=1450000,
                is_available=False,
                status="MAINTENANCE"
            )
        ]
        response = self.client.get("/api/hotels/H001/rooms")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(len(data["rooms"]), 2)
        self.assertEqual(data["rooms"][0]["room_number"], "101")
        self.assertEqual(data["rooms"][1]["status"], "MAINTENANCE")

    @patch("routes.booking_routes.room_service.get_room")
    @patch("routes.booking_routes.booking_service.create_booking_batch")
    def test_create_booking_fails_when_room_in_maintenance(self, mock_create_batch, mock_get_room):
        mock_get_room.return_value = SimpleNamespace(
            hotel_id="H001",
            room_number="102",
            room_type="Deluxe King",
            price_per_night=1450000,
            is_available=False,
            status="MAINTENANCE"
        )
        response = self.client.post(
            "/bookings/create",
            data={
                "guest_id": "G001",
                "guest_name": "Nguyễn Văn An",
                "hotel_id": "H001",
                "room_number": "102",
                "check_in_date": "2026-09-20",
                "check_out_date": "2026-09-22",
                "total_amount": "2900000",
                "payment_method": "TIỀN MẶT"
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/bookings", response.headers["Location"])
        mock_create_batch.assert_not_called()

    @patch("routes.booking_routes.booking_service.create_booking_batch")
    def test_create_booking_fails_when_checkout_before_checkin(self, mock_create_batch):
        response = self.client.post(
            "/bookings/create",
            data={
                "guest_id": "G001",
                "guest_name": "Nguyễn Văn An",
                "hotel_id": "H001",
                "room_number": "101",
                "check_in_date": "2026-09-25",
                "check_out_date": "2026-09-20",  # Ngày check-out trước check-in
                "total_amount": "1500000",
                "payment_method": "TIỀN MẶT"
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/bookings", response.headers["Location"])
        mock_create_batch.assert_not_called()

    @patch("routes.booking_routes.room_service.get_room")
    @patch("routes.booking_routes.room_service.change_room_status")
    @patch("routes.booking_routes.booking_service.create_booking_batch", return_value="BK_AUTO_999")
    @patch("routes.booking_routes.booking_service.create_invoice", return_value="INV_AUTO_999")
    def test_create_booking_auto_updates_room_status_to_occupied(
        self, mock_create_inv, mock_create_batch, mock_change_status, mock_get_room
    ):
        mock_change_status.return_value = (True, None)
        mock_get_room.return_value = SimpleNamespace(
            hotel_id="H001",
            room_number="101",
            room_type="Deluxe Twin",
            price_per_night=1350000,
            is_available=True,
            status="AVAILABLE"
        )
        response = self.client.post(
            "/bookings/create",
            data={
                "guest_id": "G001",
                "guest_name": "Nguyễn Văn An",
                "hotel_id": "H001",
                "room_number": "101",
                "check_in_date": "2026-09-20",
                "check_out_date": "2026-09-22",
                "total_amount": "",  # Để trống để test tự động tính: 2 đêm * 1350000 = 2700000
                "payment_method": "TIỀN MẶT",
                "status": "CONFIRMED"
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/invoices/BK_AUTO_999", response.headers["Location"])
        mock_create_batch.assert_called_once()
        # Kiểm tra tự động chuyển phòng sang OCCUPIED, ĐỒNG THỜI đẩy kèm tên khách và
        # mã booking sang module Phòng để trang chi tiết phòng hiện được "ai đang thuê".
        mock_change_status.assert_called_once_with(
            "H001", "101", "OCCUPIED",
            guest_name="Nguyễn Văn An", booking_id="BK_AUTO_999"
        )

    @patch("routes.booking_routes.hotel_service.get_all_hotels", return_value=[])
    @patch("routes.booking_routes.hotel_service.get_all_guests", return_value=[])
    @patch("routes.booking_routes.hotel_service.create_guest", return_value=True)
    @patch("routes.booking_routes.room_service.get_room")
    @patch("routes.booking_routes.room_service.change_room_status", return_value=(True, "Success"))
    @patch("routes.booking_routes.booking_service.create_booking_batch", return_value="BK_NEW_GUEST_01")
    @patch("routes.booking_routes.booking_service.create_invoice", return_value="INV_NEW_GUEST_01")
    def test_create_booking_for_new_guest_auto_registers_customer(
        self, mock_create_inv, mock_create_batch, mock_change_status,
        mock_get_room, mock_create_guest, mock_get_guests, mock_get_hotels
    ):
        mock_get_room.return_value = SimpleNamespace(
            hotel_id="MT_001",
            room_number="103",
            room_type="Deluxe Twin",
            price_per_night=1050000,
            is_available=True,
            status="AVAILABLE"
        )
        response = self.client.post(
            "/bookings/create",
            data={
                "guest_id": "NEW",
                "guest_name": "Nguyễn Anh Quân",
                "guest_phone": "0912345678",
                "guest_id_card": "079201001234",
                "hotel_id": "MT_001",
                "room_number": "103",
                "check_in_date": "2026-09-20",
                "check_out_date": "2026-09-21",
                "total_amount": "1050000",
                "payment_method": "TIỀN MẶT",
                "status": "PENDING"
            }
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/invoices/BK_NEW_GUEST_01", response.headers["Location"])
        mock_create_guest.assert_called_once()
        args, kwargs = mock_create_guest.call_args
        self.assertEqual(kwargs.get("full_name"), "Nguyễn Anh Quân")
        self.assertEqual(kwargs.get("phone"), "0912345678")
        mock_create_batch.assert_called_once()

    @patch("routes.booking_routes.hotel_service.get_all_hotels", return_value=[])
    @patch("routes.booking_routes.booking_service.get_all_invoices")
    def test_list_invoices_route_renders_list(self, mock_get_all_inv, mock_get_hotels):
        mock_get_all_inv.return_value = [
            {
                "invoice_id": "INV_TEST_01",
                "booking_id": "BK_TEST_01",
                "guest_name": "Nguyễn Văn Hùng",
                "guest_phone": "0912345678",
                "guest_id_card": "079201001234",
                "hotel_id": "MT_001",
                "hotel_name": "Mường Thanh Luxury Hà Nội Centre",
                "room_number": "101",
                "check_in_date": "2026-09-18",
                "check_out_date": "2026-09-20",
                "nights": 2,
                "issue_date": "2026-09-18",
                "payment_method": "TIỀN MẶT",
                "payment_status": "PAID",
                "total_amount": 2500000,
            }
        ]
        response = self.client.get("/invoices")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("INV_TEST_01", html)
        self.assertIn("Nguyễn Văn Hùng", html)
        self.assertIn("2026-09-18", html)
        self.assertIn("2026-09-20", html)
        self.assertIn("Danh Sách Hóa Đơn Thanh Toán", html)

    @patch("routes.booking_routes.hotel_service.get_all_hotels", return_value=[])
    @patch("routes.booking_routes.booking_service.get_all_invoices")
    def test_list_invoices_route_with_query_filter(self, mock_get_all_inv, mock_get_hotels):
        mock_get_all_inv.return_value = [
            {
                "invoice_id": "INV_ALPHA",
                "booking_id": "BK_ALPHA",
                "guest_name": "Trần Thị Mai",
                "hotel_id": "MT_001",
                "hotel_name": "Mường Thanh Luxury",
                "room_number": "201",
                "payment_status": "PAID",
                "total_amount": 1800000,
            },
            {
                "invoice_id": "INV_BETA",
                "booking_id": "BK_BETA",
                "guest_name": "Lê Hoàng Nam",
                "hotel_id": "MT_002",
                "hotel_name": "Mường Thanh Grand",
                "room_number": "301",
                "payment_status": "UNPAID",
                "total_amount": 3200000,
            }
        ]
        response = self.client.get("/invoices?q=Trần+Thị+Mai&status=PAID")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("INV_ALPHA", html)
        self.assertNotIn("INV_BETA", html)

    @patch("routes.booking_routes.booking_service.get_invoice_detail_enriched")
    def test_get_invoice_api_returns_json(self, mock_get_inv):
        mock_get_inv.return_value = {
            "invoice_id": "INV_JSON_01",
            "booking_id": "BK_JSON_01",
            "guest_name": "Sarah Jenkins",
            "hotel_id": "MT_004",
            "check_in_date": "2026-09-18",
            "check_out_date": "2026-09-22",
            "nights": 4,
            "total_amount": 6000000,
            "payment_status": "PAID"
        }
        response = self.client.get("/api/invoices/BK_JSON_01")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["invoice"]["invoice_id"], "INV_JSON_01")
        self.assertEqual(data["invoice"]["guest_name"], "Sarah Jenkins")

    @patch("routes.booking_routes.booking_service.get_invoice_detail_enriched", return_value=None)
    def test_get_invoice_api_not_found(self, mock_get_inv):
        response = self.client.get("/api/invoices/BK_NOT_FOUND")
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertFalse(data["success"])

    @patch("routes.booking_routes.hotel_service.get_hotel_by_id")
    @patch("routes.booking_routes.room_service.get_room")
    def test_get_room_detail_api_success(self, mock_get_room, mock_get_hotel):
        mock_get_room.return_value = SimpleNamespace(
            hotel_id="MT_004",
            room_number="203",
            room_type="Deluxe King",
            price_per_night=850000,
            is_available=True,
            status="AVAILABLE",
            capacity=2,
            bed_type="King",
            description="Phòng tiêu chuẩn có ban công và bồn tắm."
        )
        mock_get_hotel.return_value = {
            "name": "Mường Thanh Grand Tuyên Quang",
            "city": "Tuyên Quang",
            "amenities": ["Hồ bơi", "Phòng Gym", "Bãi đỗ xe"]
        }
        response = self.client.get("/api/rooms/MT_004/203")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["room"]["room_number"], "203")
        self.assertEqual(data["room"]["status"], "AVAILABLE")
        self.assertIn("Hồ bơi", data["room"]["hotel_amenities"])
        self.assertTrue(any("Ban công" in f for f in data["room"]["room_features"]))

    @patch("routes.booking_routes.room_service.get_room", return_value=None)
    def test_get_room_detail_api_not_found(self, mock_get_room):
        response = self.client.get("/api/rooms/MT_004/999")
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertFalse(data["success"])

    @patch("routes.booking_routes.booking_service.settle_invoice_payment")
    def test_settle_invoice_api_success(self, mock_settle):
        mock_settle.return_value = (True, {
            "booking_id": "BK_123",
            "invoice_id": "INV_123",
            "payment_status": "PAID",
            "deposit_amount": 2000000.0,
            "remaining_amount": 0.0,
            "payment_method": "TIỀN MẶT"
        })
        response = self.client.post("/api/invoices/BK_123/settle", data={"payment_method": "TIỀN MẶT"})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["invoice"]["payment_status"], "PAID")
        mock_settle.assert_called_once_with(
            booking_id="BK_123",
            amount_paid=None,
            payment_method="TIỀN MẶT"
        )

    @patch("routes.booking_routes.booking_service.settle_invoice_payment")
    def test_settle_invoice_form_redirect(self, mock_settle):
        mock_settle.return_value = (True, {})
        response = self.client.post(
            "/invoices/BK_123/settle",
            data={"payment_method": "CHUYỂN KHOẢN", "redirect_to": "detail"},
            follow_redirects=False
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/invoices/BK_123", response.headers["Location"])

    # ----------------------------------------------------------------
    # TRẢ PHÒNG: đóng booking + giải phóng phòng
    # ----------------------------------------------------------------

    @patch("routes.booking_routes.room_service.invalidate_rooms_cache")
    @patch("routes.booking_routes.room_service.change_room_status", return_value=(True, None))
    @patch("routes.booking_routes.booking_service.complete_booking")
    def test_checkout_closes_booking_then_frees_room(
        self, mock_complete, mock_change_status, mock_invalidate
    ):
        mock_complete.return_value = (True, {
            "booking_id": "BK_CO_01",
            "is_early_checkout": False,
            "nights_billed": 3,
            "nights_stayed": 3,
        })
        response = self.client.post(
            "/bookings/BK_CO_01/checkout",
            data={
                "guest_id": "G001",
                "hotel_id": "MT_004",
                "room_number": "102",
                "check_in_date": "2026-09-16",
                "check_out_date": "2026-09-19",
            }
        )
        self.assertEqual(response.status_code, 302)
        mock_complete.assert_called_once()
        # Phòng phải được trả về AVAILABLE và cache danh sách phòng phải bị hủy
        mock_change_status.assert_called_once_with("MT_004", "102", "AVAILABLE")
        mock_invalidate.assert_called_once()

    @patch("routes.booking_routes.room_service.invalidate_rooms_cache")
    @patch("routes.booking_routes.room_service.change_room_status", return_value=(True, None))
    @patch("routes.booking_routes.booking_service.complete_booking")
    def test_checkout_early_warns_about_night_mismatch(
        self, mock_complete, mock_change_status, mock_invalidate
    ):
        """Trả sớm: ghi nhận số đêm lệch, và nói rõ KHÔNG giảm/KHÔNG hoàn tiền."""
        mock_complete.return_value = (True, {
            "booking_id": "BK_CO_02",
            "is_early_checkout": True,
            "nights_billed": 3,
            "nights_stayed": 1,
        })
        response = self.client.post(
            "/bookings/BK_CO_02/checkout",
            data={
                "guest_id": "G001",
                "hotel_id": "MT_004",
                "room_number": "102",
                "check_in_date": "2026-09-16",
                "check_out_date": "2026-09-19",
            },
            follow_redirects=True
        )
        html = response.get_data(as_text=True)
        self.assertIn("Khách trả sớm", html)
        self.assertIn("ở 1 đêm", html)
        self.assertIn("3 đêm đã đặt", html)
        # Chính sách: không giảm, không hoàn
        self.assertIn("không giảm và không hoàn tiền", html)

    @patch("routes.booking_routes.room_service.change_room_status", return_value=(True, None))
    @patch("routes.booking_routes.booking_service.complete_booking")
    @patch("routes.booking_routes.booking_service.get_active_booking_for_room")
    def test_checkout_resolves_missing_guest_from_room(
        self, mock_active, mock_complete, mock_change_status
    ):
        """Form chỉ gửi hotel_id + room_number -> tự tra lại khách đang thuê."""
        mock_active.return_value = {
            "guest_id": "G_777",
            "check_in_date": "2026-09-10",
            "check_out_date": "2026-09-14",
        }
        mock_complete.return_value = (True, {"booking_id": "BK_CO_03", "is_early_checkout": False})
        response = self.client.post(
            "/bookings/BK_CO_03/checkout",
            data={"hotel_id": "MT_004", "room_number": "102"}
        )
        self.assertEqual(response.status_code, 302)
        mock_active.assert_called_once_with("MT_004", "102")
        self.assertEqual(mock_complete.call_args.kwargs["guest_id"], "G_777")

    @patch("routes.booking_routes.room_service.change_room_status")
    @patch("routes.booking_routes.booking_service.complete_booking")
    @patch("routes.booking_routes.booking_service.get_active_booking_for_room", return_value=None)
    def test_checkout_without_identity_does_not_free_room(
        self, mock_active, mock_complete, mock_change_status
    ):
        """Không xác định được khách thì DỪNG — không được giải phóng phòng suông."""
        response = self.client.post(
            "/bookings/BK_CO_04/checkout",
            data={"hotel_id": "MT_004", "room_number": "102"}
        )
        self.assertEqual(response.status_code, 302)
        mock_complete.assert_not_called()
        mock_change_status.assert_not_called()


if __name__ == "__main__":
    unittest.main()



