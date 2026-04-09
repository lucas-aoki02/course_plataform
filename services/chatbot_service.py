"""
services/chatbot_service.py
────────────────────────────
Chatbot services using SQLAlchemy ORM and Groq.
"""

from __future__ import annotations
import logging
import config
from db.database import get_db
from db.models import Course, Lesson, Module, ChatMessage, LessonChatMessage
from services.content_service import get_full_content_as_text
from utils.prompts import build_tutor_system_prompt, build_quick_chat_system_prompt

logger = logging.getLogger(__name__)


class _MsgRow:
    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content


class ChatbotService:
    def __init__(self, course_id: int) -> None:
        self.course_id = course_id
        with get_db() as db:
            course = db.query(Course).filter(Course.id == course_id).first()
            if not course:
                raise ValueError(f"Course {course_id} not found")
            self._course_title = course.title

        course_content = get_full_content_as_text(course_id)
        self._system_prompt = build_tutor_system_prompt(self._course_title, course_content)

    def get_history(self) -> list[_MsgRow]:
        with get_db() as db:
            rows = (
                db.query(ChatMessage)
                .filter(ChatMessage.course_id == self.course_id)
                .order_by(ChatMessage.id)
                .limit(config.MAX_CHAT_HISTORY)
                .all()
            )
            return [_MsgRow(r.role, r.content) for r in rows]

    def chat(self, user_message: str) -> str:
        from services.ai_service import ai_service
        self._save_message("user", user_message)
        history = self.get_history()
        conversation = "\n".join(f"{m.role}: {m.content}" for m in history)
        try:
            reply = ai_service.generate(conversation, system=self._system_prompt)
        except Exception as e:
            logger.error(f"Chatbot error: {e}")
            reply = "I'm sorry, I encountered an error."
        self._save_message("assistant", reply)
        return reply

    def _save_message(self, role: str, content: str) -> None:
        with get_db() as db:
            msg = ChatMessage(course_id=self.course_id, role=role, content=content)
            db.add(msg)


class QuickChatService:
    def __init__(self, lesson_id: int) -> None:
        self.lesson_id = lesson_id
        with get_db() as db:
            row = (
                db.query(Lesson, Module)
                .join(Module, Lesson.module_id == Module.id)
                .filter(Lesson.id == lesson_id)
                .first()
            )
            if not row:
                raise ValueError(f"Lesson {lesson_id} not found")
            lesson, module = row
            self._lesson_title = lesson.title
            self._module_title = module.title
            self._lesson_content = lesson.content_markdown or ""

        self._system_prompt = build_quick_chat_system_prompt(
            self._lesson_title, self._module_title, self._lesson_content
        )

    def get_history(self) -> list[_MsgRow]:
        with get_db() as db:
            rows = (
                db.query(LessonChatMessage)
                .filter(LessonChatMessage.lesson_id == self.lesson_id)
                .order_by(LessonChatMessage.id)
                .limit(config.MAX_CHAT_HISTORY)
                .all()
            )
            return [_MsgRow(r.role, r.content) for r in rows]

    def chat(self, user_message: str) -> str:
        from services.ai_service import llama_service
        self._save_message("user", user_message)
        history = self.get_history()
        conversation = "\n".join(f"{m.role}: {m.content}" for m in history)
        try:
            reply = llama_service.generate(conversation, system=self._system_prompt)
        except Exception as e:
            logger.error(f"QuickChat error: {e}")
            reply = "Sorry, error processing question."
        self._save_message("assistant", reply)
        return reply

    def _save_message(self, role: str, content: str) -> None:
        with get_db() as db:
            msg = LessonChatMessage(lesson_id=self.lesson_id, role=role, content=content)
            db.add(msg)

    def clear_history(self) -> None:
        with get_db() as db:
            db.query(LessonChatMessage).filter(
                LessonChatMessage.lesson_id == self.lesson_id
            ).delete()
