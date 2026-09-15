# ====================================================================
# DATABASE MODULE: KẾT NỐI DATASTAX ASTRADB / CASSANDRA
# PHỤ TRÁCH: NHƯ (Hạ tầng & Cấu hình)
# ====================================================================

import os
from dotenv import load_dotenv

load_dotenv()

# Biến lưu session toàn cục
_session = None

def get_session():
    """
    Kết nối tới AstraDB bằng cassandra-driver, dùng Secure Connect Bundle + Token
    lấy từ file .env (xem hướng dẫn trong .env.example).
    Session được cache lại (biến _session) để không phải kết nối lại mỗi request.
    """
    global _session
    if _session is not None:
        return _session

    bundle_path = os.getenv("ASTRA_DB_SECURE_BUNDLE_PATH")
    token = os.getenv("ASTRA_DB_TOKEN")
    keyspace = os.getenv("ASTRA_DB_KEYSPACE", "hotel_ks")

    if not bundle_path or not token:
        print("⚠️  Chưa cấu hình kết nối AstraDB (thiếu ASTRA_DB_SECURE_BUNDLE_PATH hoặc ASTRA_DB_TOKEN trong .env).")
        return None

    if not os.path.exists(bundle_path):
        print(f"❌ Không tìm thấy Secure Connect Bundle tại: {bundle_path}")
        return None

    try:
        from cassandra.cluster import Cluster
        from cassandra.auth import PlainTextAuthProvider

        cloud_config = {'secure_connect_bundle': bundle_path}
        auth_provider = PlainTextAuthProvider('token', token)
        cluster = Cluster(cloud=cloud_config, auth_provider=auth_provider)
        _session = cluster.connect(keyspace)
        print("✅ Kết nối AstraDB thành công!")
        return _session
    except Exception as e:
        print(f"❌ Lỗi kết nối AstraDB: {e}")
        return None


if __name__ == "__main__":
    # Chạy: python database/db.py  ->  để tự test kết nối độc lập (đúng yêu cầu AC của QLKS-02)
    s = get_session()
    if s:
        print("Đã sẵn sàng để truy vấn keyspace hotel_ks.")