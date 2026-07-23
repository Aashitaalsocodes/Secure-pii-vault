from search_mysql import get_db
try:
    conn = get_db()
    print("connected?", conn.is_connected())
    conn.close()
except Exception as e:
    print("DB connect error:", repr(e))