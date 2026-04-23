"""
services/certificate_service.py
───────────────────────────────
Handles dynamic certificate generation by stamping the student's name
onto a template image at specified coordinates.

All I/O operates fully in-memory (BytesIO) — no files are read from or
written to the local filesystem.
"""

from __future__ import annotations
import io
from PIL import Image, ImageDraw, ImageFont


def generate_certificate(
    template_bytes: bytes,
    student_name: str,
    x: int,
    y: int,
    font_size: int = 40,
) -> bytes:
    """
    Stamps student_name onto a certificate template image at (x, y).

    Args:
        template_bytes: Raw bytes of the template image (JPEG/PNG).
        student_name:   Name to stamp on the certificate.
        x, y:           Top-left coordinate of the text box.
        font_size:      Font size in points.

    Returns:
        JPEG bytes of the generated certificate.
    """
    with Image.open(io.BytesIO(template_bytes)) as img:
        # Ensure RGB so we can always save as JPEG
        if img.mode != "RGB":
            img = img.convert("RGB")

        draw = ImageDraw.Draw(img)

        # Try to find a nice font
        font = None
        font_paths = [
            "arial.ttf",
            "C:\\Windows\\Fonts\\arial.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        for fp in font_paths:
            try:
                font = ImageFont.truetype(fp, font_size)
                break
            except Exception:
                continue

        if font is None:
            font = ImageFont.load_default()

        draw.text((x, y), student_name, fill="black", font=font)

        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        return buf.getvalue()
