"""
services/content_service.py
────────────────────────────
Generates and persists Markdown lesson content using Groq (Llama 3 8B).
Removes SQLAlchemy and uses raw SQL.
"""

from __future__ import annotations
import logging
from collections.abc import Generator
import config
from db.database import get_connection
from services.ai_service import llama_service
from utils.prompts import (
    get_system_content_prompt,
    build_lesson_content_prompt,
)

logger = logging.getLogger(__name__)

def generate_lesson_stream(
    course_title: str,
    module_title: str,
    lesson_id: int,
    target_chars: int = 0,
) -> Generator[tuple[str, str], None, None]:
    """
    Generator that yields ('text', chunk) or ('status', msg).
    Persists paragraphs to SQLite using raw SQL.
    """

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT title FROM lessons WHERE id = ?", (lesson_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise ValueError(f"Lesson {lesson_id} not found")
    lesson_title = row["title"]
    
    # Clear existing content
    cursor.execute("UPDATE lessons SET content_markdown = '' WHERE id = ?", (lesson_id,))
    conn.commit()
    conn.close()

    prompt = build_lesson_content_prompt(course_title, module_title, lesson_title, target_chars)
    system = get_system_content_prompt(target_chars)

    full_content = ""
    current_paragraph = ""

    # Calculate max_tokens cap. Groq free tier limit is 6000 TPM (prompt + completion).
    # A massive prompt may consume ~3000 tokens. Setting max_tokens to 1500 strictly prevents 413 errors,
    # as the continuous expanding loop will just request more 1500-token chunks automatically.
    if target_chars > 0:
        dynamic_max_tokens = 1500
    else:
        dynamic_max_tokens = 1200 # Default
        
    logger.info(f"[Groq] Streaming lesson: {lesson_title}")
    
    total_loops = 0
    max_loops = 5 # Prevent infinite loops
    
    while True:
        total_loops += 1
        
        if total_loops > 1:
            prompt = f"Continue writing the lesson '{lesson_title}'. Write Part {total_loops}. Introduce entirely NEW advanced subtopics, examples, and deep-dives. DO NOT summarize or repeat anything from previous parts. Use emojis."
            yield "status", f"Iniciando Módulo de Expansão {total_loops}..."
            
        for chunk in llama_service.generate_stream(
            prompt, 
            system=system, 
            temperature=0.7, 
            max_tokens=dynamic_max_tokens
        ):
            full_content += chunk
            current_paragraph += chunk
            yield "text", chunk

            if "\n\n" in current_paragraph:
                parts = current_paragraph.split("\n\n")
                for i in range(len(parts) - 1):
                    p_text = parts[i].strip()
                    if p_text:
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute("SELECT content_markdown FROM lessons WHERE id = ?", (lesson_id,))
                        existing = cursor.fetchone()["content_markdown"] or ""
                        new_content = f"{existing}\n\n{p_text}" if existing else p_text
                        cursor.execute("UPDATE lessons SET content_markdown = ? WHERE id = ?", (new_content, lesson_id))
                        conn.commit()
                        conn.close()
                        yield "status", f"Paragraph saved: {len(p_text)} chars"
                current_paragraph = parts[-1]
                
        # Check if we've reached the target length
        if target_chars == 0 or len(full_content) >= target_chars * 0.85 or total_loops >= max_loops:
            break
            
        # Add a visual separator between parts
        yield "text", "\n\n***\n\n"
        current_paragraph += "\n\n***\n\n"

    if current_paragraph.strip():
        p_text = current_paragraph.strip()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT content_markdown FROM lessons WHERE id = ?", (lesson_id,))
        existing = cursor.fetchone()["content_markdown"] or ""
        new_content = f"{existing}\n\n{p_text}" if existing else p_text
        cursor.execute("UPDATE lessons SET content_markdown = ? WHERE id = ?", (new_content, lesson_id))
        conn.commit()
        conn.close()
    
    yield "status", f"Text completed: {len(full_content)} characters total."

    # Image generation logic has been decoupled to the Asset Manager in course_creator

def get_full_content_as_text(course_id: int) -> str:
    """
    Concatenates all lesson content of a course into a single Markdown string.
    Used for tutor context and course export.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT m.title as m_title, l.title as l_title, l.content_markdown 
        FROM modules m JOIN lessons l ON m.id = l.module_id 
        WHERE m.course_id = ? 
        ORDER BY m.order_index, l.order_index
    """, (course_id,))
    rows = cursor.fetchall()
    
    parts = []
    current_mod = None
    for r in rows:
        if r["m_title"] != current_mod:
            current_mod = r["m_title"]
            parts.append(f"\n# {current_mod}\n")
        parts.append(f"\n## {r['l_title']}\n")
        parts.append(r["content_markdown"] or "(no content)")
    
    conn.close()
    return "\n".join(parts)
