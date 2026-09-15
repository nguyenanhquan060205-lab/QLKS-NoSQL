from decimal import Decimal
import unittest
from unittest.mock import patch

from services import hotel_service


class FakeRoomSession:
    def __init__(self):
        self.calls = []
        self.prepared_query = object()
        self.rows = [
            ("H001", "101", "Deluxe", Decimal("2500000"), True),
            ("H001", "102", "Standard", Decimal("1800000"), False),
        ]

    def prepare(self, query):
        self.calls.append(("prepare", query))
        return self.prepared_query

    def execute(self, query, parameters=None):
        self.calls.append(("execute", query, parameters))
        return self.rows


class FailingRoomSession(FakeRoomSession):
    def prepare(self, query):
        raise RuntimeError("prepare failed")


class RoomServiceTest(unittest.TestCase):
    def setUp(self):
        self.session = FakeRoomSession()
        self.session_patcher = patch.object(
            hotel_service,
            "get_session",
            return_value=self.session,
        )
        self.session_patcher.start()

    def tearDown(self):
        self.session_patcher.stop()

    def test_get_rooms_uses_hotel_id_partition_key(self):
        rooms = hotel_service.get_rooms_by_hotel("H001")

        self.assertEqual(rooms, self.session.rows)
        prepared_cql = self.session.calls[0][1]
        self.assertIn("FROM rooms_by_hotel", prepared_cql)
        self.assertIn("WHERE hotel_id = ?", prepared_cql)
        self.assertEqual(
            self.session.calls[-1],
            ("execute", self.session.prepared_query, ("H001",)),
        )

    def test_create_room_uses_prepared_statement_and_cassandra_types(self):
        created = hotel_service.create_room(
            "H001",
            "103",
            "Suite",
            "3200000.50",
            "false",
        )

        self.assertTrue(created)
        prepared_cql = self.session.calls[0][1]
        self.assertIn("INSERT INTO rooms_by_hotel", prepared_cql)
        operation, query, parameters = self.session.calls[-1]
        self.assertEqual(operation, "execute")
        self.assertIs(query, self.session.prepared_query)
        self.assertEqual(parameters[0:3], ("H001", "103", "Suite"))
        self.assertEqual(parameters[3], Decimal("3200000.50"))
        self.assertIs(parameters[4], False)

    def test_returns_safe_defaults_without_database_connection(self):
        with patch.object(hotel_service, "get_session", return_value=None):
            self.assertEqual(hotel_service.get_rooms_by_hotel("H001"), [])
            self.assertFalse(
                hotel_service.create_room("H001", "103", "Suite", 3200000)
            )

    def test_returns_safe_defaults_when_cassandra_raises_error(self):
        with patch.object(
            hotel_service,
            "get_session",
            return_value=FailingRoomSession(),
        ):
            self.assertEqual(hotel_service.get_rooms_by_hotel("H001"), [])
            self.assertFalse(
                hotel_service.create_room("H001", "103", "Suite", 3200000)
            )


if __name__ == "__main__":
    unittest.main()

