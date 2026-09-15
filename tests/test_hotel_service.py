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
            return []
        if "FROM hotels" in query:
            return [("H001", "Khách sạn mẫu")]
        if "FROM guests" in query:
            return [("G001", "Khách hàng mẫu")]
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

        self.assertEqual(hotels, [("H001", "Khách sạn mẫu")])
        self.assertIn("FROM hotels", self.session.calls[-1][1])

    def test_create_hotel_uses_prepared_statement_and_cassandra_set(self):
        result = hotel_service.create_hotel(
            "H003",
            "Hotel Demo",
            "0900000000",
            "1 Đường A",
            "Đà Nẵng",
            "Vietnam",
            "Wifi, Spa, Wifi",
        )

        self.assertTrue(result)
        operation, query, parameters = self.session.calls[-1]
        self.assertEqual(operation, "execute")
        self.assertIs(query, self.session.prepared_query)
        self.assertEqual(parameters[-1], {"Wifi", "Spa"})

    def test_get_all_guests_returns_rows(self):
        guests = hotel_service.get_all_guests()

        self.assertEqual(guests, [("G001", "Khách hàng mẫu")])
        self.assertIn("FROM guests", self.session.calls[-1][1])

    def test_create_guest_uses_prepared_statement(self):
        result = hotel_service.create_guest(
            "G003",
            "Nguyễn Văn B",
            "guest@example.com",
            "0911111111",
            "123456789",
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
            ),
        )

    def test_returns_safe_defaults_without_database_connection(self):
        with patch.object(hotel_service, "get_session", return_value=None):
            self.assertEqual(hotel_service.get_all_hotels(), [])
            self.assertEqual(hotel_service.get_all_guests(), [])
            self.assertFalse(
                hotel_service.create_hotel(
                    "H001", "Hotel", "090", "Address", "City", "VN", set()
                )
            )
            self.assertFalse(
                hotel_service.create_guest(
                    "G001", "Guest", "guest@example.com", "091", "123"
                )
            )

    def test_returns_safe_defaults_when_cassandra_raises_error(self):
        with patch.object(
            hotel_service,
            "get_session",
            return_value=FailingSession(),
        ):
            self.assertEqual(hotel_service.get_all_hotels(), [])
            self.assertEqual(hotel_service.get_all_guests(), [])
            self.assertFalse(
                hotel_service.create_hotel(
                    "H001", "Hotel", "090", "Address", "City", "VN", set()
                )
            )
            self.assertFalse(
                hotel_service.create_guest(
                    "G001", "Guest", "guest@example.com", "091", "123"
                )
            )


if __name__ == "__main__":
    unittest.main()
