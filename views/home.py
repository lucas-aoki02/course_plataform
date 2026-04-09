"""
views/home.py
─────────────
Home page: displays all created courses using SQLAlchemy ORM.
"""

from __future__ import annotations
import streamlit as st
from db.database import get_db
from repositories.course_repo import list_courses, delete_course


def _status_badge(status: str) -> str:
    colors = {
        "DRAFT": ("#f59e0b", "⏳ Draft"),
        "GENERATING": ("#3b82f6", "⚙️ Generating"),
        "COMPLETE": ("#10b981", "✅ Complete"),
    }
    color, label = colors.get(status, ("#6b7280", status))
    return (
        f'<span style="background:{color};color:white;padding:2px 10px;'
        f'border-radius:12px;font-size:0.75rem;font-weight:600;">{label}</span>'
    )


def render() -> None:
    st.markdown("<h1 style='font-size:2.2rem;font-weight:700;'>🎓 Courses</h1>", unsafe_allow_html=True)
    st.markdown("---")

    col_title, col_btn = st.columns([5, 1])
    with col_btn:
        if st.button("➕ New Course", type="primary", use_container_width=True):
            st.session_state["page"] = "create"
            st.rerun()

    with get_db() as db:
        courses_db = list_courses(db)
        courses = []
        for c in courses_db:
            courses.append({
                "id": c.id,
                "title": c.title,
                "description": c.description,
                "status_value": c.status.value
            })

    if not courses:
        st.info("No courses yet. Click **➕ New Course** to start!")
        return

    for course in courses:
        with st.container(border=True):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(f"### {course['title']}")
                desc = (course['description'] or "")[:150]
                st.markdown(f"<p style='color:#6b7280'>{desc}...</p>", unsafe_allow_html=True)
                st.markdown(_status_badge(course['status_value']), unsafe_allow_html=True)
            with col2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("📖 View", key=f"v_{course['id']}", use_container_width=True):
                    st.session_state["page"] = "player"
                    st.session_state["active_course_id"] = course['id']
                    st.rerun()
                if st.button("🗑️ Delete", key=f"d_{course['id']}", use_container_width=True):
                    with get_db() as db:
                        delete_course(db, course['id'])
                    st.rerun()
