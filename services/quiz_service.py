"""
services/quiz_service.py
─────────────────────────
Generates multiple-choice quiz questions from course content and persists them.
Uses SQLAlchemy ORM via get_db().
"""

from __future__ import annotations
import json
import logging
import re
import config
from db.database import get_db
from db.models import Module, Lesson, Quiz
from services.ai_service import llama_service
from utils.prompts import SYSTEM_QUIZ_LLAMA, build_quiz_prompt

logger = logging.getLogger(__name__)


def _extract_json_array(raw: str) -> str:
    match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", raw)
    if match:
        return match.group(1).strip()
    return raw.strip()


def _build_lessons_summary(course_id: int) -> str:
    with get_db() as db:
        modules = (
            db.query(Module)
            .filter(Module.course_id == course_id)
            .order_by(Module.order_index)
            .all()
        )
        lines = []
        for mod in modules:
            lines.append(f"\nModule: {mod.title}")
            lessons = (
                db.query(Lesson)
                .filter(Lesson.module_id == mod.id)
                .order_by(Lesson.order_index)
                .all()
            )
            for lesson in lessons:
                lines.append(f"  - {lesson.title}")
    return "\n".join(lines)


def generate_quiz_questions(
    course_id: int, course_title: str, n_questions: int = config.DEFAULT_NUM_QUESTIONS
):
    summary = _build_lessons_summary(course_id)
    prompt = build_quiz_prompt(course_title, summary, n_questions)

    logger.info(f"[Groq] Generating {n_questions} questions")
    raw = llama_service.generate(prompt, system=SYSTEM_QUIZ_LLAMA)
    clean = _extract_json_array(raw)

    try:
        data = json.loads(clean)
        if not isinstance(data, list):
            raise ValueError("Expected list of questions")
        return data
    except Exception as e:
        logger.error(f"Quiz parse error: {e}")
        raise ValueError(f"Failed to generate quiz: {e}")


def save_quiz_questions(course_id: int, questions: list) -> None:
    with get_db() as db:
        # Clear existing quiz items for this course
        db.query(Quiz).filter(Quiz.course_id == course_id).delete()

        for q in questions:
            opts_json = json.dumps(q.get("options", []))
            quiz_item = Quiz(
                course_id=course_id,
                question_text=q.get("question", ""),
                options_json=opts_json,
                correct_answer=str(q.get("correct_index", 0)),
                explanation=q.get("explanation", ""),
            )
            db.add(quiz_item)


def generate_and_save_quiz(
    course_id: int, title: str, n_questions: int = None
):
    n = n_questions or config.DEFAULT_NUM_QUESTIONS
    questions = generate_quiz_questions(course_id, title, n)
    save_quiz_questions(course_id, questions)
    return questions
