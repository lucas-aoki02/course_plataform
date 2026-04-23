"""
auth.py
───────
Authentication utilities for Streamlit.
Manages login state via st.session_state.
"""

from __future__ import annotations
import streamlit as st

from db.database import get_db
from db.models import UserRole
from repositories.user_repo import (
    get_user_by_email,
    log_audit,
)
from services.security_service import verify_password


# Keys persisted in session_state
SESSION_USER_KEY = "auth_user"


def get_current_user() -> dict | None:
    """Return the currently logged-in user dict, or None."""
    return st.session_state.get(SESSION_USER_KEY)


def is_logged_in() -> bool:
    return get_current_user() is not None


def get_role() -> str | None:
    user = get_current_user()
    return user["role"] if user else None


def require_role(*roles: UserRole) -> bool:
    """Return True if logged-in user has one of the required roles."""
    role = get_role()
    return any(role == r.value for r in roles)


def login(email: str, password: str) -> tuple[bool, str]:
    """
    Attempt to log in a user.
    Returns (success: bool, message: str).
    """
    with get_db() as db:
        user = get_user_by_email(db, email)
        if not user:
            return False, "Invalid email or password."
        if not verify_password(password, user.password_hash):
            return False, "Invalid email or password."

        st.session_state[SESSION_USER_KEY] = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.user_role.value,
        }
        log_audit(db, action="LOGIN", user_id=user.id, table_name="users")
        return True, f"Welcome, {user.username}!"


def logout() -> None:
    user = get_current_user()
    if user:
        from repositories.user_repo import clear_chatbot_history
        with get_db() as db:
            clear_chatbot_history(db, user["id"])
            log_audit(db, "LOGOUT", user_id=user["id"], details="Chat history cleared on logout.")
            db.commit()

    st.session_state.pop(SESSION_USER_KEY, None)
    st.session_state["page"] = "login"


def render_login_page() -> None:
    """Render the login form."""
    st.markdown(
        """
        <div style='text-align:center; padding: 48px 0 24px;'>
            <h1 style='font-size:2.5rem; color:#4F46E5;'>🎓 WOCOTM Academy</h1>
            <p style='color:#888;'>Sign in to continue</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            email = st.text_input("Email", placeholder="you@example.com", autocomplete="email")
            password = st.text_input("Password", type="password", autocomplete="current-password")
            submitted = st.form_submit_button("Sign In", use_container_width=True, type="primary")

        if submitted:
            if not email or not password:
                st.error("Please fill in both fields.")
            else:
                ok, msg = login(email, password)
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
