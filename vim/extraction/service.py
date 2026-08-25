"""Orchestrates upload → extract → persist for the VIM web app."""

from pathlib import Path
from uuid import uuid4

from werkzeug.utils import secure_filename

from vim.extraction import config
from vim.extraction.enrich import extract_from_file
from vim.extraction.load import insert_record
from vim_database.database import db


def allowed_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in config.SUPPORTED_EXTENSIONS


def save_upload(file_storage) -> Path:
    """Save an uploaded file and return its path."""
    original = secure_filename(file_storage.filename or "")
    if not original:
        raise ValueError("No filename provided")

    ext = Path(original).suffix.lower()
    if ext not in config.SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {ext}")

    config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    dest = config.UPLOAD_DIR / f"{uuid4().hex}_{original}"
    file_storage.save(dest)
    return dest


def process_uploaded_file(file_storage) -> dict:
    """
    Full intelligent upload pipeline:
    1. Save file
    2. Extract data (LlamaParse + Groq)
    3. Validate
    4. Save to output/enriched.json
    5. Persist to VIM database
    """
    from vim.extraction.json_store import upsert_record

    config.validate()

    original_name = secure_filename(file_storage.filename or "")
    saved_path = save_upload(file_storage)
    record = extract_from_file(str(saved_path))

    # Keep human-readable filename in the record (not the uuid prefix on disk)
    record["file_name"] = original_name
    record["stored_file_name"] = saved_path.name

    upsert_record(record)

    try:
        invoice = insert_record(record)
        db.session.commit()
        record["invoice_id"] = invoice.InvoiceID
        record["status"] = "success"
    except Exception as e:
        db.session.rollback()
        record["status"] = "db_error"
        record["_db_error"] = str(e)

    upsert_record(record)
    return record
