"""Persist extracted invoice records into the VIM database."""

from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from vim_database.database import db
from vim_database.models import (
    Vendor,
    PurchaseOrder,
    Invoice,
    InvoiceDocument,
    InvoiceLineItem,
    OCRExtraction,
)


def _get(record: dict, field, default=None):
    v = record.get(field)
    if v not in (None, ""):
        return v
    return default


def _get_date(record: dict, field, default=None):
    v = _get(record, field, default=None)
    if v is None:
        return default
    if isinstance(v, date):
        return v
    try:
        return datetime.strptime(v, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return default


def _confidence_score(record: dict) -> Decimal:
    if record.get("_extraction_error"):
        return Decimal("0.00")
    issues = record.get("_validation_issues") or []
    if not issues:
        return Decimal("95.00")
    if len(issues) <= 2:
        return Decimal("75.00")
    return Decimal("50.00")


def _extraction_status(record: dict) -> str:
    if record.get("_extraction_error"):
        return "Failed"
    if record.get("_validation_issues"):
        return "NeedsReview"
    return "Success"


def _find_or_create_vendor(record: dict) -> Vendor:
    vendor_name = _get(record, "vendor_name", default="Unknown Vendor")

    vendor = Vendor.query.filter_by(VendorName=vendor_name).first()
    if vendor:
        return vendor

    vendor = Vendor(
        VendorName=vendor_name,
        GSTNumber=_get(record, "vendor_gst_number", default=""),
        Address=_get(record, "vendor_address"),
        Email=_get(record, "vendor_email", default=""),
        PhoneNumber=_get(record, "vendor_phone_number"),
        Status=1,
    )
    db.session.add(vendor)
    db.session.flush()
    return vendor


def _find_or_create_purchase_order(record: dict, vendor: Vendor, file_name: str) -> PurchaseOrder:
    po_number = _get(record, "po_number") or f"AUTO-{file_name}"

    po = PurchaseOrder.query.filter_by(PONumber=po_number).first()
    if po:
        return po

    po = PurchaseOrder(
        PONumber=po_number,
        VendorID=vendor.VendorID,
        PODate=_get_date(record, "invoice_date", default=date(1970, 1, 1)),
        TotalAmount=_get(record, "total_due", default=0) or 0,
        Status=_get(record, "invoice_status", default="Open"),
    )
    db.session.add(po)
    db.session.flush()
    return po


def _upsert_ocr_extraction(document: InvoiceDocument, record: dict) -> None:
    ocr = document.ocr_extraction
    if not ocr:
        ocr = OCRExtraction(DocumentID=document.DocumentID)
        db.session.add(ocr)

    ocr.ExtractedVendorName = _get(record, "vendor_name", default="Unknown") or "Unknown"
    ocr.ExtractedInvoiceNumber = _get(record, "invoice_number", default="") or ""
    ocr.ExtractedInvoiceDate = _get_date(record, "invoice_date", default=date(1970, 1, 1))
    ocr.ExtractedAmount = _get(record, "total_due", default=0) or 0
    ocr.ConfidenceScore = _confidence_score(record)
    ocr.ExtractionStatus = _extraction_status(record)


def insert_record(record: dict) -> Invoice:
    """Insert or update invoice data from an enriched extraction record."""
    file_name = record.get("file_name")

    vendor = _find_or_create_vendor(record)
    po = _find_or_create_purchase_order(record, vendor, file_name)

    invoice_fields = dict(
        InvoiceNumber=_get(record, "invoice_number", default="") or f"UNKNOWN-{file_name}",
        InvoiceDate=_get_date(record, "invoice_date", default=date(1970, 1, 1)),
        VendorID=vendor.VendorID,
        PONumber=po.PONumber,
        InvoiceAmount=_get(record, "total_due", default=0) or 0,
        Currency=_get(record, "currency", default="USD"),
        DueDate=_get_date(record, "due_date", default=date(1970, 1, 1)),
        InvoiceStatus=_get(record, "invoice_status", default="Pending"),
    )

    existing_doc = InvoiceDocument.query.filter_by(FileName=file_name).first()

    if existing_doc:
        invoice = db.session.get(Invoice, existing_doc.InvoiceID)
        for key, value in invoice_fields.items():
            setattr(invoice, key, value)
        document = existing_doc
    else:
        invoice = Invoice(**invoice_fields)
        db.session.add(invoice)
        db.session.flush()

        document = InvoiceDocument(
            InvoiceID=invoice.InvoiceID,
            FileName=file_name,
            FileType="",
            StoragePath="",
        )
        db.session.add(document)
        db.session.flush()

    document.FileType = Path(file_name or "").suffix.lstrip(".").upper()
    document.StoragePath = record.get("file_path") or ""

    InvoiceLineItem.query.filter_by(InvoiceID=invoice.InvoiceID).delete()
    for item in record.get("line_items") or []:
        db.session.add(InvoiceLineItem(
            InvoiceID=invoice.InvoiceID,
            Description=_get(item, "description", default=""),
            Quantity=_get(item, "quantity", default=0) or 0,
            CostAmount=_get(item, "unit_price", default=0) or 0,
            DiscountAmount=0,
            LineAmount=_get(item, "amount", default=0) or 0,
        ))

    _upsert_ocr_extraction(document, record)
    return invoice
