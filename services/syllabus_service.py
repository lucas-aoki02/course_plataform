"""
services/syllabus_service.py
────────────────────────────
AI-powered syllabus generation and persistence using SQLAlchemy ORM.
"""

from __future__ import annotations
import json
import logging
import re
import config
from db.database import get_db
from db.models import CourseStatus
from services.ai_service import AIServiceError, ai_service
from utils.prompts import SYSTEM_SYLLABUS, build_syllabus_prompt

logger = logging.getLogger(__name__)


class ModuleSchema:
    def __init__(self, title, lessons):
        self.title = title.get("title", str(title)) if isinstance(title, dict) else str(title)
        self.lessons = lessons


class SyllabusSchema:
    def __init__(self, title, description, modules):
        self.title = title.get("title", str(title)) if isinstance(title, dict) else str(title)
        self.description = description.get("description", str(description)) if isinstance(description, dict) else str(description)
        self.modules = [ModuleSchema(**m) if isinstance(m, dict) else m for m in modules]


def _extract_json(raw: str) -> str:
    match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", raw)
    if match:
        return match.group(1)
    return raw.strip()


def generate_syllabus(
    topic: str,
    num_modules: int = config.DEFAULT_NUM_MODULES,
    num_lessons: int = config.DEFAULT_NUM_LESSONS,
    module_themes: str = "",
    instructor_id: int | None = None,
) -> SyllabusSchema:
    prompt = build_syllabus_prompt(topic, num_modules, num_lessons, module_themes)
    logger.info("Generating syllabus for topic: %s", topic)

    raw_response = ai_service.generate(prompt, system=SYSTEM_SYLLABUS, user_id=instructor_id)
    clean_json = _extract_json(raw_response)

    try:
        data = json.loads(clean_json)
        if not all(k in data for k in ("title", "description", "modules")):
            raise ValueError("Missing required keys in syllabus JSON")
        return SyllabusSchema(
            title=data["title"],
            description=data["description"],
            modules=[ModuleSchema(m["title"], m["lessons"]) for m in data["modules"]],
        )
    except Exception as e:
        logger.error(f"Syllabus parse error: {e}")
        raise ValueError(f"Failed to parse syllabus: {e}")


def save_syllabus(topic: str, syllabus: SyllabusSchema, instructor_id: int | None = None):
    """Persist syllabus to DB using SQLAlchemy ORM."""
    from repositories.course_repo import create_course, create_module, create_lesson, update_course_status

    with get_db() as db:
        course = create_course(db, syllabus.title, syllabus.description, source_document=topic, instructor_id=instructor_id)

        for m_idx, mod in enumerate(syllabus.modules):
            module = create_module(db, course.id, mod.title, order_index=m_idx)
            for l_idx, lesson_data in enumerate(mod.lessons):
                l_title = (
                    lesson_data.get("title", str(lesson_data))
                    if isinstance(lesson_data, dict)
                    else str(lesson_data)
                )
                create_lesson(db, module.id, l_title[:255], order_index=l_idx)

        update_course_status(db, course.id, CourseStatus.generating)

        # Return a lightweight object for session state
        course_id = course.id
        course_title = course.title

    class _CourseRef:
        def __init__(self, id_, title):
            self.id = id_
            self.title = title

    return _CourseRef(course_id, course_title)


def generate_and_save_syllabus(topic: str, num_mod=None, num_less=None, module_themes: str = "", instructor_id: int | None = None):
    n_m = num_mod or config.DEFAULT_NUM_MODULES
    n_l = num_less or config.DEFAULT_NUM_LESSONS
    syllabus = generate_syllabus(topic, n_m, n_l, module_themes, instructor_id=instructor_id)
    course = save_syllabus(topic, syllabus, instructor_id=instructor_id)
    return course, syllabus
