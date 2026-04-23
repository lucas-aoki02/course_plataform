"""
views/quiz_view.py
──────────────────
Quiz player: displays questions, checks answers, and records progress/attempts.
"""

from __future__ import annotations
import streamlit as st
from db.database import get_db
from repositories import quiz_repo
import auth

def render() -> None:
    course_id = st.session_state.get("active_course_id")
    quiz_scope = st.session_state.get("quiz_scope", {}) # {"type": "lesson"/"module"/"course", "id": int}
    
    if not course_id or not quiz_scope:
        st.error("No course or quiz scope selected.")
        if st.button("Back to Course"):
            st.session_state["page"] = "player"
            st.rerun()
        return

    scope_type = quiz_scope["type"]
    scope_id = quiz_scope["id"]

    with get_db() as db:
        # Get target object for settings
        params = {"course_id": course_id}
        if scope_type == "lesson":
            from db.models import Lesson
            target = db.query(Lesson).filter(Lesson.id == scope_id).first()
            params = {"lesson_id": scope_id}
        elif scope_type == "module":
            from db.models import Module
            target = db.query(Module).filter(Module.id == scope_id).first()
            params = {"module_id": scope_id}
        else:
            from db.models import Course
            target = db.query(Course).filter(Course.id == course_id).first()
            params = {"course_id": course_id}

        if not target:
            st.error("Target content not found.")
            return

        pass_score = getattr(target, "quiz_passing_score", 0) or 0
        max_att = getattr(target, "quiz_max_attempts", 0) or 0
        
        quizzes_db = quiz_repo.get_quizzes(db, **params)
        if not quizzes_db:
            st.info("No quiz items found.")
            if st.button("Back"):
                st.session_state["page"] = "player"
                st.rerun()
            return

        current_user = auth.get_current_user()
        attempts = quiz_repo.get_quiz_attempts(db, current_user["id"], **params)
        num_attempts = len(attempts)
        
        # Check if already passed
        already_passed = any(a.passed for a in attempts)
        
        # Check if max attempts reached
        if max_att > 0 and num_attempts >= max_att and not already_passed:
            st.error(f"Maximum attempts ({max_att}) reached. You did not pass this quiz.")
            if st.button("Back to Course"):
                st.session_state["page"] = "player"
                st.rerun()
            return

        st.markdown(f"### 📝 {scope_type.capitalize()} Quiz: {target.title}")
        if already_passed:
            st.success("✅ You have already passed this quiz.")
        
        if max_att > 0:
            st.info(f"Attempts: {num_attempts}/{max_att} | Passing Score: {pass_score}%")
        else:
            st.info(f"Attempts: {num_attempts} (No limit) | Passing Score: {pass_score}%")

        st.markdown("---")

        # Form for submission
        with st.form(key=f"quiz_form_{scope_type}_{scope_id}"):
            user_choices = {}
            for i, q in enumerate(quizzes_db):
                st.markdown(f"**Question {i+1}: {q.question_text}**")
                user_choices[q.id] = st.radio(f"Select your answer:", q.options, key=f"q_{q.id}")
                st.markdown("---")
            
            submit = st.form_submit_button("Submit Quiz", use_container_width=True)

        if submit:
            correct_count = 0
            for q in quizzes_db:
                correct_idx = int(q.correct_answer)
                if user_choices[q.id] == q.options[correct_idx]:
                    correct_count += 1
            
            score_pct = int((correct_count / len(quizzes_db)) * 100)
            passed = score_pct >= pass_score
            
            with get_db() as db_upd:
                quiz_repo.record_quiz_attempt(
                    db_upd, current_user["id"], score_pct, passed,
                    **params
                )
            
            if passed:
                st.balloons()
                st.success(f"Congratulations! You passed with {score_pct}% ({correct_count}/{len(quizzes_db)})")
            else:
                st.error(f"You did not pass. Score: {score_pct}%. Passing score required: {pass_score}%")
            
            if st.button("Finish", use_container_width=True, type="primary"):
                if passed and scope_type == "course":
                    st.session_state["show_cert"] = {"type": "course", "id": course_id}
                st.session_state["page"] = "player"
                st.rerun()

    if st.button("Cancel"):
        st.session_state["page"] = "player"
        st.rerun()
