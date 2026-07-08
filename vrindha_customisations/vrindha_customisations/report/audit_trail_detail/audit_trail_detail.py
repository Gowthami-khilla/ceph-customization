import frappe
from frappe.utils import (
    format_datetime,
    getdate,
    today,
    add_days,
    get_first_day,
    get_last_day
)
import json


# =========================================================
# FRIENDLY FIELD LABELS
# =========================================================

FIELD_LABELS = {
    "qty": "Quantity",
    "rate": "Rate",
    "amount": "Amount",
    "customer": "Customer",
    "supplier": "Supplier",
    "posting_date": "Posting Date",
    "due_date": "Due Date",
    "remarks": "Remarks",
    "total_qty": "Total Quantity",
    "price_list_rate": "Price List Rate",
}


# =========================================================
# IGNORE FIELDS
# =========================================================

IGNORE_FIELDS = [
    "modified",
    "creation",
    "owner",
    "idx",
    "_user_tags",
    "_comments",
    "_assign",
    "_liked_by",
    "docstatus",
    "posting_time",
]


# =========================================================
# IMPORTANT FIELDS
# =========================================================

IMPORTANT_FIELDS = [
    "qty",
    "rate",
    "amount",
    "customer",
    "supplier",
    "posting_date",
    "due_date",
    "remarks",
    "total_qty",
    "price_list_rate"
]


# =========================================================
# EXECUTE
# =========================================================

def execute(filters=None):

    filters = frappe._dict(filters or {})

    report_type = (
        filters.get("report_type")
        or filters.get("report")
        or "Detailed"
    )

    # =====================================================
    # SUMMARY BY DOCTYPE
    # =====================================================

    if report_type == "Summary by DocType":

        columns = [
            {
                "label": "DocType",
                "fieldname": "doctype",
                "fieldtype": "Data",
                "width": 250
            },
            {
                "label": "New Records",
                "fieldname": "new_records",
                "fieldtype": "Int",
                "width": 180
            },
            {
                "label": "Modified Records",
                "fieldname": "modified_records",
                "fieldtype": "Int",
                "width": 180
            }
        ]

        return columns, get_summary_by_doctype(filters)

    # =====================================================
    # SUMMARY BY USER
    # =====================================================

    elif report_type == "Summary by User":

        columns = [
            {
                "label": "User",
                "fieldname": "user",
                "fieldtype": "Data",
                "width": 300
            },
            {
                "label": "New Records",
                "fieldname": "new_records",
                "fieldtype": "Int",
                "width": 180
            },
            {
                "label": "Modified Records",
                "fieldname": "modified_records",
                "fieldtype": "Int",
                "width": 180
            }
        ]

        return columns, get_summary_by_user(filters)

    # =====================================================
    # DETAILED REPORT
    # =====================================================

    columns = get_columns()
    data = get_data(filters)

    return columns, data


# =========================================================
# DETAILED COLUMNS
# =========================================================

def get_columns():

    return [

        {
            "label": "Date and Time",
            "fieldname": "date_time",
            "fieldtype": "Datetime",
            "width": 170
        },
        {
            "label": "DocType",
            "fieldname": "doctype",
            "fieldtype": "Data",
            "width": 160
        },
        {
            "label": "Document Name",
            "fieldname": "document_name",
            "fieldtype": "Dynamic Link",
            "options": "doctype",
            "width": 220
        },
        {
            "label": "Creation Date",
            "fieldname": "creation_date",
            "fieldtype": "Date",
            "width": 120
        },
        {
            "label": "Party Type",
            "fieldname": "party_type",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": "Party Name",
            "fieldname": "party_name",
            "fieldtype": "Data",
            "width": 220
        },
        {
            "label": "Amount",
            "fieldname": "amount",
            "fieldtype": "Currency",
            "width": 140
        },
        {
            "label": "Created By",
            "fieldname": "created_by",
            "fieldtype": "Link",
            "options": "User",
            "width": 180
        },
        {
            "label": "Modified By",
            "fieldname": "modified_by",
            "fieldtype": "Link",
            "options": "User",
            "width": 180
        },
        {
            "label": "Amend Count",
            "fieldname": "amend_count",
            "fieldtype": "Int",
            "width": 130
        },
        {
            "label": "Changed Fields",
            "fieldname": "changed_fields",
            "fieldtype": "Long Text",
            "width": 250
        },
        {
            "label": "Business Change Summary",
            "fieldname": "timeline",
            "fieldtype": "Long Text",
            "width": 700
        }
    ]


