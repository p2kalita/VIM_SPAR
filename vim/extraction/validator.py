import re
from datetime import datetime

from vim.extraction.schema import HEADER_FIELDS, DATE_FIELDS, MONEY_FIELDS, LINE_ITEM_FIELDS

_DATE_FORMATS = [
    "%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%B %d, %Y", "%b %d, %Y",
    "%m-%d-%Y", "%d/%m/%Y",
]

_MONEY_STRIP_RE = re.compile(r"[^\d.\-]")


def _coerce_date(value):
    if value in (None, "", "null"):
        return None, True
    if isinstance(value, str) and re.match(r"^\d{4}-\d{2}-\d{2}$", value.strip()):
        return value.strip(), True
    if isinstance(value, str):
        for fmt in _DATE_FORMATS:
            try:
                return datetime.strptime(value.strip(), fmt).strftime("%Y-%m-%d"), True
            except ValueError:
                continue
    return value, False


def _coerce_money(value):
    if value in (None, "", "null"):
        return None, True
    if isinstance(value, (int, float)):
        return float(value), True
    if isinstance(value, str):
        is_credit = "-" in value or value.strip().upper().endswith("CR")
        cleaned = _MONEY_STRIP_RE.sub("", value)
        if cleaned in ("", "-"):
            return value, False
        try:
            num = float(cleaned)
            if is_credit and num > 0:
                num = -num
            return num, True
        except ValueError:
            return value, False
    return value, False


def _looks_like_address(value) -> bool:
    if not isinstance(value, str):
        return False
    return bool(re.search(r"\d", value)) and bool(re.search(r"[A-Za-z]{3,}", value)) and " " in value


def validate_record(record: dict) -> tuple[dict, list[str]]:
    issues: list[str] = []

    for field in HEADER_FIELDS:
        if field not in record:
            record[field] = None
            issues.append(f"missing header field '{field}' — set to null")

    for field in DATE_FIELDS:
        coerced, ok = _coerce_date(record.get(field))
        record[field] = coerced
        if not ok:
            issues.append(f"{field}: could not parse date from {record.get(field)!r}")

    for field in MONEY_FIELDS:
        coerced, ok = _coerce_money(record.get(field))
        record[field] = coerced
        if not ok:
            issues.append(f"{field}: could not parse number from {record.get(field)!r}")

    if record.get("total_due") is None:
        issues.append("total_due is null — check source document / vision output")

    if _looks_like_address(record.get("account_number")):
        issues.append(
            f"account_number looks like an address, not an account number: "
            f"{record['account_number']!r}"
        )

    line_items = record.get("line_items")
    if line_items is None:
        record["line_items"] = []
    elif not isinstance(line_items, list):
        issues.append(f"line_items was not a list (got {type(line_items).__name__}) — reset to []")
        record["line_items"] = []
    else:
        cleaned_items = []
        for idx, item in enumerate(line_items):
            if not isinstance(item, dict):
                issues.append(f"line_items[{idx}] was not an object — skipped")
                continue
            for key in LINE_ITEM_FIELDS:
                item.setdefault(key, None)
            for money_key in ("unit_price", "amount"):
                coerced, ok = _coerce_money(item.get(money_key))
                item[money_key] = coerced
                if not ok:
                    issues.append(f"line_items[{idx}].{money_key}: could not parse {item.get(money_key)!r}")
            cleaned_items.append(item)
        record["line_items"] = cleaned_items

    extra = record.get("extra_fields")
    if extra is None:
        record["extra_fields"] = {}
    elif not isinstance(extra, dict):
        issues.append(f"extra_fields was not an object (got {type(extra).__name__}) — reset to {{}}")
        record["extra_fields"] = {}
    else:
        flat_extra = {}
        for k, v in extra.items():
            if isinstance(v, (dict, list)):
                flat_extra[k] = str(v)
                issues.append(f"extra_fields.{k} was nested — flattened to string")
            else:
                flat_extra[k] = v
        record["extra_fields"] = flat_extra

    if not record.get("currency"):
        record["currency"] = "USD"

    return record, issues
