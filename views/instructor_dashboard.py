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
from repositories.user_repo import list_users, get_student_progress, log_audit
from repositories.course_repo import list_courses, get_course, list_courses_by_instructor, update_course
from db.models import Enrollment
import auth


def render() -> None:
    current_user = auth.get_current_user()
    if not current_user or current_user["role"] not in (
        UserRole.instructor.value, UserRole.system_admin.value, UserRole.general_admin.value, UserRole.privacy_admin.value
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
            if current_user["role"] == UserRole.instructor.value:
                courses = list_courses_by_instructor(db, current_user["id"])
            else: # general_admin or privacy_admin
                courses = list_courses(db)

            if not courses:
                st.info("No courses available yet.")
            else:
                all_users = list_users(db)
                for course in courses:
                    full_course = get_course(db, course.id)
                    if not full_course:
                        continue
                        
                    enrollments = db.query(Enrollment).filter(Enrollment.course_id == course.id).all()
                    enrolled_student_ids = {e.user_id for e in enrollments}
                    
                    if not enrolled_student_ids:
                        continue
                        
                    students_in_course = [u for u in all_users if u.id in enrolled_student_ids]
                    total_lessons = sum(len(m.lessons) for m in full_course.modules)

                    for student in students_in_course:
                        progress = get_student_progress(db, student.id)
                        completed_lesson_ids = {p.lesson_id for p in progress}

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
        elif courses:
            st.info("No enrollments or progress data available yet.")

    # ── Tab: Courses Overview ───────────────────────────────────────────────────
    with tab_courses:
        st.subheader("📚 Courses")

        with get_db() as db:
            if current_user["role"] == UserRole.instructor.value:
                courses_db = list_courses_by_instructor(db, current_user["id"])
            else: # general_admin or privacy_admin
                courses_db = list_courses(db)
                
            courses = []
            for c in courses_db:
                courses.append({
                    "id": c.id,
                    "title": c.title,
                    "description": c.description,
                    "tags": c.tags,
                    "status_value": c.status.value,
                    "created_at": c.created_at
                })

        if not courses:
            st.info("No courses yet. Use the **Create Course** page to get started.")
        else:
            for course in courses:
                with st.expander(f"**{course['title']}** — {course['status_value']}"):
                    st.markdown(f"**Synopsis:**")
                    st.markdown(f"*{course['description'] or 'No synopsis available.'}*")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.caption(f"Created: {course['created_at'].strftime('%Y-%m-%d') if course['created_at'] else '—'}")
                    with col2:
                        if st.button("📖 Open Course", key=f"open_{course['id']}", use_container_width=True):
                            st.session_state["active_course_id"] = course['id']
                            st.session_state["page"] = "player"
                            st.rerun()

                    # ── Edit Section ──
                    st.markdown("---")
                    st.markdown("#### ✏️ Refine Course Metadata")
                    with st.form(f"edit_course_{course['id']}"):
                        edit_title = st.text_input("Course Title", value=course['title'])
                        edit_desc = st.text_area("Course Synopsis", value=course['description'] or "", height=100)
                        edit_tags = st.text_input("Tags (comma separated)", value=course.get('tags', '') or "")
                        
                        if st.form_submit_button("💾 Save Changes", type="primary", use_container_width=True):
                            with get_db() as db:
                                update_course(db, course['id'], title=edit_title, description=edit_desc, tags=edit_tags)
                                log_audit(
                                    db, 
                                    action="UPDATE", 
                                    user_id=current_user["id"], 
                                    table_name="courses", 
                                    details=f"Instructor updated metadata/tags for course ID {course['id']}"
                                )
                            st.success("Course metadata updated successfully!")
                            st.rerun()
