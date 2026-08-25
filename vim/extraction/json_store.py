"""Read/write enriched extraction records to output/enriched.json."""

import json
from pathlib import Path

from vim.extraction import config

ENRICHED_PATH = config.OUTPUT_DIR / "enriched.json"


def load_all() -> list[dict]:
    if not ENRICHED_PATH.exists():
        return []
    data = json.loads(ENRICHED_PATH.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []


def save_all(records: list[dict]) -> Path:
    ENRICHED_PATH.parent.mkdir(parents=True, exist_ok=True)
    ENRICHED_PATH.write_text(json.dumps(records, indent=2, default=str), encoding="utf-8")
    return ENRICHED_PATH


def upsert_record(record: dict) -> Path:
    """Insert or update one record in enriched.json (matched by file_path)."""
    records = load_all()
    key = record.get("file_path") or record.get("file_name")
    updated = False
    for i, existing in enumerate(records):
        existing_key = existing.get("file_path") or existing.get("file_name")
        if existing_key == key:
            records[i] = record
            updated = True
            break
    if not updated:
        records.append(record)
    return save_all(records)
