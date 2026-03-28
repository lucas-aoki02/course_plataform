"""
views/home.py
─────────────
Home page: displays all created courses as cards and provides navigation.

Responsibilities
----------------
- List all courses from the DB (via course_repo).
- Show status badges (Draft / Generating / Complete).
- Provide action buttons: View, Take Quiz, Chat, Delete.
- "Create New Course" button navigates to the creator flow.
"""

from __future__ import annotations

import streamlit as st

from db.models import CourseStatus
from repositories import course_repo


def _status_badge(status: CourseStatus) -> str:
    """Return an HTML badge string for a course status."""
    colors = {
        CourseStatus.DRAFT: ("#f59e0b", "⏳ Draft"),
        CourseStatus.GENERATING: ("#3b82f6", "⚙️ Generating"),
        CourseStatus.COMPLETE: ("#10b981", "✅ Complete"),
    }
    color, label = colors.get(status, ("#6b7280", status.value))
    return (
        f'<span style="background:{color};color:white;padding:2px 10px;'
        f'border-radius:12px;font-size:0.75rem;font-weight:600;">{label}</span>'
    )


def render() -> None:
    """
    Render the home page.

    Called by `app.py` when `st.session_state["page"] == "home"`.
    Uses `st.session_state` for page navigation to avoid st.experimental_rerun
    anti-patterns.
    """
    st.markdown(
        "<h1 style='font-size:2rem;font-weight:700;margin-bottom:0'>🎓 AI Course Platform</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color:#6b7280;margin-top:4px'>Generate complete courses with AI in minutes.</p>",
        unsafe_allow_html=True,
    )
    st.markdown("---")

    col_title, col_btn = st.columns([5, 1])
    with col_title:
        st.subheader("My Courses")
    with col_btn:
        if st.button("➕ New Course", type="primary", use_container_width=True, key="home_new_course"):
            st.session_state["page"] = "create"
            st.rerun()

    courses = course_repo.list_courses()

    if not courses:
        st.info("No courses yet. Click **➕ New Course** to create your first one!")
        return

    for course in courses:
        with st.container(border=True):
            col1, col2 = st.columns([4, 1])

            with col1:
                st.markdown(
                    f"### {course.title}\n"
                    f"<small style='color:#6b7280'>Topic: {course.topic} · "
                    f"Created: {course.created_at.strftime('%b %d, %Y')}</small>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"{course.description[:200]}{'...' if len(course.description) > 200 else ''}",
                )
                st.markdown(_status_badge(course.status), unsafe_allow_html=True)

            with col2:
                st.markdown("<br>", unsafe_allow_html=True)

                if course.status == CourseStatus.COMPLETE:
                    if st.button("📖 View", key=f"view_{course.id}", use_container_width=True):
                        st.session_state["page"] = "player"
                        st.session_state["active_course_id"] = course.id
                        st.rerun()

                    if st.button("📝 Quiz", key=f"quiz_{course.id}", use_container_width=True):
                        st.session_state["page"] = "quiz"
                        st.session_state["active_course_id"] = course.id
                        st.rerun()

                    if st.button("🤖 Tutor", key=f"chat_{course.id}", use_container_width=True):
                        st.session_state["page"] = "chatbot"
                        st.session_state["active_course_id"] = course.id
                        st.rerun()

                if st.button("🗑️ Delete", key=f"del_{course.id}", use_container_width=True):
                    course_repo.delete_course(course.id)
                    st.success(f"Course '{course.title}' deleted.")
                    st.rerun()
