"""
services/syllabus_service.py
────────────────────────────
Responsible for AI-powered syllabus generation and persistence.

Flow
----
1.  `generate_syllabus()` calls the LLM with a structured JSON prompt.
2.  The raw JSON string is parsed and validated with Pydantic models.
3.  `save_syllabus()` persists the validated structure to SQLite.
4.  `generate_and_save_syllabus()` is the high-level entry point that
    orchestrates steps 1–3 and returns a `Course` ORM object.

Why Pydantic for validation?
  The LLM might return malformed JSON, wrong field names, or missing keys.
  Pydantic raises a clear `ValidationError` instead of a cryptic `KeyError`
  deep in the persistence layer.
"""

from __future__ import annotations

import json
import logging
import re

from pydantic import BaseModel, Field, ValidationError, field_validator

import config
from db.database import get_session
from db.models import Course, CourseStatus, Lesson, Module
from services.ai_service import AIServiceError, ai_service
from utils.prompts import SYSTEM_SYLLABUS, build_syllabus_prompt

logger = logging.getLogger(__name__)


# ── Pydantic Schemas (LLM output validation) ──────────────────────────────────

class LessonSchema(BaseModel):
    """Validates a single lesson title from the LLM output."""
    title: str = Field(..., min_length=1)


class ModuleSchema(BaseModel):
    """
    Validates a module from the LLM output.
    `lessons` is a flat list of lesson title strings (not nested objects)
    to match the simpler JSON format we request in the prompt.
    """
    title: str = Field(..., min_length=1)
    lessons: list[str] = Field(..., min_length=1)

    @field_validator("title", mode="before")
    @classmethod
    def _strip_title(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v

    @field_validator("lessons", mode="before")
    @classmethod
    def _strip_lessons(cls, v: list[str]) -> list[str]:
        return [s.strip() for s in v] if isinstance(v, list) else v


class SyllabusSchema(BaseModel):
    """
    Root schema for the full syllabus JSON returned by the LLM.
    Used to validate before any database write happens.
    """
    title: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    modules: list[ModuleSchema] = Field(..., min_length=1)

    @field_validator("title", mode="before")
    @classmethod
    def _strip_title(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v

    @field_validator("description", mode="before")
    @classmethod
    def _strip_description(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v


# ── Core Functions ────────────────────────────────────────────────────────────

def _extract_json(raw: str) -> str:
    """
    Strip markdown code fences from LLM output if present.

    Some models wrap JSON in ```json ... ``` even when instructed not to.
    This function extracts the raw JSON content defensively.

    Args
    ----
    raw : Raw string from the LLM.

    Returns
    -------
    str : Cleaned JSON string ready for `json.loads()`.
    """
    # Match ```json ... ``` or ``` ... ```
    match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", raw)
    if match:
        return match.group(1)
    return raw.strip()


def generate_syllabus(
    topic: str,
    num_modules: int = config.DEFAULT_NUM_MODULES,
    num_lessons: int = config.DEFAULT_NUM_LESSONS,
) -> SyllabusSchema:
    """
    Call the LLM to generate a structured course syllabus.

    This function is *pure* — it does NOT write to the database.
    It returns a validated `SyllabusSchema` object that the caller can
    inspect, display in the UI for editing, or pass to `save_syllabus()`.

    Args
    ----
    topic       : User-provided course topic (e.g., "Python for Data Science").
    num_modules : Target number of modules (default from config).
    num_lessons : Target lessons per module (default from config).

    Returns
    -------
    SyllabusSchema : Validated Pydantic model with title, description, modules.

    Raises
    ------
    AIServiceError   : If the LLM call fails.
    ValueError       : If the LLM response cannot be parsed or validated.
    """
    prompt = build_syllabus_prompt(topic, num_modules, num_lessons)

    logger.info("Generating syllabus for topic: %s", topic)
    raw_response = ai_service.generate(prompt, system=SYSTEM_SYLLABUS)

    clean_json = _extract_json(raw_response)

    try:
        data = json.loads(clean_json)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"LLM returned invalid JSON for syllabus.\n"
            f"Raw response:\n{raw_response}\nError: {e}"
        ) from e

    try:
        syllabus = SyllabusSchema(**data)
    except ValidationError as e:
        raise ValueError(
            f"LLM syllabus JSON failed schema validation.\nErrors: {e}"
        ) from e

    logger.info(
        "Syllabus generated: '%s' with %d modules", syllabus.title, len(syllabus.modules)
    )
    return syllabus


def save_syllabus(topic: str, syllabus: SyllabusSchema) -> Course:
    """
    Persist a validated `SyllabusSchema` to SQLite.

    Creates one `Course`, N `Module`s, and M `Lesson`s per module.
    The course status is set to `GENERATING` — it becomes `COMPLETE`
    only after lesson content is also saved (handled by `content_service`).

    Args
    ----
    topic   : Original user input, stored for reference.
    syllabus: A validated SyllabusSchema (from `generate_syllabus()`).

    Returns
    -------
    Course : The persisted SQLAlchemy Course ORM object (with ID populated).
    """
    with get_session() as db:
        course = Course(
            title=syllabus.title,
            description=syllabus.description,
            topic=topic,
            status=CourseStatus.GENERATING,
        )
        db.add(course)
        db.flush()  # Flush to get course.id before inserting children

        for module_index, module_data in enumerate(syllabus.modules):
            module = Module(
                course_id=course.id,
                title=module_data.title,
                order_index=module_index,
            )
            db.add(module)
            db.flush()  # Flush to get module.id before inserting lessons

            for lesson_index, lesson_title in enumerate(module_data.lessons):
                lesson = Lesson(
                    module_id=module.id,
                    title=lesson_title,
                    content_markdown="",  # Content generated in next step
                    order_index=lesson_index,
                )
                db.add(lesson)

        # `db.commit()` is called by the context manager on exit
        return course


def generate_and_save_syllabus(
    topic: str,
    num_modules: int = config.DEFAULT_NUM_MODULES,
    num_lessons: int = config.DEFAULT_NUM_LESSONS,
) -> tuple[Course, SyllabusSchema]:
    """
    High-level orchestrator: generate → validate → persist.

    This is the function called by the Streamlit UI in Step 1 of the
    course creation flow.

    Returns
    -------
    tuple[Course, SyllabusSchema]
        - `Course`         : Persisted ORM object with `course.id` populated.
        - `SyllabusSchema` : The validated syllabus (for display in the UI).

    Example
    -------
    >>> course, syllabus = generate_and_save_syllabus("Neural Networks 101")
    >>> print(course.id, syllabus.title)
    1  "Neural Networks 101: A Beginner's Guide"
    """
    syllabus = generate_syllabus(topic, num_modules, num_lessons)
    course = save_syllabus(topic, syllabus)
    return course, syllabus
