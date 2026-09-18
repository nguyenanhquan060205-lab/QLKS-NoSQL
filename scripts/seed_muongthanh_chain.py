#!/usr/bin/env python3
"""
Seed script: Chuỗi Khách Sạn Mường Thanh Hospitality (Nội bộ)
- Dọn sạch các partition cũ trong 'hotels' và 'rooms_by_hotel'.
- Nạp đúng 40 chi nhánh Mường Thanh thực tế phủ kín 34/34 tỉnh thành trong docs/provinces.json.
- Phân khúc chuẩn:
  * Luxury (5 sao): 16 - 20 phòng
  * Grand (4 sao): 12 - 14 phòng
  * Holiday (3-4 sao resort/nghỉ dưỡng): 8 - 12 phòng
  * Boutique/Hospitality (Tiêu chuẩn vùng cao): 8 - 10 phòng
- Phòng đa dạng (Superior, Deluxe, Suite, Presidential) và trạng thái phong phú (AVAILABLE, OCCUPIED, MAINTENANCE).
"""

import sys
import os
from decimal import Decimal

# Thêm thư mục gốc vào PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.db import get_session

MUONG_THANH_BRANCHES = [
    # 01. Thành phố Hà Nội (HNI) - 2 chi nhánh
    {
        "id": "MT_001",
        "name": "Mường Thanh Luxury Hà Nội Centre",
        "city": "Thành phố Hà Nội",
        "address": "Số 78 Thợ Nhuộm, Phường Trần Hưng Đạo, Quận Hoàn Kiếm, Hà Nội",
        "phone": "02439428686",
        "tier": "MEGA_LUXURY",
        "room_count": 20,
        "amenities": {"Hồ bơi bốn mùa", "Phòng Gym & Yoga", "Nhà hàng Á - Âu", "Executive Lounge", "Trung tâm Hội nghị 1000 khách", "Spa Sen & Sauna", "Bãi đỗ xe ngầm"}
    },
    {
        "id": "MT_002",
        "name": "Mường Thanh Grand Hà Nội",
        "city": "Thành phố Hà Nội",
        "address": "Lô CC2, Khu đô thị Bắc Linh Đàm, Quận Hoàng Mai, Hà Nội",
        "phone": "02436408686",
        "tier": "LUXURY",
        "room_count": 16,
        "amenities": {"Hồ bơi trong nhà", "Phòng Gym", "Nhà hàng Yên Tử", "Phòng họp hội thảo", "Massage Sen Spa", "Bãi đỗ xe"}
    },

    # 02. Cao Bằng (CBG)
    {
        "id": "MT_003",
        "name": "Mường Thanh Luxury Cao Bằng",
        "city": "Cao Bằng",
        "address": "Số 42 Kim Đồng, Phường Hợp Giang, TP. Cao Bằng, Tỉnh Cao Bằng",
        "phone": "02063888088",
        "tier": "BOUTIQUE",
        "room_count": 10,
        "amenities": {"Nhà hàng Bản Giốc", "Phòng hội thảo Pác Bó", "Phòng Gym", "Khu Spa & Sauna", "Bãi đỗ xe"}
    },

    # 03. Tuyên Quang (TGQ)
    {
        "id": "MT_004",
        "name": "Mường Thanh Grand Tuyên Quang",
        "city": "Tuyên Quang",
        "address": "Số 207 đường Bình Thuận, Phường Tân Quang, TP. Tuyên Quang, Tỉnh Tuyên Quang",
        "phone": "02073812888",
        "tier": "BOUTIQUE",
        "room_count": 10,
        "amenities": {"Hồ bơi ngoài trời", "Nhà hàng Tân Trào", "Phòng Gym", "Karaoke & Bar", "Bãi đỗ xe"}
    },

    # 04. Điện Biên (DBN) - Cái nôi chuỗi Mường Thanh
    {
        "id": "MT_005",
        "name": "Mường Thanh Grand Điện Biên Phủ",
        "city": "Điện Biên",
        "address": "Số 514 đường Võ Nguyên Giáp, Phường Him Lam, TP. Điện Biên Phủ, Tỉnh Điện Biên",
        "phone": "02153810043",
        "tier": "GRAND",
        "room_count": 14,
        "amenities": {"Hồ bơi ngoài trời", "Nhà hàng Mường Phăng", "Phòng tiệc Him Lam", "Sân Tennis", "Spa Thái Dân tộc", "Bãi đỗ xe"}
    },

    # 05. Lai Châu (LCU)
    {
        "id": "MT_006",
        "name": "Mường Thanh Luxury Lai Châu",
        "city": "Lai Châu",
        "address": "Số 002 đường Lê Duẩn, Phường Tân Phong, TP. Lai Châu, Tỉnh Lai Châu",
        "phone": "02133798888",
        "tier": "BOUTIQUE",
        "room_count": 10,
        "amenities": {"Hồ bơi trong nhà", "Nhà hàng Pu Sam Cáp", "Phòng Gym", "Dịch vụ Massage & Xông hơi", "Bãi đỗ xe"}
    },

    # 06. Sơn La (SLA)
    {
        "id": "MT_007",
        "name": "Mường Thanh Luxury Mộc Châu",
        "city": "Sơn La",
        "address": "Đường Hoàng Quốc Việt, Thị trấn Nông trường Mộc Châu, Huyện Mộc Châu, Sơn La",
        "phone": "02122258886",
        "tier": "GRAND",
        "room_count": 12,
        "amenities": {"Hồ bơi vô cực ngắm đồi chè", "Nhà hàng Tây Bắc", "Phòng hội nghị Thảo Nguyên", "Sân Tennis", "Khu Spa & Tắm khoáng", "Bãi đỗ xe"}
    },

    # 07. Lào Cai (LCI)
    {
        "id": "MT_008",
        "name": "Mường Thanh Grand Lào Cai",
        "city": "Lào Cai",
        "address": "Số 086 đường Thanh Niên, Phường Duyên Hải, TP. Lào Cai, Tỉnh Lào Cai",
        "phone": "02143839888",
        "tier": "GRAND",
        "room_count": 12,
        "amenities": {"Hồ bơi 4 mùa", "Nhà hàng Fansipan", "Trung tâm Hội nghị Quốc tế", "Phòng Gym", "Spa & Sauna thảo dược", "Bãi đỗ xe"}
    },

    # 08. Thái Nguyên (TNN)
    {
        "id": "MT_009",
        "name": "Mường Thanh Grand Thái Nguyên",
        "city": "Thái Nguyên",
        "address": "Số 279 đường Lương Ngọc Quyến, Phường Hoàng Văn Thụ, TP. Thái Nguyên, Tỉnh Thái Nguyên",
        "phone": "02083855888",
        "tier": "GRAND",
        "room_count": 12,
        "amenities": {"Hồ bơi ngoài trời", "Nhà hàng Trà Xanh", "Phòng Gym", "Trung tâm tiệc cưới & sự kiện", "Massage Sen Spa", "Bãi đỗ xe"}
    },

    # 09. Lạng Sơn (LSN)
    {
        "id": "MT_010",
        "name": "Mường Thanh Luxury Lạng Sơn",
        "city": "Lạng Sơn",
        "address": "Số 68 đường Ngô Quyền, Phường Vĩnh Trại, TP. Lạng Sơn, Tỉnh Lạng Sơn",
        "phone": "02053866668",
        "tier": "GRAND",
        "room_count": 14,
        "amenities": {"Hồ bơi 4 mùa", "Nhà hàng Kỳ Cùng", "Phòng tiệc Mẫu Sơn", "Phòng Gym", "Spa & Karaoke", "Bãi đỗ xe"}
    },

    # 10. Quảng Ninh (QNH) - 2 chi nhánh
    {
        "id": "MT_011",
        "name": "Mường Thanh Luxury Hạ Long Centre",
        "city": "Quảng Ninh",
        "address": "Khu 2, Đường Hạ Long, Phường Bãi Cháy, TP. Hạ Long, Tỉnh Quảng Ninh",
        "phone": "02033812468",
        "tier": "MEGA_LUXURY",
        "room_count": 20,
        "amenities": {"Hồ bơi vô cực view Vịnh Hạ Long", "Sky Bar tầng thượng", "Phòng Gym cao cấp", "Executive Lounge", "Trung tâm Hội nghị 1500 khách", "Sen Spa & Massage đá nóng", "Bãi đỗ xe ngầm"}
    },
    {
        "id": "MT_012",
        "name": "Mường Thanh Grand Bãi Cháy",
        "city": "Quảng Ninh",
        "address": "Số 20 đường Hạ Long, Phường Bãi Cháy, TP. Hạ Long, Tỉnh Quảng Ninh",
        "phone": "02033646618",
        "tier": "GRAND",
        "room_count": 14,
        "amenities": {"Hồ bơi ngoài trời", "Nhà hàng Hải sản", "Phòng Gym", "Phòng họp hội thảo", "Spa & Sauna", "Bãi đỗ xe"}
    },

    # 11. Bắc Ninh (BNH)
    {
        "id": "MT_013",
        "name": "Mường Thanh Luxury Bắc Ninh",
        "city": "Bắc Ninh",
        "address": "Số 395 đường Ngô Gia Tự, Phường Tiền An, TP. Bắc Ninh, Tỉnh Bắc Ninh",
        "phone": "02223865888",
        "tier": "LUXURY",
        "room_count": 16,
        "amenities": {"Hồ bơi bốn mùa", "Nhà hàng Quan Họ", "Phòng Gym & Yoga", "Trung tâm Hội nghị Quốc tế", "Khu Massage & Xông hơi", "Bãi đỗ xe ngầm"}
    },

    # 12. Phú Thọ (PTO)
    {
        "id": "MT_014",
        "name": "Mường Thanh Luxury Phú Thọ",
        "city": "Phú Thọ",
        "address": "Lô CC17, Quảng trường Hùng Vương, Phường Gia Cẩm, TP. Việt Trì, Phú Thọ",
        "phone": "02103636666",
        "tier": "GRAND",
        "room_count": 14,
        "amenities": {"Hồ bơi ngoài trời", "Nhà hàng Đất Tổ", "Phòng Gym", "Trung tâm tiệc cưới Lạc Hồng", "Spa Sen Spa", "Bãi đỗ xe"}
    },

    # 13. Thành phố Hải Phòng (HPG)
    {
        "id": "MT_015",
        "name": "Mường Thanh Grand Hải Phòng",
        "city": "Thành phố Hải Phòng",
        "address": "Số 47 Lê Thánh Tông, Phường Máy Tơ, Quận Ngô Quyền, Hải Phòng",
        "phone": "02253831888",
        "tier": "LUXURY",
        "room_count": 16,
        "amenities": {"Hồ bơi trong nhà", "Nhà hàng Phượng Vĩ", "Phòng Gym & Fitness", "Hội trường Hội nghị Cảng Biển", "Spa & Sauna", "Bãi đỗ xe ngầm"}
    },

    # 14. Hưng Yên (HYN)
    {
        "id": "MT_016",
        "name": "Mường Thanh Grand Phố Hiến",
        "city": "Hưng Yên",
        "address": "Số 01 đường Phạm Ngũ Lão, Phường Quang Trung, TP. Hưng Yên, Tỉnh Hưng Yên",
        "phone": "02213768888",
        "tier": "BOUTIQUE",
        "room_count": 10,
        "amenities": {"Nhà hàng Phố Hiến", "Phòng Gym", "Phòng họp hội thảo", "Dịch vụ Massage", "Bãi đỗ xe"}
    },

    # 15. Ninh Bình (NBH)
    {
        "id": "MT_017",
        "name": "Mường Thanh Grand Ninh Bình",
        "city": "Ninh Bình",
        "address": "Số 01 đường Trần Hưng Đạo, Phường Phúc Thành, TP. Ninh Bình, Tỉnh Ninh Bình",
        "phone": "02293655888",
        "tier": "GRAND",
        "room_count": 14,
        "amenities": {"Hồ bơi ngoài trời", "Nhà hàng Tràng An", "Phòng Gym", "Phòng hội thảo Cố Đô", "Spa Sen & Xông hơi", "Bãi đỗ xe"}
    },

    # 16. Thanh Hóa (THA)
    {
        "id": "MT_018",
        "name": "Mường Thanh Grand Thanh Hóa",
        "city": "Thanh Hóa",
        "address": "Ngã ba Voi, Khu đô thị Nam thành phố, Phường Đông Vệ, TP. Thanh Hóa, Thanh Hóa",
        "phone": "02378868686",
        "tier": "GRAND",
        "room_count": 14,
        "amenities": {"Hồ bơi ngoài trời", "Nhà hàng Lam Sơn", "Phòng Gym", "Trung tâm Hội nghị & Tiệc cưới", "Spa & Sauna", "Bãi đỗ xe"}
    },

    # 17. Nghệ An (NAN) - 2 chi nhánh
    {
        "id": "MT_019",
        "name": "Mường Thanh Luxury Sông Lam",
        "city": "Nghệ An",
        "address": "Số 13 đường Quang Trung, Phường Quang Trung, TP. Vinh, Tỉnh Nghệ An",
        "phone": "02383737666",
        "tier": "LUXURY",
        "room_count": 18,
        "amenities": {"Hồ bơi chân mây tầng thượng", "Sky Bar & Cafe", "Nhà hàng Sông Lam", "Phòng Gym cao cấp", "Trung tâm Hội nghị Vinh 1200 khách", "Sen Spa", "Bãi đỗ xe ngầm"}
    },
    {
        "id": "MT_020",
        "name": "Mường Thanh Grand Cửa Lò",
        "city": "Nghệ An",
        "address": "Số 232 đường Bình Minh, Khối Nghi Hương, Thị xã Cửa Lò, Tỉnh Nghệ An",
        "phone": "02383948666",
        "tier": "GRAND",
        "room_count": 12,
        "amenities": {"Hồ bơi view biển Cửa Lò", "Nhà hàng Biển Bạc", "Phòng Gym", "Sân Tennis", "Khu vui chơi trẻ em", "Bãi đỗ xe"}
    },

    # 18. Hà Tĩnh (HTH)
    {
        "id": "MT_021",
        "name": "Mường Thanh Grand Hà Tĩnh",
        "city": "Hà Tĩnh",
        "address": "Quốc lộ 1A, Ngã ba Việt Lào, Thị xã Kỳ Anh, Tỉnh Hà Tĩnh",
        "phone": "02393863588",
        "tier": "GRAND",
        "room_count": 12,
        "amenities": {"Hồ bơi ngoài trời", "Nhà hàng Vũng Áng", "Phòng Gym", "Hội trường hội thảo", "Khu Spa & Sauna", "Bãi đỗ xe"}
    },

    # 19. Quảng Trị (QTI)
    {
        "id": "MT_022",
        "name": "Mường Thanh Grand Quảng Trị",
        "city": "Quảng Trị",
        "address": "Số 68 đường Lê Duẩn, Phường 2, TP. Đông Hà, Tỉnh Quảng Trị",
        "phone": "02333898888",
        "tier": "BOUTIQUE",
        "room_count": 10,
        "amenities": {"Hồ bơi ngoài trời", "Nhà hàng Thạch Hãn", "Phòng Gym", "Phòng họp hội thảo", "Spa & Massage", "Bãi đỗ xe"}
    },

    # 20. Thành phố Huế (TTH)
    {
        "id": "MT_023",
        "name": "Mường Thanh Holiday Huế",
        "city": "Thành phố Huế",
        "address": "Số 38 đường Lê Lợi, Phường Phú Hội, TP. Huế, Tỉnh Thừa Thiên Huế",
        "phone": "02343936688",
        "tier": "BOUTIQUE",
        "room_count": 12,
        "amenities": {"Hồ bơi view Sông Hương", "Nhà hàng Cung Đình", "Phòng Gym", "Quầy Bar & Terrace", "Khu Spa Trầm Hương", "Bãi đỗ xe"}
    },

    # 21. Thành phố Đà Nẵng (DNG) - 2 chi nhánh
    {
        "id": "MT_024",
        "name": "Mường Thanh Luxury Đà Nẵng",
        "city": "Thành phố Đà Nẵng",
        "address": "Số 270 đường Võ Nguyên Giáp, Phường Mỹ An, Quận Ngũ Hành Sơn, Đà Nẵng",
        "phone": "02363956789",
        "tier": "MEGA_LUXURY",
        "room_count": 20,
        "amenities": {"Hồ bơi vô cực view biển Mỹ Khê", "Sky Bar tầng 40", "Phòng Gym & Yoga", "Executive Lounge", "Trung tâm Hội nghị Quốc tế 1200 khách", "Sen Spa & Sauna thảo mộc", "Bãi đỗ xe ngầm"}
    },
    {
        "id": "MT_025",
        "name": "Mường Thanh Grand Đà Nẵng",
        "city": "Thành phố Đà Nẵng",
        "address": "Số 962 đường Ngô Quyền, Phường An Hải Tây, Quận Sơn Trà, Đà Nẵng",
        "phone": "02363929929",
        "tier": "GRAND",
        "room_count": 14,
        "amenities": {"Hồ bơi view Cầu Rồng", "Nhà hàng Hàn Giang", "Phòng Gym", "Trung tâm tiệc cưới", "Spa & Karaoke", "Bãi đỗ xe"}
    },

    # 22. Quảng Ngãi (QNI)
    {
        "id": "MT_026",
        "name": "Mường Thanh Holiday Lý Sơn",
        "city": "Quảng Ngãi",
        "address": "Thôn Đông, Xã An Vĩnh, Huyện Đảo Lý Sơn, Tỉnh Quảng Ngãi",
        "phone": "02553867333",
        "tier": "BOUTIQUE",
        "room_count": 10,
        "amenities": {"Hồ bơi vô cực ngắm hoàng hôn biển", "Nhà hàng Hải sản Đảo Ngọc", "Quầy Bar bãi biển", "Dịch vụ cano lặn biển", "Khu Spa thư giãn"}
    },

    # 23. Gia Lai (GLI)
    {
        "id": "MT_027",
        "name": "Mường Thanh Luxury Gia Lai",
        "city": "Gia Lai",
        "address": "Số 02 đường Phù Đổng, Phường Phù Đổng, TP. Pleiku, Tỉnh Gia Lai",
        "phone": "02693723555",
        "tier": "GRAND",
        "room_count": 12,
        "amenities": {"Hồ bơi ngoài trời", "Nhà hàng Biển Hồ", "Phòng Gym", "Hội trường Hội nghị Tây Nguyên", "Spa Sen đá núi", "Bãi đỗ xe"}
    },

    # 24. Khánh Hòa (KHA) - 2 chi nhánh
    {
        "id": "MT_028",
        "name": "Mường Thanh Luxury Nha Trang",
        "city": "Khánh Hòa",
        "address": "Số 60 đường Trần Phú, Phường Lộc Thọ, TP. Nha Trang, Tỉnh Khánh Hòa",
        "phone": "02583898888",
        "tier": "MEGA_LUXURY",
        "room_count": 20,
        "amenities": {"Hồ bơi vô cực ngắm Vịnh Nha Trang", "Sky Lounge & Rooftop Bar", "Phòng Gym & Sauna", "Trung tâm Hội nghị 1000 khách", "Dịch vụ tắm bùn khoáng & Spa", "Executive Lounge", "Bãi đỗ xe ngầm"}
    },
    {
        "id": "MT_029",
        "name": "Mường Thanh Grand Nha Trang",
        "city": "Khánh Hòa",
        "address": "Số 06 đường Dương Hiến Quyền, Phường Vĩnh Hòa, TP. Nha Trang, Khánh Hòa",
        "phone": "02583552468",
        "tier": "GRAND",
        "room_count": 14,
        "amenities": {"Hồ bơi ngoài trời", "Nhà hàng Hòn Chồng", "Phòng Gym", "Phòng hội thảo", "Spa Sen Spa", "Bãi đỗ xe"}
    },

    # 25. Đắk Lắk (DLK)
    {
        "id": "MT_030",
        "name": "Mường Thanh Luxury Buôn Ma Thuột",
        "city": "Đắk Lắk",
        "address": "Số 81 đường Nguyễn Tất Thành, Phường Tân An, TP. Buôn Ma Thuột, Đắk Lắk",
        "phone": "02623961555",
        "tier": "GRAND",
        "room_count": 14,
        "amenities": {"Hồ bơi ngoài trời", "Nhà hàng Ban Mê", "Phòng Gym & Yoga", "Trung tâm tiệc cưới Ê Đê", "Khu Spa & Tắm thuốc bắc", "Bãi đỗ xe"}
    },

    # 26. Lâm Đồng (LDG)
    {
        "id": "MT_031",
        "name": "Mường Thanh Holiday Đà Lạt",
        "city": "Lâm Đồng",
        "address": "Số 42 đường Phan Bội Châu, Phường 2, TP. Đà Lạt, Tỉnh Lâm Đồng",
        "phone": "02633578888",
        "tier": "BOUTIQUE",
        "room_count": 12,
        "amenities": {"Hồ bơi nước ấm 4 mùa", "Nhà hàng Xuân Hương", "Quầy Bar & Lò sưởi", "Phòng Gym", "Spa Thảo mộc ngàn hoa", "Bãi đỗ xe"}
    },

    # 27. Đồng Nai (DNI)
    {
        "id": "MT_032",
        "name": "Mường Thanh Grand Phương Đông",
        "city": "Đồng Nai",
        "address": "Số 12 đường Đồng Khởi, Phường Tân Hiệp, TP. Biên Hòa, Tỉnh Đồng Nai",
        "phone": "02513828888",
        "tier": "GRAND",
        "room_count": 12,
        "amenities": {"Hồ bơi ngoài trời", "Nhà hàng Phương Đông", "Phòng Gym", "Trung tâm Hội nghị Biên Hòa", "Spa & Sauna", "Bãi đỗ xe"}
    },

    # 28. Thành phố Hồ Chí Minh (HCM) - 2 chi nhánh
    {
        "id": "MT_033",
        "name": "Mường Thanh Luxury Sài Gòn",
        "city": "Thành phố Hồ Chí Minh",
        "address": "Số 261 đường Nguyễn Văn Trỗi, Phường 10, Quận Phú Nhuận, TP. Hồ Chí Minh",
        "phone": "02838445678",
        "tier": "MEGA_LUXURY",
        "room_count": 20,
        "amenities": {"Hồ bơi chân mây ngắm Sài Gòn", "Sky Bar & Lounge cao cấp", "Phòng Gym & Yoga 5 sao", "Executive Business Lounge", "Trung tâm Hội nghị Sài Gòn 1500 khách", "Sen Spa & Thủy liệu pháp", "Bãi đỗ xe ngầm 3 tầng"}
    },
    {
        "id": "MT_034",
        "name": "Mường Thanh Grand Sài Gòn Centre",
        "city": "Thành phố Hồ Chí Minh",
        "address": "Số 8-8A đường Mạc Đĩnh Chi, Phường Bến Nghé, Quận 1, TP. Hồ Chí Minh",
        "phone": "02838278599",
        "tier": "LUXURY",
        "room_count": 16,
        "amenities": {"Hồ bơi trên mái", "Nhà hàng Gia Định", "Phòng Gym", "Executive Boardroom", "Spa & Sauna", "Bãi đỗ xe"}
    },

    # 29. Tây Ninh (TNH)
    {
        "id": "MT_035",
        "name": "Mường Thanh Grand Tây Ninh",
        "city": "Tây Ninh",
        "address": "Số 86 đường 30 Tháng 4, Phường 3, TP. Tây Ninh, Tỉnh Tây Ninh",
        "phone": "02763888999",
        "tier": "GRAND",
        "room_count": 12,
        "amenities": {"Hồ bơi view Núi Bà Đen", "Nhà hàng Tây Ninh", "Phòng Gym", "Hội trường Hội nghị", "Khu Spa & Xông hơi", "Bãi đỗ xe"}
    },

    # 30. Đồng Tháp (DTP)
    {
        "id": "MT_036",
        "name": "Mường Thanh Grand Cao Lãnh",
        "city": "Đồng Tháp",
        "address": "Số 56 đường Nguyễn Huệ, Phường 1, TP. Cao Lãnh, Tỉnh Đồng Tháp",
        "phone": "02773858888",
        "tier": "GRAND",
        "room_count": 12,
        "amenities": {"Hồ bơi ngoài trời", "Nhà hàng Hoa Sen", "Phòng Gym", "Trung tâm Tiệc cưới Đồng Tháp", "Spa & Sauna", "Bãi đỗ xe"}
    },

    # 31. Vĩnh Long (VLG)
    {
        "id": "MT_037",
        "name": "Mường Thanh Grand Vĩnh Long",
        "city": "Vĩnh Long",
        "address": "Số 12 đường Hoàng Thái Hiếu, Phường 1, TP. Vĩnh Long, Tỉnh Vĩnh Long",
        "phone": "02703838888",
        "tier": "GRAND",
        "room_count": 12,
        "amenities": {"Hồ bơi view Sông Cổ Chiên", "Nhà hàng Cửu Long", "Phòng Gym", "Phòng họp hội thảo", "Spa & Massage", "Bãi đỗ xe"}
    },

    # 32. An Giang (AGG)
    {
        "id": "MT_038",
        "name": "Mường Thanh Luxury Long Xuyên",
        "city": "An Giang",
        "address": "Số 32 đường Nguyễn Trãi, Phường Mỹ Long, TP. Long Xuyên, Tỉnh An Giang",
        "phone": "02963888777",
        "tier": "GRAND",
        "room_count": 14,
        "amenities": {"Hồ bơi chân mây", "Nhà hàng Thất Sơn", "Phòng Gym", "Trung tâm Hội nghị An Giang", "Sen Spa & Massage trị liệu", "Bãi đỗ xe"}
    },

    # 33. Thành phố Cần Thơ (CTO)
    {
        "id": "MT_039",
        "name": "Mường Thanh Luxury Cần Thơ",
        "city": "Thành phố Cần Thơ",
        "address": "Khu cồn Cái Khế, Phường Cái Khế, Quận Ninh Kiều, TP. Cần Thơ",
        "phone": "02923688888",
        "tier": "LUXURY",
        "room_count": 18,
        "amenities": {"Hồ bơi vô cực view Sông Hậu", "Sky Bar & Lounge", "Nhà hàng Tây Đô", "Phòng Gym & Yoga", "Trung tâm Hội nghị 1200 khách", "Sen Spa & Massage", "Bãi đỗ xe"}
    },

    # 34. Cà Mau (CMU)
    {
        "id": "MT_040",
        "name": "Mường Thanh Luxury Cà Mau",
        "city": "Cà Mau",
        "address": "Lô C3A, Khu Trung tâm Hành chính, Phường 9, TP. Cà Mau, Tỉnh Cà Mau",
        "phone": "02903828888",
        "tier": "GRAND",
        "room_count": 14,
        "amenities": {"Hồ bơi ngoài trời", "Nhà hàng Đất Mũi", "Phòng Gym", "Trung tâm tiệc cưới Cà Mau", "Khu Spa & Sauna thảo mộc", "Bãi đỗ xe"}
    }
]

