"""
views/chatbot_view.py
──────────────────────
Intelligent AI Tutor: chat interface using ChatbotService.
Features persistence, encryption (LGPD/GDPR), and course recommendations.
"""

from __future__ import annotations
import streamlit as st
import auth
from services.chatbot_service import ChatbotService


def render() -> None:
    current_user = auth.get_current_user()
    course_id = st.session_state.get("active_course_id")
    
    if not current_user:
        st.error("Please log in.")
        return

    st.markdown("### 🤖 Intelligent AI Tutor")
    if course_id:
        st.caption("Ask anything about this course. Suggestions for other courses may appear based on your interest.")
    else:
        st.caption("How can I help you today? I can recommend courses based on your interests.")

    # Initialize Chat Service — always re-create if key changed by checking version
    service_key = f"chatbot_service_{course_id}"
    if "chatbot_service" not in st.session_state or st.session_state.get("chatbot_service_course_id") != course_id:
        st.session_state.chatbot_service = ChatbotService(course_id, current_user["id"])
        st.session_state.chatbot_service_course_id = course_id

    service: ChatbotService = st.session_state.chatbot_service

    # Display Decrypted chat history
    history = service.get_history()
    for message in history:
        with st.chat_message(message.role):
            st.markdown(message.content)

    # Chat input
    if prompt := st.chat_input("Ask your tutor..."):
        # Display user message immediately
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate and stream response
        with st.chat_message("assistant"):
            with st.spinner("⚡ Processing..."):
                response_placeholder = st.empty()
                full_response = ""
                try:
                    for chunk in service.chat_stream(prompt):
                        full_response += chunk
                        response_placeholder.markdown(full_response + "▌")
                    response_placeholder.markdown(full_response)
                except Exception as e:
                    error_msg = str(e)
                    st.error(f"❌ Error: {error_msg}")
                    if "API Key" in error_msg:
                        st.info("💡 Tip: Verify your **GROQ_API_KEY** in the `.env` file or your Instructor profile settings.")
                        # Clear the cached service so it re-initializes with the fresh DB key on next attempt
                        st.session_state.pop("chatbot_service", None)
                        st.session_state.pop("chatbot_service_course_id", None)
                    st.stop()
        
        # We don't save to st.session_state.messages anymore because persistence is handled by the service in the DB
        st.rerun()
