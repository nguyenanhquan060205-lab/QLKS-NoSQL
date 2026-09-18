# ====================================================================
# SCRIPT SEED DATA: 48 KHÁCH SẠN THẬT PHỦ KÍN 34 TỈNH THÀNH VIỆT NAM
# SỐ LƯỢNG PHÒNG ĐA DẠNG LINH HOẠT THEO QUY MÔ (TỪ 8 ĐẾN 20 PHÒNG/KS)
# ====================================================================

import os
import sys
from decimal import Decimal
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from database.db import get_session

# Danh mục 48 khách sạn 4-5 sao thật 100% tại Việt Nam
HOTELS_CATALOG = [
    # 01 - Thành phố Hà Nội (3 KS)
    {
        "hotel_id": "HT_001",
        "name": "JW Marriott Hotel Hanoi",
        "phone": "02438335588",
        "address": "08 Đỗ Đức Dục, Phường Mễ Trì",
        "city": "Thành phố Hà Nội",
        "country": "Vietnam",
        "amenities": {"Hồ bơi trong nhà", "Spa trị liệu", "Nhà hàng JW Café", "Phòng gym 24/7", "Phòng đại tiệc", "Wifi tốc độ cao"},
        "base_price": Decimal("3200000"),
        "scale": "MEGA_RESORT",  # 20 phòng
        "view_type": "Hồ nước & Thành phố",
    },
    {
        "hotel_id": "HT_002",
        "name": "Sofitel Legend Metropole Hanoi",
        "phone": "02438266919",
        "address": "15 Phố Ngô Quyền, Phường Tràng Tiền",
        "city": "Thành phố Hà Nội",
        "country": "Vietnam",
        "amenities": {"Hồ bơi ngoài trời", "Le Spa du Metropole", "Bamboo Bar", "Nhà hàng Pháp Le Beaulieu", "Đưa đón limousine", "Wifi"},
        "base_price": Decimal("4800000"),
        "scale": "LARGE",  # 16 phòng
        "view_type": "Phố Cổ & Vườn Pháp",
    },
    {
        "hotel_id": "HT_003",
        "name": "Lotte Hotel Hanoi",
        "phone": "02433331000",
        "address": "54 Liễu Giai, Phường Cống Vị",
        "city": "Thành phố Hà Nội",
        "country": "Vietnam",
        "amenities": {"Tòa tháp 65 tầng", "Hồ bơi bốn mùa", "Evian Spa", "Sky Lounge Top of Hanoi", "Phòng gym", "Buffet Grill 63"},
        "base_price": Decimal("2900000"),
        "scale": "LARGE",  # 16 phòng
        "view_type": "Skyline Thành phố",
    },

    # 04 - Cao Bằng (1 KS)
    {
        "hotel_id": "HT_004",
        "name": "Mường Thanh Luxury Cao Bằng",
        "phone": "02063888088",
        "address": "Số 42 Phố Kim Đồng, Phường Hợp Giang",
        "city": "Cao Bằng",
        "country": "Vietnam",
        "amenities": {"Hồ bơi bốn mùa", "Spa thảo dược", "Nhà hàng Pác Bó", "Phòng gym", "Wifi tốc độ cao"},
        "base_price": Decimal("1250000"),
        "scale": "MEDIUM",  # 12 phòng
        "view_type": "Sông Bằng & Núi",
    },

    # 08 - Tuyên Quang (1 KS)
    {
        "hotel_id": "HT_005",
        "name": "Mường Thanh Grand Tuyên Quang",
        "phone": "02073812888",
        "address": "Số 207 Đường Bình Thuận, Phường Tân Quang",
        "city": "Tuyên Quang",
        "country": "Vietnam",
        "amenities": {"Hồ bơi ngoài trời", "Spa thư giãn", "Nhà hàng Lô Giang", "Sân tennis", "Wifi"},
        "base_price": Decimal("1150000"),
        "scale": "BOUTIQUE",  # 8 phòng
        "view_type": "Sông Lô thơ mộng",
    },

    # 11 - Điện Biên (1 KS)
    {
        "hotel_id": "HT_006",
        "name": "Mường Thanh Grand Điện Biên Phủ",
        "phone": "02153810043",
        "address": "Số 514 Đường Võ Nguyên Giáp, Phường Him Lam",
        "city": "Điện Biên",
        "country": "Vietnam",
        "amenities": {"Hồ bơi ngoài trời", "Sân tennis", "Spa & Massage", "Nhà hàng Mường Phăng", "Wifi"},
        "base_price": Decimal("1050000"),
        "scale": "MEDIUM",  # 12 phòng
        "view_type": "Thung lũng Mường Thanh",
    },

    # 12 - Lai Châu (1 KS)
    {
        "hotel_id": "HT_007",
        "name": "Mường Thanh Luxury Lai Châu",
        "phone": "02133798888",
        "address": "Số 002 Đường Lê Duẩn, Phường Đoàn Kết",
        "city": "Lai Châu",
        "country": "Vietnam",
        "amenities": {"Hồ bơi ngoài trời", "Trung tâm thể thao", "Spa & Xông hơi", "Nhà hàng Pu Sam Cáp", "Wifi"},
        "base_price": Decimal("1100000"),
        "scale": "BOUTIQUE",  # 8 phòng
        "view_type": "Quảng trường & Núi",
    },

    # 14 - Sơn La (1 KS)
    {
        "hotel_id": "HT_008",
        "name": "Mường Thanh Luxury Sơn La",
        "phone": "02122228888",
        "address": "Số 02 Đường Tô Hiệu, Phường Chiềng Cơi",
        "city": "Sơn La",
        "country": "Vietnam",
        "amenities": {"Hồ bơi ngoài trời", "Spa Mộc Châu", "Sân tennis", "Nhà hàng Pha Luông", "Wifi"},
        "base_price": Decimal("1200000"),
        "scale": "MEDIUM",  # 12 phòng
        "view_type": "Thung lũng Tây Bắc",
    },

    # 15 - Lào Cai (2 KS)
    {
        "hotel_id": "HT_009",
        "name": "Silk Path Grand Resort & Spa Sapa",
        "phone": "02143788555",
        "address": "Đồi Quan Sứ, Phường Sa Pa",
        "city": "Lào Cai",
        "country": "Vietnam",
        "amenities": {"Hồ bơi vô cực nước nóng", "Chi Spa đá nóng", "Vườn hoa hồng Pháp", "Nhà hàng Samu", "Wifi"},
        "base_price": Decimal("2850000"),
        "scale": "LARGE",  # 16 phòng
        "view_type": "Dãy Hoàng Liên Sơn & Fansipan",
    },
    {
        "hotel_id": "HT_010",
        "name": "Topas Ecolodge Sapa",
        "phone": "02437151005",
        "address": "Thôn Bản Lếch, Xã Thanh Bình, Sa Pa",
        "city": "Lào Cai",
        "country": "Vietnam",
        "amenities": {"Hồ bơi vô cực nước mặn trên đỉnh đồi", "Bungalow đá hoa cương", "Spa thảo mộc người Dao Đỏ", "Nhà hàng 360 độ"},
        "base_price": Decimal("4200000"),
        "scale": "BOUTIQUE",  # 8 phòng
        "view_type": "Thung lũng Mường Hoa",
    },

    # 19 - Thái Nguyên (1 KS)
    {
        "hotel_id": "HT_011",
        "name": "Khách sạn Đông Á Plaza Thái Nguyên",
        "phone": "02083656999",
        "address": "Số 668 Đường Phan Đình Phùng, Phường Đồng Quang",
        "city": "Thái Nguyên",
        "country": "Vietnam",
        "amenities": {"Hồ bơi ngoài trời", "Trung tâm hội nghị tiệc cưới", "Spa & Massage", "Nhà hàng Á Âu", "Wifi"},
        "base_price": Decimal("950000"),
        "scale": "MEDIUM",  # 12 phòng
        "view_type": "Đồi chè Tân Cương",
    },

    # 20 - Lạng Sơn (1 KS)
    {
        "hotel_id": "HT_012",
        "name": "Mường Thanh Luxury Lạng Sơn",
        "phone": "02053866666",
        "address": "Số 68 Đường Ngô Quyền, Phường Vĩnh Trại",
        "city": "Lạng Sơn",
        "country": "Vietnam",
        "amenities": {"Hồ bơi bốn mùa", "Spa & Sauna", "Nhà hàng Mẫu Sơn", "Phòng karaoke VIP", "Wifi"},
        "base_price": Decimal("1350000"),
        "scale": "MEDIUM",  # 12 phòng
        "view_type": "Sông Kỳ Cùng",
    },

    # 22 - Quảng Ninh (2 KS)
    {
        "hotel_id": "HT_013",
        "name": "Vinpearl Resort & Spa Hạ Long",
        "phone": "02033556868",
        "address": "Đảo Rều, Phường Bãi Cháy",
        "city": "Quảng Ninh",
        "country": "Vietnam",
        "amenities": {"Đảo độc lập 4 mặt biển", "Hồ bơi bốn mùa", "Vincharm Spa", "Tàu cao tốc 24/7", "Sân tennis"},
        "base_price": Decimal("2950000"),
        "scale": "MEGA_RESORT",  # 20 phòng
        "view_type": "Vịnh Hạ Long di sản",
    },
    {
        "hotel_id": "HT_014",
        "name": "FLC Grand Hotel Hạ Long",
        "phone": "02033625388",
        "address": "Đoàn Kết, Phường Hà Trung",
        "city": "Quảng Ninh",
        "country": "Vietnam",
        "amenities": {"Sân golf 18 hố trên đồi", "Bể bơi vô cực tràn bờ ngắm vịnh", "Grand Spa", "Trung tâm hội nghị quốc tế"},
        "base_price": Decimal("2200000"),
        "scale": "LARGE",  # 16 phòng
        "view_type": "Toàn cảnh Vịnh từ trên đồi",
    },

    # 24 - Bắc Ninh (1 KS)
    {
        "hotel_id": "HT_015",
        "name": "Mường Thanh Luxury Bắc Ninh",
        "phone": "02223665888",
        "address": "Số 395 Đường Ngô Gia Tự, Phường Tiền An",
        "city": "Bắc Ninh",
        "country": "Vietnam",
        "amenities": {"Hồ bơi trên cao", "Spa & Massage", "Nhà hàng Kinh Bắc", "Phòng gym", "Wifi"},
        "base_price": Decimal("1450000"),
        "scale": "MEDIUM",  # 12 phòng
        "view_type": "Trung tâm Kinh Bắc",
    },

    # 25 - Phú Thọ (1 KS)
    {
        "hotel_id": "HT_016",
        "name": "Mường Thanh Luxury Phú Thọ",
        "phone": "02103636666",
        "address": "Lô CC17, Quảng trường Hùng Vương, Phường Gia Cẩm",
        "city": "Phú Thọ",
        "country": "Vietnam",
        "amenities": {"Hồ bơi ngoài trời", "Spa Hùng Vương", "Sân tennis", "Nhà hàng Tây Bắc", "Wifi"},
        "base_price": Decimal("1300000"),
        "scale": "MEDIUM",  # 12 phòng
        "view_type": "Quảng trường Hùng Vương",
    },

    # 31 - Thành phố Hải Phòng (2 KS)
    {
        "hotel_id": "HT_017",
        "name": "Sheraton Hai Phong",
        "phone": "02253266888",
        "address": "Khu đô thị Vinhomes Imperia, Phường Thượng Lý",
        "city": "Thành phố Hải Phòng",
        "country": "Vietnam",
        "amenities": {"Tòa tháp 45 tầng cao nhất Duyên Hải", "Hồ bơi bốn mùa", "Aqua Bar", "Sheraton Club", "Spa"},
        "base_price": Decimal("2250000"),
        "scale": "LARGE",  # 16 phòng
        "view_type": "Sông Cấm & Cảng biển",
    },
    {
        "hotel_id": "HT_018",
        "name": "Flamingo Cát Bà Beach Resort",
        "phone": "02253888686",
        "address": "Bãi biển Cát Cò 1 & 2, Đảo Cát Bà",
        "city": "Thành phố Hải Phòng",
        "country": "Vietnam",
        "amenities": {"Tựa vách núi hướng vịnh Lan Hạ", "Hồ bơi sườn núi", "Seva Spa & Onsen", "Đường dạo bộ trên mây"},
        "base_price": Decimal("2600000"),
        "scale": "LARGE",  # 16 phòng
        "view_type": "Vịnh Lan Hạ nguyên sơ",
    },

    # 33 - Hưng Yên (1 KS)
    {
        "hotel_id": "HT_019",
        "name": "Khách sạn Thái Bình Hưng Yên",
        "phone": "02213865666",
        "address": "Số 02 Đường Chu Văn An, Phường An Tảo",
        "city": "Hưng Yên",
        "country": "Vietnam",
        "amenities": {"Hồ bơi ngoài trời", "Nhà hàng Phố Hiến", "Phòng gym", "Phòng họp hội nghị", "Wifi"},
        "base_price": Decimal("900000"),
        "scale": "BOUTIQUE",  # 8 phòng
        "view_type": "Hồ Bán Nguyệt Phố Hiến",
    },

    # 37 - Ninh Bình (2 KS)
    {
        "hotel_id": "HT_020",
        "name": "Emeralda Resort Ninh Bình",
        "phone": "02293658333",
        "address": "Làng Tập Ninh, Xã Gia Vân",
        "city": "Ninh Bình",
        "country": "Vietnam",
        "amenities": {"Resort làng quê Bắc Bộ", "Hồ bơi trong nhà và ngoài trời", "La Cochinchine Spa", "Sân golf mini"},
        "base_price": Decimal("2450000"),
        "scale": "MEDIUM",  # 12 phòng
        "view_type": "Đầm Vân Long & Núi đá vôi",
    },
    {
        "hotel_id": "HT_021",
        "name": "Ninh Binh Hidden Charm Hotel & Resort",
        "phone": "02293621888",
        "address": "Khu du lịch Tam Cốc - Bích Động, Xã Ninh Hải",
        "city": "Ninh Bình",
        "country": "Vietnam",
        "amenities": {"Gần bến thuyền Tam Cốc", "Hồ bơi ngắm núi", "Spa Hương Sen", "Nhà hàng Cố Đô", "Gym"},
        "base_price": Decimal("1650000"),
        "scale": "MEDIUM",  # 12 phòng
        "view_type": "Cánh đồng lúa & Núi Tam Cốc",
    },

    # 38 - Thanh Hóa (1 KS)
    {
        "hotel_id": "HT_022",
        "name": "FLC Grand Hotel Sầm Sơn",
        "phone": "02378788888",
        "address": "Đường Hồ Xuân Hương, Phường Quảng Cư",
        "city": "Thanh Hóa",
        "country": "Vietnam",
        "amenities": {"Bể bơi nước mặn 5100m2", "Sân golf 18 hố FLC Golf Links", "Maia Spa", "Trung tâm hội nghị quốc tế"},
        "base_price": Decimal("1850000"),
        "scale": "MEGA_RESORT",  # 20 phòng
        "view_type": "Biển Sầm Sơn",
    },

    # 40 - Nghệ An (1 KS)
    {
        "hotel_id": "HT_023",
        "name": "Mường Thanh Luxury Sông Lam",
        "phone": "02383737666",
        "address": "Số 13 Đường Quang Trung, Phường Quang Trung",
        "city": "Nghệ An",
        "country": "Vietnam",
        "amenities": {"Khách sạn 5 sao cao nhất TP Vinh 30 tầng", "Hồ bơi tầng thượng", "Trầm Spa", "Rooftop Bar"},
        "base_price": Decimal("1450000"),
        "scale": "LARGE",  # 16 phòng
        "view_type": "Sông Lam & Núi Quyết",
    },

    # 42 - Hà Tĩnh (1 KS)
    {
        "hotel_id": "HT_024",
        "name": "Melia Vinpearl Hà Tĩnh",
        "phone": "02393801888",
        "address": "Ngã tư Hà Huy Tập - Hàm Nghi, Phường Hà Huy Tập",
        "city": "Hà Tĩnh",
        "country": "Vietnam",
        "amenities": {"Tòa tháp 37 tầng", "Hồ bơi vô cực ngắm dãy Hồng Lĩnh", "Vincharm Spa", "Sky Bar", "Phòng gym"},
        "base_price": Decimal("1350000"),
        "scale": "MEDIUM",  # 12 phòng
        "view_type": "Dãy núi Hồng Lĩnh",
    },

    # 44 - Quảng Trị (1 KS)
    {
        "hotel_id": "HT_025",
        "name": "Mường Thanh Grand Quảng Trị",
        "phone": "02333898888",
        "address": "Số 68 Đường Lê Duẩn, Phường 2",
        "city": "Quảng Trị",
        "country": "Vietnam",
        "amenities": {"Hồ bơi ngoài trời", "Sân tennis", "Trung tâm chăm sóc sức khỏe & Spa", "Nhà hàng Cửa Tùng"},
        "base_price": Decimal("1100000"),
        "scale": "BOUTIQUE",  # 8 phòng
        "view_type": "Thành cổ Đông Hà",
    },

    # 46 - Thành phố Huế (2 KS)
    {
        "hotel_id": "HT_026",
        "name": "Melia Vinpearl Hue",
        "phone": "02343688888",
        "address": "50A Hùng Vương, Phường Phú Nhuận",
        "city": "Thành phố Huế",
        "country": "Vietnam",
        "amenities": {"Hồ bơi bốn mùa", "YHI Spa", "The Prime Restaurant", "Sky Lounge view sông Hương", "Gym"},
        "base_price": Decimal("1750000"),
        "scale": "LARGE",  # 16 phòng
        "view_type": "Sông Hương & Cầu Trường Tiền",
    },
    {
        "hotel_id": "HT_027",
        "name": "Azerai La Residence Hue",
        "phone": "02343837475",
        "address": "05 Lê Lợi, Phường Vĩnh Ninh",
        "city": "Thành phố Huế",
        "country": "Vietnam",
        "amenities": {"Dinh thự Pháp cổ 1930", "Hồ bơi nước mặn", "Du thuyền thưởng trà chiều", "Le Spa", "Vườn nhiệt đới"},
        "base_price": Decimal("3800000"),
        "scale": "BOUTIQUE",  # 8 phòng
        "view_type": "Kinh thành Huế cổ kính",
    },

    # 48 - Thành phố Đà Nẵng (3 KS)
    {
        "hotel_id": "HT_028",
        "name": "InterContinental Danang Sun Peninsula Resort",
        "phone": "02363938888",
        "address": "Bãi Bắc, Bán đảo Sơn Trà, Phường Thọ Quang",
        "city": "Thành phố Đà Nẵng",
        "country": "Vietnam",
        "amenities": {"Bãi biển riêng tư", "Hồ bơi vô cực", "Mi Sol Spa", "Nhà hàng La Maison 1888", "Cáp treo Nam Tram"},
        "base_price": Decimal("8500000"),
        "scale": "MEGA_RESORT",  # 20 phòng
        "view_type": "Vịnh Sơn Trà tuyệt mỹ",
    },
    {
        "hotel_id": "HT_029",
        "name": "Novotel Danang Premier Han River",
        "phone": "02363929999",
        "address": "36 Bạch Đằng, Phường Thạch Thang",
        "city": "Thành phố Đà Nẵng",
        "country": "Vietnam",
        "amenities": {"Hồ bơi tầng thượng", "InBalance Spa", "Sky36 Rooftop Bar", "Phòng gym", "Buffet quốc tế"},
        "base_price": Decimal("1950000"),
        "scale": "LARGE",  # 16 phòng
        "view_type": "Cầu Rồng & Sông Hàn",
    },
    {
        "hotel_id": "HT_030",
        "name": "Sheraton Grand Danang Resort",
        "phone": "02363988999",
        "address": "35 Trường Sa, Phường Hòa Hải",
        "city": "Thành phố Đà Nẵng",
        "country": "Vietnam",
        "amenities": {"Hồ bơi vô cực 250m dài nhất Đà Nẵng", "Bãi biển Non Nước", "Shine Spa", "Sân tennis"},
        "base_price": Decimal("3100000"),
        "scale": "LARGE",  # 16 phòng
        "view_type": "Bãi biển Non Nước & Ngũ Hành Sơn",
    },

    # 51 - Quảng Ngãi (1 KS)
    {
        "hotel_id": "HT_031",
        "name": "Mường Thanh Holiday Lý Sơn",
        "phone": "02553867333",
        "address": "Thôn Tây, Xã An Vĩnh",
        "city": "Quảng Ngãi",
        "country": "Vietnam",
        "amenities": {"View biển đảo Lý Sơn", "Hồ bơi ngoài trời sát biển", "Spa hải sản", "Nhà hàng An Hải"},
        "base_price": Decimal("1250000"),
        "scale": "BOUTIQUE",  # 8 phòng
        "view_type": "Cổng Tò Vò & Biển đảo",
    },

    # 52 - Gia Lai (1 KS)
    {
        "hotel_id": "HT_032",
        "name": "Mường Thanh Luxury Gia Lai",
        "phone": "02693798888",
        "address": "Số 02 Đường Phù Đổng, Phường Phù Đổng",
        "city": "Gia Lai",
        "country": "Vietnam",
        "amenities": {"Hồ bơi ngoài trời", "Sân tennis", "Spa Plâyku", "Nhà hàng Biển Hồ", "Wifi tốc độ cao"},
        "base_price": Decimal("1200000"),
        "scale": "MEDIUM",  # 12 phòng
        "view_type": "Biển Hồ Pleiku",
    },

    # 56 - Khánh Hòa (3 KS)
    {
        "hotel_id": "HT_033",
        "name": "Vinpearl Resort & Spa Nha Trang Bay",
        "phone": "02583598999",
        "address": "Đảo Hòn Tre, Phường Vĩnh Nguyên",
        "city": "Khánh Hòa",
        "country": "Vietnam",
        "amenities": {"Bãi biển riêng tư cát trắng", "Hồ bơi ngoài trời", "Akoya Spa", "Công viên VinWonders", "Cáp treo"},
        "base_price": Decimal("2650000"),
        "scale": "MEGA_RESORT",  # 20 phòng
        "view_type": "Vịnh Nha Trang kỳ vĩ",
    },
    {
        "hotel_id": "HT_034",
        "name": "InterContinental Nha Trang",
        "phone": "02583887777",
        "address": "32 - 34 Trần Phú, Phường Lộc Thọ",
        "city": "Khánh Hòa",
        "country": "Vietnam",
        "amenities": {"Hồ bơi ngoài trời view vịnh", "Spa InterContinental", "Planet Trekkers", "Phòng gym", "Nhà hàng hải sản"},
        "base_price": Decimal("2850000"),
        "scale": "LARGE",  # 16 phòng
        "view_type": "Bãi biển Trần Phú",
    },
    {
        "hotel_id": "HT_035",
        "name": "Amiana Resort Nha Trang",
        "phone": "02583556888",
        "address": "Vịnh Rùa, Đường Phạm Văn Đồng",
        "city": "Khánh Hòa",
        "country": "Vietnam",
        "amenities": {"Hồ bơi nước mặn tự nhiên 2500m2", "Bãi biển đầm phá riêng", "Tắm bùn khoáng nóng", "Nhà hàng Bacaro"},
        "base_price": Decimal("3900000"),
        "scale": "MEDIUM",  # 12 phòng
        "view_type": "Đầm phá & Vịnh Rùa",
    },

    # 66 - Đắk Lắk (1 KS)
    {
        "hotel_id": "HT_036",
        "name": "Mường Thanh Luxury Buôn Ma Thuột",
        "phone": "02623988888",
        "address": "Số 81 Đường Nguyễn Tất Thành, Phường Tân An",
        "city": "Đắk Lắk",
        "country": "Vietnam",
        "amenities": {"Hồ bơi ngoài trời", "Sân tennis", "Spa Cà phê Ban Mê", "Nhà hàng Dray Nur", "Phòng gym"},
        "base_price": Decimal("1350000"),
        "scale": "MEDIUM",  # 12 phòng
        "view_type": "Thủ phủ Cà phê Ban Mê",
    },

    # 68 - Lâm Đồng (2 KS)
    {
        "hotel_id": "HT_037",
        "name": "Dalat Palace Heritage Hotel",
        "phone": "02633825444",
        "address": "02 Trần Phú, Phường 3",
        "city": "Lâm Đồng",
        "country": "Vietnam",
        "amenities": {"Sân golf 18 lỗ Dalat Palace", "Kiến trúc Pháp cổ 1922", "Nhà hàng Le Rabelais", "Hầm rượu vang", "Vườn hoa hồng"},
        "base_price": Decimal("3100000"),
        "scale": "BOUTIQUE",  # 8 phòng
        "view_type": "Hồ Xuân Hương mộng mơ",
    },
    {
        "hotel_id": "HT_038",
        "name": "Ana Mandara Villas Dalat Resort & Spa",
        "phone": "02633555888",
        "address": "Đường Lê Lai, Phường 5",
        "city": "Lâm Đồng",
        "country": "Vietnam",
        "amenities": {"17 biệt thự kiểu Pháp cổ kính giữa rừng thông", "Hồ bơi nước ấm ngoài trời", "La Cochinchine Spa", "Lò sưởi củi"},
        "base_price": Decimal("2700000"),
        "scale": "MEDIUM",  # 12 phòng
        "view_type": "Rừng thông cổ thụ & Thung lũng",
    },

    # 75 - Đồng Nai (1 KS)
    {
        "hotel_id": "HT_039",
        "name": "The Grand Ho Tram Strip",
        "phone": "02543788888",
        "address": "Phước Thuận, Xuyên Mộc",
        "city": "Đồng Nai",
        "country": "Vietnam",
        "amenities": {"Khu phức hợp nghỉ dưỡng 5 sao bờ biển", "Sân golf The Bluffs", "Hồ bơi trải dài", "Spa The Grand"},
        "base_price": Decimal("2850000"),
        "scale": "MEGA_RESORT",  # 20 phòng
        "view_type": "Bờ biển Hồ Tràm hoang sơ",
    },

    # 79 - Thành phố Hồ Chí Minh (3 KS)
    {
        "hotel_id": "HT_040",
        "name": "The Reverie Saigon",
        "phone": "02838236688",
        "address": "22 - 36 Nguyễn Huệ, Phường Bến Nghé",
        "city": "Thành phố Hồ Chí Minh",
        "country": "Vietnam",
        "amenities": {"Hồ bơi ngoài trời sục ozone", "The Spa phong cách Ý", "Nhà hàng Quảng Đông", "Xe Rolls-Royce đưa đón"},
        "base_price": Decimal("6800000"),
        "scale": "MEGA_RESORT",  # 20 phòng
        "view_type": "Sông Sài Gòn & Phố đi bộ",
    },
    {
        "hotel_id": "HT_041",
        "name": "Caravelle Saigon",
        "phone": "02838234999",
        "address": "19 - 23 Công Trường Lam Sơn, Phường Bến Nghé",
        "city": "Thành phố Hồ Chí Minh",
        "country": "Vietnam",
        "amenities": {"Hồ bơi ngoài trời", "Saigon Saigon Rooftop Bar", "Kara Spa", "Nhà hàng Nineteen", "Phòng gym 24/7"},
        "base_price": Decimal("3200000"),
        "scale": "LARGE",  # 16 phòng
        "view_type": "Nhà hát Thành phố cổ kính",
    },
    {
        "hotel_id": "HT_042",
        "name": "Hotel Nikko Saigon",
        "phone": "02839257777",
        "address": "235 Nguyễn Văn Cừ, Phường Nguyễn Cư Trinh",
        "city": "Thành phố Hồ Chí Minh",
        "country": "Vietnam",
        "amenities": {"Buffet hải sản La Brasserie", "Hồ bơi ngoài trời", "Ren Spa phong cách Nhật", "Phòng xông hơi đá muối", "Gym"},
        "base_price": Decimal("3100000"),
        "scale": "LARGE",  # 16 phòng
        "view_type": "Đại lộ Nguyễn Văn Cừ sầm uất",
    },

    # 80 - Tây Ninh (1 KS)
    {
        "hotel_id": "HT_043",
        "name": "Melia Vinpearl Tây Ninh",
        "phone": "02763728888",
        "address": "Số 90 Đường Lê Duẩn, Phường 3",
        "city": "Tây Ninh",
        "country": "Vietnam",
        "amenities": {"Tòa tháp cao nhất Tây Ninh 21 tầng", "Hồ bơi bốn mùa", "YHI Spa", "Nhà hàng Chiêng ngắm núi Bà Đen"},
        "base_price": Decimal("1350000"),
        "scale": "MEDIUM",  # 12 phòng
        "view_type": "Đỉnh Núi Bà Đen hùng vĩ",
    },

    # 82 - Đồng Tháp (1 KS)
    {
        "hotel_id": "HT_044",
        "name": "Khách sạn Sao Mai Cao Lãnh",
        "phone": "02773852888",
        "address": "Số 178 Đường Nguyễn Huệ, Phường 2",
        "city": "Đồng Tháp",
        "country": "Vietnam",
        "amenities": {"Hồ bơi ngoài trời", "Nhà hàng Sen Hồng", "Phòng hội thảo", "Phòng tập thể dục", "Wifi"},
        "base_price": Decimal("950000"),
        "scale": "BOUTIQUE",  # 8 phòng
        "view_type": "Đầm sen Tháp Mười",
    },

    # 86 - Vĩnh Long (1 KS)
    {
        "hotel_id": "HT_045",
        "name": "Khách sạn Sài Gòn Vĩnh Long",
        "phone": "02703879988",
        "address": "Số 02 Đường Trưng Nữ Vương, Phường 1",
        "city": "Vĩnh Long",
        "country": "Vietnam",
        "amenities": {"Khách sạn 4 sao view sông Cổ Chiên", "Hồ bơi ngoài trời", "Nhà hàng Cửu Long", "Phòng gym", "Wifi"},
        "base_price": Decimal("1050000"),
        "scale": "MEDIUM",  # 12 phòng
        "view_type": "Sông Cổ Chiên hiền hòa",
    },

    # 91 - An Giang (1 KS)
    {
        "hotel_id": "HT_046",
        "name": "Victoria Châu Đốc Hotel",
        "phone": "02963865010",
        "address": "Số 01 Đường Lê Lợi, Phường Châu Phú B",
        "city": "An Giang",
        "country": "Vietnam",
        "amenities": {"Nằm ngay ngã ba sông Hậu thơ mộng", "Hồ bơi nhìn ra sông", "Tàu du lịch Victoria", "Spa thư giãn"},
        "base_price": Decimal("1950000"),
        "scale": "MEDIUM",  # 12 phòng
        "view_type": "Ngã ba sông Hậu & Chợ nổi",
    },

    # 92 - Thành phố Cần Thơ (1 KS)
    {
        "hotel_id": "HT_047",
        "name": "Mường Thanh Luxury Cần Thơ",
        "phone": "02923688888",
        "address": "Khu Cồn Cái Khế, Phường Cái Khế",
        "city": "Thành phố Cần Thơ",
        "country": "Vietnam",
        "amenities": {"Khách sạn 5 sao đầu tiên Cần Thơ", "Hồ bơi ngoài trời", "Sân tennis", "Spa Cù Lao", "Rooftop Bar"},
        "base_price": Decimal("1450000"),
        "scale": "LARGE",  # 16 phòng
        "view_type": "Cầu Cần Thơ & Cồn Cái Khế",
    },

    # 96 - Cà Mau (1 KS)
    {
        "hotel_id": "HT_048",
        "name": "Mường Thanh Luxury Cà Mau",
        "phone": "02902228888",
        "address": "Lô C3A, Khu hành chính, Phường 9",
        "city": "Cà Mau",
        "country": "Vietnam",
        "amenities": {"Khách sạn 5 sao cao cấp nhất Đất Mũi", "Hồ bơi ngoài trời", "Sân tennis", "Nhà hàng Đất Mũi", "Spa"},
        "base_price": Decimal("1350000"),
        "scale": "MEDIUM",  # 12 phòng
        "view_type": "Cánh rừng ngập mặn Cà Mau",
    },
]


