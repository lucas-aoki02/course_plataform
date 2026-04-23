"""
views/course_creator.py
────────────────────────
3-step course creation wizard — Powered by Groq (Llama 3 8B).
"""

from __future__ import annotations
import streamlit as st
from pathlib import Path
import uuid
import config
from db.database import get_db
from repositories.course_repo import (
    get_course, update_lesson_content, add_lesson_asset, delete_lesson_asset,
    update_course_quiz_settings, update_module_quiz_settings, update_lesson_quiz_settings,
    update_course_certificate, update_module_certificate
)
from services.quiz_service import generate_quiz_draft, save_quiz_draft
from services.syllabus_service import (
    generate_and_save_syllabus,
    save_syllabus,
)
import repositories.quiz_repo as quiz_repo
import auth

def _init_state() -> None:
    """Initialise session state keys on first render (idempotent)."""
    defaults = {
        "creator_step": 1,
        "creator_syllabus": None,
        "creator_course_id": None,
        "creator_course_title": "",
        "creator_quiz_done": False,
        "creator_selected_lesson_idx": 0,
        "creator_lesson_data": {}, 
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

def _reset_creator() -> None:
    keys_to_clear = [k for k in st.session_state if k.startswith("creator_") or
                     k.startswith("mod_") or k.startswith("lesson_")]
    for k in keys_to_clear:
        del st.session_state[k]
    _init_state()

def _render_step1() -> None:
    st.markdown("### Step 1 of 3 — Enter Course Topic")
    st.markdown("Describe your course topic. **Groq** will plan the structure instantly.")

    # Model badge
    st.markdown(
        "<div style='margin-bottom:0.75rem'>"
        "<span style='background:#f3f4f6;color:#374151;padding:3px 10px;"
        "border-radius:4px;font-size:0.8rem;border:1px solid #e5e7eb'>"
        "⚡ Powered by Groq (Llama 3 8B)</span></div>",
        unsafe_allow_html=True,
    )

    topic = st.text_input("Course Topic", placeholder="e.g. Intro to Groq API", key="creator_topic_input", autocomplete="off")

    col1, col2 = st.columns(2)
    with col1:
        num_modules = st.slider("Number of Modules", 2, 8, config.DEFAULT_NUM_MODULES, key="creator_num_modules")
    with col2:
        num_lessons = st.slider("Lessons per Module", 2, 6, config.DEFAULT_NUM_LESSONS, key="creator_num_lessons")

    module_themes = st.text_area(
        "Module Themes (Optional)",
        placeholder="e.g. Module 1: Basics, Module 2: Advanced Concepts...",
        key="creator_module_themes",
        help="Specify what each module should cover to guide the AI."
    )

    if st.button("Generate Syllabus", type="primary", disabled=not topic.strip()):
        with st.spinner("⚡ Groq is planning your course..."):
            try:
                instructor_id = auth.get_current_user()["id"]
                course, syllabus = generate_and_save_syllabus(topic.strip(), num_modules, num_lessons, module_themes.strip(), instructor_id=instructor_id)
                st.session_state["creator_syllabus"] = syllabus
                st.session_state["creator_course_id"] = course.id
                st.session_state["creator_course_title"] = course.title
                st.session_state["creator_step"] = 2
                
                for i, mod in enumerate(syllabus.modules):
                    st.session_state[f"mod_{i}_title"] = mod.title
                    for j, lesson_title in enumerate(mod.lessons):
                        st.session_state[f"lesson_{i}_{j}"] = lesson_title
                st.rerun()
            except Exception as e:
                st.error(f"Generation failed: {e}")

def _render_step2() -> None:
    syllabus = st.session_state["creator_syllabus"]

    if st.session_state.get("creator_course_id") is None:
        st.error("Error: Course not initialized. Please go back to Step 1.")
        st.stop()

    course_id = st.session_state["creator_course_id"]
    with get_db() as db:
        course = get_course(db, course_id)

        flat_lessons = []
        for m_idx, module in enumerate(course.modules):
            for l_idx, lesson in enumerate(module.lessons):
                flat_lessons.append({
                    "id": lesson.id,
                    "title": lesson.title,
                    "module_title": module.title,
                    "module_idx": m_idx,
                    "lesson_idx": l_idx,
                })

    st.markdown("### Step 2 of 3 — Page-by-Page Edition")
    
    st.markdown(
        "<div style='margin-bottom:1rem'>"
        "<span style='background:#f3f4f6;color:#374151;padding:3px 10px;"
        "border-radius:4px;font-size:0.8rem;border:1px solid #e5e7eb'>"
        "⚡ Fast Generation by Groq</span></div>",
        unsafe_allow_html=True,
    )

    lesson_options = [f"Module {l['module_idx']+1}: {l['title']}" for l in flat_lessons]

    def _lesson_label(i: int) -> str:
        _l = flat_lessons[i]
        _d = st.session_state["creator_lesson_data"].get(_l["id"], {})
        _saved = _d.get("finalized") or bool(_d.get("markdown", "").strip())
        return ("\u25c6  " if _saved else "\u25cb  ") + lesson_options[i]

    selected_idx = st.selectbox(
        "Navigate between lessons:",
        range(len(lesson_options)),
        format_func=_lesson_label,
        index=st.session_state["creator_selected_lesson_idx"],
        key="lesson_selector"
    )
    st.session_state["creator_selected_lesson_idx"] = selected_idx

    # Lesson status strip — one dot per lesson
    _SAVED_COLOR = "rgb(176,43,138)"
    _dots_html = []
    for _si, _sl in enumerate(flat_lessons):
        _sd = st.session_state["creator_lesson_data"].get(_sl["id"], {})
        _is_saved = _sd.get("finalized") or bool(_sd.get("markdown", "").strip())
        _dot_color = _SAVED_COLOR if _is_saved else "#d1d5db"
        _outline = "outline:2px solid #374151;outline-offset:2px;" if _si == selected_idx else ""
        _tip = lesson_options[_si].replace("'", "&#39;")
        _dots_html.append(
            f"<div title='{_tip}' style='display:inline-block;width:13px;height:13px;"
            f"border-radius:50%;background:{_dot_color};{_outline}'></div>"
        )
    _n_saved = sum(
        1 for _l2 in flat_lessons
        if (st.session_state["creator_lesson_data"].get(_l2["id"], {}).get("finalized") or
            bool(st.session_state["creator_lesson_data"].get(_l2["id"], {}).get("markdown", "").strip()))
    )
    st.markdown(
        f"<div style='display:flex;align-items:center;gap:8px;margin:2px 0 12px 0'>"
        f"<span style='font-size:0.73rem;color:#6b7280'>{_n_saved}/{len(flat_lessons)} saved</span>"
        f"<div style='display:flex;flex-wrap:wrap;gap:4px'>{''.join(_dots_html)}</div>"
        f"<span style='font-size:0.73rem;color:{_SAVED_COLOR}'>(&#9670;&nbsp;= saved)</span>"
        f"</div>",
        unsafe_allow_html=True,
    )
    
    current_lesson = flat_lessons[selected_idx]
    lesson_id = current_lesson["id"]

    class MockAsset:
        def __init__(self, a):
            self.id = a.id
            self.type = a.type
            self.content = a.content
            self.caption = a.caption

    class MockLesson:
        def __init__(self, obj):
            self.id = obj.id
            self.content_markdown = obj.content_markdown
            self.assets = [MockAsset(a) for a in obj.assets]

    with get_db() as db:
        from repositories.course_repo import get_lesson
        db_lesson_obj = get_lesson(db, lesson_id)
        db_lesson = MockLesson(db_lesson_obj)

    if lesson_id not in st.session_state["creator_lesson_data"]:
        st.session_state["creator_lesson_data"][lesson_id] = {
            "markdown": db_lesson.content_markdown or "",
            "finalized": bool(db_lesson.content_markdown),
            "target_chars": 0
        }

    lesson_data = st.session_state["creator_lesson_data"][lesson_id]

    with st.container(border=True):
        st.subheader(f"Lesson: {current_lesson['title']}")
        
        target_chars = st.slider("Target Size (Characters)", 0, 50000, lesson_data["target_chars"], 500, key=f"s_{lesson_id}")
        lesson_data["target_chars"] = target_chars

        if not lesson_data["markdown"] or st.button("Regenerate", key=f"reg_{lesson_id}"):
            from services.content_service import generate_lesson_stream
            with st.chat_message("assistant", avatar="⚡"):
                status_placeholder = st.empty()
                full_response = ""
                instructor_id = auth.get_current_user()["id"]
                for m_type, m_val in generate_lesson_stream(st.session_state["creator_course_title"], current_lesson["module_title"], lesson_id, target_chars, instructor_id=instructor_id):
                    if m_type == "status":
                        status_placeholder.caption(f"ℹ️ {m_val}")
                    else:
                        full_response += m_val
                        status_placeholder.markdown(full_response + "▌")
                status_placeholder.markdown(full_response)
            lesson_data["markdown"] = full_response
            st.session_state[f"ed_{lesson_id}"] = full_response
            st.rerun()
        
        if f"ed_{lesson_id}" not in st.session_state:
            st.session_state[f"ed_{lesson_id}"] = lesson_data["markdown"]

        st.markdown("### 📂 Inserted Media Manager")
        if not db_lesson.assets:
            st.caption("No media attached to this lesson.")
        else:
            for idx, asset in enumerate(db_lesson.assets):
                col_ass1, col_ass2, col_ass3 = st.columns([1, 6, 2])
                with col_ass1:
                    st.markdown(f"**[{asset.type.upper()}]**")
                with col_ass2:
                    st.caption(asset.content)
                with col_ass3:
                    if st.button("Delete", key=f"del_{asset.id}_{lesson_id}"):
                        with get_db() as db:
                            delete_lesson_asset(db, asset.id)
                        
                        st.rerun()

        with st.expander("Insert Media", expanded=False):
            tab_img, tab_doc, tab_vid = st.tabs(["Image (Upload)", "Document (PDF/Word)", "Video (Upload)"])
            
            with tab_img:
                pending_img_path = None
                pending_caption = ""
                
                uploaded_img = st.file_uploader("Image Upload", type=["png", "jpg", "jpeg"], key=f"upl_img_{lesson_id}")
                if uploaded_img:
                    uploads_dir = Path("static/uploads")
                    uploads_dir.mkdir(parents=True, exist_ok=True)
                    filename = f"up_img_{uuid.uuid4().hex[:8]}_{uploaded_img.name}"
                    file_path = uploads_dir / filename
                    with open(file_path, "wb") as f:
                        f.write(uploaded_img.getbuffer())
                    
                    st.session_state[f"pending_img_{lesson_id}"] = f"static/uploads/{filename}"
                    st.session_state[f"pending_cap_{lesson_id}"] = filename
                
                if st.session_state.get(f"pending_img_{lesson_id}"):
                    st.success("✅ Image ready for insertion! Choose formatting below:")
                    local_preview_path = f"static/uploads/{st.session_state[f'pending_cap_{lesson_id}']}"
                    st.image(local_preview_path, width=150)
                    
                    col_align, col_size, col_pos = st.columns(3)
                    with col_align:
                        align = st.selectbox("Alignment", ["center", "left", "right"], key=f"align_img_{lesson_id}")
                    with col_size:
                        size = st.selectbox("Size", ["100%", "75%", "50%", "25%"], key=f"sz_img_{lesson_id}")
                    with col_pos:
                        pos_insert = st.radio("Where to insert?", ["At the End", "At the Beginning"], key=f"pos_img_{lesson_id}")
                    
                    if st.button("Add Image to Lesson", use_container_width=True, key=f"ins_btn_{lesson_id}"):
                        img_val = st.session_state[f"pending_img_{lesson_id}"]
                        cap_val = st.session_state[f"pending_cap_{lesson_id}"]
                        pos_val = "start" if pos_insert == "At the Beginning" else "end"
                        
                        with get_db() as db:
                            add_lesson_asset(db, lesson_id, 'image', img_val, cap_val, position=pos_val)
                        
                        del st.session_state[f"pending_img_{lesson_id}"]
                        st.rerun()

            with tab_doc:
                uploaded_doc = st.file_uploader("Upload PDF or Word", type=["pdf", "doc", "docx"], key=f"upl_doc_{lesson_id}")
                if uploaded_doc:
                    doc_label = st.text_input("Link Text", value=f"Download {uploaded_doc.name}", key=f"doc_lbl_{lesson_id}")
                    col_pos_d = st.radio("Where to Insert?", ["At the End", "At the Beginning"], key=f"pos_doc_{lesson_id}")
                    if st.button("Add Document to Lesson", key=f"btn_in_doc_{lesson_id}"):
                        uploads_dir = Path("static/uploads")
                        uploads_dir.mkdir(parents=True, exist_ok=True)
                        filename = f"up_doc_{uuid.uuid4().hex[:8]}_{uploaded_doc.name}"
                        file_path = uploads_dir / filename
                        with open(file_path, "wb") as f:
                            f.write(uploaded_doc.getbuffer())
                            
                        final_path = f"static/uploads/{filename}"
                        pos_val = "start" if col_pos_d == "At the Beginning" else "end"
                        with get_db() as db:
                            add_lesson_asset(db, lesson_id, 'document', final_path, doc_label, position=pos_val)
                        
                        st.rerun()
            
            with tab_vid:
                uploaded_vid = st.file_uploader("Video Upload (.mp4/etc)", type=["mp4", "mov", "webm"], key=f"upl_vid_{lesson_id}")
                if uploaded_vid:
                    col_align_v, col_size_v, col_pos_v = st.columns(3)
                    with col_align_v:
                        align_v = st.selectbox("Alignment", ["center", "left", "right"], key=f"align_vid_{lesson_id}")
                    with col_size_v:
                        size_v = st.selectbox("Size", ["100%", "75%", "50%", "25%"], key=f"sz_vid_{lesson_id}")
                    with col_pos_v:
                        pos_insert_v = st.radio("Where to Insert?", ["At the End", "At the Beginning"], key=f"pos_vid_{lesson_id}")
                    
                    if st.button("Add Video to Lesson", key=f"btn_in_vid_{lesson_id}"):
                        uploads_dir = Path("static/uploads")
                        uploads_dir.mkdir(parents=True, exist_ok=True)
                        filename = f"up_vid_{uuid.uuid4().hex[:8]}_{uploaded_vid.name}"
                        file_path = uploads_dir / filename
                        with open(file_path, "wb") as f:
                            f.write(uploaded_vid.getbuffer())
                            
                        final_path = f"static/uploads/{filename}"
                        pos_val = "start" if pos_insert_v == "At the Beginning" else "end"
                        with get_db() as db:
                            add_lesson_asset(db, lesson_id, 'video', final_path, filename, position=pos_val)
                        
                        st.rerun()

        st.markdown("---")
        edited = st.text_area("Edit Content", height=300, key=f"ed_{lesson_id}")
        lesson_data["markdown"] = edited

        if st.button("Save Changes & Finalize Page", type="primary", use_container_width=True, key=f"fin_{lesson_id}"):
            with get_db() as db:
                update_lesson_content(db, lesson_id, lesson_data["markdown"])
            lesson_data["finalized"] = True
            st.toast(f"✅ Lição **{current_lesson['title']}** salva com sucesso!", icon="✅")
            if selected_idx < len(flat_lessons) - 1:
                st.session_state["creator_selected_lesson_idx"] = selected_idx + 1
            st.rerun()

    col_back, col_next = st.columns(2)
    with col_back:
        if st.button("← Back", use_container_width=True):
            st.session_state["creator_step"] = 1
            st.rerun()
    with col_next:
        # Count lessons that have content (AI-generated or manually saved)
        lessons_with_content = sum(
            1 for d in st.session_state["creator_lesson_data"].values()
            if d.get("finalized") or d.get("markdown", "").strip()
        )
        total_lessons = len(flat_lessons)
        all_done = lessons_with_content == total_lessons

        if not all_done:
            st.progress(lessons_with_content / max(total_lessons, 1),
                        text=f"✍️ {lessons_with_content}/{total_lessons} lessons with content")
        
        if st.button("Step 3: Quiz →", type="primary" if all_done else "secondary",
                     use_container_width=True):
            if not all_done:
                st.warning(f"⚠️ {total_lessons - lessons_with_content} lesson(s) still have no content. You can proceed, but those lessons will be empty.")
            st.session_state["creator_step"] = 3
            st.rerun()

def _normalize_draft(draft: list) -> list:
    """Convert old-format drafts {options, correct_index} to flat format {option_a..d, correct}."""
    normalized = []
    for q in draft:
        if "option_a" in q:
            normalized.append(q)
            continue
        # Old format detected - migrate
        opts = q.get("options", [])
        while len(opts) < 4:
            opts.append("")
        normalized.append({
            "question": q.get("question", ""),
            "option_a": str(opts[0]), "option_b": str(opts[1]),
            "option_c": str(opts[2]), "option_d": str(opts[3]),
            "correct": min(int(q.get("correct_index", 0)), 3),
            "explanation": q.get("explanation", "")
        })
    return normalized

def _sync_quiz_state_to_draft(scope_key: str) -> None:
    """Flush all per-question widget values back into quiz_drafts[scope_key].
    Call this before any structural change (add / remove question) so that
    edits the user has already typed are not lost."""
    draft = st.session_state.get("quiz_drafts", {}).get(scope_key, [])
    synced = []
    for i, q in enumerate(draft):
        qk = f"qe_{scope_key}_{i}"
        synced.append({
            "question":    st.session_state.get(f"{qk}_q",   q.get("question",   "")),
            "option_a":   st.session_state.get(f"{qk}_a",   q.get("option_a",   "")),
            "option_b":   st.session_state.get(f"{qk}_b",   q.get("option_b",   "")),
            "option_c":   st.session_state.get(f"{qk}_c",   q.get("option_c",   "")),
            "option_d":   st.session_state.get(f"{qk}_d",   q.get("option_d",   "")),
            "correct":    st.session_state.get(f"{qk}_cor", q.get("correct",    0)),
            "explanation": st.session_state.get(f"{qk}_exp", q.get("explanation", "")),
        })
    st.session_state["quiz_drafts"][scope_key] = synced

def _render_quiz_editor(scope_key: str, title: str, content_summary: str, course_id: int, module_id: int = None, lesson_id: int = None):
    st.markdown(f"**Quiz: {title}**")

    if "quiz_drafts" not in st.session_state:
        st.session_state["quiz_drafts"] = {}

    # Load from DB if not cached
    if scope_key not in st.session_state["quiz_drafts"]:
        with get_db() as db:
            db_quizzes = quiz_repo.get_quizzes(db, course_id=course_id, module_id=module_id, lesson_id=lesson_id)
            if db_quizzes:
                draft = []
                for q in db_quizzes:
                    opts = q.options if isinstance(q.options, list) else []
                    while len(opts) < 4:
                        opts.append("")
                    draft.append({
                        "question": q.question_text,
                        "option_a": opts[0], "option_b": opts[1],
                        "option_c": opts[2], "option_d": opts[3],
                        "correct": int(q.correct_answer or 0),
                        "explanation": q.explanation or ""
                    })
                st.session_state["quiz_drafts"][scope_key] = draft
            else:
                st.session_state["quiz_drafts"][scope_key] = []

    col1, col2, col3 = st.columns(3)
    with col1:
        n_q = st.select_slider("Questions", options=list(range(1, 21)), value=5, key=f"nq_{scope_key}")
    with col2:
        pass_score = st.select_slider("Passing Score (%)", options=list(range(0, 101, 5)), value=70, key=f"ps_{scope_key}")
    with col3:
        max_att = st.select_slider("Max Attempts (0=∞)", options=list(range(0, 11)), value=3, key=f"ma_{scope_key}")

    if st.button(f"Generate {int(n_q)} Questions with AI", key=f"gen_{scope_key}"):
        with st.spinner("AI is generating questions..."):
            try:
                actual_summary = content_summary
                if content_summary == "module_content_placeholder" and module_id:
                    with get_db() as db:
                        from db.models import Lesson
                        ls = db.query(Lesson).filter(Lesson.module_id == module_id).all()
                        actual_summary = "\n".join([l.content_markdown or "" for l in ls])
                elif content_summary == "course_content_placeholder":
                    from services.content_service import get_full_content_as_text
                    actual_summary = get_full_content_as_text(course_id)

                instructor_id = auth.get_current_user()["id"]
                raw = generate_quiz_draft(title, actual_summary, n_questions=int(n_q), instructor_id=instructor_id)
                draft_flat = []
                for q in raw:
                    opts = q.get("options", [])
                    while len(opts) < 4:
                        opts.append("")
                    draft_flat.append({
                        "question": q.get("question", ""),
                        "option_a": opts[0], "option_b": opts[1],
                        "option_c": opts[2], "option_d": opts[3],
                        "correct": min(int(q.get("correct_index", 0)), 3),
                        "explanation": q.get("explanation", "")
                    })
                st.session_state["quiz_drafts"][scope_key] = draft_flat
                # Clear widget keys so the new questions re-initialize the inputs
                for k in list(st.session_state.keys()):
                    if k.startswith(f"qe_{scope_key}_"):
                        del st.session_state[k]
            except Exception as e:
                st.error(f"Generation failed: {e}")

    current_draft = st.session_state["quiz_drafts"].get(scope_key, [])
    if not isinstance(current_draft, list):
        current_draft = []

    if not current_draft:
        st.info("No questions yet. Generate some with AI or add manually.")
        if st.button("Add Empty Question", key=f"add_first_{scope_key}"):
            st.session_state["quiz_drafts"][scope_key] = [{
                "question": "", "option_a": "", "option_b": "",
                "option_c": "", "option_d": "", "correct": 0, "explanation": ""
            }]
            st.rerun()
    else:
        st.caption(f"{len(current_draft)} question(s) — expand each card to edit:")
        st.markdown("---")

        for i, q in enumerate(current_draft):
            qk = f"qe_{scope_key}_{i}"
            q_display = st.session_state.get(f"{qk}_q", q.get("question", "")) or f"(empty question {i+1})"
            label = f"Q{i+1}: {str(q_display)[:70]}{'…' if len(str(q_display)) > 70 else ''}"

            with st.expander(label, expanded=False):
                st.text_area(
                    label="Question Text",
                    value=q.get("question", ""),
                    key=f"{qk}_q",
                    height=90,
                )
                col_a, col_b = st.columns(2)
                with col_a:
                    st.text_input(label="Option A", value=q.get("option_a", ""), key=f"{qk}_a")
                    st.text_input(label="Option C", value=q.get("option_c", ""), key=f"{qk}_c")
                with col_b:
                    st.text_input(label="Option B", value=q.get("option_b", ""), key=f"{qk}_b")
                    st.text_input(label="Option D", value=q.get("option_d", ""), key=f"{qk}_d")

                st.radio(
                    label="Correct Answer",
                    options=[0, 1, 2, 3],
                    format_func=lambda x: ["A", "B", "C", "D"][x],
                    index=min(int(q.get("correct", 0)), 3),
                    horizontal=True,
                    key=f"{qk}_cor",
                )
                st.text_area(
                    label="Explanation (optional)",
                    value=q.get("explanation", ""),
                    key=f"{qk}_exp",
                    height=70,
                )

                if st.button(f"Remove Q{i+1}", key=f"rem_q_{scope_key}_{i}"):
                    _sync_quiz_state_to_draft(scope_key)
                    updated = list(st.session_state["quiz_drafts"][scope_key])
                    updated.pop(i)
                    st.session_state["quiz_drafts"][scope_key] = updated
                    for k in list(st.session_state.keys()):
                        if k.startswith(f"qe_{scope_key}_"):
                            del st.session_state[k]
                    st.rerun()

        st.markdown("---")
        col_add, col_save = st.columns([1, 2])
        with col_add:
            if st.button("Add Question", key=f"add_q_{scope_key}", use_container_width=True):
                _sync_quiz_state_to_draft(scope_key)
                updated = list(st.session_state["quiz_drafts"][scope_key])
                updated.append({
                    "question": "", "option_a": "", "option_b": "",
                    "option_c": "", "option_d": "", "correct": 0, "explanation": ""
                })
                st.session_state["quiz_drafts"][scope_key] = updated
                for k in list(st.session_state.keys()):
                    if k.startswith(f"qe_{scope_key}_"):
                        del st.session_state[k]
                st.rerun()

        with col_save:
            if st.button("Save Quiz & Settings", type="primary", key=f"save_{scope_key}", use_container_width=True):
                try:
                    n_questions = len(st.session_state["quiz_drafts"].get(scope_key, []))
                    converted = []
                    for i in range(n_questions):
                        qk = f"qe_{scope_key}_{i}"
                        question = str(st.session_state.get(f"{qk}_q", "")).strip()
                        if not question:
                            continue
                        try:
                            c_idx = int(st.session_state.get(f"{qk}_cor", 0))
                        except Exception:
                            c_idx = 0
                        converted.append({
                            "question": question,
                            "options": [
                                str(st.session_state.get(f"{qk}_a", "")),
                                str(st.session_state.get(f"{qk}_b", "")),
                                str(st.session_state.get(f"{qk}_c", "")),
                                str(st.session_state.get(f"{qk}_d", "")),
                            ],
                            "correct_index": min(c_idx, 3),
                            "explanation": str(st.session_state.get(f"{qk}_exp", "")),
                        })

                    if not converted:
                        st.warning("⚠️ No valid questions found to save.")
                    else:
                        with get_db() as db:
                            save_quiz_draft(db, converted, course_id=course_id, module_id=module_id, lesson_id=lesson_id)
                            p_score = int(st.session_state.get(f"ps_{scope_key}", 70))
                            m_att   = int(st.session_state.get(f"ma_{scope_key}", 3))
                            if lesson_id:
                                update_lesson_quiz_settings(db, lesson_id, passing_score=p_score, max_attempts=m_att)
                            elif module_id:
                                update_module_quiz_settings(db, module_id, passing_score=p_score, max_attempts=m_att)
                            else:
                                update_course_quiz_settings(db, course_id, passing_score=p_score, max_attempts=m_att)

                        # Sync saved data back to draft
                        new_draft = []
                        for item in converted:
                            opts = item["options"]
                            while len(opts) < 4:
                                opts.append("")
                            new_draft.append({
                                "question": item["question"],
                                "option_a": opts[0], "option_b": opts[1],
                                "option_c": opts[2], "option_d": opts[3],
                                "correct": item["correct_index"],
                                "explanation": item["explanation"],
                            })
                        st.session_state["quiz_drafts"][scope_key] = new_draft
                        st.success(f"✅ Quiz saved! ({len(converted)} questions)")
                except Exception as e:
                    st.error(f"❌ Save failed: {e}")


def _render_cert_manager(scope_key: str, course_id: int, module_id: int = None):
    st.subheader("Certificate Manager")

    # Load target using separate DB context
    cert_path_current = None
    target_exists = False
    with get_db() as db:
        if module_id:
            from db.models import Module
            target = db.query(Module).filter(Module.id == module_id).first()
        else:
            from db.models import Course
            target = db.query(Course).filter(Course.id == course_id).first()
        if target:
            target_exists = True
            cert_path_current = target.certificate_path

    if not target_exists: return

    st.markdown("Upload a certificate template file (PDF/Image) for this course.")
    cert_file = st.file_uploader(
        "Select Certificate File",
        type=["png", "jpg", "jpeg", "pdf"],
        key=f"cert_upl_{scope_key}"
    )

    if cert_file:
        # Use a button to trigger the save, avoiding the automatic rerun loop
        if st.button("Upload & Set Template", key=f"btn_upl_{scope_key}", type="primary"):
            with st.spinner("Uploading and saving..."):
                try:
                    uploads_dir = Path("static/certificates")
                    uploads_dir.mkdir(parents=True, exist_ok=True)
                    filename = f"cert_{uuid.uuid4().hex[:8]}_{cert_file.name}"
                    file_path = uploads_dir / filename
                    
                    with open(file_path, "wb") as f:
                        f.write(cert_file.getbuffer())
                    
                    with get_db() as db_upd:
                        if module_id:
                            update_module_certificate(db_upd, module_id, str(file_path))
                        else:
                            update_course_certificate(db_upd, course_id, str(file_path))
                    
                    st.success("Certificate template updated successfully!")
                    # Use rerun only after explicit success
                    st.rerun()
                except Exception as e:
                    st.error(f"Error uploading certificate: {e}")

    if cert_path_current:
        st.markdown("---")
        st.info("Current Certificate File:")
        st.caption(f"Path: {cert_path_current}")
        img_p = Path(cert_path_current)
        if img_p.exists():
            if img_p.suffix.lower() in [".png", ".jpg", ".jpeg"]:
                st.image(cert_path_current, use_container_width=True)
            else:
                st.write(f"📄 {img_p.name} (PDF)")
            
            if st.button("Remove Certificate", key=f"rem_cert_{scope_key}"):
                with get_db() as db_upd:
                    if module_id:
                        update_module_certificate(db_upd, module_id, None)
                    else:
                        update_course_certificate(db_upd, course_id, None)
                st.rerun()

def _render_step3() -> None:
    course_id = st.session_state["creator_course_id"]
    if not course_id: return

    modules_data = []
    course_title = ""
    with get_db() as db:
        course = get_course(db, course_id)
        if course:
            course_title = course.title
            for m in course.modules:
                m_data = {
                    "id": m.id,
                    "title": m.title,
                    "lessons": [{"id": l.id, "title": l.title, "content_markdown": l.content_markdown} for l in m.lessons]
                }
                modules_data.append(m_data)

    if not modules_data:
        st.warning("No modules found for this course.")
        return

    st.markdown("### Step 3 of 3 — Quizzes & Certificates")
    
    tab_lessons, tab_modules, tab_course = st.tabs(["Lesson Quizzes", "Module Quizzes & Certs", "Final Course Quiz & Cert"])
    
    with tab_lessons:
        st.markdown("Add quizzes to specific lessons.")
        lesson_map = {}
        for m in modules_data:
            for l in m["lessons"]:
                lesson_map[f"{m['title']} -> {l['title']}"] = l
        
        sel_l_title = st.selectbox("Select Lesson", list(lesson_map.keys()))
        sel_l = lesson_map[sel_l_title]
        _render_quiz_editor(f"lesson_{sel_l['id']}", sel_l['title'], sel_l['content_markdown'] or "", course_id, lesson_id=sel_l['id'])

    with tab_modules:
        st.markdown("Add quizzes or certificates to modules.")
        module_titles = [m["title"] for m in modules_data]
        sel_m_title = st.selectbox("Select Module", module_titles)
        sel_m = next(m for m in modules_data if m["title"] == sel_m_title)
        
        q_sub, c_sub = st.tabs(["Quiz", "Certificate"])
        with q_sub:
            # JOIN CONTENT ONLY IF NEEDED (on demand inside the button or when tab is active)
            # This reduces background processing and potential loading hangs
            _render_quiz_editor(f"module_{sel_m['id']}", sel_m['title'], "module_content_placeholder", course_id, module_id=sel_m['id'])
        with c_sub:
            _render_cert_manager(f"module_cert_{sel_m['id']}", course_id, module_id=sel_m['id'])

    with tab_course:
        st.markdown("Final assessment and course certificate.")
        q_sub_c, c_sub_c = st.tabs(["Final Quiz", "Final Certificate"])
        with q_sub_c:
            _render_quiz_editor(f"course_{course_id}", course_title, "course_content_placeholder", course_id)
        with c_sub_c:
            _render_cert_manager(f"course_cert_{course_id}", course_id)

    st.divider()
    if st.button("Finalize & View Course", type="primary"):
        st.session_state["page"] = "player"
        st.session_state["active_course_id"] = course_id
        _reset_creator()
        st.rerun()

def render() -> None:
    _init_state()
    step = st.session_state["creator_step"]
    if step == 1: _render_step1()
    elif step == 2: _render_step2()
    elif step == 3: _render_step3()
