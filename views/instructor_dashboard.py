"""
views/instructor_dashboard.py
──────────────────────────────
Instructor dashboard: Course management + Student progress overview.
Accessible to Instructors and Admins.
"""

from __future__ import annotations
import streamlit as st
import pandas as pd

from db.database import get_db
from db.models import UserRole, User
from repositories.user_repo import list_users, get_student_progress
from repositories.course_repo import list_courses, get_course
import auth


def render() -> None:
    current_user = auth.get_current_user()
    if not current_user or current_user["role"] not in (
        UserRole.instructor.value, UserRole.admin.value
    ):
        st.error("🚫 Access denied. Instructors only.")
        return

    st.title("👨‍🏫 Instructor Dashboard")
    tab_progress, tab_courses = st.tabs(["📊 Student Progress", "📚 Courses Overview"])

    # ── Tab: Student Progress ───────────────────────────────────────────────────
    with tab_progress:
        st.subheader("📊 Student Progress")

        rows = []
        with get_db() as db:
            students = [u for u in list_users(db) if u.role == UserRole.student]
            courses = list_courses(db)

            if not students:
                st.info("No students registered yet.")
            elif not courses:
                st.info("No courses available yet.")
            else:
                for student in students:
                    progress = get_student_progress(db, student.id)
                    completed_lesson_ids = {p.lesson_id for p in progress}

                    for course in courses:
                        full_course = get_course(db, course.id)
                        if not full_course:
                            continue
                        total_lessons = sum(len(m.lessons) for m in full_course.modules)
                        completed = sum(
                            1 for m in full_course.modules
                            for l in m.lessons if l.id in completed_lesson_ids
                        )
                        pct = round(100 * completed / total_lessons) if total_lessons else 0
                        rows.append({
                            "Student": student.username,
                            "Email": student.email,
                            "Course": course.title,
                            "Completed": f"{completed}/{total_lessons}",
                            "Progress": f"{pct}%",
                        })

        if rows:
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)
        elif students and courses:
            st.info("No progress data available yet.")

    # ── Tab: Courses Overview ───────────────────────────────────────────────────
    with tab_courses:
        st.subheader("📚 Courses")

        with get_db() as db:
            courses_db = list_courses(db)
            courses = []
            for c in courses_db:
                courses.append({
                    "id": c.id,
                    "title": c.title,
                    "description": c.description,
                    "status_value": c.status.value,
                    "created_at": c.created_at
                })

        if not courses:
            st.info("No courses yet. Use the **Create Course** page to get started.")
        else:
            for course in courses:
                with st.expander(f"**{course['title']}** — {course['status_value']}"):
                    st.markdown(f"*{course['description'] or 'No description.'}*")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.caption(f"Created: {course['created_at'].strftime('%Y-%m-%d') if course['created_at'] else '—'}")
                    with col2:
                        if st.button("📖 Open Course", key=f"open_{course['id']}"):
                            st.session_state["active_course_id"] = course['id']
                            st.session_state["page"] = "player"
                            st.rerun()
