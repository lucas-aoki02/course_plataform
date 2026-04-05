"""
repositories/course_repo.py
────────────────────────────
Data-access layer for Course, Module, and Lesson entities using raw SQL.
"""

from __future__ import annotations
from db.database import get_connection

class DBRow:
    """Simple container to mimic SQLAlchemy object access like row.title"""
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

def list_courses() -> list[dict]:
    """Return all courses ordered by newest first."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM courses ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_course(course_id: int) -> DBRow | None:
    """Fetch course with modules and lessons nested."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Get Course
    cursor.execute("SELECT * FROM courses WHERE id = ?", (course_id,))
    c_row = cursor.fetchone()
    if not c_row:
        conn.close()
        return None
    
    course = DBRow(**dict(c_row))
    
    # 2. Get Modules
    cursor.execute("SELECT * FROM modules WHERE course_id = ? ORDER BY order_index", (course_id,))
    m_rows = cursor.fetchall()
    
    modules = []
    for m_r in m_rows:
        mod = DBRow(**dict(m_r))
        # 3. Get Lessons per Module
        cursor.execute("SELECT * FROM lessons WHERE module_id = ? ORDER BY order_index", (mod.id,))
        l_rows = cursor.fetchall()
        
        mod.lessons = []
        for l_r in l_rows:
            lesson = DBRow(**dict(l_r))
            cursor.execute("SELECT * FROM lesson_assets WHERE lesson_id = ?", (lesson.id,))
            a_rows = cursor.fetchall()
            lesson.assets = [DBRow(**dict(a_r)) for a_r in a_rows]
            mod.lessons.append(lesson)
            
        modules.append(mod)
    
    course.modules = modules
    conn.close()
    return course

def update_course_status(course_id: int, status: str) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE courses SET status = ? WHERE id = ?", (status, course_id))
    conn.commit()
    conn.close()

def delete_course(course_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM courses WHERE id = ?", (course_id,))
    count = cursor.rowcount
    conn.commit()
    conn.close()
    return count > 0

def get_lesson(lesson_id: int) -> DBRow | None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM lessons WHERE id = ?", (lesson_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
        
    lesson = DBRow(**dict(row))
    cursor.execute("SELECT * FROM lesson_assets WHERE lesson_id = ?", (lesson_id,))
    a_rows = cursor.fetchall()
    lesson.assets = [DBRow(**dict(a_r)) for a_r in a_rows]
    
    conn.close()
    return lesson

def update_lesson_content(lesson_id: int, markdown: str, image_path: str = None) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    if image_path:
        cursor.execute("UPDATE lessons SET content_markdown = ?, image_path = ? WHERE id = ?", 
                      (markdown, image_path, lesson_id))
    else:
        cursor.execute("UPDATE lessons SET content_markdown = ? WHERE id = ?", 
                      (markdown, lesson_id))
    conn.commit()
    conn.close()

def add_lesson_asset(lesson_id: int, asset_type: str, content: str, caption: str = "") -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO lesson_assets (lesson_id, type, content, caption) VALUES (?, ?, ?, ?)",
        (lesson_id, asset_type, content, caption)
    )
    asset_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return asset_id

def delete_lesson_asset(asset_id: int) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM lesson_assets WHERE id = ?", (asset_id,))
    conn.commit()
    conn.close()
