"""
repositories/course_repo.py
────────────────────────────
Data-access layer for Course, Module, and Lesson entities using SQLAlchemy ORM.
"""

from __future__ import annotations
from typing import Optional

from sqlalchemy.orm import Session, joinedload

from db.models import Course, Module, Lesson, LessonAsset, CourseStatus
from db.database import get_db


# ── Courses ────────────────────────────────────────────────────────────────────
def list_courses(db: Session) -> list[Course]:
    return db.query(Course).order_by(Course.created_at.desc()).all()


def get_course(db: Session, course_id: int) -> Optional[Course]:
    return (
        db.query(Course)
        .options(
            joinedload(Course.modules)
            .joinedload(Module.lessons)
            .joinedload(Lesson.assets)
        )
        .filter(Course.id == course_id)
        .first()
    )


def create_course(db: Session, title: str, description: str = "", source_document: str = "") -> Course:
    course = Course(title=title, description=description, source_document=source_document)
    db.add(course)
    db.flush()
    return course


def update_course_status(db: Session, course_id: int, status: CourseStatus) -> None:
    course = db.query(Course).filter(Course.id == course_id).first()
    if course:
        course.status = status
        db.flush()


def delete_course(db: Session, course_id: int) -> bool:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        return False
    db.delete(course)
    db.flush()
    return True


# ── Modules ────────────────────────────────────────────────────────────────────
def create_module(db: Session, course_id: int, title: str, order_index: int = 0) -> Module:
    mod = Module(course_id=course_id, title=title, order_index=order_index)
    db.add(mod)
    db.flush()
    return mod


# ── Lessons ────────────────────────────────────────────────────────────────────
def get_lesson(db: Session, lesson_id: int) -> Optional[Lesson]:
    return (
        db.query(Lesson)
        .options(joinedload(Lesson.assets))
        .filter(Lesson.id == lesson_id)
        .first()
    )


def create_lesson(
    db: Session, module_id: int, title: str, order_index: int = 0
) -> Lesson:
    lesson = Lesson(module_id=module_id, title=title, order_index=order_index)
    db.add(lesson)
    db.flush()
    return lesson


def update_lesson_content(
    db: Session, lesson_id: int, markdown: str
) -> None:
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if lesson:
        lesson.content_markdown = markdown
        db.flush()


# ── Lesson Assets ──────────────────────────────────────────────────────────────
def add_lesson_asset(
    db: Session,
    lesson_id: int,
    asset_type: str,
    content: str,
    caption: str = "",
    position: str = "end",
) -> LessonAsset:
    asset = LessonAsset(
        lesson_id=lesson_id,
        type=asset_type,
        content=content,
        caption=caption,
        position=position,
    )
    db.add(asset)
    db.flush()
    return asset


def delete_lesson_asset(db: Session, asset_id: int) -> None:
    asset = db.query(LessonAsset).filter(LessonAsset.id == asset_id).first()
    if asset:
        db.delete(asset)
        db.flush()
