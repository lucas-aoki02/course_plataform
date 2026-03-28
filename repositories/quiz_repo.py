"""
repositories/quiz_repo.py
──────────────────────────
Data-access layer for Quiz and ChatMessage entities.
"""

from __future__ import annotations

from db.database import get_session
from db.models import ChatMessage, Quiz


# ── Quiz ──────────────────────────────────────────────────────────────────────

def get_quizzes(course_id: int) -> list[Quiz]:
    """
    Return all quiz questions for a course, unordered (order doesn't matter for quizzes).
    Returns empty list if no questions have been generated yet.
    """
    with get_session() as db:
        return (
            db.query(Quiz)
            .filter(Quiz.course_id == course_id)
            .all()
        )


def has_quiz(course_id: int) -> bool:
    """Return True if the course has at least one quiz question."""
    with get_session() as db:
        return db.query(Quiz).filter(Quiz.course_id == course_id).count() > 0


# ── ChatMessage ───────────────────────────────────────────────────────────────

def get_chat_messages(course_id: int, limit: int = 50) -> list[ChatMessage]:
    """
    Return recent chat messages for a course, ordered chronologically.

    Args
    ----
    course_id : Scope for the messages.
    limit     : Max messages to return (prevents unbounded loads).
    """
    with get_session() as db:
        return (
            db.query(ChatMessage)
            .filter(ChatMessage.course_id == course_id)
            .order_by(ChatMessage.created_at)
            .limit(limit)
            .all()
        )
