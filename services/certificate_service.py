"""
services/certificate_service.py
───────────────────────────────
Handles dynamic certificate generation by stamping the student's name
onto a template image/PDF at specified coordinates.
"""

from __future__ import annotations
import os
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

def generate_certificate(
    template_path: str,
    student_name: str,
    x: int,
    y: int,
    output_path: str,
    font_size: int = 40
) -> str:
    """
    Stamps student_name onto the image at (x, y) and saves to output_path.
    Returns the final output path.
    """
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Template not found: {template_path}")

    # Load image
    with Image.open(template_path) as img:
        # Convert to RGB if necessary (e.g. for PNG with alpha)
        if img.mode != "RGB":
            img = img.convert("RGB")
        
        draw = ImageDraw.Draw(img)
        
        # Try to find a nice font
        font = None
        font_paths = [
            "arial.ttf",
            "C:\\Windows\\Fonts\\arial.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        ]
        
        for fp in font_paths:
            try:
                font = ImageFont.truetype(fp, font_size)
                break
            except:
                continue
        
        if font is None:
            # Fallback to default
            font = ImageFont.load_default()

        # Draw the text
        # (x, y) is the top-left coordinate of the text box
        draw.text((x, y), student_name, fill="black", font=font)
        
        # Save result
        img.save(output_path)
    
    return output_path
