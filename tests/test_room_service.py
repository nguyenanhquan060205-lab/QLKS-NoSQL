from decimal import Decimal
import unittest
from unittest.mock import patch

from types import SimpleNamespace

from services import hotel_service, room_service


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



class ChangeRoomStatusTest(unittest.TestCase):
    """
    Test HÀM THẬT room_service.change_room_status, không mock nó đi.

    Trước đây cả bộ test đều mock change_room_status ở tầng route, nên không ai
    phát hiện là trong hàm có biến `is_available` được dùng mà không bao giờ được
    gán. Mọi lần đổi trạng thái đều nổ UnboundLocalError, bị except bắt lại rồi
    báo ra "Lỗi kết nối AstraDB, vui lòng thử lại." — sai hoàn toàn bản chất.
    """

    def setUp(self):
        self.executed = []

        class RecordingSession:
            def __init__(inner):
                inner.queries = {}

            def prepare(inner, query):
                stmt = object()
                inner.queries[id(stmt)] = query
                return stmt

            def execute(inner, stmt, parameters=None):
                self.executed.append((inner.queries.get(id(stmt), ""), parameters))
                return []

        self.session = RecordingSession()

    def _patched(self, room):
        return (
            patch.object(room_service, "get_session", return_value=self.session),
            patch.object(room_service, "get_room", return_value=room),
        )

    def test_check_out_sets_available_and_clears_guest_columns(self):
        room = SimpleNamespace(hotel_id="MT_004", room_number="102", status="OCCUPIED")
        p1, p2 = self._patched(room)
        with p1, p2:
            ok, err = room_service.change_room_status("MT_004", "102", "AVAILABLE")

        self.assertTrue(ok, msg=f"trả phòng phải thành công, nhận lỗi: {err}")
        self.assertIsNone(err)
        # 1 lệnh UPDATE phòng + 1 lệnh cập nhật counter thống kê (ghi riêng, sau)
        self.assertEqual(len(self.executed), 2)

        query, params = self.executed[0]
        self.assertIn("UPDATE rooms_by_hotel", query)
        # AVAILABLE -> is_available phải True, và 2 cột khách phải bị xóa về None
        self.assertEqual(params, ("AVAILABLE", True, None, None, "MT_004", "102"))

        counter_query, counter_params = self.executed[1]
        self.assertIn("UPDATE room_status_counts_by_hotel", counter_query)
        # (total, available, occupied, maintenance, hotel_id): OCCUPIED -1, AVAILABLE +1
        self.assertEqual(counter_params, (0, 1, -1, 0, "MT_004"))

    def test_occupied_keeps_guest_info_and_sets_unavailable(self):
        room = SimpleNamespace(hotel_id="MT_004", room_number="102", status="AVAILABLE")
        p1, p2 = self._patched(room)
        with p1, p2:
            ok, err = room_service.change_room_status(
                "MT_004", "102", "OCCUPIED",
                guest_name="Lê Hoàng Nam", booking_id="BK_X1",
            )

        self.assertTrue(ok, msg=f"nhận lỗi: {err}")
        _, params = self.executed[0]
        self.assertEqual(params, ("OCCUPIED", False, "Lê Hoàng Nam", "BK_X1", "MT_004", "102"))

    def test_maintenance_sets_unavailable_and_clears_guest(self):
        room = SimpleNamespace(hotel_id="MT_004", room_number="102", status="AVAILABLE")
        p1, p2 = self._patched(room)
        with p1, p2:
            ok, err = room_service.change_room_status(
                "MT_004", "102", "MAINTENANCE",
                guest_name="Không nên giữ", booking_id="BK_X2",
            )

        self.assertTrue(ok, msg=f"nhận lỗi: {err}")
        _, params = self.executed[0]
        self.assertEqual(params, ("MAINTENANCE", False, None, None, "MT_004", "102"))

    def test_blocked_transition_returns_reason_not_connection_error(self):
        """OCCUPIED -> MAINTENANCE bị ma trận chặn, và không được chạm tới DB."""
        room = SimpleNamespace(hotel_id="MT_004", room_number="102", status="OCCUPIED")
        p1, p2 = self._patched(room)
        with p1, p2:
            ok, err = room_service.change_room_status("MT_004", "102", "MAINTENANCE")

        self.assertFalse(ok)
        self.assertIn("Không thể chuyển", err)
        # Bị chặn thì không ghi gì, kể cả counter
        self.assertEqual(self.executed, [])

    def test_query_failure_message_is_not_mislabeled_as_connection_error(self):
        """Query lỗi thì phải nói ra lỗi thật, đừng gán nhãn 'lỗi kết nối'."""
        class BrokenSession:
            def prepare(self, query):
                raise RuntimeError("Undefined column name current_guest_name")

            def execute(self, *a, **kw):
                raise RuntimeError("không nên tới đây")

        room = SimpleNamespace(hotel_id="MT_004", room_number="102", status="OCCUPIED")
        with patch.object(room_service, "get_session", return_value=BrokenSession()), \
             patch.object(room_service, "get_room", return_value=room):
            ok, err = room_service.change_room_status("MT_004", "102", "AVAILABLE")

        self.assertFalse(ok)
        self.assertNotIn("Lỗi kết nối AstraDB", err)
        self.assertIn("Undefined column name", err)
