import sqlite3
import os
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "pii_vault.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        DROP TABLE IF EXISTS secure_customers;

        CREATE TABLE IF NOT EXISTS secure_customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            -- Encrypted PII blob
            ciphertext          TEXT NOT NULL,
            nonce               TEXT NOT NULL,

            -- Blind indexes for searching
            idx_account_id      TEXT NOT NULL,
            idx_customer_name   TEXT NOT NULL,

            -- Non-PII fields stored as plain text
            account_type        TEXT,
            branch              TEXT,
            transaction_type    TEXT,
            transaction_amount  REAL,
            account_balance     REAL,
            currency            TEXT,

            created_at          DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS ix_account_id    ON secure_customers(idx_account_id);
        CREATE INDEX IF NOT EXISTS ix_customer_name ON secure_customers(idx_customer_name);
    """)

    conn.commit()
    conn.close()
    print("[✓] Database re-initialized: secure_customers table created.")

if __name__ == "__main__":
    init_db()
