"""
views/admin_dashboard.py
─────────────────────────
Hierarchical Admin Panel:
- System Admin: Full CRUD for all roles including other Admins. Access to all tabs.
- General Admin: Metrics only. CRUD only for Instructor/Student roles.
- Privacy Admin: Privacy Audit (Decrypted). CRUD only for Instructor/Student roles.
"""

from __future__ import annotations
import streamlit as st
import pandas as pd
from datetime import datetime

from db.database import get_db
from db.models import UserRole, Course
from repositories.user_repo import (
    list_users, create_user, update_user, delete_user,
    log_audit, list_audit_logs, list_chatbot_history,
    get_decrypted_groq_key
)
from repositories.course_repo import list_courses, enroll_student, unenroll_student
from services.security_service import encryption_manager
from services.email_service import send_welcome_email
import auth


def render() -> None:
    current_user = auth.get_current_user()
    allowed_roles = (UserRole.system_admin.value, UserRole.general_admin.value, UserRole.privacy_admin.value)
    if not current_user or current_user["role"] not in allowed_roles:
        st.error("🚫 Access denied. Administrators only.")
        return

    role = current_user["role"]
    is_system_admin = role == UserRole.system_admin.value
    is_privacy_admin = role == UserRole.privacy_admin.value

    st.title("🛡️ Admin Dashboard")
    
    # Hierarchical Tabs
    tab_list = ["👥 Users", "📋 Audit Logs", "🔌 Enrollments"]
    
    # Privacy access: System and Privacy admins see decrypted logs.
    if is_system_admin or is_privacy_admin:
        tab_list.insert(1, "🔐 Privacy Audit")
    else:
        tab_list.insert(1, "📊 Privacy Metrics")
        
    tabs = st.tabs(tab_list)

    # ── Tab: Users ──────────────────────────────────────────────────────────────
    with tabs[0]:
        _render_users_tab(current_user, is_system_admin)

    # ── Tab: Privacy Audit / Metrics ───────────────────────────────────────────
    if is_system_admin or is_privacy_admin:
        with tabs[1]:
            _render_privacy_audit_tab(current_user)
    else:
        with tabs[1]:
            _render_privacy_metrics_tab()

    # ── Tab: Audit Logs ─────────────────────────────────────────────────────────
    with tabs[2]:
        _render_audit_logs_tab()

    # ── Tab: Enrollments ────────────────────────────────────────────────────────
    with tabs[3]:
        _render_enrollments_tab(current_user)


