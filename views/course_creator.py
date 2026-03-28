"""
views/course_creator.py
────────────────────────
3-step course creation wizard — Hybrid Gemini + Llama 3.2.

Step 1 — Topic Input (Gemini for Syllabus)
  - User enters topic, number of modules/lessons.
  - Optional: upload a PDF as reference material → Gemini extracts key points.
  - Gemini generates the structured syllabus (with or without PDF context).
  - Result is stored in st.session_state.

Step 2 — Syllabus Review & Content Generation (Llama 3.2)
  - Modules and lessons are displayed as editable text_input fields.
  - "Confirm & Generate Content" → Llama 3.2 expands each lesson.
  - Optional: "🔍 Refine with Gemini" → Gemini reviews tone + accuracy.
  - Model badges show which AI generated each part.

Step 3 — Quiz Generation (Llama 3.2)
  - Llama 3.2 generates multiple-choice quiz questions.
  - Preview shown, then saved to DB.
  - "Go to Course" navigates to the content player.

State keys used (all prefixed with "creator_"):
  creator_step          : int (1, 2, or 3)
  creator_syllabus      : SyllabusSchema object from Step 1
  creator_course_id     : int — set after save_syllabus() in Step 2
  creator_course_title  : str — for display in Step 3
  creator_quiz_done     : bool — set after quiz is generated
  creator_pdf_context   : str — extracted key points from uploaded PDF
"""

from __future__ import annotations

import streamlit as st

