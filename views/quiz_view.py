"""
views/quiz_view.py
──────────────────
Quiz player: displays questions and checks answers.
"""

from __future__ import annotations
import streamlit as st
from repositories import quiz_repo

def render() -> None:
    course_id = st.session_state.get("active_course_id")
    if not course_id:
        st.error("No course selected.")
        return

    quizzes = quiz_repo.get_quizzes(course_id)
    if not quizzes:
        st.info("No quiz found for this course. Generate one in 'Create Course' Step 3.")
        return

    st.markdown("### 📝 Course Quiz")
    st.markdown("---")

    score = 0
    for i, q in enumerate(quizzes):
        st.markdown(f"**Question {i+1}: {q.question_text}**")
        
        # Options are list of strings
        choice = st.radio(f"Select your answer:", q.options, key=f"q_{q.id}")
        
        # correct_answer is '0', '1', etc. as string (from SQL)
        correct_idx = int(q.correct_answer)
        correct_text = q.options[correct_idx]
        
        if st.button("Check Answer", key=f"b_{q.id}"):
            if choice == correct_text:
                st.success(f"Correct! {q.explanation}")
            else:
                st.error(f"Wrong. The correct answer was: {correct_text}. {q.explanation}")
        st.markdown("---")
