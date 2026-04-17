import frappe
from frappe import _
import openpyxl
from datetime import datetime, date
import hashlib

__all__ = ["import_bank_statement"]

def clean(val):
    return str(val).strip() if val is not None else ""


def to_amount(val):
    if val is None:
        return 0.0
    s = clean(val)
    if not s:
        return 0.0
    try:
        return float(s.replace(",", ""))
    except (ValueError, TypeError):
        return 0.0


def find_bank_account(acct_no, fallback):
    if not acct_no:
        return fallback

    acct_clean = str(acct_no).lstrip("_").strip()

    if not acct_clean:
        return fallback

    ba = frappe.db.get_value(
        "Bank Account",
        {"bank_account_no": acct_clean},
        "name"
    )

    if not ba and len(acct_clean) >= 6:
        ba = frappe.db.get_value(
            "Bank Account",
            {"bank_account_no": ["like", "%" + acct_clean[-6:]]},
            "name"
        )

    return ba or fallback


def save_transaction(txn_date, bank_account, description, reference, deposit, withdrawal, result):

    # ❌ skip only invalid rows
    if not bank_account:
        result["errors"].append(f"{txn_date} | Missing Bank Account | {description[:50]}")
        result["skipped"] += 1
        return

    try:
        bt = frappe.new_doc("Bank Transaction")

        bt.date = txn_date
        bt.bank_account = bank_account
        bt.company = frappe.db.get_value("Bank Account", bank_account, "company")
        bt.description = description
        bt.reference_number = reference
        bt.deposit = deposit
        bt.withdrawal = withdrawal

        gl_account = frappe.db.get_value("Bank Account", bank_account, "account")
        bt.currency = frappe.db.get_value("Account", gl_account, "account_currency") or "INR"

        # ✅ SAFE Transaction ID (FIXED 140 CHAR ISSUE)
        raw_id = f"{txn_date}-{reference}-{deposit}-{withdrawal}"
        bt.transaction_id = hashlib.md5(raw_id.encode()).hexdigest()[:20]

        bt.insert(ignore_permissions=True)

        bt.submit()   # ✅ THIS IS THE FIX

        result["created"] += 1

    except Exception as e:
        result["errors"].append(f"{txn_date} | {description[:50]} | {str(e)}")
        result["skipped"] += 1


def process_sheet(rows, sheet_name, fallback_bank_account, result):

    if not rows:
        return

    first_cell = clean(rows[0][0]).lower()

    # ✅ detect header row
    if "txn date" in first_cell:
        header_row_idx = 0
        account_number = fallback_bank_account
    else:
        header_row_idx = None
        account_number = fallback_bank_account

        for i, row in enumerate(rows):
            cell0 = clean(row[0])

            if "Account Number" in cell0:
                account_number = clean(row[1]).lstrip("_").strip()

            if clean(cell0).lower() == "txn date":
                header_row_idx = i
                break

        if header_row_idx is None:
            result["errors"].append(f"{sheet_name} | Header not found")
            return

    headers = [clean(h).lower() for h in rows[header_row_idx]]

    def col(*names):
        for name in names:
            for idx, h in enumerate(headers):
                if name.lower() in h:
                    return idx
        return None

    c_date = col("txn date")
    c_desc = col("description", "narration", "remarks", "particulars")
    c_ref = col("ref no", "cheque no")
    c_debit = col("debit", "dr")
    c_credit = col("credit", "cr")

    if c_date is None or c_desc is None:
        result["errors"].append(f"{sheet_name} | Required columns missing")
        return

    bank_account = find_bank_account(account_number, fallback_bank_account)

    for row in rows[header_row_idx + 1:]:

        raw_date = row[c_date]

        if not isinstance(raw_date, (datetime, date)):
            continue

        txn_date = raw_date.date() if isinstance(raw_date, datetime) else raw_date
        description = clean(row[c_desc])
        reference = clean(row[c_ref]) if c_ref is not None else ""
        withdrawal = to_amount(row[c_debit] if c_debit is not None else None)
        deposit = to_amount(row[c_credit] if c_credit is not None else None)

        save_transaction(
            txn_date,
            bank_account,
            description,
            reference,
            deposit,
            withdrawal,
            result
        )


@frappe.whitelist()
def import_bank_statement(docname):

    doc = frappe.get_doc("Bank Statement Import", docname)

    file_url = doc.get("import_file") or doc.get("custom_txt_file")

    if not file_url:
        frappe.throw(_("Please attach Excel file"))

    file_doc = frappe.get_doc("File", {"file_url": file_url})
    file_path = file_doc.get_full_path()

    if not file_path.lower().endswith((".xlsx", ".xls")):
        frappe.throw(_("Only Excel files allowed"))

    result = {
        "created": 0,
        "skipped": 0,
        "errors": []
    }

    wb = openpyxl.load_workbook(file_path, data_only=True)

    # 🔥 IMPORTANT FIX: ONLY FIRST SHEET (prevents 299 issue)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))

    process_sheet(rows, ws.title, doc.bank_account, result)

    return result