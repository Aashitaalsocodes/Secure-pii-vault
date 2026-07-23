import os
import json
import base64
import hashlib
import hmac
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from dotenv import load_dotenv

load_dotenv()

AES_KEY   = bytes.fromhex(os.getenv("ENCRYPTION_KEY_HEX"))
INDEX_KEY = bytes.fromhex(os.getenv("INDEX_KEY_HEX"))


def get_blind_index_bytes(value: str) -> bytes:
    """
    HMAC(key, normalized_value).
    BUG FIX #4: normalize with strip().lower() to match search_mysql.get_blind_index().
    Without this, searches fail because insert and lookup produce different hashes.
    """
    normalized = str(value).strip().lower()
    return hmac.new(INDEX_KEY, normalized.encode(), hashlib.sha256).digest()


def generate_blind_index(field: str, value: str) -> str:
    """
    Blind index for SQLite vault: message = field:normalized_value.
    BUG FIX #4: normalize value here too for consistency.
    Returns base64 string for storing in TEXT columns.
    """
    normalized = str(value).strip().lower()
    message = f"{field}:{normalized}".encode()
    token = hmac.new(INDEX_KEY, message, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(token).decode()


def encrypt_record(json_data: dict) -> dict:
    aesgcm    = AESGCM(AES_KEY)
    plaintext = json.dumps(json_data, sort_keys=True).encode()
    nonce     = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)

    return {
        "ciphertext": base64.urlsafe_b64encode(ciphertext).decode(),
        "nonce":      base64.urlsafe_b64encode(nonce).decode(),
    }


def decrypt_record(ciphertext: str, nonce: str) -> dict:
    aesgcm            = AESGCM(AES_KEY)
    decoded_ciphertext = base64.urlsafe_b64decode(ciphertext)
    decoded_nonce      = base64.urlsafe_b64decode(nonce)
    plaintext          = aesgcm.decrypt(decoded_nonce, decoded_ciphertext, None)
    return json.loads(plaintext.decode())
