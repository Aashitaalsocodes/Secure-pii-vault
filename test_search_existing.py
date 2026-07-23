"""
End-to-end check: search existing records in the vault (no insert).
Reads a few (account_id, customer_name) from the Excel, then searches the DB.
"""
import openpyxl
from vault import get_decrypted_record

EXCEL_PATH = "banking_dataset.xlsx"


def get_sample_records(n=5):
    """Get first n (account_id, customer_name) pairs from the dataset."""
    wb = openpyxl.load_workbook(EXCEL_PATH)
    ws = wb.active
    samples = []
    for row in ws.iter_rows(min_row=2, values_only=True, max_row=1 + n):
        account_id, customer_name, *_ = row
        samples.append((str(account_id), str(customer_name)))
    return samples


def main():
    print("Fetching sample (account_id, customer_name) from Excel...")
    samples = get_sample_records(5)
    print(f"Found {len(samples)} samples. Searching vault by account_id and customer_name.\n")

    for account_id, customer_name in samples:
        print(f"--- Search by account_id: {account_id} ---")
        rec = get_decrypted_record("account_id", account_id)
        if rec:
            print(rec)
        else:
            print("  (no match)")
        print()

        print(f"--- Search by customer_name: {customer_name} ---")
        rec = get_decrypted_record("customer_name", customer_name)
        if rec:
            print(rec)
        else:
            print("  (no match)")
        print()

    print("Done. Searches used only existing records in the DB.")


if __name__ == "__main__":
    main()
