"""
vim_event_db.py
---------------
Standalone SQLAlchemy session for the event browser's events.db.
This is intentionally separate from the main Flask-SQLAlchemy `db`
instance so neither database interferes with the other.
"""
import os
import uuid
from datetime import datetime, timezone

from sqlalchemy import create_engine, Column, String, Text, JSON, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.sql import func

# ── Database path ────────────────────────────────────────────────────────────
# Points at the existing SQLite file inside the EVENT BROWSER folder
_HERE = os.path.dirname(__file__)
_DB_PATH = os.path.join(_HERE, "..", "EVENT BROWSER", "events.db")
_DATABASE_URL = f"sqlite:///{os.path.abspath(_DB_PATH)}"

_engine = create_engine(_DATABASE_URL, connect_args={"check_same_thread": False})
_SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
EventBase = declarative_base()


# ── Event model ───────────────────────────────────────────────────────────────
def _gen_uuid():
    return str(uuid.uuid4())


class Event(EventBase):
    __tablename__ = "events"

    id          = Column(String, primary_key=True, default=_gen_uuid)
    invoice_id  = Column(String, index=True, nullable=False)
    stage       = Column(String, index=True, nullable=False)
    event_type  = Column(String, index=True, nullable=False)
    status      = Column(String, index=True, nullable=False)
    message     = Column(Text, nullable=True)
    payload     = Column(JSON, nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at  = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        return {
            "id":         self.id,
            "invoice_id": self.invoice_id,
            "stage":      self.stage,
            "event_type": self.event_type,
            "status":     self.status,
            "message":    self.message,
            "payload":    self.payload,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# Ensure tables exist (safe no-op if they already do)
EventBase.metadata.create_all(bind=_engine)


# ── Session helper ────────────────────────────────────────────────────────────
def get_event_db():
    """Return a new SQLAlchemy Session for events.db. Caller must close it."""
    return _SessionLocal()