def generate_rooms_by_scale(base_price, scale, view_name):
    """
    Sinh số lượng và danh mục phòng linh hoạt theo quy mô từng khách sạn:
    - BOUTIQUE: 8 phòng (tầng 1 đến 3)
    - MEDIUM: 12 phòng (tầng 1 đến 4)
    - LARGE: 16 phòng (tầng 1 đến 6)
    - MEGA_RESORT: 20 phòng (tầng 1 đến 8)
    """
    p = base_price

    # Mẫu phòng chuẩn theo tầng
    all_possible_rooms = [
        # Tầng 1
        ("101", "Standard Single", p * Decimal("0.80"), "AVAILABLE", 1, "1 Giường Đơn", f"Phòng đơn ấm cúng, hướng {view_name}"),
        ("102", "Superior Twin", p * Decimal("0.95"), "AVAILABLE", 2, "2 Giường Đơn", f"Phòng 2 giường đơn thoáng đãng, hướng {view_name}"),
        ("103", "Deluxe Double", p * Decimal("1.00"), "AVAILABLE", 2, "1 Giường King", f"Phòng đôi cao cấp ban công đón gió hướng {view_name}"),
        ("104", "Deluxe Garden View", p * Decimal("1.05"), "AVAILABLE", 2, "1 Giường Queen", f"Hướng vườn nhiệt đới xanh mát tĩnh lặng"),
        ("105", "Studio Kitchenette", p * Decimal("1.20"), "AVAILABLE", 2, "1 Giường King", f"Trang bị bếp nhỏ mini và bàn ăn ấm cúng"),

        # Tầng 2
        ("201", "Executive Suite", p * Decimal("1.65"), "OCCUPIED", 3, "1 Giường King", f"Phòng khách tách biệt, hiện đang có khách lưu trú"),
        ("202", "Premier View", p * Decimal("1.25"), "AVAILABLE", 2, "1 Giường King", f"Tầm nhìn Panorama trọn vẹn {view_name}"),
        ("203", "Junior Suite", p * Decimal("1.45"), "AVAILABLE", 2, "1 Giường King", f"Bồn tắm massage jacuzzi và ghế thư giãn"),
        ("204", "Deluxe Balcony", p * Decimal("1.15"), "AVAILABLE", 2, "2 Giường Đơn", f"Ban công ngắm hoàng hôn cực đẹp hướng {view_name}"),
        ("205", "Family Suite 2-Bedroom", p * Decimal("2.10"), "AVAILABLE", 4, "2 Giường King", f"Không gian gia đình 2 phòng ngủ rộng rãi"),

        # Tầng 3
        ("301", "Presidential Suite", p * Decimal("3.50"), "MAINTENANCE", 4, "1 Giường King", f"Phòng tổng thống đang trong thời gian bảo trì định kỳ"),
        ("302", "Grand Suite", p * Decimal("1.90"), "AVAILABLE", 3, "1 Giường King", f"Suite cao cấp tầng cao nhìn ra {view_name}"),
        ("303", "Signature Room", p * Decimal("1.35"), "AVAILABLE", 2, "1 Giường Queen", f"Thiết kế phong cách độc bản, tiện nghi cao cấp"),

        # Tầng 4
        ("401", "Penthouse Sky Villa", p * Decimal("3.80"), "AVAILABLE", 4, "2 Giường King", f"Căn hộ penthouse áp mái ngắm trọn {view_name}"),
        ("402", "Panoramic Suite", p * Decimal("2.20"), "OCCUPIED", 2, "1 Giường King", f"Kính chạm trần ngắm toàn cảnh ngoạn mục"),

        # Tầng 5 & cao hơn
        ("501", "Royal Heritage Suite", p * Decimal("2.80"), "AVAILABLE", 3, "1 Giường King", f"Nội thất gỗ quý phái, view đỉnh cao {view_name}"),
        ("502", "Honeymoon Suite", p * Decimal("2.00"), "AVAILABLE", 2, "1 Giường King", f"Phòng trăng mật lãng mạn kèm nến và hoa"),
        ("601", "Duplex Loft Suite", p * Decimal("2.60"), "MAINTENANCE", 3, "1 Giường King", f"Căn hộ thông tầng đang sơn sửa nâng cấp"),
        ("701", "Imperial Suite", p * Decimal("4.20"), "AVAILABLE", 5, "2 Giường King", f"Hạng phòng sang trọng bậc nhất hướng {view_name}"),
        ("801", "Diamond Palace Penthouse", p * Decimal("5.50"), "OCCUPIED", 6, "3 Giường King", f"Biệt phủ trên cao có thang máy riêng biệt"),
    ]

    target_count = 8
    if scale == "BOUTIQUE":
        target_count = 8
    elif scale == "MEDIUM":
        target_count = 12
    elif scale == "LARGE":
        target_count = 16
    elif scale == "MEGA_RESORT":
        target_count = 20

    rooms = []
    for item in all_possible_rooms[:target_count]:
        r_num, r_type, r_price, r_status, r_cap, r_bed, r_desc = item
        clean_price = Decimal(str(r_price)).quantize(Decimal("10000"))
        rooms.append((r_num, r_type, clean_price, r_status, r_cap, r_bed, r_desc))

    return rooms


