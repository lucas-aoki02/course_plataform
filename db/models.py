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
    DateTime, ForeignKey, Enum as SAEnum, LargeBinary
)
from sqlalchemy.orm import DeclarativeBase, relationship
import enum


class Base(DeclarativeBase):
    pass


# ── Role Enum ─────────────────────────────────────────────────────────────────
class UserRole(str, enum.Enum):
    system_admin = "system_admin"
    general_admin = "general_admin"
    privacy_admin = "privacy_admin"
    instructor = "instructor"
    student = "student"


# ── Users ─────────────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(80), nullable=False, unique=True)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    user_role = Column(SAEnum(UserRole), nullable=False, default=UserRole.student)
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
    created_courses = relationship("Course", back_populates="instructor", foreign_keys="Course.instructor_id")
    enrollments = relationship("Enrollment", back_populates="student", cascade="all, delete-orphan")


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


# ── Enrollments ────────────────────────────────────────────────────────────────
class Enrollment(Base):
    __tablename__ = "enrollments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    enrolled_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    student = relationship("User", back_populates="enrollments")
    course = relationship("Course", back_populates="enrollments")


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
    instructor_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    tags = Column(Text, nullable=True) # Comma-separated or space-separated keywords

    quiz_passing_score = Column(Integer, nullable=True) # Score percentage 0-100
    quiz_max_attempts = Column(Integer, nullable=True)
    # Certificate stored as blob — no filesystem dependency
    certificate_data     = Column(LargeBinary, nullable=True)
    certificate_mime     = Column(String(100), nullable=True)   # e.g. image/jpeg, application/pdf
    certificate_filename = Column(String(255), nullable=True)

    instructor = relationship("User", back_populates="created_courses", foreign_keys=[instructor_id])
    enrollments = relationship("Enrollment", back_populates="course", cascade="all, delete-orphan")
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

    quiz_passing_score = Column(Integer, nullable=True)
    quiz_max_attempts = Column(Integer, nullable=True)
    # Certificate stored as blob — no filesystem dependency
    certificate_data     = Column(LargeBinary, nullable=True)
    certificate_mime     = Column(String(100), nullable=True)
    certificate_filename = Column(String(255), nullable=True)

    course = relationship("Course", back_populates="modules")
    lessons = relationship("Lesson", back_populates="module", cascade="all, delete-orphan",
                           order_by="Lesson.order_index")


class Lesson(Base):
    __tablename__ = "lessons"

    id = Column(Integer, primary_key=True, autoincrement=True)
    module_id = Column(Integer, ForeignKey("modules.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    content_markdown = Column(Text, nullable=True)
    # Lesson thumbnail stored as blob
    image_data = Column(LargeBinary, nullable=True)
    image_mime = Column(String(100), nullable=True)
    order_index = Column(Integer, default=0)

    quiz_passing_score = Column(Integer, nullable=True)
    quiz_max_attempts = Column(Integer, nullable=True)

    module = relationship("Module", back_populates="lessons")
    assets = relationship("LessonAsset", back_populates="lesson", cascade="all, delete-orphan")
    lesson_chat_messages = relationship("LessonChatMessage", back_populates="lesson",
                                        cascade="all, delete-orphan")
    progress_entries = relationship("UserProgress", back_populates="lesson",
                                    cascade="all, delete-orphan")


class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=True)
    module_id = Column(Integer, ForeignKey("modules.id", ondelete="CASCADE"), nullable=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id", ondelete="CASCADE"), nullable=True)
    
    question_text = Column(Text, nullable=False)
    options_json = Column(Text, nullable=False)
    correct_answer = Column(String(255), nullable=False)
    explanation = Column(Text, nullable=True)

    course = relationship("Course", back_populates="quizzes")
    module = relationship("Module")
    lesson = relationship("Lesson")


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=True)
    module_id = Column(Integer, ForeignKey("modules.id", ondelete="CASCADE"), nullable=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id", ondelete="CASCADE"), nullable=True)
    
    score_percent = Column(Integer, nullable=False)
    passed = Column(Boolean, nullable=False)
    attempt_number = Column(Integer, nullable=False, default=1)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User")


class LessonAsset(Base):
    __tablename__ = "lesson_assets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False)
    type = Column(String(50), nullable=False)    # image | video | document
    # For external URLs, store here and leave file_data NULL
    content = Column(Text, nullable=True)        # external URL only (http/https)
    # For uploaded files, store raw bytes here
    file_data = Column(LargeBinary, nullable=True)
    mime_type = Column(String(100), nullable=True)
    filename  = Column(String(255), nullable=True)
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


class UserConsent(Base):
    __tablename__ = "user_consents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    consented_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User")


class ChatbotHistory(Base):
    __tablename__ = "chatbot_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    message_content = Column(Text, nullable=False) # Encrypted
    bot_response = Column(Text, nullable=False)    # Encrypted
    intent = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User")


class LessonChatMessage(Base):
    __tablename__ = "lesson_chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)

    lesson = relationship("Lesson", back_populates="lesson_chat_messages")
