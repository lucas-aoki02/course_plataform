"""
services/content_service.py
────────────────────────────
Generates and persists Markdown lesson content using the Hybrid LLM architecture.

Model routing
-------------
  generate_lesson_content()  → Llama 3.2  (fast, local, no token cost)
  refine_course_content()    → Gemini      (review for tone + accuracy)
  generate_audio_script()    → Llama 3.2  (narration script per lesson)

Flow (generate_all_content)
----------------------------
1. Load all modules + lessons for a given course_id from the DB.
2. For each lesson: call Llama to expand the lesson → persist content.
3. Update Course.status to COMPLETE when all lessons are done.
4. (Optional, user-triggered) Call Gemini to refine content lesson-by-lesson.
"""

from __future__ import annotations

import logging
from collections.abc import Generator

from sqlalchemy.orm import joinedload

import config
from db.database import get_session
from db.models import Course, CourseStatus, Lesson, Module
from services.ai_service import ai_service, llama_service
from utils.prompts import (
    SYSTEM_CONTENT_LLAMA,
    SYSTEM_CONTENT_REFINE,
    SYSTEM_AUDIO_SCRIPT,
    build_lesson_content_prompt,
    build_content_refinement_prompt,
    build_audio_script_prompt,
)

logger = logging.getLogger(__name__)


# ── Lesson Content (Llama 3.2) ────────────────────────────────────────────────

def generate_lesson_content(
    course_title: str,
    module_title: str,
    lesson_title: str,
) -> str:
    """
    Call Llama 3.2 to generate full Markdown content for a single lesson.

    This function is stateless — it does NOT touch the database.
    Use `generate_all_content()` for the full pipeline.

    Args
    ----
    course_title  : Parent course title (adds context for the LLM).
    module_title  : Parent module title (adds context for the LLM).
    lesson_title  : The specific lesson to generate content for.

    Returns
    -------
    str : Markdown-formatted lesson content.
    """
    prompt = build_lesson_content_prompt(course_title, module_title, lesson_title)
    return llama_service.generate(prompt, system=SYSTEM_CONTENT_LLAMA)


def generate_all_content(course_id: int) -> Generator[tuple[int, int, str], None, None]:
    """
    Generate and persist content for every lesson in a course using Llama 3.2.

    This is a *generator* function — it yields progress info after each lesson
    so the Streamlit UI can update a progress bar in real time.

    Yields
    ------
    tuple[current: int, total: int, lesson_title: str]
        - current     : Number of lessons completed so far.
        - total       : Total lessons to generate.
        - lesson_title: Title of the lesson just completed.

    Args
    ----
    course_id : Primary key of the Course whose lessons need content.

    Side Effects
    ------------
    - Writes `content_markdown` to each Lesson row.
    - Sets `Course.status = COMPLETE` on completion.
    """
    # 1. Load all lessons (with their module/course context) in a single query
    with get_session() as db:
        course = db.get(Course, course_id)
        if not course:
            raise ValueError(f"Course {course_id} not found")
        course_title = course.title

        modules: list[Module] = (
            db.query(Module)
            .options(joinedload(Module.lessons))
            .filter(Module.course_id == course_id)
            .order_by(Module.order_index)
            .all()
        )

        lesson_pairs: list[tuple[str, Lesson]] = [
            (module.title, lesson)
            for module in modules
            for lesson in sorted(module.lessons, key=lambda l: l.order_index)
        ]
        total = len(lesson_pairs)

    # 2. Generate content lesson-by-lesson (Llama 3.2)
    for idx, (module_title, lesson) in enumerate(lesson_pairs, start=1):
        logger.info("[Llama] Generating content for lesson: %s", lesson.title)

        content = generate_lesson_content(course_title, module_title, lesson.title)

        # 3. Persist immediately after each generation
        with get_session() as db:
            db_lesson = db.get(Lesson, lesson.id)
            if db_lesson:
                db_lesson.content_markdown = content

        yield idx, total, lesson.title

    # 4. Mark course as complete
    with get_session() as db:
        db_course = db.get(Course, course_id)
        if db_course:
            db_course.status = CourseStatus.COMPLETE

    logger.info("All content generated for course_id=%d", course_id)


