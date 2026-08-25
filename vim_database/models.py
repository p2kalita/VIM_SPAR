from datetime import datetime
from vim_database.database import db
# -------------------------------
# USER MODEL
# -------------------------------
class User(db.Model):
    __tablename__ = "user"

    UserID = db.Column(db.Integer, primary_key=True)
    Username = db.Column(db.String(100), nullable=False)
    PasswordHash = db.Column(db.String(255), nullable=False)
    Email = db.Column(db.String(100), nullable=False)
    Role = db.Column(db.String(50), nullable=False)

    VendorID = db.Column(
        db.Integer,
        db.ForeignKey("vendor.VendorID"),
        nullable=False
    )

    IsActive = db.Column(db.Boolean, nullable=False)
    CreatedDate = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship
    vendor = db.relationship("Vendor", back_populates="users")

    approvals = db.relationship("Approval", back_populates="user", lazy=True)

    def __repr__(self):
        return f"<User {self.Username}>"

# -------------------------------
# VENDOR MODEL
# -------------------------------
class Vendor(db.Model):
    __tablename__ = "vendor"

    VendorID = db.Column(db.Integer, primary_key=True)
    VendorName = db.Column(db.String(100), nullable=False)
    GSTNumber = db.Column(db.String(50), nullable=False)
    Address = db.Column(db.String(255))
    Email = db.Column(db.String(100), nullable=False)
    PhoneNumber = db.Column(db.String(20))
    Status = db.Column(db.Integer, nullable=False)

    # Relationships
    users = db.relationship("User", back_populates="vendor", lazy=True)
    purchase_orders = db.relationship("PurchaseOrder", back_populates="vendor", lazy=True)
    invoices = db.relationship("Invoice", back_populates="vendor", lazy=True)

    def __repr__(self):
        return f"<Vendor {self.VendorName}>"
    

# -------------------------------
# PurchaseOrder
# -------------------------------

class PurchaseOrder(db.Model):
    __tablename__ = "purchase_order"

    PONumber = db.Column(db.String(50), primary_key=True)
    VendorID = db.Column(
        db.Integer,
        db.ForeignKey("vendor.VendorID"),
        nullable=False
    )

    PODate = db.Column(db.Date, nullable=False)
    TotalAmount = db.Column(db.Numeric(12, 2), nullable=False)
    Status = db.Column(db.String(30), nullable=False)

    # Relationship
    vendor = db.relationship("Vendor", back_populates="purchase_orders")

    invoices = db.relationship(
        "Invoice",
        back_populates="purchase_order",
        lazy=True
    )

    def __repr__(self):
        return f"<PurchaseOrder {self.PONumber}>"
    
# -------------------------------
# Invoice
# -------------------------------
class Invoice(db.Model):
    __tablename__ = "invoice"

    InvoiceID = db.Column(db.Integer, primary_key=True)
    InvoiceNumber = db.Column(db.String(50), nullable=False)
    InvoiceDate = db.Column(db.Date, nullable=False)

    VendorID = db.Column(
        db.Integer,
        db.ForeignKey("vendor.VendorID"),
        nullable=False
    )

    PONumber = db.Column(
        db.String(50),
        db.ForeignKey("purchase_order.PONumber"),
        nullable=False
    )

    InvoiceAmount = db.Column(db.Numeric(12, 2), nullable=False)
    Currency = db.Column(db.String(10), nullable=False)
    DueDate = db.Column(db.Date, nullable=False)
    InvoiceStatus = db.Column(db.String(30), nullable=False)

    # Relationships
    vendor = db.relationship("Vendor", back_populates="invoices")

    purchase_order = db.relationship(
        "PurchaseOrder",
        back_populates="invoices"
    )

    documents = db.relationship(
        "InvoiceDocument",
        back_populates="invoice",
        lazy=True
    )

    line_items = db.relationship(
        "InvoiceLineItem",
        back_populates="invoice",
        lazy=True
    )

    validations = db.relationship(
        "ValidationResult",
        back_populates="invoice",
        lazy=True
    )

    fraud_checks = db.relationship(
        "FraudCheck",
        back_populates="invoice",
        lazy=True
    )

    approvals = db.relationship(
        "Approval",
        back_populates="invoice",
        lazy=True
    )

    payments = db.relationship(
        "Payment",
        back_populates="invoice",
        lazy=True
    )

    workflow_history = db.relationship(
        "WorkflowHistory",
        back_populates="invoice",
        lazy=True
    )

    audit_logs = db.relationship(
        "AuditLog",
        back_populates="invoice",
        lazy=True
    )

    exception_cases = db.relationship(
        "ExceptionCase",
        back_populates="invoice",
        lazy=True
    )

    def __repr__(self):
        return f"<Invoice {self.InvoiceNumber}>"



