"""
views/content_player.py
────────────────────────
Content reader for the AI Course Platform (Lite version).
"""

from __future__ import annotations
import streamlit as st
from repositories import course_repo

def render() -> None:
    course_id = st.session_state.get("active_course_id")
    if not course_id:
        st.error("No course selected.")
        return

    course = course_repo.get_course(course_id)
    if not course:
        st.error("Course not found.")
        return

    # Sidebar Navigation
    with st.sidebar:
        st.markdown(f"### 📚 {course.title}")
        st.markdown("---")
        for module in course.modules:
            st.markdown(f"**{module.title}**")
            for lesson in module.lessons:
                if st.button(lesson.title, key=f"nav_{lesson.id}", use_container_width=True):
                    st.session_state["player_lesson_id"] = lesson.id
                    st.rerun()
        st.markdown("---")
        if st.button("🏠 Home", use_container_width=True):
            st.session_state["page"] = "home"
            st.rerun()

    # Main Content Area
    lesson_id = st.session_state.get("player_lesson_id")
    if not lesson_id:
        if course.modules and course.modules[0].lessons:
            st.session_state["player_lesson_id"] = course.modules[0].lessons[0].id
            st.rerun()
        else:
            st.info("No lessons found.")
            return

    lesson = course_repo.get_lesson(lesson_id)
    if not lesson:
        st.error("Lesson not found.")
        return

    st.markdown(f"## {lesson.title}")
    st.markdown("---")
    
    if lesson.content_markdown:
        st.markdown(lesson.content_markdown, unsafe_allow_html=True)
    else:
        st.info("Content still generating for this lesson...")
