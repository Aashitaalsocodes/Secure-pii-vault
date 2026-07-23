🔐 Secure PII Vault

> Encrypted, searchable storage for sensitive personal data — built so the server can find a match without ever seeing the plaintext.
> Why this exists
  Most systems face a tradeoff: encrypt data for safety, or keep it searchable. You rarely get both. This project solves that with blind indexing— a deterministic hash of the input is stored alongside the encrypted data, so lookups happen against the hash, not the raw value. 
  The actual sensitive data stays encrypted until a match is confirmed.

> How it works
  Input → Normalize (NFKC) → Blind Index (HMAC-SHA256) → Store/Match
  ↓
  Encrypt (AES-GCM) → Ciphertext Blob → Storage
> 1) Normalize - input is cleaned and standardized (case, unicode) so the same value always hashes the same way
  2) Index     - a one-way HMAC-SHA256 hash is generated from the normalized value using a dedicated index key
  3) Encrypt   - the actual sensitive value is separately encrypted with AES-GCM
  4) Search    - queries are hashed the same way and matched against stored indexes — no decryption needed to find a record
  5) Decrypt   - only after a match is found is the ciphertext decrypted, using the master key and verified via the AES-GCM auth tag

> Key Features

 *Blind Indexing* : HMAC-SHA256 hashes enable search without exposing raw data
 *AES-GCM Encryption* : authenticated encryption with integrity verification
 *Unicode Normalization (NFKC)* : consistent matching regardless of input formatting
 *Separation of concerns* : indexing, encryption, and storage handled independently

> Tech Stack

 Component         Technology 

 Backend           Python (Flask) 
 Database          SQLite / MySQL 
 Cryptography      `cryptography` (AES-GCM), HMAC-SHA256 
 Environment       `python-dotenv` 

 > What's in this repo
  File                         Responsibility 

 `main.py`                     Entry point 
 `api.py`                      API routes 
 `db.py`, `db_test.py`         Database connection + tests 
 `crypto_utils.py`             Encryption, hashing, blind indexing logic |
 `secure_vault.py`, `vault.py` Core vault operations |
 `secure_optimizations.py`     Performance-focused improvements |
 `load_data.py`                Loads the dataset into the vault |
 `search_mysql.py`             Search against MySQL backend |
 `test_mysql_connection.py`
 `test_search_existing.py`      Test scripts 

> Setup

 1. Clone the repo
 ```bash
 git clone https://github.com/Aashitaalsocodes/Secure-pii-vault.git
 cd Secure-pii-vault
 ```
 2. Create a `.env` file in the root
   ENCRYPTION_KEY_HEX=your_32_byte_hex_master_key
   INDEX_KEY_HEX=your_32_byte_hex_index_key
 3. Install dependencies
    ```bash
    pip install flask flask-cors mysql-connector-python python-dotenv cryptography
    ```
 4. Run
   ```bash
   python main.py
   ```
> Data

 Sample banking dataset sourced from Kaggle, used for demo and testing purposes.
> Status
  Originally built in a 24-hour hackathon. Currently being revisited and cleaned up as the codebase is better understood, expect the structure and docs here to keep improving over time.
> License
  MIT
