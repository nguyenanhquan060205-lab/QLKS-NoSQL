#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script xuất báo cáo PDF toàn diện về Dự án Quản lý Khách sạn NoSQL:
- Phân công của Quân (QN) từ DB đến UI
- Toàn bộ các Query Đặt phòng & Hóa đơn
- Tư duy ngược lại: Tại sao lại thiết kế Query & NoSQL như vậy
Hỗ trợ đầy đủ tiếng Việt có dấu qua font hệ thống macOS (Arial/Arial-Bold).
"""

import os
import sys
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Đăng ký font hỗ trợ tiếng Việt
FONT_REGULAR = "Arial"
FONT_BOLD = "Arial-Bold"
FONT_ITALIC = "Arial-Italic"

try:
    pdfmetrics.registerFont(TTFont('Arial', '/System/Library/Fonts/Supplemental/Arial.ttf'))
    pdfmetrics.registerFont(TTFont('Arial-Bold', '/System/Library/Fonts/Supplemental/Arial Bold.ttf'))
    pdfmetrics.registerFont(TTFont('Arial-Italic', '/System/Library/Fonts/Supplemental/Arial Italic.ttf'))
except Exception as e:
    print(f"Lỗi đăng ký font: {e}")
    sys.exit(1)


class NumberedCanvas(canvas.Canvas):
    """Canvas tùy biến để đánh số trang kiểu 'Trang X / Y' và vẽ Header/Footer."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_header_footer(num_pages)
            super().showPage()
        super().save()

    def draw_header_footer(self, page_count):
        self.saveState()
        self.setFont("Arial", 8)
        self.setFillColor(colors.HexColor("#64748b")) # slate-500

        # Header (chỉ vẽ từ trang 2 trở đi)
        if self._pageNumber > 1:
            self.drawString(36, 810, "BÁO CÁO TOÀN DIỆN DỰ ÁN QLKS NOSQL (CASSANDRA / ASTRADB) — NGUYỄN ANH QUÂN (QN)")
            self.setStrokeColor(colors.HexColor("#e2e8f0"))
            self.setLineWidth(0.5)
            self.line(36, 804, 559, 804)

        # Footer (mọi trang)
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(36, 40, 559, 40)

        self.drawString(36, 28, "ĐH Công Thương TP.HCM (HUIT) — Học phần: Cơ sở dữ liệu NoSQL")
        page_str = f"Trang {self._pageNumber} / {page_count}"
        self.drawRightString(559, 28, page_str)
        self.restoreState()