def _render_users_tab(admin_user: dict, is_system_admin: bool) -> None:
    st.subheader("Manage Users")
    with get_db() as db:
        all_users = list_users(db)
        
        # Hierarchical filtering: Non-system admins cannot see or manage other admins
        admin_roles = (UserRole.system_admin, UserRole.general_admin, UserRole.privacy_admin)
        if is_system_admin:
            visible_users = all_users
        else:
            visible_users = [u for u in all_users if u.user_role not in admin_roles]

        if visible_users:
            df = pd.DataFrame([{
                "ID": u.id,
                "Username": u.username,
                "Email": u.email,
                "Role": u.user_role.value,
                "Key?": "✅" if u.groq_key_encrypted else "❌"
            } for u in visible_users])
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No users found within your permission scope.")
        
        st.markdown("---")
        
        # ── Create New User ──
        with st.expander("➕ Create New User"):
            with st.form("create_user_form"):
                col1, col2 = st.columns(2)
                with col1:
                    new_username = st.text_input("Username", autocomplete="username")
                    new_email = st.text_input("Email", autocomplete="email")
                with col2:
                    new_password = st.text_input("Password", type="password", autocomplete="new-password")
                    
                    # Role selection based on tier
                    if is_system_admin:
                        role_options = [r.value for r in UserRole]
                    else:
                        role_options = [UserRole.instructor.value, UserRole.student.value]
                        
                    new_role = st.selectbox("Role", options=role_options)
                    new_groq_key = st.text_input("Groq API Key (Optional)", type="password", help="Personal key for instructors.")
                
                submitted = st.form_submit_button("Create User", type="primary")
                if submitted:
                    if not all([new_username, new_email, new_password]):
                        st.error("Fields required.")
                    else:
                        try:
                            with get_db() as wdb:
                                create_user(wdb, new_username, new_email, new_password, role=UserRole(new_role), groq_key=new_groq_key or None)
                                log_audit(wdb, "INSERT", user_id=admin_user["id"], table_name="users", details=f"Created {new_role} {new_username}")
                            st.success("User created.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

        # ── Edit / Delete User ──
        with st.expander("✏️ Edit or Delete User"):
            if not visible_users:
                st.info("No users to manage.")
            else:
                user_map = {f"{u.username} ({u.user_role.value})": u for u in visible_users if u.id != admin_user["id"]}
                if not user_map:
                    st.info("No other users to manage.")
                else:
                    target_label = st.selectbox("Select User", options=list(user_map.keys()))
                    target_user = user_map[target_label]

                    with st.form(f"edit_user_{target_user.id}"):
                        col1, col2 = st.columns(2)
                        with col1:
                            edit_username = st.text_input("Username", value=target_user.username, autocomplete="username")
                            edit_email = st.text_input("Email", value=target_user.email, autocomplete="email")
                        with col2:
                            edit_password = st.text_input("New Password (blank to keep)", type="password", autocomplete="new-password")
                            
                            if is_system_admin:
                                edit_role_options = [r.value for r in UserRole]
                            else:
                                edit_role_options = [UserRole.instructor.value, UserRole.student.value]
                            
                            # Handle index for role
                            try:
                                current_role_idx = edit_role_options.index(target_user.user_role.value)
                            except ValueError:
                                current_role_idx = 0

                            edit_role = st.selectbox("Role", options=edit_role_options, index=current_role_idx)
                            
                            current_key = get_decrypted_groq_key(target_user) or ""
                            edit_groq_key = st.text_input("Personal Groq API Key", value=current_key, type="password")

                        col_save, col_del = st.columns(2)
                        if col_save.form_submit_button("💾 Save", use_container_width=True, type="primary"):
                            with get_db() as wdb:
                                update_user(wdb, target_user.id, username=edit_username, email=edit_email, password=edit_password or None, role=UserRole(edit_role), groq_key=edit_groq_key)
                                log_audit(wdb, "UPDATE", user_id=admin_user["id"], target_user_id=target_user.id, table_name="users", details=f"Updated to {edit_role}")
                            st.success("User updated.")
                            st.rerun()
                        
                        if col_del.form_submit_button("🗑️ Delete", use_container_width=True):
                            with get_db() as wdb:
                                delete_user(wdb, target_user.id)
                                log_audit(wdb, "DELETE", user_id=admin_user["id"], target_user_id=target_user.id, table_name="users")
                            st.success("User deleted.")
                            st.rerun()




def _render_privacy_audit_tab(admin_user: dict) -> None:
    st.subheader("🔐 Privacy Audit (Decrypted Logs)")
    st.warning("⚠️ Accessing these logs is a sensitive action and will be audited.")
    
    justification = st.text_input("Justification for Access", placeholder="e.g., Investigation of ethical violation reported by user.")
    
    if st.button("Unlock and View Logs", type="primary", disabled=not justification):
        with get_db() as db:
            log_audit(db, "VIEW_SENSITIVE_DATA", user_id=admin_user["id"], details=f"Justification: {justification}")
            history = list_chatbot_history(db)
            
            if not history:
                st.info("No chat interactions found.")
            else:
                data = []
                for h in history:
                    try:
                        msg = encryption_manager.decrypt(h.message_content)
                        res = encryption_manager.decrypt(h.bot_response)
                        data.append({
                            "Timestamp": h.created_at.strftime("%Y-%m-%d %H:%M"),
                            "User ID": h.user_id,
                            "Message": msg,
                            "Response": res
                        })
                    except:
                        data.append({"Timestamp": h.created_at, "User ID": h.user_id, "Message": "[Decryption Error]", "Response": "[Decryption Error]"})
                
                st.dataframe(pd.DataFrame(data), use_container_width=True)


def _render_privacy_metrics_tab() -> None:
    st.subheader("📊 Privacy Metrics (Aggregated)")
    with get_db() as db:
        history = list_chatbot_history(db)
        if not history:
            st.info("No data yet.")
            return
        col1, col2 = st.columns(2)
        col1.metric("Total Interactions", len(history))
        col2.metric("Unique Students", len(set(h.user_id for h in history)))


def _render_audit_logs_tab() -> None:
    st.subheader("📋 System Audit Logs")
    with get_db() as db:
        logs = list_audit_logs(db)
        if logs:
            data = [{
                "Time": l.timestamp.strftime("%Y-%m-%d %H:%M"),
                "Actor": l.actor.username if l.actor else "System",
                "Action": l.action,
                "Details": l.details
            } for l in logs]
            st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)


def _render_enrollments_tab(admin_user: dict) -> None:
    st.subheader("🔌 Course Enrollments")
    with get_db() as db:
        all_students = [u for u in list_users(db) if u.user_role == UserRole.student]
        all_courses = list_courses(db)
        
        if not all_students or not all_courses:
            st.info("Need both students and courses to manage enrollments.")
            return
            
        col1, col2 = st.columns(2)
        with col1:
            student_opts = {f"{u.username} ({u.email})": u.id for u in all_students}
            sel_student_id = student_opts[st.selectbox("Student", options=list(student_opts.keys()))]
        with col2:
            course_opts = {c.title: c.id for c in all_courses}
            sel_course_id = course_opts[st.selectbox("Course", options=list(course_opts.keys()))]
            
        if st.button("➕ Enroll", type="primary", use_container_width=True):
            enroll_student(db, sel_student_id, sel_course_id)
            log_audit(db, "INSERT", user_id=admin_user["id"], target_user_id=sel_student_id, table_name="enrollments", details=f"Enrolled in {sel_course_id}")
            st.success("Enrolled.")
            st.rerun()
