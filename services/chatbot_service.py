"""
services/chatbot_service.py
────────────────────────────
Lite Chatbot services using raw SQL and Groq.
"""

from __future__ import annotations
import logging
import config
from db.database import get_connection
from services.content_service import get_full_content_as_text
from utils.prompts import build_tutor_system_prompt, build_quick_chat_system_prompt
from repositories.course_repo import DBRow

logger = logging.getLogger(__name__)

class ChatbotService:
    def __init__(self, course_id: int) -> None:
        self.course_id = course_id
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT title FROM courses WHERE id = ?", (course_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            raise ValueError(f"Course {course_id} not found")
        self._course_title = row["title"]
        course_content = get_full_content_as_text(course_id)
        self._system_prompt = build_tutor_system_prompt(self._course_title, course_content)

    def get_history(self) -> list[DBRow]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT role, content FROM chat_messages WHERE course_id = ? ORDER BY id ASC LIMIT ?",
            (self.course_id, config.MAX_CHAT_HISTORY)
        )
        rows = cursor.fetchall()
        conn.close()
        return [DBRow(**dict(r)) for r in rows]

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
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO chat_messages (course_id, role, content) VALUES (?, ?, ?)",
            (self.course_id, role, content)
        )
        conn.commit()
        conn.close()

class QuickChatService:
    def __init__(self, lesson_id: int) -> None:
        self.lesson_id = lesson_id
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT l.title, l.content_markdown, m.title as module_title 
            FROM lessons l JOIN modules m ON l.module_id = m.id 
            WHERE l.id = ?
        """, (lesson_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            raise ValueError(f"Lesson {lesson_id} not found")
            
        self._lesson_title = row["title"]
        self._module_title = row["module_title"]
        self._lesson_content = row["content_markdown"] or ""
        self._system_prompt = build_quick_chat_system_prompt(
            self._lesson_title, self._module_title, self._lesson_content
        )

    def get_history(self) -> list[DBRow]:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT role, content FROM lesson_chat_messages WHERE lesson_id = ? ORDER BY id ASC LIMIT ?",
            (self.lesson_id, config.MAX_CHAT_HISTORY)
        )
        rows = cursor.fetchall()
        conn.close()
        return [DBRow(**dict(r)) for r in rows]

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
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO lesson_chat_messages (lesson_id, role, content) VALUES (?, ?, ?)",
            (self.lesson_id, role, content)
        )
        conn.commit()
        conn.close()

    def clear_history(self) -> None:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM lesson_chat_messages WHERE lesson_id = ?", (self.lesson_id,))
        conn.commit()
        conn.close()
