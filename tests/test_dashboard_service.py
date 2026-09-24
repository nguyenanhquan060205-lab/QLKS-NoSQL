import unittest
from types import SimpleNamespace
from unittest.mock import patch, MagicMock
from datetime import date
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
                # Khách sạn thêm từ giao diện có mã "H" + uuid, vẫn phải được đếm
                SimpleNamespace(hotel_id="H1A2B3C4D"),
            ],
            # rooms_by_hotel
            [
                SimpleNamespace(hotel_id="MT_001", is_available=True, status="AVAILABLE"),
                SimpleNamespace(hotel_id="MT_002", is_available=True, status="AVAILABLE"),
                SimpleNamespace(hotel_id="H1A2B3C4D", is_available=False, status="OCCUPIED"),
                SimpleNamespace(hotel_id="MT_001", is_available=False, status="MAINTENANCE"),
                # Phòng mồ côi của khách sạn đã bị xóa -> không đếm
                SimpleNamespace(hotel_id="H_DELETED", is_available=True, status="AVAILABLE"),
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
        self.assertEqual(stats["total_hotels"], 3)  # MT_001, MT_002, H1A2B3C4D
        self.assertEqual(stats["total_rooms"], 4)
        self.assertEqual(stats["available_rooms"], 2)
        self.assertEqual(stats["occupied_rooms"], 1)
        self.assertEqual(stats["maintenance_rooms"], 1)
        self.assertEqual(stats["total_bookings"], 3)
        self.assertEqual(stats["total_guests"], 2)
        self.assertEqual(stats["total_invoices"], 2)
        self.assertEqual(stats["total_revenue"], 4000000.0)


def _booking(booking_id, check_in, check_out, amount, status="CONFIRMED"):
    return SimpleNamespace(
        booking_id=booking_id, hotel_id="MT_001", status=status,
        check_in_date=check_in, check_out_date=check_out, total_amount=Decimal(amount),
    )


class DashboardPeriodTest(unittest.TestCase):
    """Lọc kỳ theo thời gian lưu trú, ADR tính trên cùng một tập booking."""

    def _report(self, bookings, invoices=(), start="2026-09-01", end="2026-09-30"):
        session = MagicMock()
        session.execute.side_effect = [
            [SimpleNamespace(hotel_id="MT_001", name="Mường Thanh Hà Nội")],
            [],  # rooms_by_hotel
            list(bookings),
            [],  # guests
            list(invoices),
        ]
        with patch("services.dashboard_service.get_session", return_value=session):
            return dashboard_service.get_dashboard_report(
                period="custom", custom_start=start, custom_end=end,
            )

    def test_stay_crossing_period_start_is_counted(self):
        # 29/08 -> 02/09: chỉ đêm 01/09 thuộc tháng 9 (ngày trả phòng không tính đêm)
        stats = self._report([_booking("BK1", date(2026, 8, 29), date(2026, 9, 2), "4000000")])
        self.assertEqual(stats["total_bookings"], 1)
        # 4 đêm, 1.000.000/đêm; đêm 01/09 thuộc kỳ -> ADR = 1.000.000
        self.assertEqual(stats["adr"], 1000000)

    def test_last_night_of_period_is_counted(self):
        # 30/09 -> 02/10: đêm 30/09 thuộc tháng 9, đêm 01/10 thì không
        stats = self._report([_booking("BK1", date(2026, 9, 30), date(2026, 10, 2), "3000000")])
        self.assertEqual(stats["total_bookings"], 1)
        self.assertEqual(stats["adr"], 1500000)

    def test_stay_ending_on_period_start_is_excluded(self):
        # Trả phòng đúng 01/09 -> không có đêm nào trong tháng 9
        stats = self._report([_booking("BK1", date(2026, 8, 28), date(2026, 9, 1), "3000000")])
        self.assertEqual(stats["total_bookings"], 0)
        self.assertIsNone(stats["adr"])

    def test_adr_does_not_mix_invoice_revenue(self):
        # Hóa đơn xuất trong kỳ của một booking ngoài kỳ không được làm lệch ADR
        stats = self._report(
            [_booking("BK1", date(2026, 9, 10), date(2026, 9, 12), "2000000")],
            invoices=[SimpleNamespace(
                invoice_id="INV9", booking_id="BK_OTHER", hotel_id="MT_001",
                issue_date=date(2026, 9, 15), total_amount=Decimal("9000000"),
            )],
        )
        self.assertEqual(stats["total_revenue"], 9000000.0)
        self.assertEqual(stats["adr"], 1000000)

    def test_cancelled_booking_is_ignored(self):
        stats = self._report([
            _booking("BK1", date(2026, 9, 10), date(2026, 9, 12), "2000000"),
            _booking("BK2", date(2026, 9, 10), date(2026, 9, 12), "8000000", status="CANCELLED"),
        ])
        self.assertEqual(stats["total_bookings"], 1)
        self.assertEqual(stats["adr"], 1000000)


if __name__ == "__main__":
    unittest.main()
