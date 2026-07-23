# Copilot / AI Agent Instructions — secure_pii_vault

Purpose: concise, actionable guidance for AI coding agents to be productive in this repository.

- **Big picture**: This project implements two vault modes:
  - a local SQLite-based vault used by `vault.py` / `db.py` for small-scale testing and ingestion ([vault.py](vault.py), [db.py](db.py)).
  - a production-like MySQL-backed secure vault with HMAC blind indexes and AES-GCM encryption used by `secure_vault.py` and accessed by the API in `api.py` ([secure_vault.py](secure_vault.py), [api.py](api.py)).

- **Primary responsibilities of each area**:
  - `crypto_utils.py`: canonical blind-index and AES-GCM helpers for the SQLite path (base64-encoded ciphertext + nonce). Use these helpers when working on the local vault flow.
  - `search_mysql.py`: MySQL blind-index helpers and DB connector for the MySQL path (returns raw bytes). Note alias `get_blind_index_bytes` is provided for compatibility.
  - `secure_optimizations.py`: implements secure search padding (k-1 dummy rows) and trigram blind-index helpers for substring search.
  - `api.py`: Flask API that orchestrates search requests and decrypts records only for verification or admin flows.
  - `load_data.py` / `main.py`: helpers to populate the local SQLite vault and smoke-run example flows.

- **Key dataflow & security decisions to respect**:
  - Blind indexes are HMACs using `INDEX_KEY`. Normalization must be `strip().lower()` consistently (see `crypto_utils.get_blind_index_bytes` and `search_mysql.get_blind_index`).
  - AES-GCM `ENCRYPTION_KEY` is used for encrypt/decrypt; MySQL stores ciphertext blob + separate auth_tag while SQLite path stores base64 ciphertext + nonce via `crypto_utils`.
  - Never interpolate user-supplied `field` into SQL — use the repository whitelist maps (`_FIELD_TO_COLUMN` in `vault.py`, `MYSQL_COLUMN_MAP` in `search_mysql.py`).
  - `secure_optimizations.secure_search` pads queries by fetching `k_padding` dummy rows to mitigate traffic analysis. Preserve this behavior when modifying search logic.

- **Developer workflows / commands (discoverable from files)**:
  - Set environment keys in `.env` (required): `ENCRYPTION_KEY_HEX`, `INDEX_KEY_HEX`, and MySQL vars `MYSQL_HOST`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE`, `MYSQL_PORT`.
  - Run local API (dev): `python api.py` (Flask debug on port 5000).
  - Run standalone secure vault (dev MySQL sim): `python secure_vault.py`.
  - Initialize local SQLite DB: `python db.py` (calls `init_db`).
  - Load sample dataset into local vault: `python load_data.py`.
  - Example quick-run script: `python main.py` demonstrates `insert_record` and `get_decrypted_record` flows.
  - Tests / checks are lightweight scripts: run `python test_mysql_connection.py` and `python test_search_existing.py` to validate DB connectivity and search logic.

- **Project-specific conventions & gotchas**:
  - Two vault models coexist (SQLite vs MySQL). Pay attention to which functions you change — `crypto_utils` targets SQLite storage format (base64 strings), while `search_mysql` and `secure_optimizations` work with raw bytes from MySQL.
  - Normalization is critical. When adding any new blind-index generation or lookup path, call the existing `get_blind_index_bytes`/`generate_blind_index` helpers instead of reimplementing.
  - When decrypting MySQL rows, callers must concat `ciphertext_blob + auth_tag` before `AESGCM.decrypt` (see `secure_optimizations._decrypt_row` and `api.py`).
  - Column name whitelist maps are authoritative. Add new searchable fields by updating both `vault.py` (SQLite) and `MYSQL_COLUMN_MAP` (MySQL) and ensure blind-index generation matches.

- **Integration points**:
  - `.env` via `python-dotenv` (already used in multiple modules).
  - MySQL: `mysql-connector-python` is used; ensure binary vs base64 handling when reading/writing blobs.
  - Flask + Flask-CORS for the HTTP API surface in `api.py` and `secure_vault.py`.

- **Small examples**:
  - Search API request payload (POST `/search_secure`): `{ "field": "account_id", "value": "ACC00001" }`.
  - Generate a blind index (use existing helper): `from crypto_utils import get_blind_index_bytes` or `from search_mysql import get_blind_index` depending on target DB.

- **When editing code, follow these rules**:
  - Reuse helper functions in `crypto_utils.py`, `search_mysql.py`, and `secure_optimizations.py` rather than duplicating normalization/crypto logic.
  - Update both SQLite and MySQL mappings when adding searchable PII fields.
  - Preserve secure padding behavior (`k_padding`) in `secure_optimizations` unless a reviewer approves changes.

If anything above is ambiguous or you want me to expand examples (request payloads, env sample, or exact lines to update), tell me which part to iterate on.
