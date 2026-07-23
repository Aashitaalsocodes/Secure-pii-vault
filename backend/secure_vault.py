import os
import re
import json
import hmac
import hashlib
import unicodedata
import socket
import mysql.connector
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from mysql.connector import Error
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# 1. INITIALIZATION
load_dotenv()
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}) 

try:
    MASTER_KEY = bytes.fromhex(os.getenv("ENCRYPTION_KEY_HEX"))
    INDEX_KEY = bytes.fromhex(os.getenv("INDEX_KEY_HEX"))
    print("✅ [INIT] Encryption and Index keys loaded successfully.")
except (TypeError, ValueError, AttributeError) as e:
    print(f"❌ [INIT] Critical Error: Missing keys in .env: {e}")
    exit(1)

# 2. UTILITY FUNCTIONS
def normalize_name(name):
    normalized = str(name).lower()
    normalized = unicodedata.normalize('NFKC', normalized)
    normalized = normalized.strip()
    normalized = re.sub(r'\s+', ' ', normalized)
    return normalized

def get_blind_index(value):
    return hmac.new(INDEX_KEY, str(value).encode(), hashlib.sha256).digest()

def get_db():
    # Using your specific IP and credentials
    return mysql.connector.connect(
        host="172.16.9.29",
        user="remote_user",
        password="2006",
        database="hackathon",
        port=3306,
        auth_plugin='mysql_native_password'
    )

# 3. SECURE SEARCH ENDPOINT
@app.route('/secure-search', methods=['POST'])
def secure_search():
    connection = None
    print("\n" + "-"*30)
    print("📥 [NEW REQUEST] Received search request...")
    
    try:
        data = request.get_json()
        if not data:
            print("⚠️ [WARN] No JSON payload received.")
            return jsonify({"error": "No data provided"}), 400

        field = data.get("field")
        value = data.get("value")
        role = str(data.get("role", "user")).lower().strip()

        print(f"📊 [PARAMS] Field: '{field}' | Value: '{value}' | Role: '{role}'")

        if not field or not value:
            print("⚠️ [WARN] Missing required fields in JSON.")
            return jsonify({"error": "Missing field or value"}), 400

        # --- NORMALIZATION ---
        search_value = value
        if field == "customer_name" or field == "name":
            search_value = normalize_name(value)
            print(f"🔄 [NORMALIZE] Formatted name to: '{search_value}'")
            target_column = "idx_name"
        elif field == "account_id":
            target_column = "idx_account_id"
            print(f"🔄 [NORMALIZE] Using raw Account ID: '{search_value}'")
        else:
            print(f"❌ [ERROR] Unsupported search field: {field}")
            return jsonify({"error": "Invalid search field"}), 400

        # --- HASHING ---
        blind_index_bytes = get_blind_index(search_value)
        print(f"🔐 [HASHING] Blind Index generated: {blind_index_bytes.hex()[:16]}...")

        # --- DATABASE QUERY ---
        print(f"🔍 [DB] Querying 'secure_vault' where {target_column} matches index...")
        connection = get_db()
        cursor = connection.cursor(dictionary=True)
        
        query = f"SELECT ciphertext_blob, nonce, auth_tag FROM secure_vault WHERE {target_column} = %s LIMIT 1;"
        cursor.execute(query, (blind_index_bytes,))
        row = cursor.fetchone()

        if not row:
            print("🚫 [RESULT] No records found for this index.")
            return jsonify({"status": "not_found", "message": "Data not found"}), 404

        print("✨ [RESULT] Record found! Proceeding to decryption...")

        # --- DECRYPTION ---
        try:
            aesgcm = AESGCM(MASTER_KEY)
            full_ciphertext = row['ciphertext_blob'] + row['auth_tag']
            decrypted_bytes = aesgcm.decrypt(row['nonce'], full_ciphertext, None)
            decrypted_data = json.loads(decrypted_bytes.decode('utf-8'))
            print("🔓 [DECRYPT] Success! Sensitive data reconstructed.")
        except Exception as decrypt_err:
            print(f"❌ [DECRYPT] Failed to decrypt record: {decrypt_err}")
            return jsonify({"error": "Decryption failed"}), 500

        # --- RBAC LOGIC ---
        if role == "admin":
            print("👑 [RBAC] Role is ADMIN. Sending full decrypted data.")
            return jsonify({
                "status": "ok",
                "message": "Search successful",
                "data": decrypted_data
            }), 200
        else:
            print("👤 [RBAC] Role is USER. Redacting sensitive data (sending success only).")
            return jsonify({
                "status": "ok",
                "message": "Search successful"
            }), 200

    except Error as db_err:
        print(f"❌ [DB ERROR] MySQL connection or query failed: {db_err}")
        return jsonify({"error": "Database error"}), 500
    except Exception as e:
        print(f"🔥 [CRITICAL] Unhandled server error: {e}")
        return jsonify({"error": "Internal server error"}), 500
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()
            print("🔌 [DB] Connection closed.")
        print("-"*30)

# 4. RUN SERVER
if __name__ == "__main__":
    port = 5000
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        local_ip = "127.0.0.1"

    print("\n" + "="*60)
    print(f"🚀 SECURE VAULT BACKEND ACTIVE")
    print(f"📡 ACCESS FROM OTHER DEVICES: http://{local_ip}:{port}/secure-search")
    print("="*60 + "\n")

    app.run(host='0.0.0.0', port=port, debug=True)