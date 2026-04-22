
from PIL import Image, ImageDraw
import tempfile, os
import numpy as np

COLORS = {
    'high':   (34, 197, 94),
    'medium': (234, 179, 8),
    'low':    (239, 68, 68),
}

def _load_as_pil_image(image_path, page=0):
    """
    Load any file (jpg, png, PDF) as a PIL Image.
    For PDFs, render first page using PyMuPDF.
    """
    ext = image_path.rsplit('.', 1)[-1].lower()

    if ext == 'pdf':
        import fitz
        pdf_doc = fitz.open(image_path)
        page_idx = max(0, min(page, len(pdf_doc) - 1))
        page = pdf_doc[page_idx]
        mat     = fitz.Matrix(2.0, 2.0)   # 2x zoom for quality
        pix     = page.get_pixmap(matrix=mat)
        pdf_doc.close()
        # Convert PyMuPDF pixmap → PIL Image
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        return img

    # Normal image
    return Image.open(image_path).convert('RGB')


def draw_bboxes(image_path, detections, page=0):
    """
    Draw colored bounding boxes on the document image.
    Returns path to annotated temp file.
    """
    img  = _load_as_pil_image(image_path, page=page)
    draw = ImageDraw.Draw(img)

    for det in detections:
        bbox  = det['bbox']
        color = COLORS.get(det.get('confidence_label', 'medium'), (234, 179, 8))

        points = [
            tuple(bbox['top_left']),
            tuple(bbox['top_right']),
            tuple(bbox['bottom_right']),
            tuple(bbox['bottom_left']),
        ]
        draw.polygon(points, outline=color)

        label = f"{det['text'][:20]} ({det['confidence']:.0%})"
        draw.text(
            (bbox['top_left'][0], max(0, bbox['top_left'][1] - 12)),
            label,
            fill=color
        )

    tmp = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
    img.save(tmp.name, 'JPEG', quality=90)
    return tmp.name