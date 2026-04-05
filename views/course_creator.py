"""
views/course_creator.py
────────────────────────
3-step course creation wizard — Powered by Groq (Llama 3 8B).
"""

from __future__ import annotations
import streamlit as st
import config
from repositories import course_repo
from services.quiz_service import generate_and_save_quiz
from services.syllabus_service import (
    generate_and_save_syllabus,
    save_syllabus,
)

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

    topic = st.text_input("Course Topic", placeholder="e.g. Intro to Groq API", key="creator_topic_input")

    col1, col2 = st.columns(2)
    with col1:
        num_modules = st.slider("Number of Modules", 2, 8, config.DEFAULT_NUM_MODULES, key="creator_num_modules")
    with col2:
        num_lessons = st.slider("Lessons per Module", 2, 6, config.DEFAULT_NUM_LESSONS, key="creator_num_lessons")

    if st.button("✨ Generate Syllabus", type="primary", disabled=not topic.strip()):
        with st.spinner("⚡ Groq is planning your course..."):
            try:
                course, syllabus = generate_and_save_syllabus(topic.strip(), num_modules, num_lessons)
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
    course = course_repo.get_course(course_id)

    flat_lessons = []
    for m_idx, module in enumerate(course.modules):
        for l_idx, lesson in enumerate(module.lessons):
            flat_lessons.append({
                "id": lesson.id,
                "title": lesson.title,
                "module_title": module.title,
                "module_idx": m_idx,
                "lesson_idx": l_idx,
                "db_obj": lesson
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
    selected_idx = st.selectbox(
        "Navigate between lessons:",
        range(len(lesson_options)),
        format_func=lambda i: lesson_options[i],
        index=st.session_state["creator_selected_lesson_idx"],
        key="lesson_selector"
    )
    st.session_state["creator_selected_lesson_idx"] = selected_idx
    
    current_lesson = flat_lessons[selected_idx]
    lesson_id = current_lesson["id"]
    db_lesson = current_lesson["db_obj"]

    if lesson_id not in st.session_state["creator_lesson_data"]:
        st.session_state["creator_lesson_data"][lesson_id] = {
            "markdown": db_lesson.content_markdown or "",
            "image_path": db_lesson.image_path or "",
            "finalized": bool(db_lesson.content_markdown),
            "target_chars": 0
        }

    lesson_data = st.session_state["creator_lesson_data"][lesson_id]

    with st.container(border=True):
        st.subheader(f"Lesson: {current_lesson['title']}")
        
        target_chars = st.slider("Target Size (Characters)", 0, 50000, lesson_data["target_chars"], 500, key=f"s_{lesson_id}")
        lesson_data["target_chars"] = target_chars

        if not lesson_data["markdown"] or st.button("🔄 Regenerate", key=f"reg_{lesson_id}"):
            from services.content_service import generate_lesson_stream
            with st.chat_message("assistant", avatar="⚡"):
                status_placeholder = st.empty()
                full_response = ""
                for m_type, m_val in generate_lesson_stream(st.session_state["creator_course_title"], current_lesson["module_title"], lesson_id, target_chars):
                    if m_type == "status":
                        status_placeholder.caption(f"ℹ️ {m_val}")
                        if "Image generated:" in m_val:
                            lesson_data["image_path"] = m_val.split("Image generated: ")[1].strip()
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
                    if st.button("❌ Delete", key=f"del_{asset.id}_{lesson_id}"):
                        from repositories.course_repo import delete_lesson_asset
                        delete_lesson_asset(asset.id)
                        
                        import re
                        current_md = st.session_state[f"ed_{lesson_id}"]
                        # Safe regex replacement matching tag enclosing the asset content
                        safe_content = re.escape(asset.content)
                        pattern = rf'<div.*?>\s*<img src="{safe_content}".*?>\s*</div>|<img src="{safe_content}".*?>|### Support Documentation\n<a href="{safe_content}".*?>.*?</a>|<video src="{safe_content}".*?>.*?</video>'
                        new_md = re.sub(pattern, "", current_md)
                        
                        st.session_state[f"ed_{lesson_id}"] = new_md
                        lesson_data["markdown"] = new_md
                        st.rerun()

        with st.expander("📎 Insert Media", expanded=False):
            tab_img, tab_doc, tab_vid = st.tabs(["🖼️ Image (Upload)", "📄 Document (PDF/Word)", "🎥 Video (Upload)"])
            
            with tab_img:
                pending_img_path = None
                pending_caption = ""
                
                uploaded_img = st.file_uploader("Image Upload", type=["png", "jpg", "jpeg"], key=f"upl_img_{lesson_id}")
                if uploaded_img:
                    from pathlib import Path
                    uploads_dir = Path("static/uploads")
                    uploads_dir.mkdir(parents=True, exist_ok=True)
                    import uuid
                    filename = f"up_img_{uuid.uuid4().hex[:8]}_{uploaded_img.name}"
                    file_path = uploads_dir / filename
                    with open(file_path, "wb") as f:
                        f.write(uploaded_img.getbuffer())
                    
                    st.session_state[f"pending_img_{lesson_id}"] = f"/app/static/uploads/{filename}"
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
                    
                    if st.button("Apply Image to Text", use_container_width=True, key=f"ins_btn_{lesson_id}"):
                        img_val = st.session_state[f"pending_img_{lesson_id}"]
                        cap_val = st.session_state[f"pending_cap_{lesson_id}"]
                        
                        course_repo.add_lesson_asset(lesson_id, 'image', img_val, cap_val)
                        
                        margin_style = "margin: auto;" if align == "center" else f"float: {align}; margin: 10px;"
                        if align == "center":
                           tag = f'\n<div align="center">\n  <img src="{img_val}" width="{size}" style="{margin_style}">\n</div>\n'
                        else:
                           tag = f'\n<img src="{img_val}" width="{size}" style="{margin_style}">\n'
                        
                        current_md = st.session_state[f"ed_{lesson_id}"]
                        new_md = current_md + "\n" + tag if pos_insert == "At the End" else tag + "\n" + current_md
                        
                        st.session_state[f"ed_{lesson_id}"] = new_md
                        lesson_data["markdown"] = new_md
                        
                        del st.session_state[f"pending_img_{lesson_id}"]
                        st.rerun()

            with tab_doc:
                uploaded_doc = st.file_uploader("Upload PDF or Word", type=["pdf", "doc", "docx"], key=f"upl_doc_{lesson_id}")
                if uploaded_doc:
                    doc_label = st.text_input("Link Text", value=f"Download {uploaded_doc.name}", key=f"doc_lbl_{lesson_id}")
                    if st.button("Insert Document", key=f"btn_in_doc_{lesson_id}"):
                        from pathlib import Path
                        import uuid
                        uploads_dir = Path("static/uploads")
                        uploads_dir.mkdir(parents=True, exist_ok=True)
                        filename = f"up_doc_{uuid.uuid4().hex[:8]}_{uploaded_doc.name}"
                        file_path = uploads_dir / filename
                        with open(file_path, "wb") as f:
                            f.write(uploaded_doc.getbuffer())
                            
                        final_path = f"/app/static/uploads/{filename}"
                        course_repo.add_lesson_asset(lesson_id, 'document', final_path, filename)
                        
                        tag = f'\n### Support Documentation\n<a href="{final_path}" target="_blank" download>📄 {doc_label}</a>\n'
                        current_md = st.session_state[f"ed_{lesson_id}"]
                        new_md = current_md + "\n" + tag
                        
                        st.session_state[f"ed_{lesson_id}"] = new_md
                        lesson_data["markdown"] = new_md
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
                    
                    if st.button("Insert Video", key=f"btn_in_vid_{lesson_id}"):
                        from pathlib import Path
                        import uuid
                        uploads_dir = Path("static/uploads")
                        uploads_dir.mkdir(parents=True, exist_ok=True)
                        filename = f"up_vid_{uuid.uuid4().hex[:8]}_{uploaded_vid.name}"
                        file_path = uploads_dir / filename
                        with open(file_path, "wb") as f:
                            f.write(uploaded_vid.getbuffer())
                            
                        final_path = f"/app/static/uploads/{filename}"
                        course_repo.add_lesson_asset(lesson_id, 'video', final_path, filename)
                        
                        margin_style = "margin: auto;" if align_v == "center" else f"float: {align_v}; margin: 10px;"
                        if align_v == "center":
                           tag = f'\n<div align="center">\n  <video controls src="{final_path}" width="{size_v}" style="{margin_style}"></video>\n</div>\n'
                        else:
                           tag = f'\n<video controls src="{final_path}" width="{size_v}" style="{margin_style}"></video>\n'
                        
                        current_md = st.session_state[f"ed_{lesson_id}"]
                        new_md = current_md + "\n" + tag if pos_insert_v == "At the End" else tag + "\n" + current_md
                        
                        st.session_state[f"ed_{lesson_id}"] = new_md
                        lesson_data["markdown"] = new_md
                        st.rerun()

        st.markdown("---")
        edited = st.text_area("Edit Content", height=300, key=f"ed_{lesson_id}")
        lesson_data["markdown"] = edited

        if st.button("✅ Save Changes & Finalize Page", type="primary", use_container_width=True, key=f"fin_{lesson_id}"):
            course_repo.update_lesson_content(lesson_id, lesson_data["markdown"], lesson_data.get("image_path", ""))
            lesson_data["finalized"] = True
            if selected_idx < len(flat_lessons) - 1:
                st.session_state["creator_selected_lesson_idx"] = selected_idx + 1
            st.rerun()

    col_back, col_next = st.columns(2)
    with col_back:
        if st.button("← Back", use_container_width=True):
            st.session_state["creator_step"] = 1
            st.rerun()
    with col_next:
        all_done = (
            len(st.session_state["creator_lesson_data"]) == len(flat_lessons) and
            all(d.get("finalized") for d in st.session_state["creator_lesson_data"].values())
        )
        if st.button("Step 3: Quiz →", type="secondary", disabled=not all_done, use_container_width=True):
            st.session_state["creator_step"] = 3
            st.rerun()

def _render_step3() -> None:
    course_id = st.session_state["creator_course_id"]
    course_title = st.session_state["creator_course_title"]

    st.markdown("### Step 3 of 3 — Generate Quiz (Optional)")
    if not st.session_state.get("creator_quiz_done"):
        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            if st.button("⚡ Generate AI Quiz", type="primary", use_container_width=True):
                with st.spinner("⚡ Generating..."):
                    generate_and_save_quiz(course_id, course_title)
                    st.session_state["creator_quiz_done"] = True
                    st.rerun()
        with btn_col2:
            if st.button("🚀 Skip - Go Direct to Course", type="secondary", use_container_width=True):
                st.session_state["creator_quiz_done"] = True
                st.rerun()
    else:
        st.success("Quiz created!")
        if st.button("🚀 Go to Course", type="primary"):
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
