"""
services/syllabus_service.py
────────────────────────────
AI-powered syllabus generation and persistence using raw SQL and dictionaries.
Removes Pydantic dependency.
"""

from __future__ import annotations
import json
import logging
import re
import config
from db.database import get_connection
from services.ai_service import AIServiceError, ai_service
from utils.prompts import SYSTEM_SYLLABUS, build_syllabus_prompt

logger = logging.getLogger(__name__)

# Mock schemas using SimpleNamespace/Dict for compatibility
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
) -> SyllabusSchema:
    prompt = build_syllabus_prompt(topic, num_modules, num_lessons)
    logger.info("Generating syllabus for topic: %s", topic)
    
    raw_response = ai_service.generate(prompt, system=SYSTEM_SYLLABUS)
    clean_json = _extract_json(raw_response)

    try:
        data = json.loads(clean_json)
        # Basic validation
        if not all(k in data for k in ("title", "description", "modules")):
            raise ValueError("Missing required keys in syllabus JSON")
        
        return SyllabusSchema(
            title=data["title"],
            description=data["description"],
            modules=[ModuleSchema(m["title"], m["lessons"]) for m in data["modules"]]
        )
    except Exception as e:
        logger.error(f"Syllabus parse error: {e}")
        raise ValueError(f"Failed to parse syllabus: {e}")

def save_syllabus(topic: str, syllabus: SyllabusSchema):
    """Persist syllabus to SQLite using raw SQL."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # 1. Create Course
        cursor.execute(
            "INSERT INTO courses (title, description, status) VALUES (?, ?, ?)",
            (syllabus.title, syllabus.description, "GENERATING")
        )
        course_id = cursor.lastrowid
        
        # 2. Create Modules & Lessons
        for m_idx, mod in enumerate(syllabus.modules):
            cursor.execute(
                "INSERT INTO modules (course_id, title, order_index) VALUES (?, ?, ?)",
                (course_id, mod.title, m_idx)
            )
            module_id = cursor.lastrowid
            
            for l_idx, lesson_data in enumerate(mod.lessons):
                l_title = lesson_data.get("title", str(lesson_data)) if isinstance(lesson_data, dict) else str(lesson_data)
                cursor.execute(
                    "INSERT INTO lessons (module_id, title, order_index) VALUES (?, ?, ?)",
                    (module_id, l_title[:255], l_idx)
                )
        
        conn.commit()
        # Return a simple object with id and title
        from repositories.course_repo import DBRow
        return DBRow(id=course_id, title=syllabus.title)
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def generate_and_save_syllabus(topic: str, num_mod=None, num_less=None):
    n_m = num_mod or config.DEFAULT_NUM_MODULES
    n_l = num_less or config.DEFAULT_NUM_LESSONS
    syllabus = generate_syllabus(topic, n_m, n_l)
    course = save_syllabus(topic, syllabus)
    return course, syllabus
