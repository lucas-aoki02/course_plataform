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
print(f"  config.py OK")

# DB layer
from db.database import init_db, get_connection
print("  db/ OK")

# Utilities (Removed obsolete wrappers)
from utils.prompts import (
    build_syllabus_prompt, build_lesson_content_prompt,
    build_quiz_prompt, build_tutor_system_prompt
)
print("  utils/ OK")

# Services
from services.ai_service import ai_service, llama_service, AIServiceError
print("  services/ai_service OK")

from services.syllabus_service import generate_syllabus, SyllabusSchema
print("  services/syllabus_service OK")

from services.content_service import generate_lesson_stream, get_full_content_as_text
print("  services/content_service OK")

from services.quiz_service import generate_quiz_questions
print("  services/quiz_service OK")

from services.chatbot_service import ChatbotService
print("  services/chatbot_service OK")



# Repositories
from repositories.course_repo import list_courses, get_course, delete_course
print("  repositories/ OK")

# Views
from views import home, course_creator, content_player, quiz_view, chatbot_view
print("  views/ OK")

print("\nAll imports successful. No API key required at import time.")
print("Run with: python -m streamlit run app.py")
