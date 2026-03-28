"""
repositories/course_repo.py
────────────────────────────
Data-access layer for Course, Module, and Lesson entities.

Why a Repository layer?
  Views shouldn't construct SQLAlchemy queries directly — that couples UI
  code to the persistence model. The repository pattern gives us one place
  to change query logic (add indexes, eager loads, filters) without touching
  any view.

All functions accept an optional `db` session parameter to support
both standalone use and transaction composition (passing an already-open
session to group multiple operations in one transaction).
"""

from __future__ import annotations

from sqlalchemy.orm import joinedload

from db.database import get_session
from db.models import Course, CourseStatus, Lesson, Module


# ── Course ────────────────────────────────────────────────────────────────────

def list_courses() -> list[Course]:
    """
    Return all courses ordered by creation date (newest first).

    Modules and lessons are NOT eagerly loaded here to keep the home
    page query fast — individual course views load them separately.
    """
    with get_session() as db:
        return (
            db.query(Course)
            .order_by(Course.created_at.desc())
            .all()
        )


def get_course(course_id: int) -> Course | None:
    """
    Fetch a single Course by primary key, eagerly loading modules → lessons.

    Returns None if not found (callers handle the 404 case).
    """
    with get_session() as db:
        return (
            db.query(Course)
            .options(
                joinedload(Course.modules).joinedload(Module.lessons)
            )
            .filter(Course.id == course_id)
            .first()
        )


def update_course_status(course_id: int, status: CourseStatus) -> None:
    """Update the lifecycle status of a course in-place."""
    with get_session() as db:
        course = db.get(Course, course_id)
        if course:
            course.status = status


def delete_course(course_id: int) -> bool:
    """
    Delete a course and all its children (cascade handles modules/lessons/quizzes).

    Returns True if a course was found and deleted, False if not found.
    """
    with get_session() as db:
        course = db.get(Course, course_id)
        if not course:
            return False
        db.delete(course)
        return True


# ── Module & Lesson ───────────────────────────────────────────────────────────

def get_modules_with_lessons(course_id: int) -> list[Module]:
    """
    Fetch all modules for a course, with their lessons eagerly loaded.
    Results are ordered by `order_index` at both levels.
    """
    with get_session() as db:
        return (
            db.query(Module)
            .options(joinedload(Module.lessons))
            .filter(Module.course_id == course_id)
            .order_by(Module.order_index)
            .all()
        )


def get_lesson(lesson_id: int) -> Lesson | None:
    """Fetch a single Lesson by primary key."""
    with get_session() as db:
        return db.get(Lesson, lesson_id)


def update_module_title(module_id: int, new_title: str) -> None:
    """Update a module's title (used after inline editing in the UI)."""
    with get_session() as db:
        module = db.get(Module, module_id)
        if module:
            module.title = new_title


def update_lesson_title(lesson_id: int, new_title: str) -> None:
    """Update a lesson's title (used after inline editing in the UI)."""
    with get_session() as db:
        lesson = db.get(Lesson, lesson_id)
        if lesson:
            lesson.title = new_title
