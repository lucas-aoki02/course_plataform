"""
repositories/quiz_repo.py
──────────────────────────
Data-access layer for Quizzes using raw SQL.
"""

from __future__ import annotations
import json
from db.database import get_connection

class DBRow:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

def get_quizzes(course_id: int) -> list[DBRow]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM quizzes WHERE course_id = ?", (course_id,))
    rows = cursor.fetchall()
    conn.close()
    
    results = []
    for r in rows:
        d = dict(r)
        # Parse JSON options
        if d.get("options_json"):
            d["options"] = json.loads(d["options_json"])
        results.append(DBRow(**d))
    return results

def has_quiz(course_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM quizzes WHERE course_id = ?", (course_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return count > 0

# Chat functionality placeholder (table created in database.py if needed, 
# but simplified for now)
def get_chat_messages(course_id: int, limit: int = 50) -> list:
    return [] # Simplified Lite version
