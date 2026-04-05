"""
app.py
──────
Streamlit entry point — Powered by Groq.
"""

import streamlit as st

st.set_page_config(
    page_title="AI Course Platform",
    page_icon="🎓",
    layout="wide",
)

import config
from db.database import init_db
from views import chatbot_view, content_player, course_creator, home, quiz_view

@st.cache_resource
def _startup() -> None:
    init_db()

_startup()

def _check_providers() -> bool:
    if config.GROQ_API_KEY:
        return True
    
    st.error("⚠️ **Groq API Key Missing**")
    st.markdown("""
    Please add your Groq API key to the `.env` file:
    `GROQ_API_KEY=your_key_here`
    
    Get one at [Groq Console](https://console.groq.com/keys).
    """)
    return False

if "page" not in st.session_state:
    st.session_state["page"] = "home"
if "active_course_id" not in st.session_state:
    st.session_state["active_course_id"] = None

def _render_navbar() -> None:
    current_page = st.session_state["page"]
    nav_items = {"home": "🏠 Home", "create": "✨ Create Course"}
    
    course_id = st.session_state.get("active_course_id")
    if course_id:
        nav_items["player"] = "📖 Content"
        nav_items["quiz"] = "📝 Quiz"
        nav_items["chatbot"] = "🤖 Tutor"

    cols = st.columns(len(nav_items) + 1)
    for i, (page_key, label) in enumerate(nav_items.items()):
        with cols[i]:
            if st.button(label, key=f"nav_{page_key}", 
                         type="primary" if current_page == page_key else "secondary",
                         use_container_width=True):
                st.session_state["page"] = page_key
                st.rerun()
    st.markdown("---")

def main() -> None:
    if not _check_providers(): return
    _render_navbar()
    page = st.session_state["page"]
    
    if page == "home": home.render()
    elif page == "create": course_creator.render()
    elif page == "player": content_player.render()
    elif page == "quiz": quiz_view.render()
    elif page == "chatbot": chatbot_view.render()
    else:
        st.session_state["page"] = "home"
        st.rerun()

if __name__ == "__main__":
    main()
