"""
views/content_player.py
────────────────────────
Content reader with sidebar quiz/certificate navigation and locking logic.
"""

from __future__ import annotations
import streamlit as st
from pathlib import Path
import os

from db.database import get_db
from db.models import UserRole
from repositories.course_repo import get_course, get_lesson
from repositories.user_repo import mark_lesson_complete, get_completed_lesson_ids
from repositories import quiz_repo
from services.privacy_service import has_consented, record_consent
import auth

def _render_assets(assets, position: str) -> None:
    filtered = [a for a in assets if getattr(a, "position", "end") == position]
    if not filtered: return
    images = [a for a in filtered if a.type == "image"]
    others = [a for a in filtered if a.type != "image"]

    if images:
        st.markdown("---")
        cols = st.columns(min(3, len(images)))
        for i, asset in enumerate(images):
            with cols[i % len(cols)]:
                if asset.content.startswith("http"):
                    st.image(asset.content, use_container_width=True)
                else:
                    p = Path(asset.content)
                    if p.exists(): st.image(str(p), use_container_width=True)

    for asset in others:
        st.markdown("---")
        if asset.type == "video":
            if asset.content.startswith("http"): st.video(asset.content)
            else:
                p = Path(asset.content)
                if p.exists():
                    with open(p, "rb") as f: st.video(f.read())
        elif asset.type == "document":
            p = Path(asset.content)
            if p.exists():
                with open(p, "rb") as f:
                    st.download_button(label=f"⬇️ {asset.caption or p.name}", data=f, file_name=p.name, key=f"dl_{asset.id}")

@st.dialog("Confidentiality Terms")
def _show_consent_dialog(user_id: int) -> None:
    st.markdown("### 🛡️ Privacy & Confidentiality Commitment (LGPD/GDPR)")
    st.markdown("By clicking 'Accept Terms', your consent will be recorded for compliance purposes.")
    if st.button("✅ I Accept", type="primary", use_container_width=True):
        with get_db() as db: record_consent(db, user_id)
        st.rerun()
    if st.button("❌ Refuse"):
        st.session_state["page"] = "home"
        st.rerun()