# =========================================================
# GET DATE FILTERS
# =========================================================

def get_filter_dates(filters):

    date_option = filters.get("date_option")

    from_date = None
    to_date = None

    if date_option == "Today":

        from_date = today()
        to_date = today()

    elif date_option == "Yesterday":

        from_date = add_days(today(), -1)
        to_date = add_days(today(), -1)

    elif date_option == "This Week":

        from_date = add_days(today(), -7)
        to_date = today()

    elif date_option == "This Month":

        from_date = get_first_day(today())
        to_date = get_last_day(today())

    elif date_option == "Last Week":

        from_date = add_days(today(), -14)
        to_date = add_days(today(), -7)

    elif date_option == "Last Month":

        current_month = get_first_day(today())
        previous_month = add_days(current_month, -1)

        from_date = get_first_day(previous_month)
        to_date = get_last_day(previous_month)

    elif date_option == "Custom":

        date_range = filters.get("date_range")

        if isinstance(date_range, list) and len(date_range) == 2:

            from_date = date_range[0]
            to_date = date_range[1]

    return from_date, to_date


# =========================================================
# DOCTYPES
# =========================================================

def get_doctypes(filters):

    if filters.get("doctype"):
        return [filters.get("doctype")]

    return [
        "Sales Invoice",
        "Purchase Invoice",
        "Payment Entry",
        "Journal Entry",
        "Purchase Receipt"
    ]


# =========================================================
# SUMMARY BY DOCTYPE
# =========================================================

def get_summary_by_doctype(filters):

    data = []

    from_date, to_date = get_filter_dates(filters)

    for dt in get_doctypes(filters):

        conditions = {}

        if from_date and to_date:
            conditions["creation"] = ["between", [from_date, to_date]]

        if filters.get("user"):
            conditions["modified_by"] = filters.get("user")

        if filters.get("company"):
            conditions["company"] = filters.get("company")

        try:

            new_records = frappe.db.count(
                dt,
                conditions
            )

            modified_records = frappe.db.count(
                "Version",
                {
                    "ref_doctype": dt
                }
            )

            data.append({
                "doctype": dt,
                "new_records": new_records,
                "modified_records": modified_records
            })

        except Exception:
            continue

    return data


# =========================================================
# SUMMARY BY USER
# =========================================================

def get_summary_by_user(filters):

    summary = {}

    from_date, to_date = get_filter_dates(filters)

    for dt in get_doctypes(filters):

        conditions = {}

        if from_date and to_date:
            conditions["creation"] = ["between", [from_date, to_date]]

        if filters.get("company"):
            conditions["company"] = filters.get("company")

        try:

            records = frappe.get_all(
                dt,
                filters=conditions,
                fields=[
                    "owner",
                    "modified_by"
                ]
            )

            for row in records:

                owner = row.owner or "Administrator"

                if owner not in summary:

                    summary[owner] = {
                        "user": owner,
                        "new_records": 0,
                        "modified_records": 0
                    }

                summary[owner]["new_records"] += 1

                modified_by = row.modified_by or "Administrator"

                if modified_by not in summary:

                    summary[modified_by] = {
                        "user": modified_by,
                        "new_records": 0,
                        "modified_records": 0
                    }

                summary[modified_by]["modified_records"] += 1

        except Exception:
            continue

    result = list(summary.values())

    result.sort(
        key=lambda x: x.get("modified_records", 0),
        reverse=True
    )

    return result


# =========================================================
# GET DETAILED DATA
# =========================================================

