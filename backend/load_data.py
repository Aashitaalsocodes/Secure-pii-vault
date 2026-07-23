import openpyxl
from vault import insert_record

EXCEL_PATH = "banking_dataset.xlsx"

def load_excel():
    wb = openpyxl.load_workbook(EXCEL_PATH)
    ws = wb.active

    total = 0
    errors = 0

    print("[...] Loading records into vault...")

    for row in ws.iter_rows(min_row=2, values_only=True):
        account_id, customer_name, account_type, branch, \
        transaction_type, transaction_amount, account_balance, currency = row

        try:
            insert_record(
                account_id         = str(account_id),
                customer_name      = str(customer_name),
                account_type       = str(account_type),
                branch             = str(branch),
                transaction_type   = str(transaction_type),
                transaction_amount = float(transaction_amount),
                account_balance    = float(account_balance),
                currency           = str(currency)
            )
            total += 1

            if total % 1000 == 0:
                print(f"[...] {total} records inserted...")

        except Exception as e:
            errors += 1
            print(f"[✗] Error on row: {row} — {e}")

    print(f"[✓] Done! {total} records inserted. {errors} errors.")

if __name__ == "__main__":
    load_excel()
