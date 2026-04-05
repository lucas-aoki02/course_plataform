"""
db/database.py
──────────────
Raw SQLite3 connection management.
Replaces SQLAlchemy to minimize external dependencies.
"""

import sqlite3
import os
import config

def get_connection():
    """Returns a raw sqlite3 connection with Row factory enabled."""
    conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Creates the database schema if it doesn't exist."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Courses table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'DRAFT',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            source_document TEXT,
            refined BOOLEAN DEFAULT 0
        )
    """)
    
    # Modules table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS modules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            order_index INTEGER DEFAULT 0,
            FOREIGN KEY (course_id) REFERENCES courses (id) ON DELETE CASCADE
        )
    """)
    
    # Lessons table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            module_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content_markdown TEXT,
            image_path TEXT,
            order_index INTEGER DEFAULT 0,
            FOREIGN KEY (module_id) REFERENCES modules (id) ON DELETE CASCADE
        )
    """)
    
    # Quizzes table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quizzes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            question_text TEXT NOT NULL,
            options_json TEXT NOT NULL,
            correct_answer TEXT NOT NULL,
            explanation TEXT,
            FOREIGN KEY (course_id) REFERENCES courses (id) ON DELETE CASCADE
        )
    """)
    
    # Lesson Assets table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lesson_assets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lesson_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            content TEXT NOT NULL,
            caption TEXT,
            FOREIGN KEY (lesson_id) REFERENCES lessons (id) ON DELETE CASCADE
        )
    """)
    
    # Chat Messages table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            FOREIGN KEY (course_id) REFERENCES courses (id) ON DELETE CASCADE
        )
    """)

    # Lesson Chat Messages table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS lesson_chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lesson_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            FOREIGN KEY (lesson_id) REFERENCES lessons (id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()

# Initialize on import
init_db()
