"""
repositories/course_repo.py
────────────────────────────
Data-access layer for Course, Module, and Lesson entities using SQLAlchemy ORM.
"""

from __future__ import annotations
from typing import Optional

from sqlalchemy.orm import Session, joinedload

from db.models import Course, Module, Lesson, LessonAsset, CourseStatus, Enrollment
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


def create_course(db: Session, title: str, description: str = "", source_document: str = "", instructor_id: Optional[int] = None, tags: str = "") -> Course:
    course = Course(title=title, description=description, source_document=source_document, instructor_id=instructor_id, tags=tags)
    db.add(course)
    db.flush()
    return course


def update_course_status(db: Session, course_id: int, status: CourseStatus) -> None:
    course = db.query(Course).filter(Course.id == course_id).first()
    if course:
        course.status = status
        db.flush()


def update_course(db: Session, course_id: int, title: str = None, description: str = None, tags: str = None) -> Optional[Course]:
    """Updates course title, description, and/or tags."""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        return None
    if title is not None:
        course.title = title
    if description is not None:
        course.description = description
    if tags is not None:
        course.tags = tags
    db.flush()
    return course


def update_course_quiz_settings(
    db: Session, 
    course_id: int, 
    passing_score: Optional[int] = None, 
    max_attempts: Optional[int] = None
) -> None:
    course = db.query(Course).filter(Course.id == course_id).first()
    if course:
        if passing_score is not None:
            course.quiz_passing_score = passing_score
        if max_attempts is not None:
            course.quiz_max_attempts = max_attempts
        db.flush()


def update_course_certificate(
    db: Session,
    course_id: int,
    path: Optional[str]
) -> None:
    course = db.query(Course).filter(Course.id == course_id).first()
    if course:
        course.certificate_path = path
        db.flush()


def delete_course(db: Session, course_id: int) -> bool:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        return False
    db.delete(course)
    db.flush()
    return True


def list_courses_by_instructor(db: Session, instructor_id: int) -> list[Course]:
    return db.query(Course).filter(Course.instructor_id == instructor_id).order_by(Course.created_at.desc()).all()


def list_courses_for_student(db: Session, student_id: int) -> list[Course]:
    return (
        db.query(Course)
        .join(Enrollment, Course.id == Enrollment.course_id)
        .filter(Enrollment.user_id == student_id)
        .order_by(Course.created_at.desc())
        .all()
    )


def search_courses(db: Session, query: str) -> list[Course]:
    """Search courses by title, description, or tags."""
    from sqlalchemy import or_
    search_term = f"%{query}%"
    return (
        db.query(Course)
        .filter(
            or_(
                Course.title.ilike(search_term),
                Course.description.ilike(search_term),
                Course.tags.ilike(search_term),
            )
        )
        .filter(Course.status == CourseStatus.complete)
        .all()
    )


def enroll_student(db: Session, student_id: int, course_id: int) -> Enrollment:
    existing = db.query(Enrollment).filter_by(user_id=student_id, course_id=course_id).first()
    if existing:
        return existing
    enrollment = Enrollment(user_id=student_id, course_id=course_id)
    db.add(enrollment)
    db.flush()
    return enrollment


def unenroll_student(db: Session, student_id: int, course_id: int) -> bool:
    enrollment = db.query(Enrollment).filter_by(user_id=student_id, course_id=course_id).first()
    if enrollment:
        db.delete(enrollment)
        db.flush()
        return True
    return False


# ── Modules ────────────────────────────────────────────────────────────────────
def create_module(db: Session, course_id: int, title: str, order_index: int = 0) -> Module:
    mod = Module(course_id=course_id, title=title, order_index=order_index)
    db.add(mod)
    db.flush()
    return mod


def update_module_quiz_settings(
    db: Session, 
    module_id: int, 
    passing_score: Optional[int] = None, 
    max_attempts: Optional[int] = None
) -> None:
    mod = db.query(Module).filter(Module.id == module_id).first()
    if mod:
        if passing_score is not None:
            mod.quiz_passing_score = passing_score
        if max_attempts is not None:
            mod.quiz_max_attempts = max_attempts
        db.flush()


def update_module_certificate(
    db: Session,
    module_id: int,
    path: Optional[str]
) -> None:
    mod = db.query(Module).filter(Module.id == module_id).first()
    if mod:
        mod.certificate_path = path
        db.flush()


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


def update_lesson_quiz_settings(
    db: Session, 
    lesson_id: int, 
    passing_score: Optional[int] = None, 
    max_attempts: Optional[int] = None
) -> None:
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if lesson:
        if passing_score is not None:
            lesson.quiz_passing_score = passing_score
        if max_attempts is not None:
            lesson.quiz_max_attempts = max_attempts
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
