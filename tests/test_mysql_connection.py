"""
Run this to verify you can reach the teammate's MySQL server.
No crypto or vault logic — just connection test.
"""
import os
from dotenv import load_dotenv

load_dotenv()

def test_connection():
    try:
        import mysql.connector
        conn = mysql.connector.connect(
            host=os.getenv("MYSQL_HOST", "172.16.9.29"),
            user=os.getenv("MYSQL_USER", "remote_user"),
            password=os.getenv("MYSQL_PASSWORD", "2006"),
            database=os.getenv("MYSQL_DATABASE", "hackathon"),
            port=int(os.getenv("MYSQL_PORT", "3306")),
            auth_plugin="mysql_native_password",
            connection_timeout=5,
        )
        conn.ping(reconnect=False)
        conn.close()
        print("Connection successful.")
        return True
    except Exception as e:
        print("Connection failed:", e)
        return False


if __name__ == "__main__":
    test_connection()
