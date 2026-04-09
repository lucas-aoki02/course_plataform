"""
views/admin_dashboard.py
─────────────────────────
Admin panel: full User CRUD, Groq key management, Audit Log viewer.
Only accessible to users with role=Admin.
Login ADMIN:

user: admin@platform.com
pswd: admin123

"""

from __future__ import annotations
import streamlit as st
import pandas as pd

from db.database import get_db
from db.models import UserRole
from repositories.user_repo import (
    list_users, create_user, update_user, delete_user,
    log_audit, list_audit_logs, get_decrypted_groq_key,
)
from services.email_service import send_welcome_email
import auth


def render() -> None:
    user = auth.get_current_user()
    if not user or user["role"] != UserRole.admin.value:
        st.error("🚫 Access denied. Admins only.")
        return

    st.title("🛡️ Admin Dashboard")
    tab_users, tab_keys, tab_logs = st.tabs(["👥 Users", "🔑 API Keys", "📋 Audit Logs"])

    # ── Tab: Users ──────────────────────────────────────────────────────────────
    with tab_users:
        st.subheader("Manage Users")

        with get_db() as db:
            users = list_users(db)

            if users:
                df = pd.DataFrame([
                    {
                        "ID": u.id,
                        "Username": u.username,
                        "Email": u.email,
                        "Role": u.role.value,
                        "Has Groq Key": "✅" if u.groq_key_encrypted else "—",
                    }
                    for u in users
                ])
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("No users found.")

        st.markdown("---")

        # Create New User
        with st.expander("➕ Create New User", expanded=False):
            with st.form("create_user_form"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    new_username = st.text_input("Username")
                    new_email = st.text_input("Email")
                with col2:
                    new_password = st.text_input("Password", type="password")
                    new_role = st.selectbox(
                        "Role",
                        options=[UserRole.instructor.value, UserRole.student.value],
                    )
                with col3:
                    st.caption("Advanced (Instructor only)")
                    new_groq_key = st.text_input("Groq API Key (Optional)", type="password", key="create_new_groq")
                submitted = st.form_submit_button("Create User", type="primary")

            if submitted:
                if not all([new_username, new_email, new_password]):
                    st.error("All fields are required.")
                else:
                    role_enum = UserRole(new_role)
                    with get_db() as db:
                        try:
                            # Only pass the groq key if role is instructor
                            final_key = new_groq_key if new_role == UserRole.instructor.value else None
                            new_user = create_user(
                                db, new_username, new_email, new_password, role=role_enum, groq_key=final_key
                            )
                            log_audit(
                                db, action="INSERT",
                                user_id=user["id"],
                                target_user_id=new_user.id,
                                table_name="users",
                                details=f"Created {new_role} '{new_username}'"
                            )
                        except Exception as e:
                            st.error(f"Failed to create user: {e}")
                        else:
                            st.success(f"User **{new_username}** created successfully!")
                            sent = send_welcome_email(new_email, new_username, new_password, new_role)
                            if sent:
                                st.info(f"📧 Welcome email sent to {new_email}")
                            else:
                                st.warning("Welcome email could not be sent (check SMTP config).")
                            st.rerun()

        # Edit / Delete User
        with st.expander("✏️ Edit or Delete User", expanded=False):
            with get_db() as db:
                users = list_users(db)
                user_options = {f"{u.username} ({u.email})": u.id for u in users if u.id != user["id"]}

                if not user_options:
                    st.info("No other users to manage.")
                else:
                    selected_label = st.selectbox("Select User", options=list(user_options.keys()), key="edit_user_sel")
                    selected_id = user_options[selected_label]

                    sel_user = next((u for u in users if u.id == selected_id), None)

                    if sel_user:
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            edit_username = st.text_input("New Username", value=sel_user.username, key="edit_uname")
                            edit_email = st.text_input("New Email", value=sel_user.email, key="edit_email")
                        with col2:
                            edit_role = st.selectbox(
                                "Role",
                                options=[r.value for r in UserRole],
                                index=[r.value for r in UserRole].index(sel_user.role.value),
                                key="edit_role",
                            )
                            edit_password = st.text_input("New Password (leave blank to keep)", type="password", key="edit_pass")
                        with col3:
                            edit_groq_key = st.text_input("New Groq API Key (leave blank to keep)", type="password", key="edit_groq_key")

                        col_save, col_del = st.columns(2)
                        with col_save:
                            if st.button("💾 Save Changes", use_container_width=True, type="primary"):
                                update_user(
                                    db, selected_id,
                                    username=edit_username or None,
                                    email=edit_email or None,
                                    password=edit_password or None,
                                    role=UserRole(edit_role),
                                    groq_key=edit_groq_key or None,
                                )
                                log_audit(db, "UPDATE", user_id=user["id"],
                                          target_user_id=selected_id, table_name="users",
                                          details=f"Updated user ID {selected_id} (Role: {edit_role})")
                                st.success("User updated.")
                                st.rerun()
                        with col_del:
                            if st.button("🗑️ Delete User", use_container_width=True):
                                log_audit(db, "DELETE", user_id=user["id"],
                                          target_user_id=None, table_name="users",
                                          details=f"Deleted user ID {selected_id}")
                                delete_user(db, selected_id)
                                st.success("User deleted.")
                                st.rerun()

    # ── Tab: API Keys ───────────────────────────────────────────────────────────
    with tab_keys:
        st.subheader("🔑 Instructor Groq API Keys")
        st.caption("Set or update the Groq API key for each Instructor.")

        with get_db() as db:
            instructors = [u for u in list_users(db) if u.role == UserRole.instructor]

            if not instructors:
                st.info("No Instructors found.")
            else:
                for instr in instructors:
                    with st.expander(f"**{instr.username}** ({instr.email})"):
                        has_key = bool(instr.groq_key_encrypted)
                        st.markdown(f"Current key: {'✅ Set' if has_key else '❌ Not set'}")
                        new_key = st.text_input(
                            "Groq API Key",
                            type="password",
                            placeholder="gsk_...",
                            key=f"groq_key_{instr.id}",
                        )
                        if st.button("Save Key", key=f"save_key_{instr.id}", type="primary"):
                            if new_key:
                                update_user(db, instr.id, groq_key=new_key)
                                log_audit(db, "UPDATE", user_id=user["id"],
                                          target_user_id=instr.id, table_name="users",
                                          details="API Key reset via Instructor list")
                                st.success(f"Key saved for {instr.username}.")
                            else:
                                st.warning("Key cannot be empty.")

    # ── Tab: Audit Logs ─────────────────────────────────────────────────────────
    with tab_logs:
        st.subheader("📋 Audit Logs")

        with get_db() as db:
            logs = list_audit_logs(db, limit=200)

            if logs:
                log_data = []
                for log in logs:
                    actor = log.actor.username if log.actor else "System"
                    target = log.target.username if log.target else "—"
                    log_data.append({
                        "Timestamp": log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                        "Actor": actor,
                        "Action": log.action,
                        "Details": log.details or "—",
                        "Target User": target,
                        "Table": log.table_name or "—",
                    })
                st.dataframe(pd.DataFrame(log_data), use_container_width=True, hide_index=True)
            else:
                st.info("No audit logs yet.")
