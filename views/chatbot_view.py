"""
views/chatbot_view.py
──────────────────────
Consultive AI Tutor chatbot (Gemini) — for cross-module questions.

This is distinct from the Quick Chat (Llama 3.2) in the content player:
  - This tutor has the full course content in context.
  - Ideal for questions that connect concepts across different modules.
  - Example: "How does what I learned in Module 1 apply to Module 4?"

Architecture
------------
- `ChatbotService` is instantiated once per course and cached in
  `st.session_state` (keyed by course_id) to avoid reloading course
  content on every Streamlit rerun.
- History is loaded from SQLite by `ChatbotService.get_history()`.
- User input is captured with `st.chat_input` (always pinned to bottom).

State keys used:
  active_course_id          : int — set before navigating here
  chatbot_service_{id}      : ChatbotService instance (cached per course)
"""

from __future__ import annotations

import streamlit as st

from repositories import course_repo
from services.chatbot_service import ChatbotService


def _get_service(course_id: int) -> ChatbotService:
    """
    Return (or create and cache) a ChatbotService for the given course.

    Caching in session_state avoids reloading the full course content
    (which can be large) on every Streamlit rerun.
    """
    key = f"chatbot_service_{course_id}"
    if key not in st.session_state:
        st.session_state[key] = ChatbotService(course_id)
    return st.session_state[key]


def render() -> None:
    """
    Render the AI tutor chatbot page.

    Called by `app.py` when `st.session_state["page"] == "chatbot"`.
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
        f"<h1 style='font-size:1.8rem;font-weight:700'>🧠 AI Tutor — {course.title}</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div style='margin-bottom:0.75rem'>"
        "<span style='background:#f3f4f6;color:#374151;padding:3px 10px;"
        "border-radius:4px;font-size:0.8rem;border:1px solid #e5e7eb'>"
        "⚡ Powered by Llama 3.2 + Resilient Chain</span></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color:#6b7280'>Ask me anything that connects concepts across different "
        "modules — I have the full course in context. "
        "Powered by a resilient LLM chain (Llama → Gemini → OpenAI). "
        "For quick questions about a specific lesson, use the ⚡ Quick Chat tab in the course player.</p>",
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            service = _get_service(course_id)
            service.clear_history()
            # Remove cached service instance so it reloads fresh
            st.session_state.pop(f"chatbot_service_{course_id}", None)
            st.rerun()

    st.markdown("---")

    # Load and display history
    try:
        service = _get_service(course_id)
    except Exception as e:
        st.error(f"Failed to load tutor: {e}")
        return

    history = service.get_history()

    if not history:
        with st.chat_message("assistant"):
            st.markdown(
                f"Hello! I'm your **Gemini AI Tutor** for **{course.title}**. "
                "I specialize in **cross-module questions** — like how concepts from Module 1 "
                "apply to what you're studying in Module 4. Ask me anything!"
            )

    for msg in history:
        with st.chat_message(msg.role):
            st.markdown(msg.content)

    # Chat input (pinned to bottom by Streamlit)
    if prompt := st.chat_input("Ask a question about the course..."):
        # Display user message immediately
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate and display AI reply
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                reply = service.chat(prompt)
            st.markdown(reply)

    # Navigation footer
    st.markdown("---")
    col_back, col_course = st.columns(2)
    with col_back:
        if st.button("🏠 Home", use_container_width=True):
            st.session_state["page"] = "home"
            st.rerun()
    with col_course:
        if st.button("📖 Back to Course", use_container_width=True):
            st.session_state["page"] = "player"
            st.rerun()
