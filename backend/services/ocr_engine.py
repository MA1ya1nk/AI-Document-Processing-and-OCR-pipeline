import easyocr
import cv2
import numpy as np


_reader = None

def get_reader():
    global _reader
    if _reader is None:
        print("Loading EasyOCR models (first time only)...")
        _reader = easyocr.Reader(['en'], gpu=False)
        print("EasyOCR ready.")
    return _reader


def extract_text(img):
    """
    Run EasyOCR on a preprocessed image.

    img: numpy array (output from preprocessor)

    Returns a list of detections, each being a dict:
    {
        'text': 'Invoice #1234',
        'confidence': 0.95,
        'bbox': {
            'top_left': [x, y],
            'top_right': [x, y],
            'bottom_right': [x, y],
            'bottom_left': [x, y]
        },
        'x': int,        # leftmost x (for sorting/positioning)
        'y': int,        # topmost y
        'width': int,
        'height': int
    }
    """
    reader = get_reader()

    
    if len(img.shape) == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

    
    results = reader.readtext(img, detail=1)

    detections = []
    for (bbox_points, text, confidence) in results:
        
        pts = np.array(bbox_points, dtype=int)
        x = int(pts[:, 0].min())
        y = int(pts[:, 1].min())
        w = int(pts[:, 0].max()) - x
        h = int(pts[:, 1].max()) - y

        detections.append({
            'text': text.strip(),
            'confidence': round(float(confidence), 3),
            'confidence_label': confidence_label(confidence),
            'bbox': {
                'top_left':     [int(bbox_points[0][0]), int(bbox_points[0][1])],
                'top_right':    [int(bbox_points[1][0]), int(bbox_points[1][1])],
                'bottom_right': [int(bbox_points[2][0]), int(bbox_points[2][1])],
                'bottom_left':  [int(bbox_points[3][0]), int(bbox_points[3][1])],
            },
            'x': x,
            'y': y,
            'width': w,
            'height': h,
        })

    
    detections.sort(key=lambda d: (d['y'], d['x']))
    return detections


def confidence_label(score):
   
    if score >= 0.85:
        return 'high'
    elif score >= 0.60:
        return 'medium'
    return 'low'


def get_full_text(detections):
   
    return ' '.join(d['text'] for d in detections)