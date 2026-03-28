"""
config.py
─────────
Central configuration module. All tuneable constants live here.

Resilience-first architecture:
  TEXT  → Llama 3.2 (Ollama, local, unlimited) → Gemini → OpenAI
  IMAGE → Pollinations.ai (free, unlimited) → Hugging Face Inference → Gemini Vision

Every provider has zero-config defaults. Only Ollama must be running locally.
All other providers are optional fallbacks.
"""

from pathlib import Path
from dotenv import load_dotenv
import os

# Load .env from project root (non-fatal if missing)
load_dotenv(Path(__file__).parent / ".env")

# ── Primary Text Engine: Llama (Ollama, local, unlimited) ─────────────────────
OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2")
OLLAMA_TIMEOUT: int = int(os.getenv("OLLAMA_TIMEOUT", "120"))  # seconds

# ── Fallback 1: Gemini ────────────────────────────────────────────────────────
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# ── Fallback 2: OpenAI ────────────────────────────────────────────────────────
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# ── Image Generation: Pollinations.ai ─────────────────────────────────────────
POLLINATIONS_ENABLED: bool = os.getenv("POLLINATIONS_ENABLED", "true").lower() == "true"
POLLINATIONS_API_KEY: str = os.getenv("POLLINATIONS_API_KEY", "")  # Optional — higher limits
POLLINATIONS_MODEL: str = os.getenv("POLLINATIONS_MODEL", "flux")
POLLINATIONS_WIDTH: int = int(os.getenv("POLLINATIONS_WIDTH", "1024"))
POLLINATIONS_HEIGHT: int = int(os.getenv("POLLINATIONS_HEIGHT", "768"))

# ── Image Fallback: Hugging Face Inference API ────────────────────────────────
HF_API_TOKEN: str = os.getenv("HF_API_TOKEN", "")
HF_IMAGE_MODEL: str = os.getenv("HF_IMAGE_MODEL", "stabilityai/stable-diffusion-xl-base-1.0")
HF_TIMEOUT: int = int(os.getenv("HF_TIMEOUT", "60"))

# ── Image Fallback 2: Gemini Vision (multimodal) ─────────────────────────────
GEMINI_IMAGE_ENABLED: bool = os.getenv("GEMINI_IMAGE_ENABLED", "true").lower() == "true"

# ── Legacy aliases (compatibilidade) ──────────────────────────────────────────
LLM_PROVIDER: str = "ollama"  # Always use Llama as primary
OLLAMA_FALLBACK_TO_GEMINI: bool = True  # Replaced by chain logic

# ── Database ──────────────────────────────────────────────────────────────────
DB_PATH: str = os.getenv("DB_PATH", "course_platform.db")
DB_URL: str = f"sqlite:///{DB_PATH}"

# ── Generation Defaults ───────────────────────────────────────────────────────
DEFAULT_NUM_MODULES: int = 4
DEFAULT_NUM_LESSONS: int = 3
DEFAULT_NUM_QUESTIONS: int = 5

# ── Content Language ──────────────────────────────────────────────────────────
CONTENT_LANGUAGE: str = os.getenv("CONTENT_LANGUAGE", "English (US)")

# ── Chatbot ───────────────────────────────────────────────────────────────────
MAX_CHAT_HISTORY: int = 20
