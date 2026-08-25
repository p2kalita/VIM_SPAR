"""Fixed JSON schema for invoice extraction."""

HEADER_FIELDS = [
    "vendor_name",
    "invoice_number",
    "invoice_date",
    "due_date",
    "billing_period_start",
    "billing_period_end",
    "account_number",
    "customer_name",
    "bill_to_address",
    "subtotal",
    "tax_total",
    "total_due",
    "previous_balance",
    "payment_received",
    "currency",
    "po_number",
    "invoice_status",
    "vendor_gst_number",
    "vendor_address",
    "vendor_email",
    "vendor_phone_number",
]

DATE_FIELDS = [
    "invoice_date",
    "due_date",
    "billing_period_start",
    "billing_period_end",
]

MONEY_FIELDS = [
    "subtotal",
    "tax_total",
    "total_due",
    "previous_balance",
    "payment_received",
]

LINE_ITEM_FIELDS = ["description", "quantity", "unit_price", "amount"]

SCHEMA_DESCRIPTION_FOR_PROMPT = """
{
  "vendor_name": "string or null",
  "invoice_number": "string or null",
  "invoice_date": "YYYY-MM-DD or null",
  "due_date": "YYYY-MM-DD or null",
  "billing_period_start": "YYYY-MM-DD or null",
  "billing_period_end": "YYYY-MM-DD or null",
  "account_number": "string or null",
  "customer_name": "string or null",
  "bill_to_address": "string or null",
  "subtotal": "number or null",
  "tax_total": "number or null",
  "total_due": "number or null",
  "previous_balance": "number or null",
  "payment_received": "number or null",
  "currency": "string or null (e.g. USD)",
  "po_number": "string or null",
  "invoice_status": "string or null",
  "vendor_gst_number": "string or null",
  "vendor_address": "string or null",
  "vendor_email": "string or null",
  "vendor_phone_number": "string or null",
  "line_items": [
    {
      "description": "string or null",
      "quantity": "number or null",
      "unit_price": "number or null",
      "amount": "number or null"
    }
  ],
  "extra_fields": { "key": "value — flat object for other printed fields" }
}
""".strip()


def empty_record() -> dict:
    record = {field: None for field in HEADER_FIELDS}
    record["line_items"] = []
    record["extra_fields"] = {}
    return record