def build_pdf(filename="BAO_CAO_TOAN_BO_QUERY_VA_TU_DUY_NOSQL.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=46,
        bottomMargin=46
    )

    styles = getSampleStyleSheet()

    # Định nghĩa các styles chuẩn tiếng Việt
    title_style = ParagraphStyle(
        'DocTitle',
        fontName='Arial-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0f172a"),
        alignment=1, # Center
        spaceAfter=8
    )

    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        fontName='Arial-Bold',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#b45309"), # amber-700
        alignment=1,
        spaceAfter=14
    )

    h1_style = ParagraphStyle(
        'H1',
        fontName='Arial-Bold',
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'H2',
        fontName='Arial-Bold',
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor("#0369a1"), # sky-700
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'Body',
        fontName='Arial',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#334155"),
        spaceAfter=5
    )

    body_bold = ParagraphStyle(
        'BodyBold',
        fontName='Arial-Bold',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=4
    )

    code_style = ParagraphStyle(
        'CodeBlock',
        fontName='Arial',
        fontSize=7.5,
        leading=10.5,
        textColor=colors.HexColor("#0f172a"),
        backColor=colors.HexColor("#f1f5f9"),
        borderColor=colors.HexColor("#cbd5e1"),
        borderWidth=0.5,
        borderPadding=5,
        spaceBefore=3,
        spaceAfter=5
    )

    callout_style = ParagraphStyle(
        'Callout',
        fontName='Arial-Italic',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#1e293b"),
        backColor=colors.HexColor("#fef3c7"), # amber-100
        borderColor=colors.HexColor("#f59e0b"),
        borderWidth=1,
        borderPadding=6,
        spaceBefore=5,
        spaceAfter=8
    )

    story = []

    # 1. TIÊU ĐỀ BÁO CÁO
    story.append(Paragraph("BÁO CÁO TOÀN DIỆN DỰ ÁN QUẢN LÝ KHÁCH SẠN NOSQL", title_style))
    story.append(Paragraph("KIẾN TRÚC HỆ THỐNG — PHẦN VIỆC NGUYỄN ANH QUÂN (QN) TỪ DB ĐẾN UI<br/>VÀ TƯ DUY THIẾT KẾ TRUY VẤN CƠ SỞ DỮ LIỆU CASSANDRA / ASTRADB", subtitle_style))

    # Thông tin sinh viên & đồ án
    info_data = [
        [
            Paragraph("<b>Sinh viên phụ trách:</b> Nguyễn Anh Quân (<b>QN</b>)", body_style),
            Paragraph("<b>Học phần:</b> Cơ sở dữ liệu NoSQL — HUIT", body_style)
        ],
        [
            Paragraph("<b>Phạm vi phụ trách:</b> Đặt phòng, Giao dịch BATCH & Hóa đơn", body_style),
            Paragraph("<b>Trọng số Sprint:</b> 13 SP (~37.5% toàn hệ thống)", body_style)
        ],
        [
            Paragraph("<b>Công nghệ:</b> AstraDB Cloud, Python Flask, Tailwind v4", body_style),
            Paragraph("<b>Kết quả Test:</b> 94/94 Unit Tests PASS · 79/79 E2E PASS", body_style)
        ]
    ]
    t_info = Table(info_data, colWidths=[260, 260])
    t_info.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_info)
    story.append(Spacer(1, 10))

    # PHẦN 1: TỔNG QUAN HỆ THỐNG & CÁC LUỒNG VẬN HÀNH
    story.append(Paragraph("1. TỔNG QUAN HỆ THỐNG VÀ CÁC LUỒNG VẬN HÀNH (WORKFLOWS)", h1_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284c7"), spaceAfter=6))

    story.append(Paragraph("<b>1.1. Kiến trúc phân tầng 3 lớp (3-Tier Distributed Architecture):</b>", body_bold))
    arch_desc = """
    Hệ thống được thiết kế theo kiến trúc chuẩn Web Doanh nghiệp kết hợp Cơ sở dữ liệu phân tán NoSQL:
    <br/>• <b>Tầng Giao diện (Presentation Layer):</b> Trình duyệt web render HTML5 qua Jinja2 Templates, giao diện hiện đại xây dựng trên Tailwind CSS v4, tối ưu hiển thị dạng Canvas rộng (Full-width), tích hợp biểu đồ Chart.js trực quan.
    <br/>• <b>Tầng Điều khiển & Dịch vụ (Controller & Service Layer):</b> Xây dựng trên Python Flask chia thành 3 Blueprint độc lập (hotel_bp, booking_bp, dashboard_bp). Tầng Service đóng gói toàn bộ Prepared Statements, cơ chế Cache In-Memory TTL 30s và xử lý tính toán số đêm, doanh thu, thanh toán cọc.
    <br/>• <b>Tầng Cơ sở dữ liệu phân tán (Distributed Database Layer):</b> Cụm Cassandra trên nền tảng DataStax AstraDB Cloud, kết nối bảo mật qua Secure Connect Bundle Singleton (get_session()). Gồm 6 bảng phục vụ chính xác 5 câu hỏi nghiệp vụ (Query Q1 đến Q5).
    """
    story.append(Paragraph(arch_desc, body_style))

    story.append(Spacer(1, 4))
    story.append(Paragraph("<b>1.2. Ba luồng nghiệp vụ cốt lõi xuyên suốt hệ thống:</b>", body_bold))
    wf_text = """
    <b>1. Luồng Đặt phòng mới (Booking Flow):</b> Người dùng tìm kiếm phòng trống theo bộ lọc đa tiêu chí tại <code>/bookings</code> -> Bấm đặt phòng -> Modal tự tính tiền theo số đêm và chọn cọc (100%, 50%, 0%) -> Hệ thống chạy <b>Query Q5 (Atomic BATCH)</b> ghi đồng thời vào <code>bookings_by_guest</code> và <code>bookings_by_hotel_date</code> -> Tự động sinh hóa đơn <code>invoices_by_booking</code> (Q4) -> Chuyển trạng thái phòng sang <code>OCCUPIED</code>, lưu tên khách và mã booking -> Xóa cache -> Điều hướng đến Hóa đơn để in ấn.
    <br/><b>2. Luồng Thu tiền còn lại (Settlement Flow):</b> Lọc hóa đơn có trạng thái <code>PARTIAL</code> tại <code>/invoices</code> -> Bấm 'Thu tiền còn lại' -> Hệ thống cập nhật bảng hóa đơn: <code>payment_status = 'PAID'</code>, <code>deposit_amount = total_amount</code>, <code>remaining_amount = 0</code> -> Cập nhật phương thức thanh toán -> Invalidate cache.
    <br/><b>3. Luồng Trả phòng & Trả sớm (Check-out Flow):</b> Lễ tân bấm 'Trả phòng' tại trang chi tiết phòng -> Hệ thống kiểm tra nếu khách trả sớm hơn dự kiến thì ghi lại ngày trả thực tế vào <code>check_out_date</code> ở bảng khách để thống kê số đêm chuẩn (không hoàn tiền, hóa đơn giữ nguyên) -> BATCH UPDATE chuyển trạng thái booking sang <code>COMPLETED</code> ở cả 2 bảng -> Giải phóng phòng về <code>AVAILABLE</code>, xóa tên khách cũ về <code>NULL</code>.
    """
    story.append(Paragraph(wf_text, body_style))

    story.append(Spacer(1, 8))

    # PHẦN 2: PHÂN CÔNG PHẦN VIỆC CỦA NGUYỄN ANH QUÂN (QN)
    story.append(Paragraph("2. CHI TIẾT PHẦN VIỆC CỦA NGUYỄN ANH QUÂN (QN) TỪ DB ĐẾN UI", h1_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284c7"), spaceAfter=6))

    task_table_data = [
        [Paragraph("<b>Tầng kiến trúc</b>", body_bold), Paragraph("<b>Nhiệm vụ cụ thể (Tasks)</b>", body_bold), Paragraph("<b>Mã nguồn phụ trách</b>", body_bold), Paragraph("<b>Kết quả đạt được</b>", body_bold)],
        [
            Paragraph("<b>Database<br/>(CQL Schema)</b>", body_style),
            Paragraph("• Tạo bảng <code>bookings_by_guest</code> (Q2)<br/>• Tạo bảng <code>bookings_by_hotel_date</code> (Q3)<br/>• Tạo bảng <code>invoices_by_booking</code> (Q4)<br/>• Mở rộng cột cọc: <code>deposit_amount</code>, <code>remaining_amount</code>", body_style),
            Paragraph("<code>cql/schema.cql</code><br/>(Dòng 74–111)", body_style),
            Paragraph("Mô hình dữ liệu phi chuẩn hóa tối ưu, khóa chính chuẩn xác, không quét toàn bảng.", body_style)
        ],
        [
            Paragraph("<b>Service Layer<br/>(Business Logic)</b>", body_style),
            Paragraph("• Cài đặt BATCH INSERT Q5<br/>• Truy vấn lịch sử khách Q2<br/>• Truy vấn lễ tân theo ngày Q3<br/>• Tra cứu & tạo hóa đơn Q4<br/>• Thu nốt tiền cọc (Settle payment)<br/>• BATCH UPDATE trả phòng sớm<br/>• In-Memory Caching TTL 30s", body_style),
            Paragraph("<code>services/<br/>booking_service.py</code><br/>(1.320 dòng code)", body_style),
            Paragraph("Ghi đồng thời nguyên tử, giải quyết bài toán tính nhất quán dữ liệu phân tán, xử lý ngoại lệ và fallback an toàn.", body_style)
        ],
        [
            Paragraph("<b>Controller<br/>(Flask Routes)</b>", body_style),
            Paragraph("• 13 Route Endpoints (Web forms & JSON APIs)<br/>• API phòng trống theo khách sạn<br/>• API chi tiết phòng & booking đang ở<br/>• Xử lý Validation ràng buộc ngày đi > ngày đến, chặn trùng phòng bận", body_style),
            Paragraph("<code>routes/<br/>booking_routes.py</code><br/>(860 dòng code)", body_style),
            Paragraph("Điều hướng mượt mà, phân tách rõ ràng giữa Web View và RESTful API cho modal.", body_style)
        ],
        [
            Paragraph("<b>UI / Frontend<br/>(Templates)</b>", body_style),
            Paragraph("• <code>bookings.html</code>: Bộ lọc phòng 5 tiêu chí, Modal đặt phòng, Bảng lịch sử đặt phòng<br/>• <code>invoices.html</code>: Phiếu hóa đơn cao cấp nhận diện Mường Thanh, Bảng quản lý hóa đơn, Modal thu tiền cọc", body_style),
            Paragraph("<code>templates/<br/>bookings.html<br/>invoices.html</code>", body_style),
            Paragraph("Giao diện sắc nét, chuẩn responsive, có nút In hóa đơn trực tiếp, trạng thái màu sắc rõ ràng.", body_style)
        ]
    ]

    t_task = Table(task_table_data, colWidths=[75, 185, 110, 150])
    t_task.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f1f5f9")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_task)

    story.append(Spacer(1, 10))

    # PHẦN 3: BẢNG KÊ CỨU TOÀN BỘ TRUY VẤN
    story.append(Paragraph("3. BẢNG KÊ CỨU TOÀN BỘ CÁC TRUY VẤN CQL VỀ ĐẶT PHÒNG & HÓA ĐƠN", h1_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284c7"), spaceAfter=6))

    story.append(Paragraph("<b>QUERY 1 & 2: DDL Khởi tạo bảng dữ liệu Đặt phòng (bookings_by_guest & bookings_by_hotel_date)</b>", h2_style))
    cql_q12 = """-- Bảng 4: Lịch sử theo khách (Query Q2: PK = guest_id, CK = booking_id)
CREATE TABLE IF NOT EXISTS bookings_by_guest (
    guest_id text, booking_id text, hotel_id text, room_number text,
    check_in_date date, check_out_date date, status text, total_amount decimal,
    PRIMARY KEY (guest_id, booking_id)
);

-- Bảng 5: Lịch sử theo khách sạn và ngày (Query Q3: Composite PK = ((hotel_id, check_in_date)), CK = booking_id)
CREATE TABLE IF NOT EXISTS bookings_by_hotel_date (
    hotel_id text, check_in_date date, booking_id text,
    guest_id text, guest_name text, room_number text, status text,
    PRIMARY KEY ((hotel_id, check_in_date), booking_id)
);"""
    story.append(Paragraph(cql_q12.replace("\n", "<br/>").replace(" ", "&nbsp;"), code_style))

    story.append(Paragraph("<b>QUERY 3: DDL Khởi tạo bảng Hóa đơn thanh toán (invoices_by_booking - Query Q4)</b>", h2_style))
    cql_q3 = """-- Bảng 6: Hóa đơn theo đơn đặt phòng (PK = booking_id, CK = invoice_id)
CREATE TABLE IF NOT EXISTS invoices_by_booking (
    booking_id text, invoice_id text, guest_name text, hotel_id text,
    issue_date date, payment_method text, payment_status text, total_amount decimal,
    deposit_amount decimal, remaining_amount decimal,
    PRIMARY KEY (booking_id, invoice_id)
);"""
    story.append(Paragraph(cql_q3.replace("\n", "<br/>").replace(" ", "&nbsp;"), code_style))

    story.append(Paragraph("<b>QUERY 4: [TRỌNG TÂM ĐỒ ÁN] Atomic BATCH INSERT Đặt phòng (Query Q5 Đề Cương)</b>", h2_style))
    cql_q5 = """BEGIN BATCH
  INSERT INTO bookings_by_guest (guest_id, booking_id, hotel_id, room_number,
                                check_in_date, check_out_date, status, total_amount)
  VALUES (?, ?, ?, ?, ?, ?, ?, ?);

  INSERT INTO bookings_by_hotel_date (hotel_id, check_in_date, booking_id,
                                     guest_id, guest_name, room_number, status)
  VALUES (?, ?, ?, ?, ?, ?, ?);
APPLY BATCH;"""
    story.append(Paragraph(cql_q5.replace("\n", "<br/>").replace(" ", "&nbsp;"), code_style))
    story.append(Paragraph("<b>Vị trí cài đặt:</b> <code>services/booking_service.py</code> hàm <code>create_booking_batch(...)</code> (dòng 80–110). Dùng <code>BatchStatement()</code> của Cassandra driver để đảm bảo dữ liệu ghi đồng thời vào cả 2 bảng phân tán.", body_style))

    story.append(Paragraph("<b>QUERY 5: Tra cứu lịch sử đặt phòng theo khách hàng (Query Q2 Đề Cương)</b>", h2_style))
    cql_q2 = """SELECT guest_id, booking_id, hotel_id, room_number,
       check_in_date, check_out_date, status, total_amount
FROM bookings_by_guest
WHERE guest_id = ?;"""
    story.append(Paragraph(cql_q2.replace("\n", "<br/>").replace(" ", "&nbsp;"), code_style))
    story.append(Paragraph("<b>Vị trí cài đặt:</b> <code>services/booking_service.py</code> hàm <code>get_bookings_by_guest(guest_id)</code> (dòng 256–290). Truy vấn O(1) theo Partition Key <code>guest_id</code>, không quét toàn bảng.", body_style))

    story.append(Paragraph("<b>QUERY 6: Tra cứu khách check-in theo khách sạn và ngày (Query Q3 Đề Cương)</b>", h2_style))
    cql_q3_stmt = """SELECT hotel_id, check_in_date, booking_id,
       guest_id, guest_name, room_number, status
FROM bookings_by_hotel_date
WHERE hotel_id = ? AND check_in_date = ?;"""
    story.append(Paragraph(cql_q3_stmt.replace("\n", "<br/>").replace(" ", "&nbsp;"), code_style))
    story.append(Paragraph("<b>Vị trí cài đặt:</b> <code>services/booking_service.py</code> hàm <code>get_bookings_by_hotel_date(hotel_id, check_in_date)</code> (dòng 296–343). Truy vấn O(1) theo Composite Partition Key <code>(hotel_id, check_in_date)</code>.", body_style))

    story.append(Paragraph("<b>QUERY 7 & 8: Tạo mới và Tra cứu chi tiết hóa đơn thanh toán (Query Q4 Đề Cương)</b>", h2_style))
    cql_q4_stmt = """-- 1. Tạo hóa đơn kèm quản lý đặt cọc
INSERT INTO invoices_by_booking (
    booking_id, invoice_id, guest_name, hotel_id,
    issue_date, payment_method, payment_status, total_amount,
    deposit_amount, remaining_amount
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);

-- 2. Tra cứu chi tiết hóa đơn theo mã đặt phòng
SELECT booking_id, invoice_id, guest_name, hotel_id,
       issue_date, payment_method, payment_status, total_amount,
       deposit_amount, remaining_amount
FROM invoices_by_booking
WHERE booking_id = ?;"""
    story.append(Paragraph(cql_q4_stmt.replace("\n", "<br/>").replace(" ", "&nbsp;"), code_style))
    story.append(Paragraph("<b>Vị trí cài đặt:</b> <code>create_invoice(...)</code> (dòng 406–560) và <code>get_invoice_by_booking(booking_id)</code> (dòng 349–404).", body_style))

    story.append(Paragraph("<b>QUERY 9: Cập nhật thanh toán nốt tiền cọc (Settle Payment)</b>", h2_style))
    cql_settle = """UPDATE invoices_by_booking
SET payment_status = ?, deposit_amount = ?, remaining_amount = ?, payment_method = ?
WHERE booking_id = ? AND invoice_id = ?;"""
    story.append(Paragraph(cql_settle.replace("\n", "<br/>").replace(" ", "&nbsp;"), code_style))
    story.append(Paragraph("<b>Vị trí cài đặt:</b> <code>settle_invoice_payment(...)</code> (dòng 1071–1186). Cập nhật sang PAID khi khách đóng nốt số tiền còn lại.", body_style))

    story.append(Paragraph("<b>QUERY 10: Đóng booking khi khách trả phòng bằng BATCH UPDATE (Trả phòng sớm)</b>", h2_style))
    cql_complete = """BEGIN BATCH
  -- Cập nhật bảng khách (ghi nhận ngày trả thực tế nếu trả sớm)
  UPDATE bookings_by_guest SET status = 'COMPLETED', check_out_date = ?
  WHERE guest_id = ? AND booking_id = ?;

  -- Cập nhật bảng lễ tân
  UPDATE bookings_by_hotel_date SET status = 'COMPLETED'
  WHERE hotel_id = ? AND check_in_date = ? AND booking_id = ?;
APPLY BATCH;"""
    story.append(Paragraph(cql_complete.replace("\n", "<br/>").replace(" ", "&nbsp;"), code_style))
    story.append(Paragraph("<b>Vị trí cài đặt:</b> <code>complete_booking(...)</code> (dòng 1194–1320). Đồng bộ trạng thái COMPLETED ở cả 2 bảng, không giảm giá và không hoàn tiền.", body_style))

    story.append(Paragraph("<b>QUERY 11: Cập nhật phòng khi Đặt và khi Trả phòng (rooms_by_hotel)</b>", h2_style))
    cql_room = """-- Khi Đặt phòng thành công:
UPDATE rooms_by_hotel
SET status = 'OCCUPIED', is_available = false, current_guest_name = ?, current_booking_id = ?
WHERE hotel_id = ? AND room_number = ?;

-- Khi Khách trả phòng (Giải phóng phòng trống):
UPDATE rooms_by_hotel
SET status = 'AVAILABLE', is_available = true, current_guest_name = null, current_booking_id = null
WHERE hotel_id = ? AND room_number = ?;"""
    story.append(Paragraph(cql_room.replace("\n", "<br/>").replace(" ", "&nbsp;"), code_style))

    story.append(Spacer(1, 10))

    # PHẦN 4: TƯ DUY NGƯỢC LẠI: TẠI SAO LẠI THIẾT KẾ NHƯ VẬY?
    story.append(Paragraph("4. TƯ DUY NGƯỢC LẠI: TẠI SAO LẠI THIẾT KẾ QUERY & DỮ LIỆU NHƯ VẬY?", h1_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284c7"), spaceAfter=6))

    why_data = [
        [
            Paragraph("<b>Câu hỏi bản chất</b>", body_bold),
            Paragraph("<b>Cách làm & Hạn chế của SQL (RDBMS)</b>", body_bold),
            Paragraph("<b>Tư duy & Giải pháp trong Cassandra (NoSQL)</b>", body_bold)
        ],
        [
            Paragraph("<b>1. Tại sao có 2 bảng Đặt phòng thay vì 1?</b>", body_style),
            Paragraph("Dùng 1 bảng <code>bookings</code>. Khi cần xem lịch sử khách hay lễ tân thì dùng lệnh <code>SELECT ... WHERE ...</code> và tạo Secondary Index.", body_style),
            Paragraph("Cassandra phân tán dữ liệu theo hash Partition Key. Không có JOIN. Nếu dùng 1 bảng mà query không đúng Partition Key sẽ bị <b>Full Cluster Scan</b> làm sập hệ thống. Tách 2 bảng (Denormalization) giúp cả 2 góc nhìn đều đạt tốc độ $O(1)$ (< 5ms).", body_style)
        ],
        [
            Paragraph("<b>2. Tại sao bắt buộc dùng BATCH STATEMENT?</b>", body_style),
            Paragraph("SQL dùng ACID Transaction (<code>BEGIN TRANSACTION ... COMMIT</code>). Dữ liệu chỉ nằm ở 1 bảng nên không lo lệch pha giữa các bảng trùng lặp.", body_style),
            Paragraph("Vì có 2 bảng lưu cùng 1 sự kiện đặt phòng, nếu chạy 2 lệnh INSERT rời, rủi ro sập mạng giữa chừng sẽ làm bảng khách có đơn mà bảng lễ tân không có. <code>BATCH</code> đảm bảo tính nguyên tử (Atomicity) trên cụm phân tán.", body_style)
        ],
        [
            Paragraph("<b>3. Tại sao bảng lễ tân dùng Composite Partition Key?</b>", body_style),
            Paragraph("SQL chỉ cần đánh chỉ mục (Index) trên cột <code>hotel_id</code> và <code>check_in_date</code>.", body_style),
            Paragraph("Nếu chỉ lấy <code>hotel_id</code> làm Partition Key, qua nhiều năm một khách sạn lớn sẽ gom hàng trăm nghìn dòng vào 1 Partition, vượt mốc 100MB khuyến nghị gây <b>Hotspot</b>. Dùng <code>((hotel_id, check_in_date))</code> giúp mỗi ngày là 1 partition nhỏ (~vài chục KB) siêu tốc.", body_style)
        ],
        [
            Paragraph("<b>4. Tại sao Denormalize tên khách vào phòng?</b>", body_style),
            Paragraph("Dùng lệnh <code>JOIN</code> giữa bảng <code>rooms</code>, <code>bookings</code> và <code>guests</code> để lấy tên khách đang ở.", body_style),
            Paragraph("Cassandra không có JOIN. Nếu không lưu sẵn tên khách vào dòng phòng đó, mỗi khi xem chi tiết phòng sẽ phải quét toàn bộ bảng đặt phòng. Denormalize <code>current_guest_name</code> giúp xem chi tiết phòng chỉ tốn đúng 1 lần đọc duy nhất!", body_style)
        ],
        [
            Paragraph("<b>5. Tại sao Trả phòng sớm không hoàn tiền?</b>", body_style),
            Paragraph("Tùy chính sách, thường tính lại số đêm thực tế và hoàn tiền thừa.", body_style),
            Paragraph("Theo quy chuẩn vận hành chuỗi Mường Thanh đã thống nhất: Khách trả sớm giữ phòng nên không giảm giá/hoàn tiền. Việc lưu ngày trả thực tế chỉ để tính chỉ số công suất phòng (Occupancy Rate/ADR) cho Dashboard.", body_style)
        ],
        [
            Paragraph("<b>6. Tại sao cần In-Memory Cache TTL 30s?</b>", body_style),
            Paragraph("SQL Server thường có buffer pool tự động trên RAM máy chủ.", body_style),
            Paragraph("AstraDB là Cloud DB tính phí theo Request Units và có độ trễ internet (network hop). Cache 30s ở RAM máy chủ web giúp người dùng load trang tức thì, giảm 80% truy vấn lặp lại vào cloud.", body_style)
        ]
    ]

    t_why = Table(why_data, colWidths=[120, 190, 210])
    t_why.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f1f5f9")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(t_why)

    story.append(Spacer(1, 10))

    # PHẦN 5: CẨM NANG BẢO VỆ ĐỒ ÁN
    story.append(Paragraph("5. CẨM NANG THUYẾT TRÌNH BẢO VỆ ĐỒ ÁN TRƯỚC HỘI ĐỒNG", h1_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284c7"), spaceAfter=6))

    tips = """
    <b>Ba câu nói then chốt giúp đạt điểm tối đa khi thầy cô hỏi phản biện:</b><br/>
    <b>1. Khi thầy cô hỏi 'Tại sao cơ sở dữ liệu lại có nhiều bảng trùng lặp dữ liệu thế này?':</b><br/>
    <i>'Thưa thầy cô, đây là nguyên lý cốt lõi của NoSQL Cassandra: <b>Query-First Design</b> và <b>Denormalization</b>. Trong RDBMS, ta chuẩn hóa 3NF để tiết kiệm ổ đĩa và dùng JOIN. Nhưng Cassandra là hệ CSDL phân tán quy mô lớn, không hỗ trợ JOIN vì JOIN qua mạng giữa các node sẽ gây nghẽn cổ chai. Do đó, ta thiết kế mỗi bảng chuyên biệt cho đúng một truy vấn đọc. Dung lượng ổ đĩa ngày nay rất rẻ, nhưng độ trễ truy vấn O(1) là yếu tố sống còn.'</i><br/><br/>
    <b>2. Khi thầy cô hỏi 'BATCH STATEMENT ở đây dùng để làm gì? Có giống Transaction trong SQL không?':</b><br/>
    <i>'Dạ thưa thầy cô, BATCH trong Cassandra dùng để đảm bảo tính nguyên tử (Atomicity) khi ghi đồng thời vào nhiều bảng phân tán (ở đây là <code>bookings_by_guest</code> và <code>bookings_by_hotel_date</code>). Cassandra sử dụng cơ chế batchlog trên coordinator node để đảm bảo hoặc cả hai bảng cùng được ghi hoặc nếu gặp sự cố mạng thì các node khác sẽ replay lại log, ngăn chặn hoàn toàn tình trạng mất đồng bộ dữ liệu.'</i><br/><br/>
    <b>3. Khi thầy cô hỏi 'Tại sao không dùng ALLOW FILTERING để tìm kiếm cho tiện?':</b><br/>
    <i>'Dạ thưa thầy cô, <code>ALLOW FILTERING</code> trong môi trường production của Cassandra là một anti-pattern nghiêm trọng. Nó bắt buộc Cassandra phải quét qua tất cả các node trong toàn cụm, gây ngốn CPU và timeout. Trong toàn bộ code của nhóm em, mọi câu lệnh truy vấn chính đều đánh thẳng vào Partition Key để đạt hiệu năng O(1).'</i>
    """
    story.append(Paragraph(tips, callout_style))

    # Xây dựng file PDF với NumberedCanvas
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"✅ Đã xuất báo cáo PDF thành công: {filename}")


if __name__ == "__main__":
    out_pdf = "BAO_CAO_TOAN_BO_QUERY_VA_TU_DUY_NOSQL.pdf"
    if len(sys.argv) > 1:
        out_pdf = sys.argv[1]
    build_pdf(out_pdf)
