"""
config.py
─────────
Central configuration for the AI Course Platform.
Reads from .env in the project root.
"""

from pathlib import Path
from dotenv import load_dotenv
import os

# Load .env from project root
load_dotenv(Path(__file__).parent / ".env")

# ── Primary Text Engine: Groq ─────────────────────────────────────────────────
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

# ── Database (PostgreSQL or SQLite fallback) ───────────────────────────────────
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///course_platform.db")

# ── Security & Encryption ──────────────────────────────────────────────────────
ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "")

# ── Email / SMTP (Outlook default) ───────────────────────────────────────────
EMAIL_HOST: str = os.getenv("EMAIL_HOST", "smtp-mail.outlook.com")
EMAIL_PORT: int = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER: str = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD: str = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_FROM: str = os.getenv("EMAIL_FROM", EMAIL_HOST_USER)
PLATFORM_URL: str = os.getenv("PLATFORM_URL", "http://localhost:8501")

# ── Generation Defaults ────────────────────────────────────────────────────────
DEFAULT_NUM_MODULES: int = 4
DEFAULT_NUM_LESSONS: int = 3
DEFAULT_NUM_QUESTIONS: int = 5

# ── Content Language ───────────────────────────────────────────────────────────
CONTENT_LANGUAGE: str = os.getenv("CONTENT_LANGUAGE", "English (US)")

# ── Chatbot ────────────────────────────────────────────────────────────────────
MAX_CHAT_HISTORY: int = 20
