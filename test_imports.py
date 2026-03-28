"""
test_imports.py
───────────────
Verifies that ALL project modules can be imported without ANY API call or crash.
"""
import sys
sys.path.insert(0, ".")

print("Testing imports (no API key required)...")

# Core
import config
print(f"  config.py OK — ollama={config.OLLAMA_MODEL}, pollinations={config.POLLINATIONS_ENABLED}")

# DB layer
from db.database import init_db, get_session
from db.models import Course, Module, Lesson, Quiz, ChatMessage, CourseStatus
print("  db/ OK")

# Utils
from utils.prompts import (
    build_syllabus_prompt, build_lesson_content_prompt,
    build_quiz_prompt, build_tutor_system_prompt
)
from utils.exporters import export_to_docx, export_to_pptx
print("  utils/ OK")

# Services — must import without triggering API calls
from services.ai_service import AIService, ai_service, llama_service, AIServiceError
print("  services/ai_service OK — chain+llama singletons (no API call)")

from services.syllabus_service import generate_syllabus, SyllabusSchema
print("  services/syllabus_service OK")

from services.content_service import generate_lesson_content, generate_all_content
print("  services/content_service OK")

from services.quiz_service import generate_quiz_questions, QuizQuestionSchema
print("  services/quiz_service OK")

from services.chatbot_service import ChatbotService, QuickChatService
print("  services/chatbot_service OK")

from services.image_service import generate_image, generate_image_for_lesson, get_provider_status
print("  services/image_service OK")

# Repositories
from repositories.course_repo import list_courses, get_course, delete_course
from repositories.quiz_repo import get_quizzes, has_quiz, get_chat_messages
print("  repositories/ OK")

# Views — must import without crash
from views import home, course_creator, content_player, quiz_view, chatbot_view
print("  views/ OK")

print("\nAll imports successful. No API key required at import time.")
print("Run with: python -m streamlit run app.py")
