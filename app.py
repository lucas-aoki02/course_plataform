"""
app.py
──────
Streamlit entry point for the AI Course Platform.

Responsibilities
----------------
1. Configure page-wide Streamlit settings (layout, title, favicon).
2. Call `init_db()` once on startup to ensure all tables exist.
3. Check for a valid API key and show a setup guide if missing.
4. Render the top navigation bar.
5. Route to the correct view based on `st.session_state["page"]`.

Navigation model
----------------
All page transitions happen by setting `st.session_state["page"]`
and calling `st.rerun()`. This avoids Streamlit's multi-page file
convention and keeps all routing in one place.

Run
---
    python -m streamlit run app.py
"""

import streamlit as st

# ── Page config (MUST be the first Streamlit call) ────────────────────────────
st.set_page_config(
    page_title="AI Course Platform",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="auto",
    menu_items={
        "About": "AI Course Platform — Built with Streamlit",
    },
)

# ── Imports after page config ─────────────────────────────────────────────────
import config
from db.database import init_db
from views import chatbot_view, content_player, course_creator, home, quiz_view


# ── One-time DB initialisation ────────────────────────────────────────────────
@st.cache_resource
def _startup() -> None:
    """
    Run once per Streamlit server process (not per rerun).

    `@st.cache_resource` ensures this executes only on cold start,
    not on every user interaction or page rerun.
    """
    init_db()


_startup()


# ── Provider Health Check ─────────────────────────────────────────────────────
def _check_providers() -> bool:
    """
    Check if at least one LLM provider is available.

    Primary: Ollama (Llama 3.2) — must be running locally.
    Optional: Gemini API key (fallback), OpenAI API key (last resort).

    Returns True if the app can function. Shows warnings for missing fallbacks.
    """
    import httpx

    # Check Ollama (required)
    ollama_ok = False
    try:
        with httpx.Client(timeout=5) as client:
            resp = client.get(f"{config.OLLAMA_BASE_URL}/api/tags")
            resp.raise_for_status()
            models = [m["name"] for m in resp.json().get("models", [])]
            ollama_ok = any(config.OLLAMA_MODEL in m for m in models)
    except Exception:
        pass

    if ollama_ok:
        # Ollama is running — app works
        if not config.GEMINI_API_KEY:
            st.info(
                "ℹ️ **Running on local Llama 3.2 only.** "
                "Add a Gemini API key to `.env` for fallback resilience."
            )
        return True

    # Ollama not available — check fallbacks
    if config.GEMINI_API_KEY or config.OPENAI_API_KEY:
        st.warning(
            "⚠️ **Ollama not detected.** Using cloud LLM fallbacks.\n\n"
            "Start Ollama for the best experience: `ollama serve`"
        )
        return True

    # No provider available
    st.error("⚠️ **No LLM provider available.**")
    st.markdown(
        """
        ### Setup Instructions

        **Option A — Local Llama (recommended, free, unlimited):**
        1. Install Ollama: https://ollama.ai
        2. Pull the model: `ollama pull llama3.2`
        3. Start the server: `ollama serve`
        4. Restart this app.

        **Option B — Cloud API key (fallback):**
        1. Get a Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey).
        2. Add to `.env`: `GEMINI_API_KEY=your_key_here`
        3. Restart this app.
        """
    )
    return False


# ── Session State Defaults ────────────────────────────────────────────────────
if "page" not in st.session_state:
    st.session_state["page"] = "home"
if "active_course_id" not in st.session_state:
    st.session_state["active_course_id"] = None


# ── Top Navigation Bar ────────────────────────────────────────────────────────
def _render_navbar() -> None:
    """
    Render a horizontal navigation bar at the top of every page.

    Uses CSS injection to style navigation buttons as tab-like links.
    Non-active tabs are muted; the active tab is highlighted in indigo.
    """
    current_page = st.session_state["page"]

    nav_items = {
        "home": "🏠 Home",
        "create": "✨ Create Course",
    }

    # Add contextual nav items when a course is active
    course_id = st.session_state.get("active_course_id")
    if course_id:
        nav_items["player"] = "📖 Course Content"
        nav_items["quiz"] = "📝 Quiz"
        nav_items["chatbot"] = "🤖 AI Tutor"

    cols = st.columns(len(nav_items) + 2)  # +2 for spacing
    for i, (page_key, label) in enumerate(nav_items.items()):
        with cols[i]:
            is_active = current_page == page_key
            btn_type = "primary" if is_active else "secondary"
            if st.button(label, key=f"nav_{page_key}", type=btn_type, use_container_width=True):
                if page_key != current_page:
                    st.session_state["page"] = page_key
                    st.rerun()

    st.markdown("---")


# ── Main Router ───────────────────────────────────────────────────────────────
def main() -> None:
    """
    Main application entry point.

    Renders the navbar and delegates to the appropriate view module
    based on the current page in session state.
    """
    if not _check_providers():
        return

    _render_navbar()

    page = st.session_state["page"]

    if page == "home":
        home.render()
    elif page == "create":
        course_creator.render()
    elif page == "player":
        content_player.render()
    elif page == "quiz":
        quiz_view.render()
    elif page == "chatbot":
        chatbot_view.render()
    else:
        st.error(f"Unknown page: '{page}'")
        st.session_state["page"] = "home"
        st.rerun()


if __name__ == "__main__" or True:
    main()
