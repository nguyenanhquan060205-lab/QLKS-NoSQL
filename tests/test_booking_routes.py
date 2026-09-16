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
    @patch("routes.booking_routes.booking_service.create_booking_batch", return_value="BK_NEW_123")
    @patch("routes.booking_routes.booking_service.create_invoice", return_value="INV_NEW_123")
    def test_create_booking_success_redirects_to_invoice(
        self, mock_create_inv, mock_create_batch, mock_guests, mock_hotels
    ):
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


if __name__ == "__main__":
    unittest.main()
