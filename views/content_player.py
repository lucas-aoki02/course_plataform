"""
views/content_player.py
────────────────────────
Content reader for the AI Course Platform.
Features:
- Sidebar lesson navigation with completion badges
- Lesson content rendering with media assets (images in columns gallery, videos inline)
- Student progress tracking (mark lesson as complete)
"""

from __future__ import annotations
import streamlit as st
from pathlib import Path

from db.database import get_db
from db.models import UserRole
from repositories.course_repo import get_course, get_lesson
from repositories.user_repo import mark_lesson_complete, get_completed_lesson_ids
import auth


def _render_assets(assets, position: str) -> None:
    """Render lesson assets at the given position (start | end)."""
    filtered = [a for a in assets if getattr(a, "position", "end") == position]
    if not filtered:
        return

    images = [a for a in filtered if a.type == "image"]
    others = [a for a in filtered if a.type != "image"]

    # ── Image Gallery (columns grid) ──────────────────────────────────────────
    if images:
        st.markdown("---")
        num_cols = min(3, len(images))
        cols = st.columns(num_cols)
        for i, asset in enumerate(images):
            with cols[i % num_cols]:
                img_path = asset.content
                # Support both file-system paths and URLs
                if img_path.startswith("http"):
                    st.image(img_path, use_container_width=True)
                else:
                    p = Path(img_path)
                    if p.exists():
                        st.image(str(p), use_container_width=True)
                    else:
                        st.warning("Image not found.")

    # ── Other Assets (video, document) ────────────────────────────────────────
    for asset in others:
        st.markdown("---")
        if asset.type == "video":
            p = Path(asset.content)
            if p.exists():
                with open(p, "rb") as f:
                    st.video(f.read())
            elif asset.content.startswith("http"):
                st.video(asset.content)
            else:
                st.warning("Video not found.")
        elif asset.type == "document":
            p = Path(asset.content)
            if p.exists():
                with open(p, "rb") as f:
                    st.download_button(
                        label=f"⬇️ Download {asset.caption or p.name}",
                        data=f,
                        file_name=p.name,
                        key=f"dl_{asset.id}",
                    )
            else:
                st.warning("Document not found.")


def render() -> None:
    current_user = auth.get_current_user()
    course_id = st.session_state.get("active_course_id")
    if not course_id:
        st.error("No course selected.")
        return

    with get_db() as db:
        course_db = get_course(db, course_id)
        if not course_db:
            st.error("Course not found.")
            return
            
        course = {"title": course_db.title, "modules": []}
        for m in course_db.modules:
            course["modules"].append({
                "title": m.title,
                "lessons": [{"id": l.id, "title": l.title} for l in m.lessons]
            })

    # Load completed lessons for current student
    is_student = current_user and current_user["role"] == UserRole.student.value
    completed_ids: set[int] = set()
    if is_student:
        with get_db() as db:
            completed_ids = get_completed_lesson_ids(db, current_user["id"])

    # ── Sidebar Navigation ───────────────────────────────────────────────────
    with st.sidebar:
        st.markdown(f"### 📚 {course['title']}")
        st.markdown("---")
        for module in course['modules']:
            st.markdown(f"**{module['title']}**")
            for lesson_info in module['lessons']:
                done = lesson_info['id'] in completed_ids
                label = f"{'✅ ' if done else ''}{lesson_info['title']}"
                if st.button(label, key=f"nav_{lesson_info['id']}", use_container_width=True):
                    st.session_state["player_lesson_id"] = lesson_info['id']
                    st.rerun()
        st.markdown("---")
        if st.button("🏠 Home", use_container_width=True):
            st.session_state["page"] = "home"
            st.rerun()

    # ── Main Content Area ─────────────────────────────────────────────────────
    lesson_id = st.session_state.get("player_lesson_id")
    if not lesson_id:
        if course['modules'] and course['modules'][0]['lessons']:
            st.session_state["player_lesson_id"] = course['modules'][0]['lessons'][0]['id']
            st.rerun()
        else:
            st.info("No lessons found.")
            return

    class MockAsset:
        def __init__(self, a):
            self.id = a.id
            self.type = a.type
            self.content = a.content
            self.caption = a.caption
            self.position = a.position

    class MockLesson:
        def __init__(self, obj):
            self.id = obj.id
            self.title = obj.title
            self.content_markdown = obj.content_markdown
            self.assets = [MockAsset(a) for a in obj.assets]

    with get_db() as db:
        lesson_db = get_lesson(db, lesson_id)
        if not lesson_db:
            st.error("Lesson not found.")
            return
        lesson = MockLesson(lesson_db)

    st.markdown(f"## {lesson.title}")

    # Assets at start position
    _render_assets(lesson.assets, position="start")

    st.markdown("---")

    if lesson.content_markdown:
        st.markdown(lesson.content_markdown, unsafe_allow_html=True)
    else:
        st.info("Content still generating for this lesson...")

    # Assets at end position (gallery)
    _render_assets(lesson.assets, position="end")

    # ── Lesson Completion (Students only) ─────────────────────────────────────
    if is_student:
        st.markdown("---")
        if lesson_id in completed_ids:
            st.success("✅ You have completed this lesson.")
        else:
            if st.button("✔️ Mark as Complete", type="primary"):
                with get_db() as db:
                    mark_lesson_complete(db, current_user["id"], lesson_id)
                st.success("Lesson marked as complete!")
                st.rerun()
