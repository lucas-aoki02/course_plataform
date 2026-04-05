"""
config.py
─────────
Groq-powered configuration module.
Primary engine: Llama 3 8B (via Groq API) for instant responses.
"""

from pathlib import Path
from dotenv import load_dotenv
import os

# Load .env from project root
load_dotenv(Path(__file__).parent / ".env")

# ── Primary Text Engine: Groq ────────────────────────────────────────────────
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

# ── Image Generation: Hugging Face (Free API) ──────────────────────────────
HF_API_TOKEN: str = os.getenv("HF_API_TOKEN", "")
IMAGE_MODEL: str = os.getenv("IMAGE_MODEL", "stabilityai/stable-diffusion-3.5-large")
IMAGE_GENERATION_ENABLED: bool = os.getenv("IMAGE_GENERATION_ENABLED", "true").lower() == "true"

# ── Database ──────────────────────────────────────────────────────────────────
DB_PATH: str = os.getenv("DB_PATH", "course_platform.db")

# ── Generation Defaults ───────────────────────────────────────────────────────
DEFAULT_NUM_MODULES: int = 4
DEFAULT_NUM_LESSONS: int = 3
DEFAULT_NUM_QUESTIONS: int = 5

# ── Content Language ──────────────────────────────────────────────────────────
CONTENT_LANGUAGE: str = os.getenv("CONTENT_LANGUAGE", "English (US)")

# ── Chatbot ───────────────────────────────────────────────────────────────────
MAX_CHAT_HISTORY: int = 20
