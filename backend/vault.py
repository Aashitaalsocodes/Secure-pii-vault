from db import get_connection
from crypto_utils import encrypt_record, generate_blind_index, decrypt_record

# BUG FIX #5: Whitelist maps field name -> actual column name.
# Never interpolate user-supplied 'field' directly into a query string.
_FIELD_TO_COLUMN = {
    "account_id":    "idx_account_id",
    "customer_name": "idx_customer_name",
}


def insert_record(account_id, customer_name, account_type, branch,
                  transaction_type, transaction_amount, account_balance, currency):

    # Step 1: Encrypt only PII fields
    encrypted = encrypt_record({
        "account_id":    account_id,
        "customer_name": customer_name,
    })

    # Step 2: Generate blind indexes for searchable PII fields
    idx_account_id    = generate_blind_index("account_id",    account_id)
    idx_customer_name = generate_blind_index("customer_name", customer_name)

    # Step 3: Store in DB
    conn   = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO secure_customers (
            ciphertext, nonce,
            idx_account_id, idx_customer_name,
            account_type, branch, transaction_type,
            transaction_amount, account_balance, currency
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        encrypted["ciphertext"],
        encrypted["nonce"],
        idx_account_id,
        idx_customer_name,
        account_type,
        branch,
        transaction_type,
        transaction_amount,
        account_balance,
        currency,
    ))

    conn.commit()
    conn.close()


def search_record(field, value):
    # BUG FIX #5: look up column name from whitelist instead of
    # interpolating 'field' directly into the SQL string.
    if field not in _FIELD_TO_COLUMN:
        print(f"[✗] Invalid search field: {field}")
        return None

    column       = _FIELD_TO_COLUMN[field]
    search_index = generate_blind_index(field, value)

    conn   = get_connection()
    cursor = conn.cursor()

    # Safe: column name comes from our whitelist, not from user input
    cursor.execute(
        f"SELECT * FROM secure_customers WHERE {column} = ?",
        (search_index,),
    )
    row = cursor.fetchone()
    conn.close()

    if row is None:
        print(f"[✗] No record found for {field}: {value}")
        return None

    print(f"[✓] Match found for {field}: {value}")
    return row


def get_decrypted_record(field, value):
    # NOTE: depends on db.get_connection() setting row_factory = sqlite3.Row
    # so that row["column"] access works. db.py already does this.
    row = search_record(field, value)

    if row is None:
        return None

    decrypted = decrypt_record(row["ciphertext"], row["nonce"])

    result = {
        "account_id":         decrypted["account_id"],
        "customer_name":      decrypted["customer_name"],
        "account_type":       row["account_type"],
        "branch":             row["branch"],
        "transaction_type":   row["transaction_type"],
        "transaction_amount": row["transaction_amount"],
        "account_balance":    row["account_balance"],
        "currency":           row["currency"],
    }

    print(f"[✓] Decrypted Record: {result}")
    return result