# ── Content Refinement (Gemini) ───────────────────────────────────────────────

def refine_course_content(course_id: int) -> Generator[tuple[int, int, str], None, None]:
    """
    Refine all lesson content for a course using Gemini.

    Reads Llama-generated content for each lesson, sends it to Gemini for
    tone/accuracy review, and persists the refined version back to the DB.
    Sets Course.refined = True when done.

    Yields
    ------
    tuple[current: int, total: int, lesson_title: str]
        - current     : Lessons refined so far.
        - total       : Total lessons to refine.
        - lesson_title: Title of the lesson just refined.

    Args
    ----
    course_id : Primary key of the Course to refine.
    """
    with get_session() as db:
        course = db.get(Course, course_id)
        if not course:
            raise ValueError(f"Course {course_id} not found")
        course_title = course.title

        modules: list[Module] = (
            db.query(Module)
            .options(joinedload(Module.lessons))
            .filter(Module.course_id == course_id)
            .order_by(Module.order_index)
            .all()
        )

        lesson_triples: list[tuple[str, Lesson]] = [
            (module.title, lesson)
            for module in modules
            for lesson in sorted(module.lessons, key=lambda l: l.order_index)
        ]
        total = len(lesson_triples)

    for idx, (module_title, lesson) in enumerate(lesson_triples, start=1):
        logger.info("[Gemini] Refining content for lesson: %s", lesson.title)

        prompt = build_content_refinement_prompt(
            course_title, module_title, lesson.title, lesson.content_markdown
        )
        refined_content = ai_service.generate(prompt, system=SYSTEM_CONTENT_REFINE)

        with get_session() as db:
            db_lesson = db.get(Lesson, lesson.id)
            if db_lesson:
                db_lesson.content_markdown = refined_content

        yield idx, total, lesson.title

    with get_session() as db:
        db_course = db.get(Course, course_id)
        if db_course:
            db_course.refined = True

    logger.info("[Gemini] Refinement complete for course_id=%d", course_id)


# ── Audio Script (Llama 3.2) ──────────────────────────────────────────────────

def generate_audio_script(lesson_id: int) -> str:
    """
    Generate and persist a narration script for a single lesson using Llama 3.2.

    Args
    ----
    lesson_id : Primary key of the Lesson to generate the script for.

    Returns
    -------
    str : The generated narration script text (plain text, no Markdown).

    Raises
    ------
    ValueError : If the lesson is not found or has no content.
    """
    with get_session() as db:
        lesson = db.get(Lesson, lesson_id)
        if not lesson:
            raise ValueError(f"Lesson {lesson_id} not found")
        if not lesson.content_markdown:
            raise ValueError("Lesson has no content — generate content first.")
        lesson_title = lesson.title
        content = lesson.content_markdown

    logger.info("[Llama] Generating audio script for lesson: %s", lesson_title)
    prompt = build_audio_script_prompt(lesson_title, content)
    script = llama_service.generate(prompt, system=SYSTEM_AUDIO_SCRIPT)

    with get_session() as db:
        db_lesson = db.get(Lesson, lesson_id)
        if db_lesson:
            db_lesson.audio_script = script

    return script


# ── Read Helpers ──────────────────────────────────────────────────────────────

def get_full_content_as_text(course_id: int) -> str:
    """
    Concatenate all lesson content into a single plain-text document.

    Used by `chatbot_service` to build the knowledge base for the tutor.

    Returns
    -------
    str : All lesson Markdown content joined by section separators.
    """
    with get_session() as db:
        modules = (
            db.query(Module)
            .options(joinedload(Module.lessons))
            .filter(Module.course_id == course_id)
            .order_by(Module.order_index)
            .all()
        )
        parts: list[str] = []
        for module in modules:
            parts.append(f"\n# {module.title}\n")
            for lesson in sorted(module.lessons, key=lambda l: l.order_index):
                parts.append(f"\n## {lesson.title}\n")
                parts.append(lesson.content_markdown or "(no content yet)")

    return "\n".join(parts)
