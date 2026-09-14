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
    TODO (Như):
    1. Lấy thông tin cấu hình từ file .env:
       - ASTRA_DB_SECURE_BUNDLE_PATH (đường dẫn tới file secure-connect-*.zip)
       - ASTRA_DB_TOKEN (Token dạng AstraCS:...)
       - ASTRA_DB_KEYSPACE (hotel_ks)
    2. Sử dụng thư viện cassandra-driver để kết nối:
       from cassandra.cluster import Cluster
       from cassandra.auth import PlainTextAuthProvider
    3. Trả về session để các Service thực hiện truy vấn CQL.
    """
    global _session
    if _session is not None:
        return _session

    bundle_path = os.getenv("ASTRA_DB_SECURE_BUNDLE_PATH")
    token = os.getenv("ASTRA_DB_TOKEN")
    keyspace = os.getenv("ASTRA_DB_KEYSPACE", "hotel_ks")

    # TODO (Như): Bỏ comment và hoàn thiện đoạn kết nối bên dưới khi có file zip bundle
    """
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
    """

    print("⚠️  Chưa cấu hình kết nối AstraDB (Đang chạy ở chế độ khung sườn).")
    return None
