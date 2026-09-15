from types import SimpleNamespace
import unittest
from unittest.mock import patch

from flask import Flask

from routes.booking_routes import booking_bp
from routes.hotel_routes import hotel_bp


class HotelRoutesTest(unittest.TestCase):
    def setUp(self):
        app = Flask(__name__, template_folder="../templates")
        app.config.update(TESTING=True, SECRET_KEY="test-secret")
        app.register_blueprint(hotel_bp)
        app.register_blueprint(booking_bp)
        self.client = app.test_client()

    @patch("routes.hotel_routes.hotel_service.get_all_hotels")
    def test_list_hotels_renders_database_rows(self, get_all_hotels):
        get_all_hotels.return_value = [
            SimpleNamespace(
                hotel_id="H001",
                name="Ocean View Hotel",
                phone="0901234567",
                address="1 Đường Biển",
                city="Đà Nẵng",
                country="Vietnam",
                amenities={"Wifi", "Hồ bơi"},
            )
        ]

        response = self.client.get("/hotels")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Ocean View Hotel", response.get_data(as_text=True))
        self.assertIn("/hotels/H001/rooms", response.get_data(as_text=True))

    @patch("routes.hotel_routes.hotel_service.get_all_hotels", return_value=[])
    @patch("routes.hotel_routes.hotel_service.create_hotel", return_value=True)
    def test_add_hotel_calls_service_and_redirects(self, create_hotel, _):
        response = self.client.post(
            "/hotels/add",
            data={
                "name": "Ocean View Hotel",
                "phone": "0901234567",
                "address": "1 Đường Biển",
                "city": "Đà Nẵng",
                "country": "Vietnam",
                "amenities": "Wifi, Hồ bơi",
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Đã thêm khách sạn", response.get_data(as_text=True))
        create_hotel.assert_called_once()
        parameters = create_hotel.call_args.args
        self.assertRegex(parameters[0], r"^H[A-F0-9]{8}$")
        self.assertEqual(parameters[1:], (
            "Ocean View Hotel",
            "0901234567",
            "1 Đường Biển",
            "Đà Nẵng",
            "Vietnam",
            "Wifi, Hồ bơi",
        ))

    @patch("routes.hotel_routes.hotel_service.get_all_hotels", return_value=[])
    @patch("routes.hotel_routes.hotel_service.create_hotel")
    def test_add_hotel_rejects_missing_required_fields(self, create_hotel, _):
        response = self.client.post(
            "/hotels/add",
            data={
                "name": "",
                "phone": "0901234567",
                "address": "1 Đường Biển",
                "city": "Đà Nẵng",
                "country": "Vietnam",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Tên khách sạn không được để trống", response.get_data(as_text=True))
        create_hotel.assert_not_called()

    @patch("routes.hotel_routes.hotel_service.get_all_guests")
    def test_list_guests_renders_database_rows(self, get_all_guests):
        get_all_guests.return_value = [
            SimpleNamespace(
                guest_id="G001",
                full_name="Nguyễn Văn An",
                email="an@example.com",
                phone="0912345678",
                id_card="079201001234",
            )
        ]

        response = self.client.get("/guests")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Nguyễn Văn An", body)
        self.assertIn("/bookings/guest/G001", body)

    @patch("routes.hotel_routes.hotel_service.get_all_guests", return_value=[])
    @patch("routes.hotel_routes.hotel_service.create_guest", return_value=True)
    def test_add_guest_calls_service_and_redirects(self, create_guest, _):
        response = self.client.post(
            "/guests/add",
            data={
                "full_name": "Nguyễn Văn An",
                "email": "an@example.com",
                "phone": "0912345678",
                "id_card": "079201001234",
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("Đã thêm khách hàng", response.get_data(as_text=True))
        create_guest.assert_called_once()
        parameters = create_guest.call_args.args
        self.assertRegex(parameters[0], r"^G[A-F0-9]{8}$")
        self.assertEqual(parameters[1:], (
            "Nguyễn Văn An",
            "an@example.com",
            "0912345678",
            "079201001234",
        ))

    @patch("routes.hotel_routes.hotel_service.get_all_guests", return_value=[])
    @patch("routes.hotel_routes.hotel_service.create_guest")
    def test_add_guest_rejects_invalid_email(self, create_guest, _):
        response = self.client.post(
            "/guests/add",
            data={
                "full_name": "Nguyễn Văn An",
                "email": "an@@example.com",
                "phone": "0912345678",
                "id_card": "079201001234",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Email chưa đúng định dạng", response.get_data(as_text=True))
        create_guest.assert_not_called()

    @patch("routes.hotel_routes.hotel_service.get_all_hotels", return_value=[])
    @patch("routes.hotel_routes.hotel_service.create_hotel", return_value=False)
    def test_add_hotel_returns_503_when_database_write_fails(self, _, __):
        response = self.client.post(
            "/hotels/add",
            data={
                "name": "Ocean View Hotel",
                "phone": "0901234567",
                "address": "1 Đường Biển",
                "city": "Đà Nẵng",
                "country": "Vietnam",
            },
        )

        self.assertEqual(response.status_code, 503)
        self.assertIn("Không thể thêm khách sạn", response.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
