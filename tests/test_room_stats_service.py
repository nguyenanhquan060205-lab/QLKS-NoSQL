import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from services import dashboard_service, room_service, room_stats_service


class RecordingSession:
    """Session giả: ghi lại (câu CQL, tham số) của mọi lệnh execute, trả rows theo câu SELECT."""

    def __init__(self, select_rows=None):
        self.executed = []
        self.select_rows = select_rows or {}

    def prepare(self, query):
        return SimpleNamespace(query=query)

    def execute(self, stmt, parameters=None):
        query = getattr(stmt, "query", stmt)
        self.executed.append((query, parameters))
        for marker, rows in self.select_rows.items():
            if marker in query and query.lstrip().upper().startswith("SELECT"):
                return rows
        return []

    def counter_updates(self):
        return [p for q, p in self.executed if "UPDATE room_status_counts_by_hotel" in q]


def _counter_row(hotel_id, total, available, occupied, maintenance):
    return SimpleNamespace(hotel_id=hotel_id, total_rooms=total, available_rooms=available,
                           occupied_rooms=occupied, maintenance_rooms=maintenance)


class RecordCounterTest(unittest.TestCase):
    def test_status_change_moves_one_room_between_columns(self):
        session = RecordingSession()
        room_stats_service.record_status_change(session, "MT_001", "AVAILABLE", "OCCUPIED")
        # (total, available, occupied, maintenance, hotel_id)
        self.assertEqual(session.counter_updates(), [(0, -1, 1, 0, "MT_001")])

    def test_room_created_adds_to_total_and_available(self):
        session = RecordingSession()
        room_stats_service.record_room_created(session, "MT_001")
        self.assertEqual(session.counter_updates(), [(1, 1, 0, 0, "MT_001")])

    def test_counter_error_never_raises(self):
        """Ghi counter lỗi chỉ được cảnh báo — không được làm hỏng luồng đặt/trả phòng."""
        broken = MagicMock()
        broken.prepare.side_effect = RuntimeError("unconfigured table room_status_counts_by_hotel")
        self.assertFalse(room_stats_service.record_status_change(broken, "MT_001", "OCCUPIED", "AVAILABLE"))

    def test_get_counts_returns_none_when_table_missing_or_empty(self):
        broken = MagicMock()
        broken.execute.side_effect = RuntimeError("unconfigured table")
        self.assertIsNone(room_stats_service.get_counts(broken))
        self.assertIsNone(room_stats_service.get_counts(RecordingSession()))


class RoomServiceHookTest(unittest.TestCase):
    def test_create_room_increments_counter(self):
        session = RecordingSession()
        with patch.object(room_service, "get_session", return_value=session):
            self.assertTrue(room_service.create_room("MT_001", "999", "Deluxe", 1000000, 2, "King"))
        self.assertEqual(session.counter_updates(), [(1, 1, 0, 0, "MT_001")])

    def test_failed_room_update_does_not_touch_counter(self):
        broken = MagicMock()
        broken.prepare.side_effect = RuntimeError("write timeout")
        room = SimpleNamespace(hotel_id="MT_001", room_number="101", status="AVAILABLE")
        with patch.object(room_service, "get_session", return_value=broken), \
             patch.object(room_service, "get_room", return_value=room), \
             patch.object(room_stats_service, "record_status_change") as record:
            ok, _ = room_service.change_room_status("MT_001", "101", "MAINTENANCE")
        self.assertFalse(ok)
        record.assert_not_called()


class ReconcileTest(unittest.TestCase):
    def _session(self, counters):
        return RecordingSession(select_rows={
            "FROM hotels": [SimpleNamespace(hotel_id="MT_001"), SimpleNamespace(hotel_id="MT_002")],
            "FROM rooms_by_hotel": [
                SimpleNamespace(hotel_id="MT_001", is_available=True, status="AVAILABLE"),
                SimpleNamespace(hotel_id="MT_001", is_available=False, status="OCCUPIED"),
                SimpleNamespace(hotel_id="MT_002", is_available=False, status="MAINTENANCE"),
                # Dòng cũ chưa có cột status -> suy từ is_available
                SimpleNamespace(hotel_id="MT_002", is_available=True, status=None),
            ],
            "FROM room_status_counts_by_hotel": counters,
        })

    def test_reconcile_applies_only_the_difference(self):
        session = self._session([
            _counter_row("MT_001", 2, 1, 1, 0),          # đã đúng
            _counter_row("MT_002", 1, 0, 0, 1),          # thiếu 1 phòng trống
            _counter_row("H_DELETED", 5, 5, 0, 0),       # khách sạn đã xóa
        ])
        drifted, orphans = room_stats_service.reconcile(session)

        self.assertEqual(drifted, [("MT_002", {"total_rooms": 1, "available_rooms": 1,
                                               "occupied_rooms": 0, "maintenance_rooms": 0})])
        self.assertEqual(session.counter_updates(), [(1, 1, 0, 0, "MT_002")])
        self.assertEqual(orphans, ["H_DELETED"])
        self.assertIn(("H_DELETED",), [p for q, p in session.executed if q.startswith("DELETE")])

    def test_check_mode_writes_nothing(self):
        session = self._session([])
        drifted, _ = room_stats_service.reconcile(session, apply=False)
        self.assertEqual(len(drifted), 2)
        self.assertEqual(session.counter_updates(), [])


class DashboardReadsCounterTest(unittest.TestCase):
    def test_dashboard_uses_counter_table_not_room_scan(self):
        session = MagicMock()
        session.execute.side_effect = [
            [SimpleNamespace(hotel_id="MT_001", name="A"), SimpleNamespace(hotel_id="MT_002", name="B")],
            [_counter_row("MT_001", 20, 1, 19, 0), _counter_row("MT_002", 10, 7, 1, 2),
             _counter_row("H_DELETED", 9, 9, 0, 0)],
            [],  # bookings_by_guest
            [],  # guests
            [],  # invoices_by_booking
        ]
        with patch.object(dashboard_service, "get_session", return_value=session):
            stats = dashboard_service.get_dashboard_stats()

        queries = [c.args[0] for c in session.execute.call_args_list]
        self.assertFalse(any("FROM rooms_by_hotel" in q for q in queries),
                         "đã có counter thì không được quét rooms_by_hotel")
        self.assertEqual((stats["total_rooms"], stats["available_rooms"],
                          stats["occupied_rooms"], stats["maintenance_rooms"]), (30, 8, 20, 2))


if __name__ == "__main__":
    unittest.main()
