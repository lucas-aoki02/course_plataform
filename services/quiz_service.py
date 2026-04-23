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
    # Try to find a JSON array directly
    arr_match = re.search(r"(\[\s*\{[\s\S]*\}\s*\])", raw)
    if arr_match:
        return arr_match.group(1).strip()
    return raw.strip()


def _repair_json(raw: str) -> str:
    """Attempt common JSON repairs before raising a parse error."""
    # Remove trailing commas before ] or }
    cleaned = re.sub(r",\s*([\]\}])", r"\1", raw)
    # Replace fancy quotes
    cleaned = cleaned.replace("\u201c", '"').replace("\u201d", '"').replace("\u2018", "'").replace("\u2019", "'")
    return cleaned


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
    topic: str, content_summary: str, n_questions: int = config.DEFAULT_NUM_QUESTIONS, instructor_id: int | None = None
):
    prompt = build_quiz_prompt(topic, content_summary, n_questions)

    logger.info(f"[Groq] Generating {n_questions} questions for topic: {topic}")

    for attempt in range(3):
        if attempt > 0:
            # On retry, use a stricter prompt
            prompt = (
                f"Generate EXACTLY {n_questions} multiple-choice quiz questions about '{topic}' "
                f"based on the following content:\n\n{content_summary}\n\n"
                f"Your response must be a valid JSON array. Each element must be an object with keys: "
                f"\"question\" (string), \"options\" (array of 4 strings), "
                f"\"correct_index\" (integer 0-3), \"explanation\" (string). "
                f"Output ONLY the JSON array, no extra text, no markdown fences. "
                f"Every string value must use escaped double-quotes where needed."
            )
            logger.warning(f"[Groq] Quiz retry attempt {attempt}")

        raw = llama_service.generate(prompt, system=SYSTEM_QUIZ_LLAMA, user_id=instructor_id, max_tokens=3000)
        clean = _extract_json_array(raw)

        try:
            data = json.loads(clean)
            if isinstance(data, list) and data:
                # Enforce exact count: trim if too many, warn if too few
                if len(data) > n_questions:
                    data = data[:n_questions]
                return data
            raise ValueError("Expected non-empty list of questions")
        except json.JSONDecodeError:
            # Try JSON repair
            try:
                repaired = _repair_json(clean)
                data = json.loads(repaired)
                if isinstance(data, list) and data:
                    logger.info("Quiz JSON repaired successfully.")
                    return data
            except Exception:
                pass
            logger.warning(f"Quiz parse failed on attempt {attempt + 1}, retrying...")

    logger.error("All quiz generation attempts failed.")
    raise ValueError("Failed to generate a valid quiz after 3 attempts. Please try again.")


def save_quiz_draft(db_session, draft_questions: list, course_id: int, module_id: int | None = None, lesson_id: int | None = None) -> None:
    from repositories.quiz_repo import empty_quizzes_for_scope, create_quiz_item
    # Clear existing quiz items for this specific scope
    empty_quizzes_for_scope(db_session, course_id=course_id, module_id=module_id, lesson_id=lesson_id)

    for q in draft_questions:
        options = q.get("options", [])
        # Pad to 4 options if needed
        while len(options) < 4:
            options.append("")
        options = options[:4]
        question_text = q.get("question", "").strip()
        if not question_text:
            continue  # Skip empty questions
        create_quiz_item(
            db_session,
            course_id=course_id if not module_id and not lesson_id else None,
            module_id=module_id,
            lesson_id=lesson_id,
            question_text=question_text,
            options=options,
            correct_answer=str(min(q.get("correct_index", 0), 3)),
            explanation=q.get("explanation", "")
        )


def generate_quiz_draft(
    topic: str, content_summary: str, n_questions: int = None, instructor_id: int | None = None
):
    n = n_questions or config.DEFAULT_NUM_QUESTIONS
    questions = generate_quiz_questions(topic, content_summary, n, instructor_id=instructor_id)
    return questions
