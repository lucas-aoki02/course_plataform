"""
services/ai_service.py
──────────────────────
Resilience-first LLM chain — Llama (Ollama) → Gemini → OpenAI.

Architecture
------------
Three named singletons are exported:

    ai_service   → ResilientChain (Llama → Gemini → OpenAI)
    llama_service → Direct Ollama access (no fallback needed — primary engine)
    gemini_service → Direct Gemini access (for multimodal tasks)

The `ResilientChain` tries providers in order:
  1. Llama 3.2 (Ollama) — local, unlimited, free
  2. Gemini — if Llama is down or returns empty
  3. OpenAI — last resort if both above fail

Each fallback is transparent to the caller. The user never sees the switch.
"""

from __future__ import annotations

import logging
import time

import config

logger = logging.getLogger(__name__)


# ── Custom Exception ──────────────────────────────────────────────────────────

class AIServiceError(Exception):
    """Raised when ALL LLM providers in the chain fail."""
    pass


# ── Error Detection Helpers ───────────────────────────────────────────────────

_QUOTA_INDICATORS = (
    "429", "RESOURCE_EXHAUSTED", "quota", "rate limit", "rate_limit",
    "rateLimit", "Too Many Requests", "exceeded your current quota",
    "billing", "insufficient_quota", "tokens per minute", "tpm",
    "per-minute", "connection refused", "connection error",
    "max retries", "timeout", "server error", "500", "502", "503",
)


def _is_provider_failure(error: Exception) -> bool:
    """
    Detect whether an error means the provider is unavailable.
    Broad matching: any API error triggers fallback to next provider.
    """
    msg = str(error).lower()
    return any(indicator.lower() in msg for indicator in _QUOTA_INDICATORS)


def _is_quota_error(error: Exception) -> bool:
    """Detect specifically quota/rate-limit errors."""
    quota_specific = (
        "429", "RESOURCE_EXHAUSTED", "quota", "rate limit", "rate_limit",
        "rateLimit", "Too Many Requests", "exceeded your current quota",
        "billing", "insufficient_quota",
    )
    msg = str(error).lower()
    return any(ind.lower() in msg for ind in quota_specific)


# ── Ollama / Llama Provider (PRIMARY — local, unlimited) ─────────────────────

