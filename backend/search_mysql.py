import os
import hmac
import hashlib
import mysql.connector
from mysql.connector import errors as mysql_errors
from dotenv import load_dotenv

load_dotenv()

INDEX_KEY = bytes.fromhex(os.getenv("INDEX_KEY_HEX"))

MYSQL_COLUMN_MAP = {
    "account_id":       "idx_account_id",
    "name":             "idx_name",
    "customer_name":    "idx_name",
    "branch":           "idx_branch",
    "transaction_type": "idx_transaction_type",
}


def get_blind_index(value) -> bytes:
    # BUG FIX #4: normalize consistently (strip + lower) so blind indexes
    # always match regardless of where they are generated.
    normalized = str(value).strip().lower()
    return hmac.new(INDEX_KEY, normalized.encode(), hashlib.sha256).digest()


# Alias used by app.py and secure_optimizations.py
get_blind_index_bytes = get_blind_index


def get_db():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),   # BUG FIX #1: was MYSQL_DATABASE
        database=os.getenv("MYSQL_DATABASE"),
        port=int(os.getenv("MYSQL_PORT")),
        auth_plugin="mysql_native_password",
    )


def search_record(field: str, value: str) -> str:
    if field not in MYSQL_COLUMN_MAP:
        return "INVALID FIELD"

    column = MYSQL_COLUMN_MAP[field]
    blind_index = get_blind_index(value)

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        f"SELECT 1 FROM secure_vault WHERE {column} = %s LIMIT 1",
        (blind_index,),
    )

    row = cursor.fetchone()
    cursor.close()
    conn.close()

    return "YES" if row else "NO"


if __name__ == "__main__":
    try:
        print("Search by account_id:", search_record("account_id", "ACC00001"))
        print("Search by name:", search_record("name", "Amanda Pugh"))
    except mysql_errors.DatabaseError as e:
        print(f"MySQL connection failed: {e}")
