"""
services/chatbot_service.py
────────────────────────────
Two chatbot services for the hybrid architecture:

1. ChatbotService (Consultive Tutor — Gemini)
   - Cross-module questions: "How does Module 1 apply to Module 4?"
   - Uses full course content as context (long context window).
   - Persists history in `chat_messages` table (scoped to course).

2. QuickChatService (Per-Lesson Quick Chat — Llama 3.2)
   - Simple, direct questions about the lesson currently being watched.
   - Scoped to a single lesson — fast and focused.
   - Persists history in `lesson_chat_messages` table (scoped to lesson).
   - Falls back to Gemini automatically if Ollama is unavailable.
"""

from __future__ import annotations

import logging

import config
from db.database import get_session
from db.models import ChatMessage, Course, Lesson, LessonChatMessage
from services.content_service import get_full_content_as_text
from utils.prompts import build_tutor_system_prompt, build_quick_chat_system_prompt

logger = logging.getLogger(__name__)


# ── 1. ChatbotService — Consultive Tutor (Gemini) ─────────────────────────────

class ChatbotService:
    """
    Manages cross-module tutor chat sessions for a specific course (Gemini).

    Answers questions that require connecting concepts across different modules.
    The full course content is injected into the system prompt as a knowledge base.

    Usage
    -----
    >>> bot = ChatbotService(course_id=1)
    >>> reply = bot.chat("How does what I learned in Module 1 apply to Module 4?")
    """

    def __init__(self, course_id: int) -> None:
        self.course_id = course_id

        with get_session() as db:
            course = db.get(Course, course_id)
            if not course:
                raise ValueError(f"Course {course_id} not found")
            self._course_title = course.title

        # Build system prompt with full course context (loaded once per instance)
        course_content = get_full_content_as_text(course_id)
        self._system_prompt = build_tutor_system_prompt(self._course_title, course_content)

    def get_history(self) -> list[ChatMessage]:
        """
        Load all past messages for this course from SQLite, ordered by time.

        Returns
        -------
        list[ChatMessage] : ORM objects with `.role` and `.content` fields.
        """
        with get_session() as db:
            messages = (
                db.query(ChatMessage)
                .filter(ChatMessage.course_id == self.course_id)
                .order_by(ChatMessage.created_at)
                .limit(config.MAX_CHAT_HISTORY)
                .all()
            )
            return list(messages)

    def chat(self, user_message: str) -> str:
        """
        Send a user message and get a tutor reply via the LLM chain.

        Chain order: Llama (Ollama) → Gemini → OpenAI.
        The user never sees which provider answered.
        Conversation history is built as a text context string
        so it works with all providers (Llama needs stateless context).
        """
        from services.ai_service import ai_service

        self._save_message("user", user_message)

        history = self.get_history()

        # Build conversation context for stateless providers
        conversation = "\n".join(
            f"{'Student' if m.role == 'user' else 'Tutor'}: {m.content}"
            for m in history[:-1]  # Exclude the message we just saved
        )

        if conversation:
            full_prompt = (
                f"Previous conversation:\n{conversation}\n\n"
                f"Student: {user_message}"
            )
        else:
            full_prompt = user_message

        try:
            reply = ai_service.generate(full_prompt, system=self._system_prompt)
        except Exception as e:
            logger.error("[Chatbot] All providers failed: %s", e)
            reply = "I'm sorry, I encountered an error. Please try again."

        self._save_message("assistant", reply)
        return reply

    def clear_history(self) -> None:
        """Delete all chat messages for this course."""
        with get_session() as db:
            db.query(ChatMessage).filter(
                ChatMessage.course_id == self.course_id
            ).delete()

    def _save_message(self, role: str, content: str) -> None:
        """Internal helper: persist a single message to SQLite."""
        with get_session() as db:
            msg = ChatMessage(
                course_id=self.course_id,
                role=role,
                content=content,
            )
            db.add(msg)


# ── 2. QuickChatService — Per-Lesson Quick Chat (Llama 3.2) ───────────────────

class QuickChatService:
    """
    Manages fast, per-lesson Q&A sessions using Llama 3.2 (via Ollama).

    Scoped to a single lesson — answers simple, direct questions about
    the lesson content currently being watched. Does NOT handle cross-module
    questions (those belong in ChatbotService/Gemini).

    History is persisted to `lesson_chat_messages` in SQLite so the student's
    questions survive page reruns.

    Usage
    -----
    >>> qc = QuickChatService(lesson_id=5)
    >>> reply = qc.chat("What does 'epoch' mean in this context?")
    """

    def __init__(self, lesson_id: int) -> None:
        self.lesson_id = lesson_id

        with get_session() as db:
            lesson = db.get(Lesson, lesson_id)
            if not lesson:
                raise ValueError(f"Lesson {lesson_id} not found")

            # Load lesson + module relationships
            from db.models import Module
            module = db.get(Module, lesson.module_id)
            self._lesson_title = lesson.title
            self._module_title = module.title if module else "Unknown Module"
            self._lesson_content = lesson.content_markdown or "(no content yet)"

        # Build system prompt scoped to this lesson only
        self._system_prompt = build_quick_chat_system_prompt(
            self._lesson_title, self._module_title, self._lesson_content
        )

    def get_history(self) -> list[LessonChatMessage]:
        """
        Load all past messages for this lesson from SQLite, ordered by time.

        Returns
        -------
        list[LessonChatMessage] : ORM objects with `.role` and `.content` fields.
        """
        with get_session() as db:
            messages = (
                db.query(LessonChatMessage)
                .filter(LessonChatMessage.lesson_id == self.lesson_id)
                .order_by(LessonChatMessage.created_at)
                .limit(config.MAX_CHAT_HISTORY)
                .all()
            )
            return list(messages)

    def chat(self, user_message: str) -> str:
        """
        Send a user message and get a Llama 3.2 quick-chat reply.

        Builds a conversation string from history (Ollama doesn't retain state
        across requests), then calls Llama with the full context.

        Args
        ----
        user_message : The student's quick question about the current lesson.

        Returns
        -------
        str : The AI assistant's response.
        """
        from services.ai_service import llama_service

        self._save_message("user", user_message)
        history = self.get_history()

        # Build a conversation context string for stateless Llama calls
        conversation = "\n".join(
            f"{'Student' if m.role == 'user' else 'Assistant'}: {m.content}"
            for m in history[:-1]  # Exclude the message we just saved (it's the prompt)
        )

        if conversation:
            full_prompt = f"Previous conversation:\n{conversation}\n\nStudent: {user_message}"
        else:
            full_prompt = user_message

        try:
            reply = llama_service.generate(full_prompt, system=self._system_prompt)
        except Exception as e:
            logger.error("[Llama] QuickChat error: %s", e)
            reply = "Sorry, I couldn't process your question right now. Please try again."

        self._save_message("assistant", reply)
        return reply

    def clear_history(self) -> None:
        """Delete all quick-chat messages for this lesson."""
        with get_session() as db:
            db.query(LessonChatMessage).filter(
                LessonChatMessage.lesson_id == self.lesson_id
            ).delete()

    def _save_message(self, role: str, content: str) -> None:
        """Internal helper: persist a single message to lesson_chat_messages."""
        with get_session() as db:
            msg = LessonChatMessage(
                lesson_id=self.lesson_id,
                role=role,
                content=content,
            )
            db.add(msg)