class _OllamaProvider:
    """
    Wraps the Ollama REST API (pure httpx, no SDK).

    PRIMARY engine for all text tasks: syllabus, content, quizzes,
    scripts, chat, refinement.

    Endpoint: POST {OLLAMA_BASE_URL}/api/chat
    """

    def generate(self, prompt: str, system: str | None = None) -> str:
        try:
            import httpx
        except ImportError as e:
            raise AIServiceError("httpx not installed. Run: pip install httpx") from e

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": config.OLLAMA_MODEL,
            "messages": messages,
            "stream": False,
        }

        with httpx.Client(timeout=config.OLLAMA_TIMEOUT) as client:
            response = client.post(
                f"{config.OLLAMA_BASE_URL}/api/chat",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            text = data["message"]["content"].strip()
            if not text:
                raise AIServiceError("Ollama returned empty response")
            return text


# ── Gemini Provider (FALLBACK 1) ──────────────────────────────────────────────

class _GeminiProvider:
    """
    Wraps the google-genai SDK.
    FALLBACK when Ollama is unavailable. Also used for multimodal tasks
    (PDF extraction) where Gemini has unique capabilities.
    """

    def __init__(self) -> None:
        self._client = None

    def _get_client(self):
        if self._client is None:
            from google import genai
            self._genai = genai
            self._client = genai.Client(api_key=config.GEMINI_API_KEY)
        return self._client

    def generate(self, prompt: str, system: str | None = None) -> str:
        try:
            from google.genai import types
            client = self._get_client()

            config_kwargs = {}
            if system:
                config_kwargs["system_instruction"] = system

            response = client.models.generate_content(
                model=config.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(**config_kwargs)
                if config_kwargs else None,
            )
            return response.text.strip()
        except Exception as e:
            raise AIServiceError(f"Gemini error: {e}") from e


# ── OpenAI Provider (FALLBACK 2 — last resort) ───────────────────────────────

class _OpenAIProvider:
    """
    Wraps the openai SDK.
    LAST RESORT fallback if both Ollama and Gemini fail.
    """

    def __init__(self) -> None:
        self._client = None

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=config.OPENAI_API_KEY)
        return self._client

    def generate(self, prompt: str, system: str | None = None) -> str:
        client = self._get_client()
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        response = client.chat.completions.create(
            model=config.OPENAI_MODEL,
            messages=messages,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()


# ── Resilient Chain (Llama → Gemini → OpenAI) ────────────────────────────────

class ResilientChain:
    """
    Tries each provider in order until one succeeds.

    Chain: Llama (Ollama) → Gemini → OpenAI

    Rules:
    - If provider returns empty string → try next.
    - If provider raises any error → try next.
    - If ALL providers fail → raise AIServiceError with combined messages.
    - The user never sees which provider answered.

    Usage
    -----
    >>> from services.ai_service import ai_service
    >>> result = ai_service.generate("Design a syllabus about Python")
    """

    def generate(self, prompt: str, system: str | None = None) -> str:
        errors: list[tuple[str, Exception]] = []

        # ── 1. Try Llama (Ollama) — primary, local, unlimited ────────────
        try:
            logger.info("[Chain] Trying Llama (Ollama)...")
            return _OllamaProvider().generate(prompt, system=system)
        except Exception as e:
            errors.append(("Ollama/Llama", e))
            logger.warning("[Chain] Llama failed: %s — trying next provider.", e)

        # ── 2. Try Gemini — fallback 1 ───────────────────────────────────
        if config.GEMINI_API_KEY:
            try:
                logger.info("[Chain] Trying Gemini (fallback)...")
                result = _GeminiProvider().generate(prompt, system=system)
                logger.info("[Chain] Gemini succeeded (Llama was unavailable).")
                return result
            except Exception as e:
                errors.append(("Gemini", e))
                logger.warning("[Chain] Gemini failed: %s — trying next provider.", e)

        # ── 3. Try OpenAI — fallback 2 (last resort) ─────────────────────
        if config.OPENAI_API_KEY:
            try:
                logger.info("[Chain] Trying OpenAI (last resort)...")
                result = _OpenAIProvider().generate(prompt, system=system)
                logger.info("[Chain] OpenAI succeeded (Llama + Gemini were unavailable).")
                return result
            except Exception as e:
                errors.append(("OpenAI", e))
                logger.error("[Chain] OpenAI also failed: %s", e)

        # ── All providers exhausted ──────────────────────────────────────
        error_summary = "; ".join(f"{name}: {err}" for name, err in errors)
        raise AIServiceError(
            f"All providers failed. Chain: {error_summary}"
        )


# ── Public Interface ──────────────────────────────────────────────────────────

class AIService:
    """
    Public LLM interface. Wraps a single provider behind `generate()`.
    """

    def __init__(self, provider_name: str = "ollama") -> None:
        p = provider_name.lower()
        if p == "ollama":
            self._provider = _OllamaProvider()
        elif p == "gemini":
            self._provider = _GeminiProvider()
        elif p == "openai":
            self._provider = _OpenAIProvider()
        elif p == "chain":
            self._provider = ResilientChain()
        else:
            raise AIServiceError(
                f"Unknown provider '{provider_name}'. "
                "Choose 'ollama', 'gemini', 'openai', or 'chain'."
            )

    def generate(self, prompt: str, system: str | None = None) -> str:
        return self._provider.generate(prompt, system=system)


# ── Module-level Singletons ───────────────────────────────────────────────────

# Resilient chain: Llama → Gemini → OpenAI (automatic fallback)
ai_service = AIService(provider_name="chain")

# Direct Llama access (no fallback — for tasks that MUST be local)
llama_service = AIService(provider_name="ollama")

# Direct Gemini access (for multimodal tasks: PDF, image analysis)
gemini_service = AIService(provider_name="gemini") if config.GEMINI_API_KEY else None
