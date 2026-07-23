# Step-by-Step: Connecting to Teammate's MySQL Database

This guide is for **Member 1 (Backend Crypto)** to connect your Flask app and search logic to **Member 2's MySQL** database on `172.16.9.29`.

---

## Step 1: Fix the Firewall (Teammate 2's Laptop)

**Who:** Your teammate (API & Database Engineer)  
**Where:** On the machine running MySQL (`172.16.9.29`)

1. Open **Windows Defender Firewall** (or the firewall they use).
2. Add an **Inbound Rule** to allow **TCP port 3306** (MySQL).
   - Rule type: Port  
   - Protocol: TCP  
   - Port: 3306  
   - Action: Allow  
   - Scope: Either "Any" or your subnet (e.g. `172.16.0.0/16`) so your IP `172.16.12.177` can connect.
3. Ensure **MySQL is bound to all interfaces** (not only localhost):
   - In `my.ini` or `my.cnf`: `bind-address = 0.0.0.0` (or comment out `bind-address`).
   - Restart MySQL after changing config.

**Quick test from your laptop (PowerShell):**
```powershell
Test-NetConnection -ComputerName 172.16.9.29 -Port 3306
```
If `TcpTestSucceeded : True`, the firewall is open.

---

## Step 2: Agree on Blind Index Format (Team Contract)

For search to work, **you and Member 2 must use the same algorithm** when generating blind indexes.

| Item | Your side (Member 1) | Teammate's side (Member 2) |
|------|----------------------|-----------------------------|
| Key | `INDEX_KEY_HEX` from `.env` (32-byte hex) | Same key in their `.env` |
| Message | `f"{field}:{value}"` — **no** strip/lower; use raw value | Same |
| Output for MySQL | Raw 32 bytes (SHA256 digest) | Same, stored in `BINARY(32)` |

**Field names in the message (must match):**
- `account_id` → column `idx_account_id`
- `customer_name` → column `idx_name` (MySQL uses `idx_name`, your API uses "customer_name")

Share this with Member 2 so their insert/upload code uses the same key and same `field:value` (no normalization) when writing to `secure_vault`.

---

## Step 3: Your .env for MySQL

Ensure your `.env` has the key used for **blind indexes** (for MySQL search):

```env
INDEX_KEY_HEX=d426a790cd9b3956a75ce0b41570a1aae7514f350c922902ae32f2a7d579dac0
```

Optional (if you want to override defaults without editing code):

```env
MYSQL_HOST=172.16.9.29
MYSQL_USER=remote_user
MYSQL_PASSWORD=2006
MYSQL_DATABASE=hackathon
MYSQL_PORT=3306
```

Your `crypto_utils.py` uses `AES_KEY` and `HMAC_KEY` for SQLite. For MySQL, `search_mysql.py` uses `INDEX_KEY_HEX` so both you and your teammate can use the same key for indexes.

---

## Step 4: Install MySQL Connector (Your Laptop)

From your project folder:

```powershell
cd C:\Users\Aashita\Desktop\secure_pii_vault
pip install mysql-connector-python
```

---

## Step 5: Test MySQL Connection

Run the test script (see `test_mysql_connection.py` in the project):

```powershell
python test_mysql_connection.py
```

If it prints `Connection successful`, you're done with connectivity. If it fails, go back to Step 1 (firewall / MySQL bind-address).

---

## Step 6: Run Search Against MySQL

Use `search_mysql.py` to search by `account_id` or `customer_name` (maps to `idx_name` in MySQL):

```powershell
python search_mysql.py
```

This will call `search_record("account_id", "ACC00001")` and `search_record("name", "Amanda Pugh")` as examples. Adjust the `if __name__ == "__main__"` block to test your own values.

---

## Step 7: (Optional) Use MySQL from Your Flask API

If you want the **same Flask API** to support both SQLite (local) and MySQL (teammate):

- Keep current `/search` and `/insert` using SQLite (your vault).
- Add a separate route, e.g. `/search-mysql`, that uses `search_mysql.search_record()` and returns the same JSON shape, so the frontend can call either backend.

Only add this once Step 1–6 work and the team agrees on the blind index contract (Step 2).

---

## Checklist

- [ ] Teammate opened port 3306 and set `bind-address` (Step 1)
- [ ] Team agreed on blind index key + format (Step 2)
- [ ] `.env` has `INDEX_KEY_HEX` (Step 3)
- [ ] `pip install mysql-connector-python` (Step 4)
- [ ] `python test_mysql_connection.py` succeeds (Step 5)
- [ ] `python search_mysql.py` runs without errors (Step 6)

---

## If MySQL Is Still Blocked (Demo Fallback)

Use your **SQLite vault** for the judge demo:

1. Initialize DB: `python db.py`
2. Load data: `python load_data.py` (with `banking_dataset.xlsx` in the same folder)
3. Run API: `python api.py`
4. Frontend already points to `http://172.16.12.177:5000` — use `/insert` and `/search` as usual.

Your searchable encryption (blind index + AES-GCM) is the same; only the database backend differs.
