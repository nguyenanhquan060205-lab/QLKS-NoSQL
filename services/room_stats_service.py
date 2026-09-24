# ====================================================================
# SERVICES: COUNTER THỐNG KÊ TRẠNG THÁI PHÒNG (room_status_counts_by_hotel)
# PHỤ TRÁCH: NHƯ
#
# Dashboard cần "mỗi khách sạn có bao nhiêu phòng trống / đang thuê / bảo trì".
# Trước đây phải quét toàn bảng rooms_by_hotel rồi đếm ở Python. Theo nguyên tắc
# query-first của Cassandra, con số này được gộp sẵn vào một bảng COUNTER, cập
# nhật ngay tại lúc trạng thái phòng thay đổi, nên dashboard chỉ đọc 1 dòng / KS.
#
# Chỉ 2 hàm của room_service ghi vào đây: create_room() và change_room_status().
# Mọi luồng đặt phòng / trả phòng của các module khác đều đổi trạng thái phòng
# qua change_room_status(), nên không phải sửa code của ai khác.
#
# Hai giới hạn của counter mà code này phải tính tới:
#   1. Counter KHÔNG được nằm chung BATCH với lệnh thường -> ghi riêng, sau khi
#      UPDATE rooms_by_hotel đã thành công.
#   2. Counter có thể lệch (ghi lỗi giữa chừng, script seed ghi thẳng vào bảng
#      phòng). Vì vậy có reconcile(): đếm lại từ rooms_by_hotel rồi cộng/trừ phần
#      chênh — scripts/sync_room_status_counts.py gọi hàm này.
#
# Lỗi ghi counter chỉ in cảnh báo, KHÔNG raise: thống kê lệch thì đồng bộ lại
# được, còn làm hỏng luồng đặt phòng vì thống kê thì không chấp nhận được.
# ====================================================================

STATUS_COLUMNS = {
    "AVAILABLE": "available_rooms",
    "OCCUPIED": "occupied_rooms",
    "MAINTENANCE": "maintenance_rooms",
}
COUNT_FIELDS = ("total_rooms", "available_rooms", "occupied_rooms", "maintenance_rooms")

# Một câu UPDATE duy nhất cho mọi thay đổi: truyền phần chênh (có thể âm hoặc 0)
# cho từng cột. Counter chỉ hỗ trợ "cột = cột + n", không gán thẳng được giá trị.
_UPDATE_CQL = """
    UPDATE room_status_counts_by_hotel
    SET total_rooms = total_rooms + ?,
        available_rooms = available_rooms + ?,
        occupied_rooms = occupied_rooms + ?,
        maintenance_rooms = maintenance_rooms + ?
    WHERE hotel_id = ?;
"""


def room_status_of(row):
    """Trạng thái của 1 dòng rooms_by_hotel; dòng cũ chưa có cột status thì suy từ is_available."""
    status = getattr(row, "status", None)
    if status in STATUS_COLUMNS:
        return status
    return "AVAILABLE" if getattr(row, "is_available", False) else "OCCUPIED"


def _apply_delta(session, hotel_id, delta):
    """Cộng dict delta {tên_cột: số} vào counter của hotel_id. Trả True nếu ghi được."""
    if not session or not hotel_id or not any(delta.values()):
        return False
    try:
        stmt = session.prepare(_UPDATE_CQL)
        session.execute(stmt, tuple(int(delta.get(f, 0)) for f in COUNT_FIELDS) + (str(hotel_id),))
        return True
    except Exception as error:
        print(f"⚠️ [Counter phòng] Không cập nhật được counter của {hotel_id}: {error}. "
              "Chạy scripts/sync_room_status_counts.py để đồng bộ lại.")
        return False


def record_room_created(session, hotel_id, status="AVAILABLE"):
    """Phòng mới: +1 tổng phòng và +1 ở cột trạng thái ban đầu."""
    column = STATUS_COLUMNS.get(status)
    if not column:
        return False
    return _apply_delta(session, hotel_id, {"total_rooms": 1, column: 1})


def record_status_change(session, hotel_id, old_status, new_status):
    """Đổi trạng thái: -1 ở cột cũ, +1 ở cột mới. Tổng phòng không đổi."""
    old_col = STATUS_COLUMNS.get(old_status)
    new_col = STATUS_COLUMNS.get(new_status)
    if not old_col or not new_col or old_col == new_col:
        return False
    return _apply_delta(session, hotel_id, {old_col: -1, new_col: 1})


def get_counts(session):
    """
    Đọc toàn bộ counter: {hotel_id: {total_rooms, available_rooms, ...}}.
    Bảng chỉ có 1 dòng / khách sạn nên đọc hết vẫn rất nhẹ.
    Trả None nếu bảng chưa tạo hoặc chưa có dữ liệu — dashboard sẽ lùi về quét bảng phòng.
    """
    if not session:
        return None
    try:
        rows = list(session.execute(
            "SELECT hotel_id, total_rooms, available_rooms, occupied_rooms, maintenance_rooms "
            "FROM room_status_counts_by_hotel;"
        ))
    except Exception as error:
        print(f"⚠️ [Counter phòng] Chưa đọc được bảng counter, lùi về quét rooms_by_hotel: {error}")
        return None
    if not rows:
        return None
    return {
        r.hotel_id: {f: int(getattr(r, f, None) or 0) for f in COUNT_FIELDS}
        for r in rows
    }


def count_from_rooms(session, hotel_ids=None):
    """Đếm THẬT từ rooms_by_hotel (quét toàn bảng) — nguồn gốc để đối chiếu/đồng bộ counter."""
    actual = {}
    for r in session.execute("SELECT hotel_id, is_available, status FROM rooms_by_hotel;"):
        hid = getattr(r, "hotel_id", None)
        if hotel_ids is not None and hid not in hotel_ids:
            continue
        counts = actual.setdefault(hid, dict.fromkeys(COUNT_FIELDS, 0))
        counts["total_rooms"] += 1
        counts[STATUS_COLUMNS[room_status_of(r)]] += 1
    return actual


def reconcile(session, apply=True):
    """
    Đưa counter về đúng số thật trong rooms_by_hotel.

    Counter không gán thẳng được giá trị, nên với mỗi khách sạn: đọc counter hiện
    tại, tính phần chênh so với số thật, rồi cộng phần chênh đó. Khách sạn không
    còn trong bảng hotels thì xóa dòng counter của nó.

    apply=False: chỉ báo cáo chênh lệch, không ghi gì.
    Trả về list (hotel_id, {cột: chênh}) cho các khách sạn bị lệch, và list hotel_id đã xóa.
    """
    hotel_ids = {r.hotel_id for r in session.execute("SELECT hotel_id FROM hotels;")}
    actual = count_from_rooms(session, hotel_ids)
    current = get_counts(session) or {}

    drifted = []
    for hid in hotel_ids:
        want = actual.get(hid, dict.fromkeys(COUNT_FIELDS, 0))
        have = current.get(hid, dict.fromkeys(COUNT_FIELDS, 0))
        delta = {f: want[f] - have[f] for f in COUNT_FIELDS}
        if any(delta.values()):
            drifted.append((hid, delta))
            if apply:
                _apply_delta(session, hid, delta)

    orphans = sorted(hid for hid in current if hid not in hotel_ids)
    if apply and orphans:
        stmt = session.prepare("DELETE FROM room_status_counts_by_hotel WHERE hotel_id = ?;")
        for hid in orphans:
            session.execute(stmt, (hid,))

    return drifted, orphans
