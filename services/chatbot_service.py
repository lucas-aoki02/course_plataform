"""
services/chatbot_service.py
────────────────────────────
Chatbot services using SQLAlchemy ORM and Groq.
"""

from __future__ import annotations
import logging
import config
from db.database import get_db
from db.models import Course, Lesson, Module, ChatMessage, LessonChatMessage, ChatbotHistory
from repositories.course_repo import search_courses
from services.content_service import get_full_content_as_text
from utils.prompts import build_tutor_system_prompt, build_quick_chat_system_prompt
from services.security_service import encryption_manager

logger = logging.getLogger(__name__)


class _MsgRow:
    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content


class ChatbotService:
    def __init__(self, course_id: int | None, user_id: int) -> None:
        self.course_id = course_id
        self.user_id = user_id
        self._course_title = "General Platform"
        self._instructor_id = None
        
        course_content = ""
        if course_id:
            with get_db() as db:
                course = db.query(Course).filter(Course.id == course_id).first()
                if not course:
                    # Course not found — fall back to general platform mode
                    logger.warning(f"Course {course_id} not found. Falling back to general platform mode.")
                    self.course_id = None
                    from utils.prompts import build_general_tutor_system_prompt
                    from repositories.course_repo import list_courses
                    all_courses = [{"id": c.id, "title": c.title} for c in list_courses(db)]
                    self._system_prompt = build_general_tutor_system_prompt(courses=all_courses)
                    return
                self._course_title = course.title
                self._instructor_id = course.instructor_id
            course_content = get_full_content_as_text(course_id)
            self._system_prompt = build_tutor_system_prompt(self._course_title, course_content)
        else:
            from utils.prompts import build_general_tutor_system_prompt
            from repositories.course_repo import list_courses
            from db.models import Enrollment
            with get_db() as db:
                all_courses = [
                    {
                        "id": c.id,
                        "title": c.title,
                        "enrolled": db.query(Enrollment).filter(
                            Enrollment.user_id == user_id,
                            Enrollment.course_id == c.id
                        ).first() is not None
                    }
                    for c in list_courses(db)
                ]
            self._system_prompt = build_general_tutor_system_prompt(courses=all_courses)

    def get_history(self) -> list[_MsgRow]:
        """Fetch and decrypt chat history from ChatbotHistory table."""
        with get_db() as db:
            rows = (
                db.query(ChatbotHistory)
                .filter(ChatbotHistory.user_id == self.user_id)
                .order_by(ChatbotHistory.id.desc())
                .limit(config.MAX_CHAT_HISTORY)
                .all()
            )
            history = []
            for r in reversed(rows):
                try:
                    user_msg = encryption_manager.decrypt(r.message_content)
                    bot_reply = encryption_manager.decrypt(r.bot_response)
                    history.append(_MsgRow("user", user_msg))
                    history.append(_MsgRow("assistant", bot_reply))
                except Exception as e:
                    logger.warning(f"Failed to decrypt message {r.id}: {e}")
            return history

    def chat_stream(self, user_message: str) -> Generator[str, None, None]:
        """Process chat with streaming, keywords detection, and encrypted persistence."""
        from services.ai_service import ai_service
        
        # 1. Recommendation Logic (Keyword Match)
        recommendations = self._get_recommendations(user_message)
        context_enrichment = ""
        if recommendations:
            enrolled_recs = [r for r in recommendations if r["enrolled"]]
            not_enrolled_recs = [r for r in recommendations if not r["enrolled"]]
            parts = []
            if enrolled_recs:
                parts.append("Enrolled: " + ", ".join(r["title"] for r in enrolled_recs))
            if not_enrolled_recs:
                parts.append("Not enrolled (suggest contacting WOCOTM): " + ", ".join(r["title"] for r in not_enrolled_recs))
            if parts:
                context_enrichment = f"\n\n[SYSTEM: Related courses found — {'; '.join(parts)}]"

        full_system = self._system_prompt + context_enrichment
        history = self.get_history()
        # Limit history context for LLM
        history_str = "\n".join(f"{m.role}: {m.content}" for m in history[-10:])
        prompt = f"Recent History:\n{history_str}\n\nUser: {user_message}"
        
        full_response = ""
        for chunk in ai_service.generate_stream(prompt, system=full_system, user_id=self._instructor_id):
            full_response += chunk
            yield chunk
            
        # 2. Persist Encrypted Interaction
        self._save_interaction(user_message, full_response)

    def _get_recommendations(self, message: str) -> list[dict]:
        """Search for relevant courses based on message keywords, with enrollment status."""
        from db.models import Enrollment
        keywords = ["alcohol", "prevention", "health", "mental", "drug", "addiction", "family", "recovery",
                    "smoke", "tobacco", "wellness", "stress", "trauma"]
        found_key = next((k for k in keywords if k in message.lower()), None)
        if found_key:
            with get_db() as db:
                courses = search_courses(db, found_key)
                return [
                    {
                        "id": c.id,
                        "title": c.title,
                        "enrolled": db.query(Enrollment).filter(
                            Enrollment.user_id == self.user_id,
                            Enrollment.course_id == c.id
                        ).first() is not None
                    }
                    for c in courses if c.id != self.course_id
                ]
        return []

    def _save_interaction(self, user_msg: str, bot_reply: str) -> None:
        """Encrypt and save the interaction to history."""
        with get_db() as db:
            try:
                enc_user = encryption_manager.encrypt(user_msg)
                enc_bot = encryption_manager.encrypt(bot_reply)
                history_entry = ChatbotHistory(
                    user_id=self.user_id,
                    message_content=enc_user,
                    bot_response=enc_bot,
                )
                db.add(history_entry)
                db.flush()
            except Exception as e:
                logger.error(f"Failed to save encrypted interaction: {e}")


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
