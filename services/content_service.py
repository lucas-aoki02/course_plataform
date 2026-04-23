"""
services/content_service.py
────────────────────────────
Generates and persists Markdown lesson content using Groq (Llama 3 8B).
Uses SQLAlchemy ORM via get_db().
"""

from __future__ import annotations
import logging
from collections.abc import Generator
import config
from db.database import get_db
from db.models import Lesson
from services.ai_service import llama_service
from utils.prompts import (
    get_system_content_prompt,
    build_lesson_content_prompt,
)

logger = logging.getLogger(__name__)


def generate_lesson_stream(
    course_title: str,
    module_title: str,
    lesson_id: int,
    target_chars: int = 0,
    instructor_id: int | None = None,
) -> Generator[tuple[str, str], None, None]:
    """
    Generator that yields ('text', chunk) or ('status', msg).
    Persists paragraph chunks to the DB using SQLAlchemy.
    """

    # Fetch lesson title and clear existing content
    with get_db() as db:
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        if not lesson:
            raise ValueError(f"Lesson {lesson_id} not found")
        lesson_title = lesson.title
        lesson.content_markdown = ""

    prompt = build_lesson_content_prompt(course_title, module_title, lesson_title, target_chars)
    system = get_system_content_prompt(target_chars)

    full_content = ""
    current_paragraph = ""
    dynamic_max_tokens = 1500 if target_chars > 0 else 1200
    total_loops = 0
    max_loops = 5

    logger.info(f"[Groq] Streaming lesson: {lesson_title}")

    while True:
        total_loops += 1

        if total_loops > 1:
            prompt = (
                f"Continue writing the lesson '{lesson_title}'. "
                f"Write Part {total_loops}. Introduce entirely NEW advanced subtopics, examples, "
                f"and deep-dives. DO NOT summarize or repeat anything from previous parts. Use emojis."
            )
            yield "status", f"Starting Expansion Module {total_loops}..."

        for chunk in llama_service.generate_stream(
            prompt,
            system=system,
            temperature=0.7,
            max_tokens=dynamic_max_tokens,
            user_id=instructor_id,
        ):
            full_content += chunk
            current_paragraph += chunk
            yield "text", chunk

            if "\n\n" in current_paragraph:
                parts = current_paragraph.split("\n\n")
                for i in range(len(parts) - 1):
                    p_text = parts[i].strip()
                    if p_text:
                        with get_db() as db:
                            lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
                            if lesson:
                                existing = lesson.content_markdown or ""
                                lesson.content_markdown = f"{existing}\n\n{p_text}" if existing else p_text
                        yield "status", f"Paragraph saved: {len(p_text)} chars"
                current_paragraph = parts[-1]

        if target_chars == 0 or len(full_content) >= target_chars * 0.85 or total_loops >= max_loops:
            break

        yield "text", "\n\n***\n\n"
        current_paragraph += "\n\n***\n\n"

    # Save the final trailing paragraph
    if current_paragraph.strip():
        p_text = current_paragraph.strip()
        with get_db() as db:
            lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
            if lesson:
                existing = lesson.content_markdown or ""
                lesson.content_markdown = f"{existing}\n\n{p_text}" if existing else p_text

    yield "status", f"Text completed: {len(full_content)} characters total."


def get_full_content_as_text(course_id: int) -> str:
    """
    Concatenates all lesson content of a course into a single Markdown string.
    Used for tutor context.
    """
    from db.models import Module, Lesson

    with get_db() as db:
        modules = (
            db.query(Module)
            .filter(Module.course_id == course_id)
            .order_by(Module.order_index)
            .all()
        )
        parts: list[str] = []
        for mod in modules:
            parts.append(f"\n# {mod.title}\n")
            lessons = (
                db.query(Lesson)
                .filter(Lesson.module_id == mod.id)
                .order_by(Lesson.order_index)
                .all()
            )
            for lesson in lessons:
                parts.append(f"\n## {lesson.title}\n")
                parts.append(lesson.content_markdown or "(no content)")

    return "\n".join(parts)
