"""
services/ai_service.py
──────────────────────
Direct Groq integration for instant LLM responses.
Uses llama3-8b-8192 from Groq Cloud.
"""

from __future__ import annotations
import logging
from collections.abc import Generator
import time
from groq import Groq
import config

logger = logging.getLogger(__name__)

class AIServiceError(Exception):
    """Raised when Groq API fails."""
    pass

class GroqProvider:
    """
    Official Groq SDK wrapper with streaming support.
    """
    def __init__(self) -> None:
        self._client = None

    def _get_client(self):
        if self._client is None:
            if not config.GROQ_API_KEY:
                raise AIServiceError("GROQ_API_KEY is missing in .env")
            self._client = Groq(api_key=config.GROQ_API_KEY)
        return self._client

    def generate(self, prompt: str, system: str | None = None, temperature: float = 0.7, max_tokens: int | None = None) -> str:
        client = self._get_client()
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        max_retries = 3
        for attempt in range(max_retries):
            try:
                kwargs = {
                    "model": config.GROQ_MODEL,
                    "messages": messages,
                    "temperature": temperature,
                }
                if max_tokens:
                    kwargs["max_tokens"] = max_tokens
                else:
                    kwargs["max_tokens"] = 1500 # Safe fallback for Groq 6000 TPM tier

                response = client.chat.completions.create(**kwargs)
                return response.choices[0].message.content.strip()
            except Exception as e:
                error_str = str(e).lower()
                if "429" in error_str or "rate limit" in error_str:
                    if attempt < max_retries - 1:
                        logger.warning(f"Groq API rate limit hit. Retrying in 2s (Attempt {attempt+1}/{max_retries})")
                        time.sleep(2)
                        continue
                logger.error(f"Groq generate error: {e}")
                raise AIServiceError(f"Groq error: {e}")

    def generate_stream(self, prompt: str, system: str | None = None, temperature: float = 0.7, max_tokens: int | None = None) -> Generator[str, None, None]:
        client = self._get_client()
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        max_retries = 3
        for attempt in range(max_retries):
            try:
                kwargs = {
                    "model": config.GROQ_MODEL,
                    "messages": messages,
                    "temperature": temperature,
                    "stream": True,
                }
                if max_tokens:
                    kwargs["max_tokens"] = max_tokens
                else:
                    kwargs["max_tokens"] = 1500 # Safe fallback for Groq 6000 TPM tier

                response = client.chat.completions.create(**kwargs)
                for chunk in response:
                    if chunk.choices and chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
                return # Exit successfully after streaming is complete
            except Exception as e:
                error_str = str(e).lower()
                if "429" in error_str or "rate limit" in error_str:
                    if attempt < max_retries - 1:
                        # Yield a system message temporarily if desired, or skip. Streamlit will just pause.
                        logger.warning(f"Groq streaming rate limit hit. Retrying in 2s (Attempt {attempt+1}/{max_retries})")
                        time.sleep(2)
                        continue
                logger.error(f"Groq stream error: {e}")
                raise AIServiceError(f"Groq streaming error: {e}")

# Singletons for project compatibility
ai_service = GroqProvider()
llama_service = GroqProvider() # Keep alias for backward compat
gemini_service = None # Removed as requested