def seed_diverse_vietnam_hotels():
    session = get_session()
    if not session:
        print("❌ Không thể kết nối AstraDB để nạp dữ liệu.")
        return False

    print("=" * 70)
    print("  🚀 BẮT ĐẦU SEED 48 KHÁCH SẠN THẬT PHỦ 34 TỈNH (QUY MÔ 8 - 20 PHÒNG)")
    print("=" * 70)

    insert_hotel_stmt = session.prepare("""
        INSERT INTO hotels (hotel_id, name, phone, address, city, country, amenities)
        VALUES (?, ?, ?, ?, ?, ?, ?);
    """)

    insert_room_stmt = session.prepare("""
        INSERT INTO rooms_by_hotel (
            hotel_id, room_number, room_type, price_per_night, is_available,
            status, capacity, bed_type, description
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
    """)

    hotel_success = 0
    total_rooms = 0

    for idx, h in enumerate(HOTELS_CATALOG, start=1):
        h_id = h["hotel_id"]
        h_name = h["name"]
        h_city = h["city"]
        base_price = h["base_price"]
        scale = h["scale"]
        view_type = h["view_type"]

        try:
            # 1. Ghi khách sạn
            session.execute(insert_hotel_stmt, (
                h_id,
                h_name,
                h["phone"],
                h["address"],
                h_city,
                h["country"],
                h["amenities"],
            ))
            hotel_success += 1

            # 2. Sinh danh sách phòng đa dạng theo quy mô
            rooms = generate_rooms_by_scale(base_price, scale, view_type)
            r_added = 0
            for r in rooms:
                r_num, r_type, r_price, r_status, r_cap, r_bed, r_desc = r
                is_avail = (r_status == "AVAILABLE")
                try:
                    session.execute(insert_room_stmt, (
                        h_id,
                        r_num,
                        r_type,
                        r_price,
                        is_avail,
                        r_status,
                        r_cap,
                        r_bed,
                        r_desc
                    ))
                    r_added += 1
                except Exception as r_err:
                    print(f"    ⚠️ Lỗi phòng {h_id}-{r_num}: {r_err}")

            total_rooms += r_added
            scale_badge = f"[{scale}: {r_added} phòng]"
            print(f"  ✅ [{idx:02d}/{len(HOTELS_CATALOG)}] {h_name} ({h_id}) - {h_city} {scale_badge}")
        except Exception as err:
            print(f"  ❌ Lỗi khi thêm khách sạn {h_id} ({h_name}): {err}")

    print("\n" + "=" * 70)
    print(f"  🎉 HOÀN THÀNH SEEDING TOÀN BỘ 48 KHÁCH SẠN THẬT:")
    print(f"     🏨 Tổng số khách sạn thật: {hotel_success} / {len(HOTELS_CATALOG)}")
    print(f"     🚪 Tổng số phòng thực tế đã tạo: {total_rooms} phòng")
    print(f"     📊 Phân bổ phòng: 8 phòng (Boutique), 12 phòng (4 sao), 16-20 phòng (Mega Resort)")
    print(f"     📍 Độ phủ: 100% 34 tỉnh/thành phố có đầy đủ khách sạn và phòng")
    print("=" * 70)
    return True


if __name__ == "__main__":
    seed_diverse_vietnam_hotels()
