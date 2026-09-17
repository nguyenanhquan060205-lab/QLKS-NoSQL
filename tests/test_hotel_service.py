import unittest
from unittest.mock import patch

from services import hotel_service


class FakeSession:
    def __init__(self):
        self.calls = []
        self.prepared_query = object()

    def prepare(self, query):
        self.calls.append(("prepare", query))
        return self.prepared_query

    def execute(self, query, parameters=None):
        self.calls.append(("execute", query, parameters))

        if query is self.prepared_query:
            if parameters and len(parameters) == 1 and str(parameters[0]).startswith("H"):
                return [("H001", "Mường Thanh Luxury Đà Nẵng")]
            if parameters and len(parameters) == 1 and str(parameters[0]).startswith("G"):
                return [("G001", "Nguyễn Văn An")]
            return []
        if isinstance(query, str) and "FROM hotels" in query:
            return [("H001", "Mường Thanh Luxury Đà Nẵng")]
        if isinstance(query, str) and "FROM guests" in query:
            return [("G001", "Nguyễn Văn An")]
        return []


class FailingSession(FakeSession):
    def prepare(self, query):
        raise RuntimeError("prepare failed")

    def execute(self, query, parameters=None):
        raise RuntimeError("execute failed")


class HotelServiceTest(unittest.TestCase):
    def setUp(self):
        self.session = FakeSession()
        self.session_patcher = patch.object(
            hotel_service,
            "get_session",
            return_value=self.session,
        )
        self.session_patcher.start()

    def tearDown(self):
        self.session_patcher.stop()

    def test_get_all_hotels_returns_rows(self):
        hotels = hotel_service.get_all_hotels()

        self.assertEqual(hotels, [("H001", "Mường Thanh Luxury Đà Nẵng")])
        self.assertIn("FROM hotels", self.session.calls[-1][1])

    def test_get_hotel_by_id_returns_row(self):
        hotel = hotel_service.get_hotel_by_id("H001")
        self.assertIsNotNone(hotel)
        self.assertEqual(hotel[0], "H001")

    def test_create_hotel_uses_prepared_statement_and_cassandra_set(self):
        result = hotel_service.create_hotel(
            "H003",
            "Mường Thanh Grand Hà Nội",
            "02436408686",
            "1 Đường A",
            "Thành phố Hà Nội",
            "Vietnam",
            "Wifi, Spa, Wifi",
        )

        self.assertTrue(result)
        operation, query, parameters = self.session.calls[-1]
        self.assertEqual(operation, "execute")
        self.assertIs(query, self.session.prepared_query)
        self.assertEqual(parameters[-1], {"Wifi", "Spa"})

    def test_update_hotel_uses_prepared_statement(self):
        result = hotel_service.update_hotel(
            "H001",
            "Mường Thanh Luxury Đà Nẵng Mới",
            "02363956789",
            "270 Võ Nguyên Giáp",
            "Thành phố Đà Nẵng",
            "Vietnam",
            "Wifi, Bể bơi",
        )
        self.assertTrue(result)
        operation, query, parameters = self.session.calls[-1]
        self.assertEqual(operation, "execute")
        self.assertEqual(parameters[0], "Mường Thanh Luxury Đà Nẵng Mới")
        self.assertEqual(parameters[-1], "H001")

    def test_delete_hotel_calls_delete_on_session(self):
        result = hotel_service.delete_hotel("H001")
        self.assertTrue(result)
        operation, query, parameters = self.session.calls[-1]
        self.assertEqual(operation, "execute")
        self.assertEqual(parameters, ("H001",))

    def test_get_all_guests_returns_rows(self):
        guests = hotel_service.get_all_guests()

        self.assertEqual(guests, [("G001", "Nguyễn Văn An")])
        self.assertIn("FROM guests", self.session.calls[-1][1])

    def test_create_guest_uses_prepared_statement(self):
        result = hotel_service.create_guest(
            "G003",
            "Nguyễn Văn B",
            "guest@example.com",
            "0911111111",
            "123456789",
            "Hà Nội",
        )

        self.assertTrue(result)
        operation, query, parameters = self.session.calls[-1]
        self.assertEqual(operation, "execute")
        self.assertIs(query, self.session.prepared_query)
        self.assertEqual(
            parameters,
            (
                "G003",
                "Nguyễn Văn B",
                "guest@example.com",
                "0911111111",
                "123456789",
                "Hà Nội",
            ),
        )

    def test_update_guest_uses_prepared_statement(self):
        result = hotel_service.update_guest(
            "G001",
            "Nguyễn Văn An Cập Nhật",
            "an.new@example.com",
            "0912345678",
            "079201001234",
            "Đà Nẵng",
        )
        self.assertTrue(result)
        operation, query, parameters = self.session.calls[-1]
        self.assertEqual(operation, "execute")
        self.assertEqual(parameters[0], "Nguyễn Văn An Cập Nhật")
        self.assertEqual(parameters[-1], "G001")

    def test_delete_guest_calls_delete_on_session(self):
        result = hotel_service.delete_guest("G001")
        self.assertTrue(result)
        operation, query, parameters = self.session.calls[-1]
        self.assertEqual(operation, "execute")
        self.assertEqual(parameters, ("G001",))

    def test_returns_safe_defaults_without_database_connection(self):
        with patch.object(hotel_service, "get_session", return_value=None):
            self.assertEqual(hotel_service.get_all_hotels(), [])
            self.assertIsNone(hotel_service.get_hotel_by_id("H001"))
            self.assertEqual(hotel_service.get_all_guests(), [])
            self.assertIsNone(hotel_service.get_guest_by_id("G001"))
            self.assertFalse(
                hotel_service.create_hotel(
                    "H001", "Hotel", "090", "Address", "City", "VN", set()
                )
            )
            self.assertFalse(
                hotel_service.update_hotel(
                    "H001", "Hotel", "090", "Address", "City", "VN", set()
                )
            )
            self.assertFalse(hotel_service.delete_hotel("H001"))
            self.assertFalse(
                hotel_service.create_guest(
                    "G001", "Guest", "guest@example.com", "091", "123"
                )
            )
            self.assertFalse(
                hotel_service.update_guest(
                    "G001", "Guest", "guest@example.com", "091", "123"
                )
            )
            self.assertFalse(hotel_service.delete_guest("G001"))

    def test_returns_safe_defaults_when_cassandra_raises_error(self):
        with patch.object(
            hotel_service,
            "get_session",
            return_value=FailingSession(),
        ):
            self.assertEqual(hotel_service.get_all_hotels(), [])
            self.assertIsNone(hotel_service.get_hotel_by_id("H001"))
            self.assertEqual(hotel_service.get_all_guests(), [])
            self.assertIsNone(hotel_service.get_guest_by_id("G001"))
            self.assertFalse(
                hotel_service.create_hotel(
                    "H001", "Hotel", "090", "Address", "City", "VN", set()
                )
            )
            self.assertFalse(
                hotel_service.update_hotel(
                    "H001", "Hotel", "090", "Address", "City", "VN", set()
                )
            )
            self.assertFalse(hotel_service.delete_hotel("H001"))
            self.assertFalse(
                hotel_service.create_guest(
                    "G001", "Guest", "guest@example.com", "091", "123"
                )
            )
            self.assertFalse(
                hotel_service.update_guest(
                    "G001", "Guest", "guest@example.com", "091", "123"
                )
            )
            self.assertFalse(hotel_service.delete_guest("G001"))


if __name__ == "__main__":
    unittest.main()
