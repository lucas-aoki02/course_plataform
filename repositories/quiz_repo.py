"""
repositories/quiz_repo.py
──────────────────────────
Data-access layer for Quizzes using SQLAlchemy ORM.
"""

from __future__ import annotations
import json
from typing import Optional

from sqlalchemy.orm import Session

from db.models import Quiz, ChatMessage, LessonChatMessage


# ── Quizzes ────────────────────────────────────────────────────────────────────
def get_quizzes(db: Session, course_id: int) -> list[Quiz]:
    quizzes = db.query(Quiz).filter(Quiz.course_id == course_id).all()
    # Deserialize options_json into .options attr for view compatibility
    for q in quizzes:
        if q.options_json:
            q.options = json.loads(q.options_json)
    return quizzes


def has_quiz(db: Session, course_id: int) -> bool:
    return db.query(Quiz).filter(Quiz.course_id == course_id).count() > 0


def create_quiz_item(
    db: Session,
    course_id: int,
    question_text: str,
    options: list[str],
    correct_answer: str,
    explanation: Optional[str] = None,
) -> Quiz:
    q = Quiz(
        course_id=course_id,
        question_text=question_text,
        options_json=json.dumps(options),
        correct_answer=correct_answer,
        explanation=explanation,
    )
    db.add(q)
    db.flush()
    return q


# ── Course Chatbot Messages ────────────────────────────────────────────────────
def get_chat_messages(db: Session, course_id: int, limit: int = 50) -> list[ChatMessage]:
    return (
        db.query(ChatMessage)
        .filter(ChatMessage.course_id == course_id)
        .order_by(ChatMessage.id)
        .limit(limit)
        .all()
    )


def add_chat_message(db: Session, course_id: int, role: str, content: str) -> ChatMessage:
    msg = ChatMessage(course_id=course_id, role=role, content=content)
    db.add(msg)
    db.flush()
    return msg


# ── Lesson Chatbot Messages ────────────────────────────────────────────────────
def get_lesson_chat_messages(db: Session, lesson_id: int, limit: int = 50) -> list[LessonChatMessage]:
    return (
        db.query(LessonChatMessage)
        .filter(LessonChatMessage.lesson_id == lesson_id)
        .order_by(LessonChatMessage.id)
        .limit(limit)
        .all()
    )


def add_lesson_chat_message(db: Session, lesson_id: int, role: str, content: str) -> LessonChatMessage:
    msg = LessonChatMessage(lesson_id=lesson_id, role=role, content=content)
    db.add(msg)
    db.flush()
    return msg
