"""
services/privacy_service.py
────────────────────────────
Logic for managing user consent for LGPD/GDPR compliance.
"""

from __future__ import annotations
from datetime import datetime
from sqlalchemy.orm import Session
from db.models import UserConsent

def has_consented(db: Session, user_id: int) -> bool:
    """Check if the user has signed the terms of confidentiality."""
    consent = db.query(UserConsent).filter(UserConsent.user_id == user_id).first()
    return consent is not None

def record_consent(db: Session, user_id: int) -> None:
    """Record that the user has accepted the terms."""
    if not has_consented(db, user_id):
        consent = UserConsent(user_id=user_id, consented_at=datetime.utcnow())
        db.add(consent)
        db.flush()
