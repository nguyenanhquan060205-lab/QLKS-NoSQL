# ====================================================================
# SERVICES: ĐỊA CHỈ & TỈNH THÀNH VIỆT NAM (Dữ liệu từ docs/provinces.json)
# PHỤ TRÁCH: ĐỊNH (QLKS-04 ĐẾN QLKS-06)
# ====================================================================

import json
import unicodedata
from pathlib import Path

_PROVINCES_CACHE = None
_WARDS_CACHE = None


def remove_accents(input_str):
    """Loại bỏ dấu tiếng Việt để phục vụ so sánh và tìm kiếm không dấu."""
    if not input_str:
        return ""
    s = unicodedata.normalize("NFD", input_str)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.replace("đ", "d").replace("Đ", "D")
    return s.lower()


def _parse_ward_name(raw_name):
    """
    Tách tiền tố hành chính (Phường/Xã/Thị trấn) để lấy tên cốt lõi của xã/phường.
    Ví dụ: 'Xã Dầu Tiếng' -> ('Dầu Tiếng', 'Xã', 'Dầu Tiếng (Xã)')
    """
    if not raw_name:
        return "", "", ""
    raw_clean = raw_name.strip()
    for prefix in ("Phường ", "Xã ", "Thị trấn ", "Thị Trấn "):
        if raw_clean.startswith(prefix):
            core = raw_clean[len(prefix):].strip()
            ptype = prefix.strip()
            return core, ptype, f"{core} ({ptype})"
    return raw_clean, "", raw_clean


def _load_location_data():
    """Tải dữ liệu 34 tỉnh thành và phường/xã từ docs/provinces.json vào bộ nhớ cache."""
    global _PROVINCES_CACHE, _WARDS_CACHE
    if _PROVINCES_CACHE is not None and _WARDS_CACHE is not None:
        return

    json_path = Path(__file__).resolve().parent.parent / "docs" / "provinces.json"
    if not json_path.exists():
        _PROVINCES_CACHE = []
        _WARDS_CACHE = {}
        return

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            tables = json.load(f)

        provinces = []
        wards_by_prov = {}

        for table in tables:
            t_name = table.get("name")
            if t_name == "provinces":
                for row in table.get("data", []):
                    raw_name = (row.get("name") or "").strip()
                    # Bỏ tiền tố 'Thành phố ' trong clean_name để hiển thị gọn gàng (Hà Nội, Hồ Chí Minh, Đà Nẵng...)
                    clean_name = raw_name
                    if clean_name.startswith("Thành phố "):
                        clean_name = clean_name.replace("Thành phố ", "", 1).strip()

                    provinces.append({
                        "code": row.get("province_code"),
                        "name": raw_name,
                        "clean_name": clean_name,
                        "short_name": row.get("short_name"),
                        "place_type": row.get("place_type"),
                    })
            elif t_name == "wards":
                for row in table.get("data", []):
                    p_code = row.get("province_code")
                    if p_code not in wards_by_prov:
                        wards_by_prov[p_code] = []

                    raw_ward = (row.get("name") or "").strip()
                    core, ptype, display_name = _parse_ward_name(raw_ward)

                    wards_by_prov[p_code].append({
                        "code": row.get("ward_code"),
                        "name": raw_ward,          # Lưu DB: 'Xã Dầu Tiếng'
                        "core_name": core,         # Tên gốc: 'Dầu Tiếng'
                        "display_name": display_name,  # Hiển thị: 'Dầu Tiếng (Xã)'
                        "prefix": ptype,
                    })

        # Sắp xếp các xã/phường theo tên cốt lõi A-Z để khi gõ chữ cái đầu sẽ nhảy tới đúng mục
        for p_code in wards_by_prov:
            wards_by_prov[p_code].sort(
                key=lambda w: (remove_accents(w["core_name"]), w["core_name"])
            )

        _PROVINCES_CACHE = provinces
        _WARDS_CACHE = wards_by_prov
    except Exception as e:
        print(f"Lỗi khi nạp dữ liệu tỉnh thành từ provinces.json: {e}")
        _PROVINCES_CACHE = []
        _WARDS_CACHE = {}


def get_all_provinces():
    """Trả về danh sách 34 tỉnh thành sau sáp nhập."""
    _load_location_data()
    return _PROVINCES_CACHE or []


def get_wards_by_province(province_code):
    """Trả về danh sách phường/xã đã sắp xếp A-Z theo tên cốt lõi."""
    _load_location_data()
    return (_WARDS_CACHE or {}).get(str(province_code), [])
