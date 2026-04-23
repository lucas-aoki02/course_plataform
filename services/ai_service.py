"""
services/ai_service.py
──────────────────────
Groq integration for instant LLM responses.
Uses llama-3.1-8b-instant by default.
Dynamically resolves the API key: Instructor's stored key → master .env key.
"""

from __future__ import annotations
import logging
from collections.abc import Generator
from typing import Optional
import time

from groq import Groq
import config

logger = logging.getLogger(__name__)


class AIServiceError(Exception):
    """Raised when Groq API fails."""
    pass


def _resolve_groq_key(user_id: Optional[int] = None) -> str:
    """
    Resolve the Groq API key to use:
    1. If user_id is provided and user is an Instructor, fetch their encrypted key.
    2. Fall back to any available Instructor key in the database.
    3. Fall back to the master GROQ_API_KEY from .env.
    """
    if user_id is not None:
        try:
            from db.database import get_db
            from db.models import UserRole
            from repositories.user_repo import get_user_by_id, get_decrypted_groq_key

            with get_db() as db:
                user = get_user_by_id(db, user_id)
                if user and user.user_role == UserRole.instructor and user.groq_key_encrypted:
                    key = get_decrypted_groq_key(user)
                    if key:
                        return key
        except Exception as e:
            logger.warning(f"Could not load Instructor Groq key (user_id={user_id}): {e}")

    # Fallback: try to find any instructor with a valid key in the database
    try:
        from db.database import get_db
        from db.models import User, UserRole
        from repositories.user_repo import get_decrypted_groq_key

        with get_db() as db:
            instructor = (
                db.query(User)
                .filter(User.user_role == UserRole.instructor, User.groq_key_encrypted.isnot(None))
                .first()
            )
            if instructor:
                key = get_decrypted_groq_key(instructor)
                if key:
                    logger.info(f"Using fallback key from instructor ID {instructor.id}")
                    return key
    except Exception as e:
        logger.warning(f"Could not load any fallback instructor key: {e}")

    if not config.GROQ_API_KEY:
        raise AIServiceError("GROQ_API_KEY is missing in .env and no instructor keys are available.")
    return config.GROQ_API_KEY


class GroqProvider:
    """
    Official Groq SDK wrapper with streaming support.
    Accepts an optional user_id to resolve the API key dynamically.
    """

    def __init__(self, user_id: Optional[int] = None) -> None:
        self._user_id = user_id
        self._clients: dict[Optional[int], Groq] = {}

    def _get_client(self, user_id: Optional[int] = None) -> Groq:
        uid = user_id if user_id is not None else self._user_id
        if uid not in self._clients:
            key = _resolve_groq_key(uid)
            self._clients[uid] = Groq(api_key=key)
        return self._clients[uid]

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        user_id: Optional[int] = None,
    ) -> str:
        client = self._get_client(user_id)
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        for attempt in range(3):
            try:
                response = client.chat.completions.create(
                    model=config.GROQ_MODEL,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens or 1500,
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                if ("429" in str(e) or "rate limit" in str(e).lower()) and attempt < 2:
                    logger.warning(f"Rate limit. Retrying ({attempt+1}/3)...")
                    time.sleep(2)
                    continue
                
                error_msg = str(e)
                key_info = "Master API Key" if (user_id is None and self._user_id is None) else f"Instructor (ID: {user_id or self._user_id}) API Key"
                if "invalid_api_key" in error_msg.lower() or "401" in error_msg:
                    raise AIServiceError(f"Invalid Groq API Key! Problem source: {key_info}. Please check your .env or profile settings.")
                
                logger.error(f"Groq generate error: {e}")
                raise AIServiceError(f"Groq error: {e}")

    def generate_stream(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        user_id: Optional[int] = None,
    ) -> Generator[str, None, None]:
        client = self._get_client(user_id)
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        for attempt in range(3):
            try:
                response = client.chat.completions.create(
                    model=config.GROQ_MODEL,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens or 1500,
                    stream=True,
                )
                for chunk in response:
                    if chunk.choices and chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
                return
            except Exception as e:
                if ("429" in str(e) or "rate limit" in str(e).lower()) and attempt < 2:
                    logger.warning(f"Stream rate limit. Retrying ({attempt+1}/3)...")
                    time.sleep(2)
                    continue
                
                error_msg = str(e)
                key_info = "Master API Key" if (user_id is None and self._user_id is None) else f"Instructor (ID: {user_id or self._user_id}) API Key"
                if "invalid_api_key" in error_msg.lower() or "401" in error_msg:
                    raise AIServiceError(f"Invalid Groq API Key! Problem source: {key_info}. Please check your .env or profile settings.")
                
                logger.error(f"Groq stream error: {e}")
                raise AIServiceError(f"Groq streaming error: {e}")


# Module-level singletons (use master key by default)
ai_service = GroqProvider()
llama_service = GroqProvider()   # Backward-compat alias
gemini_service = None            # Removed — only Groq used for text
