"""
repositories/quiz_repo.py
──────────────────────────
Data-access layer for Quizzes using SQLAlchemy ORM.
"""

from __future__ import annotations
import json
from typing import Optional

from sqlalchemy.orm import Session

from db.models import Quiz, QuizAttempt, ChatMessage, LessonChatMessage


# ── Quizzes ────────────────────────────────────────────────────────────────────
def get_quizzes(
    db: Session, 
    course_id: Optional[int] = None, 
    module_id: Optional[int] = None, 
    lesson_id: Optional[int] = None
) -> list[Quiz]:
    query = db.query(Quiz)
    if lesson_id:
        query = query.filter(Quiz.lesson_id == lesson_id)
    elif module_id:
        query = query.filter(Quiz.module_id == module_id)
    elif course_id:
        query = query.filter(Quiz.course_id == course_id)
        
    quizzes = query.all()
    # Deserialize options_json into .options attr for view compatibility
    for q in quizzes:
        if q.options_json:
            q.options = json.loads(q.options_json)
    return quizzes


def empty_quizzes_for_scope(
    db: Session, 
    course_id: Optional[int] = None, 
    module_id: Optional[int] = None, 
    lesson_id: Optional[int] = None
) -> None:
    query = db.query(Quiz)
    if lesson_id:
        query = query.filter(Quiz.lesson_id == lesson_id)
    elif module_id:
        query = query.filter(Quiz.module_id == module_id)
    elif course_id:
        query = query.filter(Quiz.course_id == course_id)
    query.delete(synchronize_session="fetch")


def has_quiz(
    db: Session, 
    course_id: Optional[int] = None, 
    module_id: Optional[int] = None, 
    lesson_id: Optional[int] = None
) -> bool:
    query = db.query(Quiz)
    if lesson_id:
        query = query.filter(Quiz.lesson_id == lesson_id)
    elif module_id:
        query = query.filter(Quiz.module_id == module_id)
    elif course_id:
        query = query.filter(Quiz.course_id == course_id)
    return query.count() > 0


def get_course_quizzes_metadata(db: Session, course_id: int) -> dict:
    """
    Returns a dict with sets of IDs that have quizzes:
    { 'lessons': {id1, id2...}, 'modules': {id3...}, 'has_final': bool }
    """
    from db.models import Module, Lesson
    
    # Quizzes for lessons in this course
    lesson_q = db.query(Quiz.lesson_id).join(Lesson).join(Module).filter(Module.course_id == course_id, Quiz.lesson_id.isnot(None)).all()
    # Quizzes for modules in this course
    module_q = db.query(Quiz.module_id).join(Module).filter(Module.course_id == course_id, Quiz.module_id.isnot(None)).all()
    # Quizzes for the course directly (final)
    course_q = db.query(Quiz.course_id).filter(Quiz.course_id == course_id, Quiz.module_id.is_(None), Quiz.lesson_id.is_(None)).count() > 0
    
    return {
        "lessons": {r.lesson_id for r in lesson_q},
        "modules": {r.module_id for r in module_q},
        "has_final": course_q
    }


def create_quiz_item(
    db: Session,
    course_id: Optional[int],
    question_text: str,
    options: list[str],
    correct_answer: str,
    explanation: Optional[str] = None,
    module_id: Optional[int] = None,
    lesson_id: Optional[int] = None
) -> Quiz:
    q = Quiz(
        course_id=course_id,
        module_id=module_id,
        lesson_id=lesson_id,
        question_text=question_text,
        options_json=json.dumps(options),
        correct_answer=correct_answer,
        explanation=explanation,
    )
    db.add(q)
    db.flush()
    return q


# ── Quiz Attempts ─────────────────────────────────────────────────────────────
def get_quiz_attempts(
    db: Session, 
    user_id: int, 
    course_id: Optional[int] = None, 
    module_id: Optional[int] = None, 
    lesson_id: Optional[int] = None
) -> list[QuizAttempt]:
    query = db.query(QuizAttempt).filter(QuizAttempt.user_id == user_id)
    if lesson_id:
        query = query.filter(QuizAttempt.lesson_id == lesson_id)
    elif module_id:
        query = query.filter(QuizAttempt.module_id == module_id)
    elif course_id:
        query = query.filter(QuizAttempt.course_id == course_id)
    return query.order_by(QuizAttempt.timestamp.desc()).all()


def get_user_course_quiz_status(db: Session, user_id: int, course_id: int) -> dict:
    """
    Returns sets of IDs (lesson, module, or True for course) where the user has PASSED.
    """
    from db.models import Module, Lesson
    
    # Attempts for lessons
    l_passed = db.query(QuizAttempt.lesson_id).join(Lesson).join(Module).filter(
        QuizAttempt.user_id == user_id, 
        Module.course_id == course_id, 
        QuizAttempt.passed == True,
        QuizAttempt.lesson_id.isnot(None)
    ).all()
    
    # Attempts for modules
    m_passed = db.query(QuizAttempt.module_id).join(Module).filter(
        QuizAttempt.user_id == user_id, 
        Module.course_id == course_id, 
        QuizAttempt.passed == True,
        QuizAttempt.module_id.isnot(None)
    ).all()
    
    # Final course quiz pass
    c_passed = db.query(QuizAttempt.id).filter(
        QuizAttempt.user_id == user_id, 
        QuizAttempt.course_id == course_id, 
        QuizAttempt.passed == True,
        QuizAttempt.module_id.is_(None),
        QuizAttempt.lesson_id.is_(None)
    ).count() > 0
    
    return {
        "lessons": {r.lesson_id for r in l_passed},
        "modules": {r.module_id for r in m_passed},
        "final_passed": c_passed
    }


def record_quiz_attempt(
    db: Session, 
    user_id: int, 
    score_percent: int, 
    passed: bool, 
    course_id: Optional[int] = None, 
    module_id: Optional[int] = None, 
    lesson_id: Optional[int] = None
) -> QuizAttempt:
    existing_attempts = get_quiz_attempts(db, user_id, course_id, module_id, lesson_id)
    attempt_number = len(existing_attempts) + 1
    
    qa = QuizAttempt(
        user_id=user_id,
        course_id=course_id,
        module_id=module_id,
        lesson_id=lesson_id,
        score_percent=score_percent,
        passed=passed,
        attempt_number=attempt_number
    )
    db.add(qa)
    db.flush()
    return qa


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
