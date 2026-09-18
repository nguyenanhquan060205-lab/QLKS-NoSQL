import unittest
from types import SimpleNamespace
from unittest.mock import patch, MagicMock
from decimal import Decimal

from services import dashboard_service


class DashboardServiceTest(unittest.TestCase):
    """Kiểm tra logic tổng hợp số liệu thống kê Dashboard & Trang chủ."""

    @patch("services.dashboard_service.get_session")
    def test_get_dashboard_stats_empty_fallback(self, mock_get_session):
        mock_get_session.return_value = None
        stats = dashboard_service.get_dashboard_stats()
        self.assertEqual(stats["total_hotels"], 0)
        self.assertEqual(stats["total_rooms"], 0)
        self.assertEqual(stats["available_rooms"], 0)
        self.assertEqual(stats["occupied_rooms"], 0)
        self.assertEqual(stats["maintenance_rooms"], 0)
        self.assertEqual(stats["total_bookings"], 0)
        self.assertEqual(stats["total_invoices"], 0)
        self.assertEqual(stats["total_revenue"], 0)

    @patch("services.dashboard_service.get_session")
    def test_get_dashboard_stats_calculates_correct_breakdown(self, mock_get_session):
        mock_session = MagicMock()
        mock_get_session.return_value = mock_session

        # 1. hotels
        mock_session.execute.side_effect = [
            # hotels
            [
                SimpleNamespace(hotel_id="MT_001"),
                SimpleNamespace(hotel_id="MT_002"),
                SimpleNamespace(hotel_id="H_QLKS04_TEST"),  # test hotel excluded from count
            ],
            # rooms_by_hotel
            [
                SimpleNamespace(is_available=True, status="AVAILABLE"),
                SimpleNamespace(is_available=True, status="AVAILABLE"),
                SimpleNamespace(is_available=False, status="OCCUPIED"),
                SimpleNamespace(is_available=False, status="MAINTENANCE"),
            ],
            # bookings_by_guest
            [
                SimpleNamespace(booking_id="BK01"),
                SimpleNamespace(booking_id="BK02"),
                SimpleNamespace(booking_id="BK03"),
            ],
            # guests
            [
                SimpleNamespace(guest_id="G_001"),
                SimpleNamespace(guest_id="G_002"),
            ],
            # invoices_by_booking
            [
                SimpleNamespace(total_amount=Decimal("1500000")),
                SimpleNamespace(total_amount=Decimal("2500000")),
            ]
        ]

        stats = dashboard_service.get_dashboard_stats()
        self.assertEqual(stats["total_hotels"], 2)  # MT_001, MT_002
        self.assertEqual(stats["total_rooms"], 4)
        self.assertEqual(stats["available_rooms"], 2)
        self.assertEqual(stats["occupied_rooms"], 1)
        self.assertEqual(stats["maintenance_rooms"], 1)
        self.assertEqual(stats["total_bookings"], 3)
        self.assertEqual(stats["total_guests"], 2)
        self.assertEqual(stats["total_invoices"], 2)
        self.assertEqual(stats["total_revenue"], 4000000.0)


if __name__ == "__main__":
    unittest.main()