# -------------------------------
# InvoiceDocument
# -------------------------------
class InvoiceDocument(db.Model):
    __tablename__ = "invoice_document"

    DocumentID = db.Column(db.Integer, primary_key=True)

    InvoiceID = db.Column(
        db.Integer,
        db.ForeignKey("invoice.InvoiceID"),
        nullable=False
    )

    FileName = db.Column(db.String(255), nullable=False)
    FileType = db.Column(db.String(20), nullable=False)
    UploadDate = db.Column(db.DateTime, default=datetime.utcnow)
    StoragePath = db.Column(db.String(500), nullable=False)

    # Relationship
    invoice = db.relationship(
        "Invoice",
        back_populates="documents"
    )

    ocr_extraction = db.relationship(
        "OCRExtraction",
        back_populates="document",
        uselist=False
    )

    def __repr__(self):
        return f"<InvoiceDocument {self.FileName}>"


# -------------------------------
# OCRExtraction
# -------------------------------
class OCRExtraction(db.Model):
    __tablename__ = "ocr_extraction"

    ExtractionID = db.Column(db.Integer, primary_key=True)

    DocumentID = db.Column(
        db.Integer,
        db.ForeignKey("invoice_document.DocumentID"),
        nullable=False
    )

    ExtractedVendorName = db.Column(db.String(255), nullable=False)
    ExtractedInvoiceNumber = db.Column(db.String(100), nullable=False)
    ExtractedInvoiceDate = db.Column(db.Date, nullable=False)
    ExtractedAmount = db.Column(db.Numeric(12, 2), nullable=False)
    ConfidenceScore = db.Column(db.Numeric(5, 2), nullable=False)
    ExtractionStatus = db.Column(db.String(30), nullable=False)

    # Relationship
    document = db.relationship(
        "InvoiceDocument",
        back_populates="ocr_extraction"
    )

    def __repr__(self):
        return f"<OCRExtraction {self.ExtractionID}>"


# -------------------------------
# InvoiceLineItem
# -------------------------------
class InvoiceLineItem(db.Model):
    __tablename__ = "invoice_line_item"

    LineItemID = db.Column(db.Integer, primary_key=True)

    InvoiceID = db.Column(
        db.Integer,
        db.ForeignKey("invoice.InvoiceID"),
        nullable=False
    )

    Description = db.Column(db.String(255), nullable=False)
    Quantity = db.Column(db.Numeric(10, 2), nullable=False)
    CostAmount = db.Column(db.Numeric(12, 2), nullable=False)
    DiscountAmount = db.Column(db.Numeric(12, 2), nullable=False)
    LineAmount = db.Column(db.Numeric(12, 2), nullable=False)

    # Relationship
    invoice = db.relationship(
        "Invoice",
        back_populates="line_items"
    )

    def __repr__(self):
        return f"<InvoiceLineItem {self.LineItemID}>"


# -------------------------------
# ValidationResult
# -------------------------------

class ValidationResult(db.Model):
    __tablename__ = "validation_result"

    ValidationID = db.Column(db.Integer, primary_key=True)

    InvoiceID = db.Column(
        db.Integer,
        db.ForeignKey("invoice.InvoiceID"),
        nullable=False
    )

    ValidationType = db.Column(db.String(50), nullable=False)
    ValidationStatus = db.Column(db.String(30), nullable=False)
    ValidationMessage = db.Column(db.String(255))
    ValidationDate = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    # Relationship
    invoice = db.relationship(
        "Invoice",
        back_populates="validations"
    )

    def __repr__(self):
        return f"<ValidationResult {self.ValidationID}>"

# -------------------------------
# FraudCheck
# -------------------------------
class FraudCheck(db.Model):
    __tablename__ = "fraud_check"

    FraudCheckID = db.Column(db.Integer, primary_key=True)

    InvoiceID = db.Column(
        db.Integer,
        db.ForeignKey("invoice.InvoiceID"),
        nullable=False
    )

    DuplicateFlag = db.Column(db.Boolean, nullable=False)
    RiskScore = db.Column(db.Numeric(5, 2), nullable=False)
    CheckDate = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship
    invoice = db.relationship(
        "Invoice",
        back_populates="fraud_checks"
    )

    def __repr__(self):
        return f"<FraudCheck {self.FraudCheckID}>"




