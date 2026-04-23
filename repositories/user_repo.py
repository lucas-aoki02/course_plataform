"""
repositories/user_repo.py
──────────────────────────
Data-access layer for User, AuditLog, and UserProgress entities.
"""

from __future__ import annotations
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from db.models import User, UserRole, AuditLog, UserProgress
from services.security_service import hash_password, encryption_manager


# ── Users ──────────────────────────────────────────────────────────────────────
def create_user(
    db: Session,
    username: str,
    email: str,
    password: str,
    role: UserRole = UserRole.student,
    groq_key: Optional[str] = None,
) -> User:
    encrypted_key = encryption_manager.encrypt(groq_key) if groq_key else None
    user = User(
        username=username,
        email=email,
        password_hash=hash_password(password),
        user_role=role,
        groq_key_encrypted=encrypted_key,
    )
    db.add(user)
    db.flush()  # Get the new ID before commit
    return user


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def list_users(db: Session) -> list[User]:
    return db.query(User).order_by(User.id).all()


def update_user(
    db: Session,
    user_id: int,
    username: Optional[str] = None,
    email: Optional[str] = None,
    password: Optional[str] = None,
    role: Optional[UserRole] = None,
    groq_key: Optional[str] = None,
) -> Optional[User]:
    user = get_user_by_id(db, user_id)
    if not user:
        return None
    if username:
        user.username = username
    if email:
        user.email = email
    if password:
        user.password_hash = hash_password(password)
    if role:
        user.user_role = role
    if groq_key is not None:
        user.groq_key_encrypted = encryption_manager.encrypt(groq_key) if groq_key else None
    db.flush()
    return user


def delete_user(db: Session, user_id: int) -> bool:
    user = get_user_by_id(db, user_id)
    if not user:
        return False
    db.delete(user)
    db.flush()
    return True


def get_decrypted_groq_key(user: User) -> Optional[str]:
    """Decrypt and return the Groq API key stored for this user."""
    if not user.groq_key_encrypted:
        return None
    return encryption_manager.decrypt(user.groq_key_encrypted)


# ── Audit Log ──────────────────────────────────────────────────────────────────
def log_audit(
    db: Session,
    action: str,
    user_id: Optional[int] = None,
    target_user_id: Optional[int] = None,
    table_name: Optional[str] = None,
    details: Optional[str] = None,
) -> AuditLog:
    entry = AuditLog(
        user_id=user_id,
        action=action,
        target_user_id=target_user_id,
        table_name=table_name,
        details=details,
        timestamp=datetime.utcnow(),
    )
    db.add(entry)
    db.flush()
    return entry


def list_audit_logs(db: Session, limit: int = 200) -> list[AuditLog]:
    return (
        db.query(AuditLog)
        .order_by(AuditLog.timestamp.desc())
        .limit(limit)
        .all()
    )


# ── User Progress ──────────────────────────────────────────────────────────────
def mark_lesson_complete(db: Session, user_id: int, lesson_id: int) -> UserProgress:
    """Mark a lesson as completed for a user (idempotent)."""
    existing = (
        db.query(UserProgress)
        .filter(UserProgress.user_id == user_id, UserProgress.lesson_id == lesson_id)
        .first()
    )
    if existing:
        return existing
    entry = UserProgress(user_id=user_id, lesson_id=lesson_id, completed_at=datetime.utcnow())
    db.add(entry)
    db.flush()
    return entry


def get_completed_lesson_ids(db: Session, user_id: int) -> set[int]:
    rows = db.query(UserProgress.lesson_id).filter(UserProgress.user_id == user_id).all()
    return {r.lesson_id for r in rows}


def get_student_progress(db: Session, user_id: int) -> list[UserProgress]:
    return (
        db.query(UserProgress)
        .filter(UserProgress.user_id == user_id)
        .order_by(UserProgress.completed_at.desc())
        .all()
    )


# ── Chatbot History Audit ───────────────────────────────────────────────────
def list_chatbot_history(db: Session, limit: int = 500) -> list[ChatbotHistory]:
    from db.models import ChatbotHistory
    return (
        db.query(ChatbotHistory)
        .order_by(ChatbotHistory.created_at.desc())
        .limit(limit)
        .all()
    )


def clear_chatbot_history(db: Session, user_id: int) -> int:
    """Clear all tutor chat history for the specified user."""
    from db.models import ChatbotHistory
    count = db.query(ChatbotHistory).filter(ChatbotHistory.user_id == user_id).delete()
    db.flush()
    return count