ROOM_TIER_CONFIGS = [
    {"type": "Superior Single", "capacity": 1, "bed": "Single", "price_multiplier": Decimal("0.85"), "desc": "Phòng đơn tiện nghi dành cho khách công tác cá nhân."},
    {"type": "Deluxe King", "capacity": 2, "bed": "King", "price_multiplier": Decimal("1.0"), "desc": "Phòng tiêu chuẩn giường đôi King-size sang trọng, cửa sổ panorama."},
    {"type": "Deluxe Twin", "capacity": 2, "bed": "Twin", "price_multiplier": Decimal("1.0"), "desc": "Phòng 2 giường đơn cao cấp, ban công thoáng mát và bàn làm việc."},
    {"type": "Executive Suite", "capacity": 2, "bed": "King", "price_multiplier": Decimal("1.6"), "desc": "Phòng Suite cao cấp có phòng khách riêng biệt và bồn tắm thủy lực."},
    {"type": "Family Suite", "capacity": 4, "bed": "Double", "price_multiplier": Decimal("2.1"), "desc": "Phòng gia đình rộng rãi gồm 2 giường đôi, khu bếp mini và ban công lớn."},
    {"type": "Royal Presidential Suite", "capacity": 4, "bed": "King", "price_multiplier": Decimal("3.5"), "desc": "Căn hộ Hoàng gia cao cấp nhất với tầm nhìn toàn cảnh, phòng họp riêng và quản gia."}
]