def get_data(filters):

    data = []

    from_date, to_date = get_filter_dates(filters)

    for dt in get_doctypes(filters):

        conditions = {}

        if filters.get("company"):
            conditions["company"] = filters.get("company")

        if filters.get("user"):
            conditions["modified_by"] = filters.get("user")

        if from_date and to_date:
            conditions["modified"] = ["between", [from_date, to_date]]

        try:

            records = frappe.get_all(
                dt,
                filters=conditions,
                fields=[
                    "name",
                    "creation",
                    "modified",
                    "modified_by",
                    "owner"
                ],
                order_by="modified desc"
            )

        except Exception:
            continue

        for r in records:

            try:

                doc = frappe.get_doc(dt, r.name)

                party_type, party_name = get_party_details(doc)

                amount = get_document_amount(doc)

                changed_fields, timeline = get_change_history(
                    dt,
                    r.name
                )

                amend_count = get_amend_count(
                    dt,
                    r.name
                )

                data.append({

                    "date_time": r.modified,
                    "doctype": dt,
                    "document_name": r.name,
                    "creation_date": getdate(r.creation),
                    "party_type": party_type,
                    "party_name": party_name,
                    "amount": amount,
                    "created_by": r.owner,
                    "modified_by": r.modified_by,
                    "amend_count": amend_count,
                    "changed_fields": changed_fields,
                    "timeline": "\n\n━━━━━━━━━━━━━━━━━━━━━━\n\n".join(timeline)

                })

            except Exception:
                continue

    return data


# =========================================================
# CHANGE HISTORY
# =========================================================

def get_change_history(doctype, docname):

    versions = frappe.get_all(
        "Version",
        filters={
            "ref_doctype": doctype,
            "docname": docname
        },
        fields=["owner", "creation", "data"],
        order_by="creation asc"
    )

    timeline = []
    changed_fields = set()

    for index, v in enumerate(versions, start=1):

        try:
            data = json.loads(v.data)
        except Exception:
            continue

        changes = data.get("changed")

        if not changes:
            continue

        version_changes = []

        for ch in changes:

            field = None
            old = None
            new = None

            if isinstance(ch, (list, tuple)) and len(ch) >= 3:

                field = ch[0]
                old = ch[1]
                new = ch[2]

            elif isinstance(ch, dict):

                field = ch.get("fieldname")
                old = ch.get("old")
                new = ch.get("value")

            if not field:
                continue

            if field in IGNORE_FIELDS:
                continue

            if field not in IMPORTANT_FIELDS:
                continue

            if str(old) == str(new):
                continue

            friendly_field = FIELD_LABELS.get(
                field,
                field.replace("_", " ").title()
            )

            changed_fields.add(friendly_field)

            version_changes.append(
                f'• {friendly_field}: "{old}" → "{new}"'
            )

        if version_changes:

            timeline.append(

                f"Update #{index}\n"
                f"Changed By : {v.owner}\n"
                f"Changed On : {format_datetime(v.creation)}\n\n"
                f"Changes Made:\n"
                + "\n".join(version_changes)

            )

    if changed_fields:

        changed_fields_summary = (
            f"{len(changed_fields)} Fields Updated\n\n"
            f"• " +
            "\n• ".join(sorted(changed_fields))
        )

    else:

        changed_fields_summary = "No Important Changes"

    return changed_fields_summary, timeline


# =========================================================
# PARTY DETAILS
# =========================================================

def get_party_details(doc):

    if hasattr(doc, "customer") and doc.customer:
        return "Customer", doc.customer

    if hasattr(doc, "supplier") and doc.supplier:
        return "Supplier", doc.supplier

    return "", ""


# =========================================================
# DOCUMENT AMOUNT
# =========================================================

def get_document_amount(doc):

    if hasattr(doc, "grand_total"):
        return doc.grand_total or 0

    if hasattr(doc, "paid_amount"):
        return doc.paid_amount or 0

    if hasattr(doc, "total"):
        return doc.total or 0

    return 0


# =========================================================
# AMEND COUNT
# =========================================================

def get_amend_count(doctype, docname):

    return frappe.db.count(
        doctype,
        {
            "amended_from": docname
        }
    )