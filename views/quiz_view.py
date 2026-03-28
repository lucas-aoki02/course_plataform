"""
views/quiz_view.py
───────────────────
Interactive quiz page: renders questions, captures answers, shows score.

Flow
----
1. Load all quiz questions for the active course.
2. Render each question with st.radio (options as answer choices).
3. On submit: compare user answers to correct_index, show per-question
   feedback (correct/wrong + explanation), display final score.

State keys used:
  active_course_id          : int — set before navigating here
  quiz_submitted            : bool — True after user clicks Submit
  quiz_answer_{question_id} : int — user's selected option index per question
"""

from __future__ import annotations

import streamlit as st

from repositories import course_repo
from repositories.quiz_repo import get_quizzes


def render() -> None:
    """
    Render the quiz interface.

    Called by `app.py` when `st.session_state["page"] == "quiz"`.
    """
    course_id: int | None = st.session_state.get("active_course_id")
    if not course_id:
        st.error("No course selected.")
        return

    course = course_repo.get_course(course_id)
    if not course:
        st.error("Course not found.")
        return

    st.markdown(
        f"<h1 style='font-size:1.8rem;font-weight:700'>📝 Quiz — {course.title}</h1>",
        unsafe_allow_html=True,
    )

    questions = get_quizzes(course_id)
    if not questions:
        st.warning("No quiz questions available for this course yet.")
        if st.button("🏠 Home"):
            st.session_state["page"] = "home"
            st.rerun()
        return

    submitted = st.session_state.get("quiz_submitted", False)

    with st.form("quiz_form"):
        for q in questions:
            st.markdown(f"**{q.question}**")
            st.radio(
                label=q.question,
                options=q.options,
                key=f"quiz_answer_{q.id}",
                index=None,  # No default selection
                label_visibility="collapsed",
            )
            st.markdown("&nbsp;")

        if not submitted:
            submit_clicked = st.form_submit_button("Submit Answers", type="primary")
            if submit_clicked:
                # Check at least one question answered
                answered = sum(
                    1 for q in questions
                    if st.session_state.get(f"quiz_answer_{q.id}") is not None
                )
                if answered == 0:
                    st.warning("Please answer at least one question before submitting.")
                else:
                    st.session_state["quiz_submitted"] = True
                    st.rerun()

    # ── Results ────────────────────────────────────────────────────────────────
    if submitted:
        correct = 0
        st.markdown("---")
        st.markdown("### Results")

        for q in questions:
            user_answer_text = st.session_state.get(f"quiz_answer_{q.id}")
            if user_answer_text is None:
                st.markdown(f"**{q.question}**")
                st.markdown("_Skipped_")
                continue

            # Map selected text back to index
            try:
                user_idx = q.options.index(user_answer_text)
            except ValueError:
                user_idx = -1

            is_correct = user_idx == q.correct_index
            if is_correct:
                correct += 1

            icon = "✅" if is_correct else "❌"
            st.markdown(f"{icon} **{q.question}**")
            st.markdown(f"Your answer: *{user_answer_text}*")
            if not is_correct:
                st.markdown(f"Correct answer: *{q.options[q.correct_index]}*")
            with st.expander("See explanation"):
                st.markdown(q.explanation)
            st.markdown("---")

        # Final score
        total = len(questions)
        pct = int((correct / total) * 100) if total else 0
        score_color = "#10b981" if pct >= 70 else "#f59e0b" if pct >= 40 else "#ef4444"
        st.markdown(
            f"<h2 style='text-align:center;color:{score_color}'>"
            f"Score: {correct}/{total} ({pct}%)</h2>",
            unsafe_allow_html=True,
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🔄 Retake Quiz", use_container_width=True):
                # Clear submission state but keep answers for reference
                st.session_state["quiz_submitted"] = False
                for q in questions:
                    st.session_state.pop(f"quiz_answer_{q.id}", None)
                st.rerun()
        with col2:
            if st.button("📖 Review Content", use_container_width=True):
                st.session_state["page"] = "player"
                st.rerun()
        with col3:
            if st.button("🏠 Home", use_container_width=True):
                st.session_state["page"] = "home"
                st.rerun()
