"""
utils/exporters.py
───────────────────
Stub module for future export functionality.

These functions are intentionally NOT implemented in v1 — they exist
to define the interface contract and prevent import errors if they are
called prematurely. Replace `raise NotImplementedError` with actual
`python-docx` / `python-pptx` logic in v2.

Dependencies are already installed (python-docx, python-pptx in requirements.txt).
"""

from __future__ import annotations


def export_to_docx(course_id: int, output_path: str) -> str:
    """
    [STUB] Export all course content to a .docx file.

    Future implementation:
      - Load course + modules + lessons from DB.
      - Use `python-docx` to create a Word document with headings per module
        and body text per lesson.
      - Return the path to the saved file for Streamlit `st.download_button`.

    Args
    ----
    course_id   : Course to export.
    output_path : File path where the .docx will be written.

    Returns
    -------
    str : Path to the created file.
    """
    raise NotImplementedError(
        "DOCX export not implemented yet. Planned for v2."
    )


def export_to_pptx(course_id: int, output_path: str) -> str:
    """
    [STUB] Export course syllabus/overview to a .pptx presentation.

    Future implementation:
      - One slide per module (title + bullet list of lessons).
      - Use `python-pptx` with a branded slide template.
      - Return path for Streamlit download.

    Args
    ----
    course_id   : Course to export.
    output_path : File path where the .pptx will be written.

    Returns
    -------
    str : Path to the created file.
    """
    raise NotImplementedError(
        "PPTX export not implemented yet. Planned for v2."
    )
