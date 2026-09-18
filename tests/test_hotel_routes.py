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
                name="Mường Thanh Luxury Đà Nẵng",
                phone="0236395678",
                address="270 Võ Nguyên Giáp",
                city="Thành phố Đà Nẵng",
                country="Vietnam",
                amenities={"Wifi", "Hồ bơi"},
            )
        ]

        response = self.client.get("/hotels")

        self.assertEqual(response.status_code, 200)
        self.assertIn("Mường Thanh Luxury Đà Nẵng", response.get_data(as_text=True))
        self.assertIn("/hotels/H001/rooms", response.get_data(as_text=True))

    @patch("routes.hotel_routes.hotel_service.get_all_hotels", return_value=[])
    @patch("routes.hotel_routes.hotel_service.create_hotel", return_value=True)
    def test_add_hotel_calls_service_and_redirects(self, create_hotel, _):
        response = self.client.post(
            "/hotels/add",
            data={
                "name": "Mường Thanh Luxury Đà Nẵng",
                "phone": "0901234567",
                "address": "270 Võ Nguyên Giáp",
                "city": "Thành phố Đà Nẵng",
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
            "Mường Thanh Luxury Đà Nẵng",
            "0901234567",
            "270 Võ Nguyên Giáp",
            "Thành phố Đà Nẵng",
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

    @patch("routes.hotel_routes.hotel_service.get_all_hotels", return_value=[])
    @patch("routes.hotel_routes.hotel_service.create_hotel")
    def test_add_hotel_rejects_invalid_phone_number(self, create_hotel, _):
        response = self.client.post(
            "/hotels/add",
            data={
                "name": "Mường Thanh Test",
                "phone": "12345",
                "address": "1 Đường Biển",
                "city": "Đà Nẵng",
                "country": "Vietnam",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Số điện thoại phải gồm đúng 10 chữ số", response.get_data(as_text=True))
        create_hotel.assert_not_called()

    @patch("routes.hotel_routes.hotel_service.update_hotel", return_value=True)
    def test_edit_hotel_calls_service_and_redirects(self, update_hotel):
        response = self.client.post(
            "/hotels/H001/edit",
            data={
                "name": "Mường Thanh Luxury Đà Nẵng Mới",
                "phone": "0901234567",
                "address": "270 Võ Nguyên Giáp",
                "city": "Thành phố Đà Nẵng",
                "country": "Vietnam",
                "amenities": "Wifi, Spa",
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        update_hotel.assert_called_once_with(
            "H001",
            "Mường Thanh Luxury Đà Nẵng Mới",
            "0901234567",
            "270 Võ Nguyên Giáp",
            "Thành phố Đà Nẵng",
            "Vietnam",
            "Wifi, Spa",
        )

    @patch("routes.hotel_routes.hotel_service.delete_hotel", return_value=True)
    def test_delete_hotel_calls_service_and_redirects(self, delete_hotel):
        response = self.client.post(
            "/hotels/H001/delete",
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        delete_hotel.assert_called_once_with("H001")

    @patch("routes.hotel_routes.hotel_service.get_all_guests")
    def test_list_guests_renders_database_rows(self, get_all_guests):
        get_all_guests.return_value = [
            SimpleNamespace(
                guest_id="G001",
                full_name="Nguyễn Văn An",
                email="an@example.com",
                phone="0912345678",
                id_card="079201001234",
                address="123 Nguyễn Thị Minh Khai, Đà Nẵng",
            )
        ]

        response = self.client.get("/guests")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn("Nguyễn Văn An", body)
        self.assertIn("123 Nguyễn Thị Minh Khai", body)

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
                "address": "Hà Nội",
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
            "Hà Nội",
        ))

    @patch("routes.hotel_routes.hotel_service.get_all_guests", return_value=[])
    @patch("routes.hotel_routes.hotel_service.create_guest")
    def test_add_guest_rejects_invalid_phone(self, create_guest, _):
        response = self.client.post(
            "/guests/add",
            data={
                "full_name": "Nguyễn Văn An",
                "email": "an@example.com",
                "phone": "0912345",
                "id_card": "079201001234",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Số điện thoại phải gồm đúng 10 chữ số", response.get_data(as_text=True))
        create_guest.assert_not_called()

    @patch("routes.hotel_routes.hotel_service.get_all_guests", return_value=[])
    @patch("routes.hotel_routes.hotel_service.update_guest", return_value=True)
    def test_edit_guest_calls_service_and_redirects(self, update_guest, _):
        response = self.client.post(
            "/guests/G001/edit",
            data={
                "full_name": "Nguyễn Văn An Mới",
                "email": "an.new@example.com",
                "phone": "0912345678",
                "id_card": "079201001234",
                "address": "Đà Nẵng",
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        update_guest.assert_called_once_with(
            "G001",
            "Nguyễn Văn An Mới",
            "an.new@example.com",
            "0912345678",
            "079201001234",
            "Đà Nẵng",
        )

    @patch("routes.hotel_routes.hotel_service.delete_guest", return_value=True)
    def test_delete_guest_calls_service_and_redirects(self, delete_guest):
        response = self.client.post(
            "/guests/G001/delete",
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        delete_guest.assert_called_once_with("G001")

    def test_api_provinces_returns_json_list(self):
        response = self.client.get("/api/provinces")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)

    @patch("routes.hotel_routes.hotel_service.get_all_hotels")
    @patch("routes.hotel_routes.hotel_service.create_hotel")
    def test_add_hotel_rejects_duplicate_name(self, create_hotel, get_all_hotels):
        get_all_hotels.return_value = [
            SimpleNamespace(hotel_id="H001", name="Mường Thanh Luxury Đà Nẵng")
        ]
        response = self.client.post(
            "/hotels/add",
            data={
                "name": "mường thanh luxury đà nẵng",
                "phone": "0901234567",
                "address": "123 Đường Biển",
                "city": "Đà Nẵng",
                "country": "Vietnam",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("đã tồn tại trong hệ thống", response.get_data(as_text=True))
        create_hotel.assert_not_called()

    @patch("routes.hotel_routes.hotel_service.get_all_guests", return_value=[])
    @patch("routes.hotel_routes.hotel_service.create_guest")
    def test_add_guest_rejects_invalid_id_card(self, create_guest, _):
        # Từ chối CMND 9 chữ số cũ (hệ thống hiện tại chỉ dùng CCCD 12 số và Hộ chiếu)
        res_cmnd = self.client.post(
            "/guests/add",
            data={
                "full_name": "Nguyễn Văn An",
                "email": "an@example.com",
                "phone": "0912345678",
                "id_card": "123456789",
            },
        )
        self.assertEqual(res_cmnd.status_code, 400)
        self.assertIn("Số CCCD phải gồm đúng 12 chữ số", res_cmnd.get_data(as_text=True))

        # Từ chối chuỗi ký tự sai định dạng
        response = self.client.post(
            "/guests/add",
            data={
                "full_name": "Nguyễn Văn An",
                "email": "an@example.com",
                "phone": "0912345678",
                "id_card": "12345",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Số CCCD phải gồm đúng 12 chữ số", response.get_data(as_text=True))
        create_guest.assert_not_called()

    @patch("routes.hotel_routes.hotel_service.get_all_guests", return_value=[])
    @patch("routes.hotel_routes.hotel_service.create_guest", return_value=True)
    def test_add_guest_accepts_passport(self, create_guest, _):
        response = self.client.post(
            "/guests/add",
            data={
                "full_name": "John Doe",
                "email": "john@example.com",
                "phone": "0987654321",
                "id_card": "b1234567",
            },
            follow_redirects=False,
        )
        self.assertEqual(response.status_code, 302)
        create_guest.assert_called_once()
        # Xác nhận Hộ chiếu được tự động viết hoa
        args, _ = create_guest.call_args
        self.assertEqual(args[4], "B1234567")

    @patch("routes.hotel_routes.hotel_service.get_all_guests")
    @patch("routes.hotel_routes.hotel_service.create_guest")
    def test_add_guest_rejects_duplicate_id_card_or_email_or_phone(self, create_guest, get_all_guests):
        get_all_guests.return_value = [
            SimpleNamespace(
                guest_id="G001",
                full_name="Khách cũ",
                email="cu@example.com",
                phone="0911111111",
                id_card="079201001234",
            )
        ]
        # Trùng CCCD
        res1 = self.client.post(
            "/guests/add",
            data={
                "full_name": "Khách Mới",
                "email": "moi@example.com",
                "phone": "0922222222",
                "id_card": "079201001234",
            },
        )
        self.assertEqual(res1.status_code, 400)
        self.assertIn("đã được đăng ký cho khách hàng khác", res1.get_data(as_text=True))

        # Trùng Email
        res2 = self.client.post(
            "/guests/add",
            data={
                "full_name": "Khách Mới",
                "email": "cu@example.com",
                "phone": "0922222222",
                "id_card": "079201009999",
            },
        )
        self.assertEqual(res2.status_code, 400)
        self.assertIn("đã tồn tại trong hệ thống", res2.get_data(as_text=True))

        # Trùng Phone
        res3 = self.client.post(
            "/guests/add",
            data={
                "full_name": "Khách Mới",
                "email": "moi@example.com",
                "phone": "0911111111",
                "id_card": "079201009999",
            },
        )
        self.assertEqual(res3.status_code, 400)
        self.assertIn("đã được đăng ký cho khách hàng khác", res3.get_data(as_text=True))
        create_guest.assert_not_called()

    @patch("routes.hotel_routes.room_service.get_room")
    def test_room_detail_shows_active_guest_when_occupied(self, mock_get_room):
        """
        Trang chi tiết phòng lấy "ai đang thuê" từ 2 cột denormalize trên rooms_by_hotel
        (current_guest_name / current_booking_id), do booking_routes ghi vào lúc đặt phòng
        thành công — không truy vấn bookings_by_guest ở đây nữa.

        Hồ sơ khách đầy đủ (điện thoại, CMND, số đêm, tiền) nằm ở modal chi tiết phòng của
        trang Đặt phòng, qua booking_service.get_active_booking_for_room.
        """
        mock_get_room.return_value = SimpleNamespace(
            hotel_id="MT_004",
            room_number="102",
            room_type="Deluxe King",
            price_per_night=850000,
            is_available=False,
            status="OCCUPIED",
            capacity=2,
            bed_type="King",
            description="Phòng tiêu chuẩn view biển",
            current_guest_name="Đinh Quang Khải",
            current_booking_id="BK2026091045",
        )
        response = self.client.get("/hotels/MT_004/rooms/102")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Khách đang thuê", html)
        self.assertIn("Đinh Quang Khải", html)
        self.assertIn("BK2026091045", html)

    @patch("routes.hotel_routes.room_service.get_room")
    def test_room_detail_occupied_without_guest_info_shows_fallback(self, mock_get_room):
        """Phòng OCCUPIED nhưng 2 cột khách còn NULL (đổi trạng thái tay) -> không để trống trơn."""
        mock_get_room.return_value = SimpleNamespace(
            hotel_id="MT_004",
            room_number="103",
            room_type="Standard",
            price_per_night=550000,
            is_available=False,
            status="OCCUPIED",
            capacity=2,
            bed_type="Twin",
            description="",
            current_guest_name=None,
            current_booking_id=None,
        )
        response = self.client.get("/hotels/MT_004/rooms/103")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Chưa rõ", response.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()