def render() -> None:
    current_user = auth.get_current_user()
    course_id = st.session_state.get("active_course_id")
    if not course_id:
        st.error("No course selected.")
        return

    is_student = current_user and current_user["role"] == UserRole.student.value
    if is_student:
        with get_db() as db:
            if not has_consented(db, current_user["id"]):
                _show_consent_dialog(current_user["id"])
                st.stop()

    with get_db() as db:
        course_db = get_course(db, course_id)
        if not course_db: return
        
        # Student progress
        completed_ids = get_completed_lesson_ids(db, current_user["id"]) if is_student else set()
        
        # Batch Fetch Quiz Metadata and Pass Status
        quiz_meta = quiz_repo.get_course_quizzes_metadata(db, course_id)
        pass_status = quiz_repo.get_user_course_quiz_status(db, current_user["id"], course_id) if is_student else {"lessons": set(), "modules": set(), "final_passed": False}

        # Sidebar
        with st.sidebar:
            st.title(f"📚 {course_db.title}")
            st.divider()
            
            can_access = True # Simple linear progression
            
            for m in course_db.modules:
                st.markdown(f"#### {m.title}")
                
                # Check for module quiz pass if locking enabled
                mod_quiz_exists = m.id in quiz_meta["modules"]
                mod_passed = m.id in pass_status["modules"]

                for l in m.lessons:
                    l_quiz_exists = l.id in quiz_meta["lessons"]
                    l_passed = l.id in pass_status["lessons"]
                    
                    done = l.id in completed_ids
                    icon = "✅ " if done else ("🔒 " if not can_access else "📄 ")
                    
                    if st.button(f"{icon}{l.title}", key=f"l_{l.id}", use_container_width=True, disabled=not can_access):
                        st.session_state["player_lesson_id"] = l.id
                        st.rerun()
                    
                    # Show quiz if exists
                    if l_quiz_exists:
                        q_icon = "📝 " if l_passed else "🛑 "
                        if st.button(f"   {q_icon}Lesson Quiz", key=f"lq_{l.id}", use_container_width=True, disabled=not can_access):
                            st.session_state["page"] = "quiz"
                            st.session_state["quiz_scope"] = {"type": "lesson", "id": l.id}
                            st.rerun()
                    
                    # Update can_access for next item
                    if is_student:
                        # Lock depends on lesson completion AND lesson quiz pass
                        if not done or (l_quiz_exists and not l_passed):
                            can_access = False

                # Module Quiz
                if mod_quiz_exists:
                    mq_icon = "📝 " if mod_passed else "🏁 "
                    if st.button(f"{mq_icon}Module Assessment", key=f"mq_{m.id}", use_container_width=True, disabled=not can_access):
                        st.session_state["page"] = "quiz"
                        st.session_state["quiz_scope"] = {"type": "module", "id": m.id}
                        st.rerun()
                    if not mod_passed: can_access = False
                
                # Module Certificate
                if m.certificate_path and (mod_passed or not mod_quiz_exists):
                    if st.button(f"🎓 Module Certificate", key=f"mc_{m.id}", use_container_width=True, disabled=not can_access):
                        st.session_state["show_cert"] = {"type": "module", "id": m.id}
                
                st.divider()

            # Course Quiz
            c_quiz_exists = quiz_meta["has_final"]
            c_passed = pass_status["final_passed"]
            
            if c_quiz_exists:
                if st.button(f"🏆 Final Exam", key=f"cq_{course_id}", use_container_width=True, disabled=not can_access):
                    st.session_state["page"] = "quiz"
                    st.session_state["quiz_scope"] = {"type": "course", "id": course_id}
                    st.rerun()
                if not c_passed: can_access = False
            
            if course_db.certificate_path and (c_passed or not c_quiz_exists):
                if st.button("🎓 Course Certificate", key=f"cc_{course_id}", use_container_width=True, disabled=not can_access):
                    st.session_state["show_cert"] = {"type": "course", "id": course_id}

            if st.button("🏠 Home", use_container_width=True):
                st.session_state["page"] = "home"
                st.rerun()

        # Main Content Area (Moved INSIDE with get_db Block)
        if st.session_state.get("show_cert"):
            _render_cert_view(st.session_state["show_cert"]["type"], st.session_state["show_cert"]["id"])
            if st.button("Back to Lesson"):
                del st.session_state["show_cert"]
                st.rerun()
            return

        lesson_id = st.session_state.get("player_lesson_id")
        if not lesson_id:
            if course_db.modules and course_db.modules[0].lessons:
                st.session_state["player_lesson_id"] = course_db.modules[0].lessons[0].id
                st.rerun()
            else:
                st.info("No lessons.")
                return

        lesson = get_lesson(db, lesson_id)
        if not lesson: return
        st.title(lesson.title)
        _render_assets(lesson.assets, "start")
        st.divider()
        if lesson.content_markdown:
            st.markdown(lesson.content_markdown, unsafe_allow_html=True)
        _render_assets(lesson.assets, "end")
        
        if is_student:
            st.divider()
            if lesson_id in completed_ids:
                st.success("✅ Lesson Completed")
            else:
                if st.button("✔️ Mark as Complete", type="primary"):
                    mark_lesson_complete(db, current_user["id"], lesson_id)
                    st.rerun()

def _render_cert_view(scope_type: str, scope_id: int):
    st.header("Your Certificate")
    
    with get_db() as db:
        if scope_type == "module":
            from db.models import Module
            target = db.query(Module).filter(Module.id == scope_id).first()
        else:
            from db.models import Course
            target = db.query(Course).filter(Course.id == scope_id).first()
        
        if not target or not target.certificate_path:
            st.error("Certificate not found.")
            return
        
        cert_path = Path(target.certificate_path)
        if not cert_path.exists():
            st.error("The certificate file is missing on the server.")
            return

        # Display preview if it's an image
        if cert_path.suffix.lower() in [".png", ".jpg", ".jpeg"]:
            st.image(str(cert_path), use_container_width=True)
        else:
            st.info(f"Certificate available for download: {cert_path.name}")
        
        with open(cert_path, "rb") as f:
            st.download_button("📥 Download Certificate", f, file_name=cert_path.name)
