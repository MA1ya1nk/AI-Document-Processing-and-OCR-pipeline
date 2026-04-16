from PIL import Image, ImageDraw, ImageFont
import tempfile, os

# Color map by confidence level
COLORS = {
    'high':   (34, 197, 94),   # green
    'medium': (234, 179, 8),   # yellow
    'low':    (239, 68, 68),   # red
}


def draw_bboxes(image_path, detections):
    """
    Draw colored bounding boxes on the original image.
    Returns path to the annotated image (saved in a temp file).
    """
    img = Image.open(image_path).convert('RGB')
    draw = ImageDraw.Draw(img)

    for det in detections:
        bbox = det['bbox']
        color = COLORS.get(det.get('confidence_label', 'medium'), (234, 179, 8))

        # Draw the quadrilateral outline
        points = [
            tuple(bbox['top_left']),
            tuple(bbox['top_right']),
            tuple(bbox['bottom_right']),
            tuple(bbox['bottom_left']),
        ]
        draw.polygon(points, outline=color)

        # Small label above the box
        label = f"{det['text'][:20]} ({det['confidence']:.0%})"
        draw.text(
            (bbox['top_left'][0], bbox['top_left'][1] - 12),
            label,
            fill=color
        )

    # Save to a temp file (not the original)
    tmp = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
    img.save(tmp.name, 'JPEG', quality=90)
    return tmp.name