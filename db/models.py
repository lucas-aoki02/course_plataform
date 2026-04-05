"""
db/models.py
────────────
Simplified models for the AI Course Platform (Lite).
SQLAlchemy was removed in favor of raw SQL.
"""

class CourseStatus:
    DRAFT = "DRAFT"
    GENERATING = "GENERATING"
    COMPLETE = "COMPLETE"
