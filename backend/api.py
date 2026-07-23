import traceback
import os
import json

from flask import Flask, request, jsonify
from flask_cors import CORS
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from dotenv import load_dotenv

from secure_optimizations import secure_search
from search_mysql import (
    search_record as mysql_search_record,
    get_blind_index_bytes,
    MYSQL_COLUMN_MAP,
)
from mysql.connector import errors as mysql_errors
import mysql.connector

load_dotenv()

app = Flask(__name__)

# CORS: explicit origins for cross-device (frontend on laptop, backend on another).
# With supports_credentials=True, browser requires explicit origin (not "*").
CORS(
    app,
    resources={r"/*": {"origins": ["http://localhost:5173", "http://127.0.0.1:5173"]}},
    supports_credentials=True,
    allow_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "OPTIONS"],
)

ENCRYPTION_KEY = bytes.fromhex(os.getenv("ENCRYPTION_KEY_HEX"))

# Fields the frontend may send; all map to MySQL secure_vault columns
ALLOWED_FIELDS = ["account_id", "customer_name", "name"]


@app.before_request
def log_request():
    """Log every incoming request for debugging CORS and routing."""
    print(f"[REQUEST] {request.method} {request.path}")
    print(f"[ORIGIN]  {request.headers.get('Origin', '(none)')}")
    if request.method in ("POST", "PUT", "PATCH") and request.is_json:
        try:
            body = request.get_json(silent=True)
            print(f"[BODY]    {json.dumps(body) if body is not None else '(null)'}")
        except Exception:
            print("[BODY]    (failed to parse JSON)")
            traceback.print_exc()


@app.route("/health", methods=["GET", "OPTIONS"])
def health():
    """Lightweight health check for backend liveness."""
    if request.method == "OPTIONS":
        return "", 200
    return jsonify({"status": "backend_alive"}), 200


def get_db():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST"),
        user=os.getenv("MYSQL_USER"),
        password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DATABASE"),
        port=int(os.getenv("MYSQL_PORT")),
        auth_plugin="mysql_native_password",
    )


@app.route("/search_secure", methods=["POST", "OPTIONS"])
def search():
    try:
        if request.method == "OPTIONS":
            print("[CORS]    OPTIONS /search_secure -> 200")
            return "", 200

        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return jsonify({"error": "Invalid JSON body"}), 400

        if "field" not in data or "value" not in data:
            return jsonify({"error": "Missing field or value"}), 400

        field = str(data.get("field", "")).strip().lower()
        value = str(data.get("value", "")).strip()

        if not value:
            return jsonify({"error": "Search value cannot be empty"}), 400

        if field not in ALLOWED_FIELDS:
            return jsonify({"error": "Invalid search field"}), 400

        try:
            result = mysql_search_record(field, value)
        except mysql_errors.DatabaseError as e:
            print(f"[DB]      DatabaseError: {e}")
            return jsonify({"error": "Database unavailable", "detail": str(e)}), 503

        # ---------------- IF FOUND → DECRYPT AND RETURN RECORD ----------------
        if result == "YES":
            record = None
            try:
                column = MYSQL_COLUMN_MAP[field]
                blind_index = get_blind_index_bytes(value)

                conn = get_db()
                cursor = conn.cursor(dictionary=True)

                cursor.execute(
                    f"""
                    SELECT ciphertext_blob, nonce, auth_tag
                    FROM secure_vault
                    WHERE {column} = %s
                    LIMIT 1
                    """,
                    (blind_index,),
                )

                row = cursor.fetchone()
                cursor.close()
                conn.close()

                if row:
                    aesgcm = AESGCM(ENCRYPTION_KEY)
                    full_ciphertext = row['ciphertext_blob'] + row['auth_tag']
                    nonce = row['nonce']
                    decrypted_bytes = aesgcm.decrypt(nonce, full_ciphertext, None)
                    record = json.loads(decrypted_bytes.decode('utf-8'))
                    # Decryption verified; record not sent to frontend
            except Exception as decrypt_error:
                print("⚠ [DECRYPT] Decryption error:", decrypt_error)
                traceback.print_exc()
                return jsonify({"error": "Could not decrypt record", "detail": str(decrypt_error)}), 500

            return jsonify({"message": "Search successful"}), 200
        # ----------------------------------------------------

        if result == "NO":
            return jsonify({"message": "Search unsuccessful"}), 404

        return jsonify({"message": "Search unsuccessful"}), 404

    except Exception as e:
        print("[ERROR]   Unhandled exception in /search_secure:")
        traceback.print_exc()
        return jsonify({"error": "Internal server error", "detail": str(e)}), 500


@app.route("/search_secure", methods=["POST"])
def search_secure_route():
    try:
        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return jsonify({"error": "Invalid JSON body"}), 400

        if "field" not in data or "value" not in data:
            return jsonify({"error": "Missing field or value"}), 400

        field = data["field"].strip().lower()
        value = str(data["value"]).strip()

        if not value:
            return jsonify({"error": "Search value cannot be empty"}), 400

        if field not in ALLOWED_FIELDS:
            return jsonify({"error": "Invalid search field"}), 400

        try:
            result = secure_search(field, value, k_padding=5)
        except mysql_errors.DatabaseError as e:
            print(f"[DB]      DatabaseError (secure): {e}")
            return jsonify({"error": "Database unavailable", "detail": str(e)}), 503

        if result["found"]:
            return jsonify({
                "message": "Record found (secure mode)",
                "found": True,
                "padding_used": result["padding_count"],
                "match_type": result["match_type"]
            }), 200

        return jsonify({
            "message": "No record found (secure mode)",
            "found": False,
            "padding_used": result["padding_count"]
        }), 404

    except Exception as e:
        print("[ERROR]   Unhandled exception in search_secure_route:")
        traceback.print_exc()
        return jsonify({"error": "Internal server error", "detail": str(e)}), 500


if __name__ == "__main__":
    import socket
    host = "0.0.0.0"
    port = 5000
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            my_ip = s.getsockname()[0]
        print(f"API reachable from other devices at: http://{my_ip}:{port}")
    except Exception:
        print(f"API listening on port {port}. Use this machine's IPv4 in the URL from other laptops.")
    app.run(host=host, port=port, debug=True)