"""
db/models.py
────────────
SQLAlchemy ORM models for the course platform.

Design decisions:
  - All models inherit from a shared `Base` (DeclarativeBase).
  - `options` in Quiz is stored as JSON string — SQLite doesn't have a native
    JSON type, so we use a JSON-encoded TEXT column. SQLAlchemy's `JSON` type
    handles serialization/deserialization transparently.
  - `order_index` on Module and Lesson enables reordering without renaming.
  - `status` on Course uses a Python Enum for type safety and readability.
  - Relationships use `back_populates` (explicit, preferred over `backref`)
    and `cascade="all, delete-orphan"` so deleting a Course cascades
    automatically to its Modules → Lessons and Quizzes.
"""

from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


# ── Shared Base ───────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    """All ORM models inherit from this base."""
    pass


# ── Enums ─────────────────────────────────────────────────────────────────────

class CourseStatus(str, enum.Enum):
    """
    Lifecycle of a course through the AI generation pipeline.

    DRAFT       → Created but not yet fully generated.
    GENERATING  → AI pipeline is running.
    COMPLETE    → All content (syllabus, lessons, quizzes) is ready.
    """
    DRAFT = "draft"
    GENERATING = "generating"
    COMPLETE = "complete"


# ── Models ────────────────────────────────────────────────────────────────────

class Course(Base):
    """
    Top-level entity. Represents a full course.

    Columns
    -------
    title       : Human-readable course title (AI-generated or user-edited).
    description : Short overview of the course (AI-generated).
    topic       : Raw user input — the seed used for AI generation.
    status      : CourseStatus enum tracking where the course is in its lifecycle.
    created_at  : UTC timestamp, auto-set on INSERT.

    Relationships
    -------------
    modules     : Ordered list of Module objects (cascade delete).
    quizzes     : List of Quiz questions scoped to this course (cascade delete).
    messages    : ChatMessage history for the tutor chatbot (cascade delete).
    """
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    topic: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[CourseStatus] = mapped_column(
        Enum(CourseStatus), nullable=False, default=CourseStatus.DRAFT
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    modules: Mapped[list[Module]] = relationship(
        "Module",
        back_populates="course",
        cascade="all, delete-orphan",
        order_by="Module.order_index",
    )
    quizzes: Mapped[list[Quiz]] = relationship(
        "Quiz",
        back_populates="course",
        cascade="all, delete-orphan",
    )
    messages: Mapped[list[ChatMessage]] = relationship(
        "ChatMessage",
        back_populates="course",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )

    # AI generation metadata
    source_document: Mapped[str] = mapped_column(
        Text, nullable=False, default="",
        doc="Key points extracted from a PDF/video via Gemini multimodal analysis."
    )
    refined: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        doc="True after Gemini has reviewed/refined Llama-generated content."
    )


class Module(Base):
    """
    A thematic section of a Course (e.g., "Chapter 2: Supervised Learning").

    Columns
    -------
    course_id   : FK to the parent Course.
    title       : Module heading.
    order_index : 0-based integer for display ordering.

    Relationships
    -------------
    lessons     : Ordered list of Lesson objects (cascade delete).
    """
    __tablename__ = "modules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    course: Mapped[Course] = relationship("Course", back_populates="modules")
    lessons: Mapped[list[Lesson]] = relationship(
        "Lesson",
        back_populates="module",
        cascade="all, delete-orphan",
        order_by="Lesson.order_index",
    )


class Lesson(Base):
    """
    A single piece of content within a Module.

    Columns
    -------
    module_id        : FK to the parent Module.
    title            : Lesson heading.
    content_markdown : AI-generated lesson body stored as Markdown.
                       Using Markdown lets the Streamlit `st.markdown()` render
                       it richly without extra processing.
    order_index      : 0-based integer for display ordering.
    """
    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    module_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("modules.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content_markdown: Mapped[str] = mapped_column(Text, nullable=False, default="")
    audio_script: Mapped[str] = mapped_column(
        Text, nullable=False, default="",
        doc="Narration script for audio/video production, generated by Llama."
    )
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    module: Mapped[Module] = relationship("Module", back_populates="lessons")
    quick_messages: Mapped[list[LessonChatMessage]] = relationship(
        "LessonChatMessage",
        back_populates="lesson",
        cascade="all, delete-orphan",
        order_by="LessonChatMessage.created_at",
    )


class Quiz(Base):
    """
    A single multiple-choice question associated with a Course.

    Columns
    -------
    course_id     : FK to the parent Course.
    question      : The question stem text.
    options       : List of answer strings, serialized as JSON.
                    Example: ["Option A", "Option B", "Option C", "Option D"]
    correct_index : 0-based index into `options` pointing to the correct answer.
    explanation   : AI-generated rationale shown after the student answers.
    """
    __tablename__ = "quizzes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    correct_index: Mapped[int] = mapped_column(Integer, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # Relationships
    course: Mapped[Course] = relationship("Course", back_populates="quizzes")


class ChatMessage(Base):
    """
    A single turn in the tutor chatbot conversation for a given Course.

    Columns
    -------
    course_id  : FK scoping the message to a specific course.
    role       : "user" or "assistant" — matches the Gemini/OpenAI message role.
    content    : Plain text message body.
    created_at : UTC timestamp for chronological ordering.
    """
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    course: Mapped[Course] = relationship("Course", back_populates="messages")


class LessonChatMessage(Base):
    """
    A single turn in the Quick Chat (Llama) for a specific lesson.

    Scoped to a Lesson (not a Course) — the Llama chatbot only has context
    for the lesson being watched, making it fast and focused.

    Columns
    -------
    lesson_id  : FK scoping the message to a specific lesson.
    role       : "user" or "assistant".
    content    : Plain text message body.
    created_at : UTC timestamp for chronological ordering.
    """
    __tablename__ = "lesson_chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lesson_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    lesson: Mapped[Lesson] = relationship("Lesson", back_populates="quick_messages")
