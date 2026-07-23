from vault import insert_record, get_decrypted_record

insert_record(
    account_id         = "ACC00001",
    customer_name      = "Amanda Pugh",
    account_type       = "Recurring Deposit",
    branch             = "New York",
    transaction_type   = "Debit",
    transaction_amount = 2687.19,
    account_balance    = 36676.19,
    currency           = "GBP"
)

get_decrypted_record("account_id", "ACC00001")
get_decrypted_record("customer_name", "Amanda Pugh")


