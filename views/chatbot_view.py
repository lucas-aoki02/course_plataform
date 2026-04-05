"""
views/chatbot_view.py
──────────────────────
Lite AI Tutor: simple chat interface using Groq.
"""

from __future__ import annotations
import streamlit as st
from services.ai_service import llama_service
from services.content_service import get_full_content_as_text

def render() -> None:
    course_id = st.session_state.get("active_course_id")
    if not course_id:
        st.error("Select a course first.")
        return

    st.markdown("### 🤖 AI Tutor (Groq Powered)")
    st.caption("Ask anything about the entire course.")

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("Ask your tutor..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("⚡ Thinking..."):
                # Get full course context for the tutor (truncated to fit Groq 6000 TPM limit)
                context = get_full_content_as_text(course_id)
                if len(context) > 12000:
                    context = context[:12000] + "\n\n...[Content Truncated to fit AI memory limits]..."
                
                system = f"You are an AI Tutor. Use the course content below to answer: \n\n{context}"
                
                # Streaming response
                response_placeholder = st.empty()
                full_response = ""
                for chunk in llama_service.generate_stream(prompt, system=system):
                    full_response += chunk
                    response_placeholder.markdown(full_response + "▌")
                response_placeholder.markdown(full_response)
                
        st.session_state.messages.append({"role": "assistant", "content": full_response})