import config
from repositories import course_repo
from services.quiz_service import generate_and_save_quiz
from services.syllabus_service import (
    ModuleSchema,
    SyllabusSchema,
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
        "creator_pdf_context": "",
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def _reset_creator() -> None:
    """Clear all creator state keys to restart the wizard."""
    keys_to_clear = [k for k in st.session_state if k.startswith("creator_") or
                     k.startswith("mod_") or k.startswith("lesson_")]
    for k in keys_to_clear:
        del st.session_state[k]
    _init_state()


# ── Step 1: Topic Input ───────────────────────────────────────────────────────

def _render_step1() -> None:
    st.markdown("### Step 1 of 3 — Enter Course Topic")
    st.markdown(
        "Describe what your course is about. "
        "**Gemini** will plan the full syllabus structure.",
        help="Be specific for better results, e.g. 'Python for Data Science' "
             "rather than just 'Python'."
    )

    # Model badge
    st.markdown(
        "<div style='margin-bottom:0.75rem'>"
        "<span style='background:#f3f4f6;color:#374151;padding:3px 10px;"
        "border-radius:4px;font-size:0.8rem;border:1px solid #e5e7eb'>"
        "⚡ Syllabus by Llama 3.2</span>"
        "<span style='background:#e0e7ff;color:#4338ca;padding:3px 10px;"
        "border-radius:4px;font-size:0.8rem;border:1px solid #c7d2fe;margin-left:6px'>"
        "🧠 Fallback: Gemini/OpenAI</span></div>",
        unsafe_allow_html=True,
    )

    topic = st.text_input(
        "Course Topic",
        placeholder="e.g. Machine Learning for Beginners",
        key="creator_topic_input",
    )

    col1, col2 = st.columns(2)
    with col1:
        num_modules = st.slider(
            "Number of Modules", min_value=2, max_value=8,
            value=config.DEFAULT_NUM_MODULES, key="creator_num_modules"
        )
    with col2:
        num_lessons = st.slider(
            "Lessons per Module", min_value=2, max_value=6,
            value=config.DEFAULT_NUM_LESSONS, key="creator_num_lessons"
        )

    # PDF upload (optional)
    st.markdown("---")
    st.markdown("#### 📎 Reference Document _(optional)_")
    st.markdown(
        "Upload a PDF technical document or reference material. "
        "**Gemini** will read it (up to 1M tokens) and use its key points "
        "to anchor the syllabus to your source material.",
    )
    uploaded_pdf = st.file_uploader(
        "Upload PDF reference material",
        type=["pdf"],
        key="creator_pdf_upload",
        help="Gemini will extract key concepts to enrich the syllabus.",
    )

    if uploaded_pdf:
        if st.button("🔍 Extract Key Points from PDF", key="extract_pdf_btn"):
            with st.spinner("🧠 Gemini is reading your PDF..."):
                try:
                    from services.multimodal_service import extract_from_pdf
                    key_points = extract_from_pdf(
                        file_bytes=uploaded_pdf.read(),
                        topic=topic.strip() or "the course topic",
                        filename=uploaded_pdf.name,
                    )
                    st.session_state["creator_pdf_context"] = key_points
                    st.success("✅ Key points extracted!")
                except Exception as e:
                    st.error(f"PDF extraction failed: {e}")

        if st.session_state.get("creator_pdf_context"):
            with st.expander("📋 Extracted Key Points", expanded=False):
                st.markdown(st.session_state["creator_pdf_context"])

    st.markdown(" ")
    has_pdf_context = bool(st.session_state.get("creator_pdf_context"))

    btn_label = "✨ Generate Syllabus from PDF" if has_pdf_context else "✨ Generate Syllabus"
    if st.button(btn_label, type="primary", disabled=not topic.strip()):
        with st.spinner("🧠 Gemini is planning your course structure..."):
            try:
                pdf_context = st.session_state.get("creator_pdf_context", "")

                if pdf_context:
                    # Use PDF-enriched syllabus prompt
                    from utils.prompts import build_syllabus_with_context_prompt
                    from services.syllabus_service import generate_syllabus, save_syllabus as _save
                    from services.ai_service import ai_service
                    from services.syllabus_service import _extract_json, SyllabusSchema
                    import json
                    from pydantic import ValidationError

                    prompt = build_syllabus_with_context_prompt(
                        topic.strip(), num_modules, num_lessons, pdf_context
                    )
                    from utils.prompts import SYSTEM_SYLLABUS
                    raw = ai_service.generate(prompt, system=SYSTEM_SYLLABUS)
                    clean = _extract_json(raw)
                    try:
                        data = json.loads(clean)
                        syllabus = SyllabusSchema(**data)
                    except (json.JSONDecodeError, ValidationError) as e:
                        raise ValueError(f"Failed to parse syllabus: {e}") from e

                    course = _save(topic.strip(), syllabus)
                    # Store the extracted PDF context in the course record
                    from db.database import get_session
                    with get_session() as db:
                        from db.models import Course
                        db_course = db.get(Course, course.id)
                        if db_course:
                            db_course.source_document = pdf_context
                else:
                    _, syllabus = generate_and_save_syllabus(
                        topic.strip(), num_modules, num_lessons
                    )

                # Store generated syllabus in session state to pre-populate Step 2
                st.session_state["creator_syllabus"] = syllabus
                st.session_state["creator_step"] = 2
                # Pre-populate editable fields from the generated syllabus
                for i, mod in enumerate(syllabus.modules):
                    st.session_state[f"mod_{i}_title"] = mod.title
                    for j, lesson_title in enumerate(mod.lessons):
                        st.session_state[f"lesson_{i}_{j}"] = lesson_title
                st.rerun()
            except Exception as e:
                st.error(f"Generation failed: {e}")


# ── Step 2: Syllabus Review ───────────────────────────────────────────────────

def _render_step2() -> None:
    syllabus: SyllabusSchema = st.session_state["creator_syllabus"]

    st.markdown("### Step 2 of 3 — Review & Edit Syllabus")
    st.markdown(
        "Edit any module or lesson titles inline. "
        "**Llama 3.2** will then expand each lesson into full Markdown content."
    )

    # Model badges
    col_b1, col_b2, _ = st.columns([2, 2, 4])
    with col_b1:
        st.markdown(
            "<span style='background:#f3f4f6;color:#374151;padding:3px 10px;"
            "border-radius:4px;font-size:0.8rem;border:1px solid #e5e7eb'>"
            "⚡ Syllabus by Llama 3.2</span>",
            unsafe_allow_html=True,
        )
    with col_b2:
        st.markdown(
            "<span style='background:#f3f4f6;color:#374151;padding:3px 10px;"
            "border-radius:4px;font-size:0.8rem;border:1px solid #e5e7eb'>"
            "⚡ Content by Llama 3.2</span>",
            unsafe_allow_html=True,
        )

    # Course title and description (read-only preview)
    st.markdown(f"**Course:** {syllabus.title}")
    st.markdown(f"*{syllabus.description}*")
    st.markdown("---")

    # Editable fields for each module and lesson
    for i, mod in enumerate(syllabus.modules):
        with st.expander(f"Module {i+1}", expanded=True):
            st.text_input(
                f"Module {i+1} Title",
                key=f"mod_{i}_title",
                label_visibility="collapsed",
            )
            for j in range(len(mod.lessons)):
                st.text_input(
                    f"Lesson {j+1}",
                    key=f"lesson_{i}_{j}",
                    label_visibility="collapsed",
                )

    st.markdown(" ")
    col_back, col_confirm = st.columns([1, 3])
    with col_back:
        if st.button("← Back", use_container_width=True):
            st.session_state["creator_step"] = 1
            st.rerun()

    with col_confirm:
        if st.button("⚡ Confirm & Generate Content (Llama 3.2)", type="primary", use_container_width=True):
            # Collect edits from session state and rebuild SyllabusSchema
            edited_modules: list[ModuleSchema] = []
            for i, mod in enumerate(syllabus.modules):
                mod_title = st.session_state.get(f"mod_{i}_title", mod.title)
                lessons = [
                    st.session_state.get(f"lesson_{i}_{j}", t)
                    for j, t in enumerate(mod.lessons)
                ]
                edited_modules.append(ModuleSchema(title=mod_title, lessons=lessons))

            edited_syllabus = SyllabusSchema(
                title=syllabus.title,
                description=syllabus.description,
                modules=edited_modules,
            )

            # Save edited syllabus to DB and generate all lesson content with Llama
            with st.spinner("Saving syllabus..."):
                course = save_syllabus(edited_syllabus.title.split(":")[0], edited_syllabus)
                st.session_state["creator_course_id"] = course.id
                st.session_state["creator_course_title"] = course.title

            # Generate content with a live progress bar (Llama 3.2)
            from services.content_service import generate_all_content
            progress_bar = st.progress(0, text="⚡ Llama 3.2 is writing your lessons...")
            try:
                for current, total, lesson_title in generate_all_content(course.id):
                    pct = int((current / total) * 100)
                    progress_bar.progress(pct, text=f"⚡ Generated: {lesson_title}")
                progress_bar.progress(100, text="✅ All lessons generated by Llama 3.2!")
                st.session_state["creator_step"] = 3
                st.rerun()
            except Exception as e:
                st.error(f"Content generation failed: {e}")

    # ── Optional: Refine with Gemini ───────────────────────────────────────────
    course_id = st.session_state.get("creator_course_id")
    if course_id:
        st.markdown("---")
        st.markdown("#### 🔍 Optional: Refine with Gemini")
        st.markdown(
            "Ask Gemini to review the Llama-generated lessons for tone consistency "
            "and technical accuracy. This may take a few minutes."
        )

        course = course_repo.get_course(course_id)
        if course and getattr(course, "refined", False):
            st.success("✨ This course has already been refined by Gemini.")
        else:
            if st.button(
                "✨ Refine All Lessons with Gemini",
                key="refine_btn",
                help="Gemini will review and improve each lesson for tone and accuracy.",
            ):
                from services.content_service import refine_course_content
                refine_bar = st.progress(0, text="🧠 Gemini is refining your lessons...")
                try:
                    for current, total, lesson_title in refine_course_content(course_id):
                        pct = int((current / total) * 100)
                        refine_bar.progress(pct, text=f"🧠 Refined: {lesson_title}")
                    refine_bar.progress(100, text="✨ All lessons refined by Gemini!")
                    st.success("Content refined successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Refinement failed: {e}")


# ── Step 3: Quiz ──────────────────────────────────────────────────────────────

def _render_step3() -> None:
    course_id: int = st.session_state["creator_course_id"]
    course_title: str = st.session_state["creator_course_title"]

    st.markdown("### Step 3 of 3 — Generate Quiz")
    st.markdown(f"Course **{course_title}** is ready! **Llama 3.2** will create your quiz questions.")

    # Model badge
    st.markdown(
        "<div style='margin-bottom:0.75rem'>"
        "<span style='background:#f3f4f6;color:#374151;padding:3px 10px;"
        "border-radius:4px;font-size:0.8rem;border:1px solid #e5e7eb'>"
        "⚡ Quiz generated by Llama 3.2</span></div>",
        unsafe_allow_html=True,
    )

    if not st.session_state.get("creator_quiz_done"):
        n_questions = st.slider(
            "Number of Questions", min_value=3, max_value=15,
            value=config.DEFAULT_NUM_QUESTIONS, key="creator_n_questions"
        )
        if st.button("⚡ Generate Quiz (Llama 3.2)", type="primary"):
            with st.spinner("⚡ Llama 3.2 is generating your quiz..."):
                try:
                    questions = generate_and_save_quiz(course_id, course_title, n_questions)
                    st.session_state["creator_quiz_done"] = True
                    st.success(f"Generated {len(questions)} questions!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Quiz generation failed: {e}")
    else:
        st.success("Quiz generated successfully!")

        if st.button("🚀 Go to Course", type="primary"):
            st.session_state["page"] = "player"
            st.session_state["active_course_id"] = course_id
            _reset_creator()
            st.rerun()

        if st.button("🏠 Back to Home"):
            st.session_state["page"] = "home"
            _reset_creator()
            st.rerun()


# ── Entry Point ───────────────────────────────────────────────────────────────

def render() -> None:
    """
    Main render function called by app.py.

    Delegates to the correct step renderer based on `creator_step`
    in session state. The step state persists across Streamlit reruns.
    """
    _init_state()

    st.markdown(
        "<h1 style='font-size:2rem;font-weight:700'>✨ Create New Course</h1>",
        unsafe_allow_html=True,
    )

    # Progress indicator
    step = st.session_state["creator_step"]
    cols = st.columns(3)
    labels = ["1 — Topic", "2 — Review", "3 — Quiz"]
    for i, (col, label) in enumerate(zip(cols, labels)):
        active = i + 1 == step
        done = i + 1 < step
        color = "#6366f1" if active else ("#10b981" if done else "#d1d5db")
        weight = "700" if active else "400"
        col.markdown(
            f"<div style='text-align:center;color:{color};font-weight:{weight};'>"
            f"{'✅ ' if done else ''}{label}</div>",
            unsafe_allow_html=True,
        )
    st.markdown("---")

    if step == 1:
        _render_step1()
    elif step == 2:
        _render_step2()
    elif step == 3:
        _render_step3()