# -------------------------------
# Approval
# -------------------------------
class Approval(db.Model):
    __tablename__ = "approval"

    ApprovalID = db.Column(db.Integer, primary_key=True)

    InvoiceID = db.Column(
        db.Integer,
        db.ForeignKey("invoice.InvoiceID"),
        nullable=False
    )

    ApproverUserID = db.Column(
        db.Integer,
        db.ForeignKey("user.UserID"),
        nullable=False
    )

    ApprovalStatus = db.Column(db.String(30), nullable=False)
    ApprovalDate = db.Column(db.DateTime)
    Comments = db.Column(db.String(255))

    # Relationships
    invoice = db.relationship(
        "Invoice",
        back_populates="approvals"
    )

    user = db.relationship(
        "User",
        back_populates="approvals"
    )

    def __repr__(self):
        return f"<Approval {self.ApprovalID}>"



# -------------------------------
# Payment
# -------------------------------

class Payment(db.Model):
    __tablename__ = "payment"

    PaymentID = db.Column(db.Integer, primary_key=True)

    InvoiceID = db.Column(
        db.Integer,
        db.ForeignKey("invoice.InvoiceID"),
        nullable=False
    )

    PaymentDate = db.Column(db.DateTime, default=datetime.utcnow)
    PaymentAmount = db.Column(db.Numeric(12, 2), nullable=False)
    PaymentMethod = db.Column(db.String(50), nullable=False)
    PaymentReference = db.Column(db.String(100))
    PaymentStatus = db.Column(db.String(30), nullable=False)

    # Relationship
    invoice = db.relationship(
        "Invoice",
        back_populates="payments"
    )

    def __repr__(self):
        return f"<Payment {self.PaymentID}>"

# -------------------------------
# WorkflowHistory
# -------------------------------

class WorkflowHistory(db.Model):
    __tablename__ = "workflow_history"

    WorkflowHistoryID = db.Column(db.Integer, primary_key=True)

    InvoiceID = db.Column(
        db.Integer,
        db.ForeignKey("invoice.InvoiceID"),
        nullable=False
    )

    PreviousStatus = db.Column(db.String(30))
    CurrentStatus = db.Column(db.String(30), nullable=False)
    ActionBy = db.Column(db.Integer, nullable=False)
    ActionDate = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship
    invoice = db.relationship(
        "Invoice",
        back_populates="workflow_history"
    )

    def __repr__(self):
        return f"<WorkflowHistory {self.WorkflowHistoryID}>"


# -------------------------------
# AuditLog
# -------------------------------

class AuditLog(db.Model):
    __tablename__ = "audit_log"

    AuditLogID = db.Column(db.Integer, primary_key=True)

    InvoiceID = db.Column(
        db.Integer,
        db.ForeignKey("invoice.InvoiceID"),
        nullable=False
    )

    UserID = db.Column(db.Integer, nullable=False)
    ActionType = db.Column(db.String(50), nullable=False)
    ActionTimestamp = db.Column(db.DateTime, default=datetime.utcnow)
    Comments = db.Column(db.String(255))

    # Relationship
    invoice = db.relationship(
        "Invoice",
        back_populates="audit_logs"
    )

    def __repr__(self):
        return f"<AuditLog {self.AuditLogID}>"

# -------------------------------
# ExceptionCase
# -------------------------------
class ExceptionCase(db.Model):
    __tablename__ = "exception_case"

    ExceptionID = db.Column(db.Integer, primary_key=True)

    InvoiceID = db.Column(
        db.Integer,
        db.ForeignKey("invoice.InvoiceID"),
        nullable=False
    )

    ExceptionType = db.Column(db.String(50), nullable=False)
    Description = db.Column(db.String(255))
    Status = db.Column(db.String(30), nullable=False)
    CreatedDate = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship
    invoice = db.relationship(
        "Invoice",
        back_populates="exception_cases"
    )

    def __repr__(self):
        return f"<ExceptionCase {self.ExceptionID}>"
        
        
class SystemConfiguration(db.Model):

    __tablename__ = "system_configuration"

    ConfigID = db.Column(
        db.Integer,
        primary_key=True
    )

    AppName = db.Column(
        db.String(200)
    )

    Environment = db.Column(
        db.String(20)
    )

    Currency = db.Column(
        db.String(10)
    )

    LLMProvider = db.Column(
        db.String(100)
    )

    ModelName = db.Column(
        db.String(100)
    )

    Temperature = db.Column(
        db.Float
    )

    OCRProvider = db.Column(
        db.String(100)
    )

    ConfidenceThreshold = db.Column(
        db.Float
    )

    ApprovalLevels = db.Column(
        db.Integer
    )

    AutoApproveLimit = db.Column(
        db.Numeric(12,2)
    )

    SMTPServer = db.Column(
        db.String(200)
    )

    SMTPPort = db.Column(
        db.Integer
    )

    OpenAIKey = db.Column(
        db.String(500)
    )

    GeminiKey = db.Column(
        db.String(500)
    )