"""
services/quiz_service.py
─────────────────────────
Generates multiple-choice quiz questions from course content and persists them.

Flow
----
1. Build a lessons summary from all lesson titles in the course.
2. Call the LLM with the quiz prompt → parse JSON → validate with Pydantic.
3. Persist all questions as `Quiz` rows scoped to the course.

Design note:
  Quiz questions are generated in a single LLM call (not per-lesson) to
  allow the model to produce varied, complementary questions that cover
  the full course — not just individual lessons in isolation.
"""

from __future__ import annotations

import json
import logging
import re

from pydantic import BaseModel, Field, ValidationError, field_validator

import config
from db.database import get_session
from db.models import Module, Quiz
from services.ai_service import AIServiceError, llama_service
from utils.prompts import SYSTEM_QUIZ_LLAMA, build_quiz_prompt

logger = logging.getLogger(__name__)


# ── Pydantic Schema ───────────────────────────────────────────────────────────

class QuizQuestionSchema(BaseModel):
    """
    Validates a single quiz question from the LLM output.

    Fields
    ------
    question      : The question stem.
    options       : Exactly 4 answer strings.
    correct_index : 0-based index into options (0–3).
    explanation   : Rationale for the correct answer.
    """
    question: str = Field(..., min_length=5)
    options: list[str] = Field(..., min_length=4, max_length=4)
    correct_index: int = Field(..., ge=0, le=3)
    explanation: str = Field(..., min_length=5)

    @field_validator("question", "explanation", mode="before")
    @classmethod
    def _strip_text(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v

    @field_validator("options", mode="before")
    @classmethod
    def _strip_options(cls, v: list[str]) -> list[str]:
        return [s.strip() for s in v] if isinstance(v, list) else v


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_json_array(raw: str) -> str:
    """
    Extract a JSON array from an LLM response, stripping markdown fences.
    Also handles the case where the model wraps the array in an object.
    """
    # Try stripping code fences first
    match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", raw)
    if match:
        return match.group(1).strip()
    return raw.strip()


def _build_lessons_summary(course_id: int) -> str:
    """
    Build a bullet-point summary of all lesson titles for a course.

    Used as context in the quiz generation prompt so the LLM knows
    exactly which topics were covered.
    """
    with get_session() as db:
        modules = (
            db.query(Module)
            .filter(Module.course_id == course_id)
            .order_by(Module.order_index)
            .all()
        )
        lines: list[str] = []
        for module in modules:
            lines.append(f"\nModule: {module.title}")
            for lesson in sorted(module.lessons, key=lambda l: l.order_index):
                lines.append(f"  - {lesson.title}")
    return "\n".join(lines)


# ── Core Functions ────────────────────────────────────────────────────────────

def generate_quiz_questions(
    course_id: int,
    course_title: str,
    n_questions: int = config.DEFAULT_NUM_QUESTIONS,
) -> list[QuizQuestionSchema]:
    """
    Call the LLM to generate quiz questions for a course.

    Stateless — does NOT write to the database.

    Args
    ----
    course_id    : Used to fetch lesson titles as context.
    course_title : Used in the prompt for coherence.
    n_questions  : Number of questions to request (default from config).

    Returns
    -------
    list[QuizQuestionSchema] : Validated list of quiz questions.

    Raises
    ------
    AIServiceError : On LLM failure.
    ValueError     : On JSON parse or schema validation failure.
    """
    lessons_summary = _build_lessons_summary(course_id)
    prompt = build_quiz_prompt(course_title, lessons_summary, n_questions)

    logger.info("[Llama] Generating %d quiz questions for course_id=%d", n_questions, course_id)
    raw = llama_service.generate(prompt, system=SYSTEM_QUIZ_LLAMA)
    clean = _extract_json_array(raw)

    try:
        data = json.loads(clean)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM returned invalid JSON for quiz.\nRaw: {raw}\nError: {e}") from e

    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON array, got {type(data).__name__}")

    questions: list[QuizQuestionSchema] = []
    for i, item in enumerate(data):
        try:
            questions.append(QuizQuestionSchema(**item))
        except ValidationError as e:
            logger.warning("Question %d failed validation, skipping: %s", i, e)

    if not questions:
        raise ValueError("No valid questions could be parsed from LLM output.")

    logger.info("Generated %d valid questions", len(questions))
    return questions


def save_quiz_questions(course_id: int, questions: list[QuizQuestionSchema]) -> list[Quiz]:
    """
    Persist validated quiz questions to SQLite.

    Clears any existing questions for this course before inserting,
    preventing duplicates if regeneration is triggered.

    Args
    ----
    course_id : Scope for the quiz questions.
    questions : Validated list from `generate_quiz_questions()`.

    Returns
    -------
    list[Quiz] : Newly created Quiz ORM objects.
    """
    with get_session() as db:
        # Clear existing questions for idempotency
        db.query(Quiz).filter(Quiz.course_id == course_id).delete()

        saved: list[Quiz] = []
        for q in questions:
            quiz = Quiz(
                course_id=course_id,
                question=q.question,
                options=q.options,
                correct_index=q.correct_index,
                explanation=q.explanation,
            )
            db.add(quiz)
            saved.append(quiz)

    return saved


def generate_and_save_quiz(
    course_id: int,
    course_title: str,
    n_questions: int = config.DEFAULT_NUM_QUESTIONS,
) -> list[QuizQuestionSchema]:
    """
    High-level orchestrator: generate → validate → persist.

    Returns
    -------
    list[QuizQuestionSchema] : For display in the UI immediately after saving.
    """
    questions = generate_quiz_questions(course_id, course_title, n_questions)
    save_quiz_questions(course_id, questions)
    return questions