def generate_rooms_for_hotel(hotel_id, tier, room_count):
    """
    Sinh danh sách phòng đa dạng theo số lượng yêu cầu (8 đến 20 phòng).
    """
    rooms = []
    base_price = Decimal("850000")
    if tier == "MEGA_LUXURY":
        base_price = Decimal("1600000")
    elif tier == "LUXURY":
        base_price = Decimal("1300000")
    elif tier == "GRAND":
        base_price = Decimal("1050000")
    elif tier == "BOUTIQUE":
        base_price = Decimal("850000")

    for i in range(1, room_count + 1):
        floor = (i - 1) // 5 + 1
        room_idx = (i - 1) % 5 + 1
        room_number = f"{floor}{room_idx:02d}"

        cfg_idx = (i - 1) % len(ROOM_TIER_CONFIGS)
        if i == room_count and tier in ("MEGA_LUXURY", "LUXURY"):
            cfg = ROOM_TIER_CONFIGS[-1] # Presidential Suite
        else:
            cfg = ROOM_TIER_CONFIGS[cfg_idx]

        price = int(base_price * cfg["price_multiplier"])
        # Làm tròn đến 50,000 đ
        price = (price // 50000) * 50000

        # Phân bổ trạng thái: 
        # Phòng thứ 4 là MAINTENANCE, phòng thứ 2 và 5 là OCCUPIED, còn lại AVAILABLE
        if i % 7 == 4:
            status = "MAINTENANCE"
            is_avail = False
        elif i % 5 == 2 or i % 6 == 0:
            status = "OCCUPIED"
            is_avail = False
        else:
            status = "AVAILABLE"
            is_avail = True

        rooms.append({
            "hotel_id": hotel_id,
            "room_number": room_number,
            "room_type": cfg["type"],
            "price_per_night": Decimal(price),
            "is_available": is_avail,
            "status": status,
            "capacity": cfg["capacity"],
            "bed_type": cfg["bed"],
            "description": cfg["desc"]
        })

    return rooms

def run_seed():
    print("======================================================================")
    print("  CHUỖI KHÁCH SẠN MƯỜNG THANH HOSPITALITY - HỆ THỐNG NỘI BỘ (PMS)")
    print("======================================================================")
    
    session = get_session()
    if session is None:
        print("❌ Lỗi: Không thể kết nối DataStax AstraDB!")
        sys.exit(1)

    print("✅ Đã kết nối AstraDB thành công!")

    # 1. Dọn dẹp dữ liệu cũ (Xóa toàn bộ các partition hotels và rooms cũ)
    print("\n--- [BƯỚC 1] DỌN DẸP DỮ LIỆU CŨ TRONG BẢNG HOTELS VÀ ROOMS_BY_HOTEL ---")
    try:
        old_hotels = list(session.execute("SELECT hotel_id FROM hotels"))
        print(f"  Tìm thấy {len(old_hotels)} khách sạn cũ cần dọn dẹp...")
        
        del_room_stmt = session.prepare("DELETE FROM rooms_by_hotel WHERE hotel_id = ?")
        del_hotel_stmt = session.prepare("DELETE FROM hotels WHERE hotel_id = ?")
        
        for h in old_hotels:
            session.execute(del_room_stmt, (h.hotel_id,))
            session.execute(del_hotel_stmt, (h.hotel_id,))
        print("  ✅ Đã dọn dẹp sạch sẽ dữ liệu cũ!")
    except Exception as e:
        print(f"  ⚠️ Cảnh báo khi dọn dẹp dữ liệu cũ: {e}")

    # 2. Chuẩn bị Prepared Statements
    insert_hotel_stmt = session.prepare("""
        INSERT INTO hotels (hotel_id, name, phone, address, city, country, amenities)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """)

    insert_room_stmt = session.prepare("""
        INSERT INTO rooms_by_hotel (hotel_id, room_number, room_type, price_per_night, is_available, status, capacity, bed_type, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """)

    # 3. Nạp 40 chi nhánh Mường Thanh
    print(f"\n--- [BƯỚC 2] NẠP 40 CHI NHÁNH MƯỜNG THANH PHỦ KÍN 34 TỈNH THÀNH ---")
    total_rooms_inserted = 0

    for idx, b in enumerate(MUONG_THANH_BRANCHES, 1):
        # Insert Hotel
        session.execute(insert_hotel_stmt, (
            b["id"],
            b["name"],
            b["phone"],
            b["address"],
            b["city"],
            "Việt Nam",
            b["amenities"]
        ))

        # Generate & Insert Rooms
        rooms = generate_rooms_for_hotel(b["id"], b["tier"], b["room_count"])
        for r in rooms:
            session.execute(insert_room_stmt, (
                r["hotel_id"],
                r["room_number"],
                r["room_type"],
                r["price_per_night"],
                r["is_available"],
                r["status"],
                r["capacity"],
                r["bed_type"],
                r["description"]
            ))

        total_rooms_inserted += len(rooms)
        print(f"  ✅ [{idx:02d}/40] {b['name']} ({b['id']}) - {b['city']} [{b['tier']}: {b['room_count']} phòng]")

    print("\n======================================================================")
    print(f"🎉 HOÀN TẤT SEED CHUỖI KHÁCH SẠN MƯỜNG THANH HOSPITALITY:")
    print(f"   - Tổng chi nhánh đã tạo : {len(MUONG_THANH_BRANCHES)} chi nhánh (Phủ 34/34 tỉnh)")
    print(f"   - Tổng số phòng đã nạp : {total_rooms_inserted} phòng (Quy mô 8 - 20 phòng/chi nhánh)")
    print("======================================================================")

if __name__ == "__main__":
    run_seed()
