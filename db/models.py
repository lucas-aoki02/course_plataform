"""
db/models.py
────────────
SQLAlchemy ORM models for the AI Course Platform.
Tables: User, AuditLog, UserProgress + Course, Module, Lesson, Quiz, LessonAsset, ChatMessage, LessonChatMessage
"""

from __future__ import annotations
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Boolean,
    DateTime, ForeignKey, Enum as SAEnum
)
from sqlalchemy.orm import DeclarativeBase, relationship
import enum


class Base(DeclarativeBase):
    pass


# ── Role Enum ─────────────────────────────────────────────────────────────────
class UserRole(str, enum.Enum):
    admin = "Admin"
    instructor = "Instructor"
    student = "Student"


# ── Users ─────────────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(80), nullable=False, unique=True)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(SAEnum(UserRole), nullable=False, default=UserRole.student)
    groq_key_encrypted = Column(Text, nullable=True)

    # Relationships
    audit_actions = relationship(
        "AuditLog", foreign_keys="AuditLog.user_id",
        back_populates="actor", cascade="all, delete-orphan"
    )
    audit_targets = relationship(
        "AuditLog", foreign_keys="AuditLog.target_user_id",
        back_populates="target"
    )
    progress_entries = relationship("UserProgress", back_populates="user", cascade="all, delete-orphan")


# ── Audit Log ─────────────────────────────────────────────────────────────────
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(50), nullable=False)   # INSERT, UPDATE, DELETE, LOGIN
    target_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    table_name = Column(String(100), nullable=True)
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    actor = relationship("User", foreign_keys=[user_id], back_populates="audit_actions")
    target = relationship("User", foreign_keys=[target_user_id], back_populates="audit_targets")


# ── User Progress ──────────────────────────────────────────────────────────────
class UserProgress(Base):
    __tablename__ = "user_progress"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False)
    completed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="progress_entries")
    lesson = relationship("Lesson", back_populates="progress_entries")


# ── Courses ────────────────────────────────────────────────────────────────────
class CourseStatus(str, enum.Enum):
    draft = "DRAFT"
    generating = "GENERATING"
    complete = "COMPLETE"


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(SAEnum(CourseStatus), default=CourseStatus.draft)
    created_at = Column(DateTime, default=datetime.utcnow)
    source_document = Column(Text, nullable=True)
    refined = Column(Boolean, default=False)

    modules = relationship("Module", back_populates="course", cascade="all, delete-orphan",
                           order_by="Module.order_index")
    quizzes = relationship("Quiz", back_populates="course", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", back_populates="course", cascade="all, delete-orphan")


class Module(Base):
    __tablename__ = "modules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    order_index = Column(Integer, default=0)

    course = relationship("Course", back_populates="modules")
    lessons = relationship("Lesson", back_populates="module", cascade="all, delete-orphan",
                           order_by="Lesson.order_index")


class Lesson(Base):
    __tablename__ = "lessons"

    id = Column(Integer, primary_key=True, autoincrement=True)
    module_id = Column(Integer, ForeignKey("modules.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    content_markdown = Column(Text, nullable=True)
    image_path = Column(String(512), nullable=True)
    order_index = Column(Integer, default=0)

    module = relationship("Module", back_populates="lessons")
    assets = relationship("LessonAsset", back_populates="lesson", cascade="all, delete-orphan")
    lesson_chat_messages = relationship("LessonChatMessage", back_populates="lesson",
                                        cascade="all, delete-orphan")
    progress_entries = relationship("UserProgress", back_populates="lesson",
                                    cascade="all, delete-orphan")


class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    question_text = Column(Text, nullable=False)
    options_json = Column(Text, nullable=False)
    correct_answer = Column(String(255), nullable=False)
    explanation = Column(Text, nullable=True)

    course = relationship("Course", back_populates="quizzes")


class LessonAsset(Base):
    __tablename__ = "lesson_assets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False)
    type = Column(String(50), nullable=False)    # image | video | document
    content = Column(Text, nullable=False)       # URL or file path
    caption = Column(Text, nullable=True)
    position = Column(String(10), default="end") # start | end

    lesson = relationship("Lesson", back_populates="assets")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)

    course = relationship("Course", back_populates="chat_messages")


class LessonChatMessage(Base):
    __tablename__ = "lesson_chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)

    lesson = relationship("Lesson", back_populates="lesson_chat_messages")
