import os
import hmac
import hashlib
import json
from typing import List

from dotenv import load_dotenv
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import mysql.connector

from search_mysql import (
    get_db,
    get_blind_index,
    get_blind_index_bytes,
    MYSQL_COLUMN_MAP,
)

load_dotenv()

INDEX_KEY       = bytes.fromhex(os.getenv("INDEX_KEY_HEX", ""))
ENCRYPTION_KEY  = bytes.fromhex(os.getenv("ENCRYPTION_KEY_HEX", ""))

TRIGRAM_MIN_LEN = 3


def get_trigrams(value: str) -> List[str]:
    s = (value or "").strip()
    if len(s) < TRIGRAM_MIN_LEN:
        return []
    return [s[i: i + 3] for i in range(len(s) - 2)]


def get_trigram_blind_indexes(value: str) -> List[bytes]:
    if not INDEX_KEY:
        return []
    trigrams = get_trigrams(value)
    return [
        hmac.new(INDEX_KEY, tg.encode("utf-8"), hashlib.sha256).digest()
        for tg in trigrams
    ]


def _decrypt_row(ciphertext_blob, nonce, auth_tag) -> dict:
    aesgcm = AESGCM(ENCRYPTION_KEY)
    # Cast to bytes in case MySQL returns memoryview / bytearray
    full_ciphertext = bytes(ciphertext_blob) + bytes(auth_tag)
    decrypted_bytes = aesgcm.decrypt(bytes(nonce), full_ciphertext, None)
    return json.loads(decrypted_bytes.decode("utf-8"))


def secure_search(
    field: str,
    value: str,
    k_padding: int = 5,
) -> dict:
    if field not in MYSQL_COLUMN_MAP:
        return {"found": False, "padding_count": k_padding, "match_type": "exact"}

    column     = MYSQL_COLUMN_MAP[field]
    exact_blind = get_blind_index(value)

    conn   = get_db()
    cursor = conn.cursor(dictionary=True)

    # 1. Try exact match
    cursor.execute(
        f"""
        SELECT ciphertext_blob, nonce, auth_tag
        FROM secure_vault
        WHERE {column} = %s
        LIMIT 1
        """,
        (exact_blind,),
    )
    match_row = cursor.fetchone()

    if match_row is not None:
        first_row = match_row
        found = True
    else:
        # BUG FIX #8: guard against empty vault — fetchone() returns None
        cursor.execute(
            """
            SELECT ciphertext_blob, nonce, auth_tag
            FROM secure_vault
            ORDER BY RAND()
            LIMIT 1
            """,
        )
        first_row = cursor.fetchone()   # may be None if vault is empty
        found = False

    # 2. Fetch k dummy rows for traffic-analysis padding
    cursor.execute(
        """
        SELECT ciphertext_blob, nonce, auth_tag
        FROM secure_vault
        ORDER BY RAND()
        LIMIT %s
        """,
        (k_padding,),
    )
    _dummy_rows = cursor.fetchall()
    cursor.close()
    conn.close()

    # 3. Verify decryption if we have a real or fallback row
    if found and first_row:
        try:
            _decrypt_row(
                first_row["ciphertext_blob"],
                first_row["nonce"],
                first_row["auth_tag"],
            )
        except Exception:
            found = False
    # BUG FIX #8 cont.: if first_row is None (empty vault) we simply skip decrypt

    return {
        "found":         found,
        "padding_count": k_padding,
        "match_type":    "exact",
    }
