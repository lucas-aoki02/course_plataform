"""
app.py
──────
Streamlit entry point — Role-based routing.
"""

import streamlit as st

st.set_page_config(
    page_title="WOCOTM Academy",
    page_icon="🎓",
    layout="wide",
)

st.markdown("""
<style>
/* Style secondary buttons to use the requested Blue (48, 63, 159) */
button[kind="secondary"] {
    background-color: rgb(48, 63, 159) !important;
    color: white !important;
    border-color: rgb(48, 63, 159) !important;
}
button[kind="secondary"]:hover, button[kind="secondary"]:focus, button[kind="secondary"]:active {
    background-color: rgb(38, 51, 133) !important; /* Slightly darker on hover */
    color: white !important;
    border-color: rgb(38, 51, 133) !important;
}
</style>
""", unsafe_allow_html=True)

import config
from db.database import init_db
import auth
from db.models import UserRole


@st.cache_resource
def _startup() -> None:
    init_db()


_startup()


def _render_navbar() -> None:
    current_user = auth.get_current_user()
    role = current_user["role"] if current_user else None
    current_page = st.session_state.get("page", "home")

    nav_items: dict[str, str] = {}

    if role == UserRole.admin.value:
        nav_items["admin"] = "🛡️ Admin"
        nav_items["instructor"] = "👨‍🏫 Instructor"
        nav_items["create"] = "✨ Create Course"

    elif role == UserRole.instructor.value:
        nav_items["instructor"] = "👨‍🏫 My Dashboard"
        nav_items["create"] = "✨ Create Course"

    # All authenticated roles can see content if a course is active
    nav_items["home"] = "🏠 Home"
    course_id = st.session_state.get("active_course_id")
    if course_id:
        nav_items["player"] = "📖 Content"
        nav_items["quiz"] = "📝 Quiz"
        nav_items["chatbot"] = "🤖 Tutor"

    cols = st.columns(len(nav_items) + 1)
    for i, (page_key, label) in enumerate(nav_items.items()):
        with cols[i]:
            if st.button(
                label,
                key=f"nav_{page_key}",
                type="primary" if current_page == page_key else "secondary",
                use_container_width=True,
            ):
                st.session_state["page"] = page_key
                st.rerun()

    # Logout button in last column
    with cols[len(nav_items)]:
        if st.button("🚪 Logout", use_container_width=True):
            auth.logout()
            st.rerun()

    st.markdown("---")


def main() -> None:
    # ── Auth Gate ──────────────────────────────────────────────────────────────
    if not auth.is_logged_in():
        auth.render_login_page()
        return

    current_user = auth.get_current_user()
    role = current_user["role"]
    page = st.session_state.get("page", "home")

    # Redirect after login to role-appropriate default page
    if page == "login":
        if role == UserRole.admin.value:
            st.session_state["page"] = "admin"
        elif role == UserRole.instructor.value:
            st.session_state["page"] = "instructor"
        else:
            st.session_state["page"] = "home"
        st.rerun()

    _render_navbar()

    # ── Role-gated Routing ─────────────────────────────────────────────────────
    from views import chatbot_view, content_player, course_creator, home, quiz_view
    from views.admin_dashboard import render as admin_render
    from views.instructor_dashboard import render as instructor_render

    if page == "home":
        home.render()
    elif page == "admin":
        admin_render()
    elif page == "instructor":
        instructor_render()
    elif page == "create":
        if role in (UserRole.admin.value, UserRole.instructor.value):
            course_creator.render()
        else:
            st.error("🚫 Only Instructors and Admins can create courses.")
    elif page == "player":
        content_player.render()
    elif page == "quiz":
        quiz_view.render()
    elif page == "chatbot":
        chatbot_view.render()
    else:
        st.session_state["page"] = "home"
        st.rerun()


if __name__ == "__main__":
    main()
