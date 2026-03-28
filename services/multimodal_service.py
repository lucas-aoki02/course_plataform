"""
services/multimodal_service.py
──────────────────────────────
Gemini multimodal analysis — extracts key points from PDF files.

Uses the Google Gen AI File API to upload documents and then request
structured key-point extraction in a single call. Gemini's 1M+ token
context window makes it ideal for long technical documents.

Quota Resilience
----------------
Since Llama cannot process PDF files, this module handles Gemini quota
errors via retry with exponential backoff (3 attempts). If all retries
fail, a user-friendly error is raised (no raw API error leaks to UI).

Usage
-----
>>> with open("machine_learning.pdf", "rb") as f:
...     key_points = extract_from_pdf(f.read(), topic="Machine Learning")
>>> print(key_points)  # Markdown string with key points
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

import config
from services.ai_service import AIServiceError, _is_quota_error
from utils.prompts import SYSTEM_MULTIMODAL, build_multimodal_extraction_prompt

logger = logging.getLogger(__name__)

# Retry settings for Gemini quota errors (no Llama fallback for multimodal)
_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 5  # seconds


def extract_from_pdf(file_bytes: bytes, topic: str, filename: str = "document.pdf") -> str:
    """
    Upload a PDF to the Gemini File API and extract key points.

    Gemini reads the full PDF (including text, tables, and figures) and
    returns a structured Markdown summary of key concepts to use as a
    foundation for course syllabus generation.

    Args
    ----
    file_bytes : Raw bytes of the uploaded PDF file.
    topic      : The course topic (used to focus the extraction).
    filename   : Original filename (for MIME type detection).

    Returns
    -------
    str : Markdown-formatted key points extracted from the document.

    Raises
    ------
    AIServiceError : If the upload or extraction call fails.
    """
    try:
        from google import genai
        from google.genai import types
    except ImportError as e:
        raise AIServiceError(
            "google-genai not installed. Run: pip install google-genai"
        ) from e

    if not config.GEMINI_API_KEY:
        raise AIServiceError("GEMINI_API_KEY not configured.")

    client = genai.Client(api_key=config.GEMINI_API_KEY)

    # Write bytes to a temporary file — the File API requires a file path
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = Path(tmp.name)

    try:
        logger.info("[Gemini] Uploading PDF for multimodal extraction: %s", filename)

        # Upload the file to the File API
        uploaded_file = client.files.upload(
            file=tmp_path,
            config=types.UploadFileConfig(
                mime_type="application/pdf",
                display_name=filename,
            ),
        )

        logger.info("[Gemini] File uploaded: %s, extracting key points...", uploaded_file.name)

        # Build the extraction prompt
        prompt = build_multimodal_extraction_prompt(topic)

        # Retry loop for quota errors (no Llama fallback for multimodal)
        import time
        last_error = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                response = client.models.generate_content(
                    model=config.GEMINI_MODEL,
                    contents=[
                        types.Part.from_uri(
                            file_uri=uploaded_file.uri,
                            mime_type="application/pdf",
                        ),
                        types.Part.from_text(text=prompt),
                    ],
                    config=types.GenerateContentConfig(
                        system_instruction=SYSTEM_MULTIMODAL,
                    ),
                )

                key_points = response.text.strip()
                logger.info("[Gemini] Extracted %d chars of key points", len(key_points))
                return key_points

            except Exception as inner_e:
                last_error = inner_e
                if _is_quota_error(inner_e) and attempt < _MAX_RETRIES:
                    delay = _RETRY_BASE_DELAY * (2 ** (attempt - 1))  # exponential backoff
                    logger.warning(
                        "[Gemini] Quota hit on PDF extraction attempt %d/%d — "
                        "retrying in %ds. Error: %s",
                        attempt, _MAX_RETRIES, delay, inner_e,
                    )
                    time.sleep(delay)
                    continue
                # Non-quota error or last attempt — break and raise
                break

        # All retries exhausted or non-quota error
        if _is_quota_error(last_error):
            raise AIServiceError(
                "PDF analysis is temporarily unavailable due to high demand. "
                "Please try again in a few minutes."
            )
        raise AIServiceError(f"Gemini multimodal extraction failed: {last_error}")

    except AIServiceError:
        raise
    finally:
        # Clean up temp file
        try:
            tmp_path.unlink()
        except Exception:
            pass
