"""
services/quiz_service.py
─────────────────────────
Generates multiple-choice quiz questions from course content and persists them.
Removes Pydantic and uses raw SQL.
"""

from __future__ import annotations
import json
import logging
import re
import config
from db.database import get_connection
from services.ai_service import llama_service
from utils.prompts import SYSTEM_QUIZ_LLAMA, build_quiz_prompt

logger = logging.getLogger(__name__)

def _extract_json_array(raw: str) -> str:
    match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", raw)
    if match:
        return match.group(1).strip()
    return raw.strip()

def _build_lessons_summary(course_id: int) -> str:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT m.title as m_title, l.title as l_title 
        FROM modules m JOIN lessons l ON m.id = l.module_id 
        WHERE m.course_id = ? 
        ORDER BY m.order_index, l.order_index
    """, (course_id,))
    rows = cursor.fetchall()
    conn.close()
    
    lines = []
    current_mod = None
    for r in rows:
        if r["m_title"] != current_mod:
            current_mod = r["m_title"]
            lines.append(f"\nModule: {current_mod}")
        lines.append(f"  - {r['l_title']}")
    return "\n".join(lines)

def generate_quiz_questions(course_id: int, course_title: str, n_questions: int = config.DEFAULT_NUM_QUESTIONS):
    summary = _build_lessons_summary(course_id)
    prompt = build_quiz_prompt(course_title, summary, n_questions)
    
    logger.info(f"[Groq] Generating {n_questions} questions")
    raw = llama_service.generate(prompt, system=SYSTEM_QUIZ_LLAMA)
    clean = _extract_json_array(raw)
    
    try:
        data = json.loads(clean)
        if not isinstance(data, list):
            raise ValueError("Expected list of questions")
        return data
    except Exception as e:
        logger.error(f"Quiz parse error: {e}")
        raise ValueError(f"Failed to generate quiz: {e}")

def save_quiz_questions(course_id: int, questions: list):
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Clear existing
        cursor.execute("DELETE FROM quizzes WHERE course_id = ?", (course_id,))
        
        for q in questions:
            # We assume q has 'question', 'options', 'correct_index', 'explanation'
            opts_json = json.dumps(q.get("options", []))
            cursor.execute("""
                INSERT INTO quizzes (course_id, question_text, options_json, correct_answer, explanation)
                VALUES (?, ?, ?, ?, ?)
            """, (course_id, q.get("question", ""), opts_json, str(q.get("correct_index", 0)), q.get("explanation", "")))
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def generate_and_save_quiz(course_id: int, title: str, n_questions: int = None):
    n = n_questions or config.DEFAULT_NUM_QUESTIONS
    questions = generate_quiz_questions(course_id, title, n)
    save_quiz_questions(course_id, questions)
    return questions
