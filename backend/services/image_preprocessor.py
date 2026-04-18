
import cv2
import numpy as np
import os

def load_image(file_path):
    """Load image from disk. If PDF, convert first page to image first."""
    ext = file_path.rsplit('.', 1)[-1].lower()

    if ext == 'pdf':
        try:
            import fitz  # PyMuPDF
            pdf_doc = fitz.open(file_path)
            page = pdf_doc[0]  # take first page only
            mat = fitz.Matrix(2.0, 2.0)  # zoom 2x for better OCR quality
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            pdf_doc.close()
            nparr = np.frombuffer(img_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError(f"Could not decode PDF page from {file_path}")
            return img
        except ImportError:
            raise ValueError("PyMuPDF not installed. Run: pip install pymupdf")

    # Normal image files (jpg, png, tiff, webp)
    img = cv2.imread(file_path)
    if img is None:
        raise ValueError(f"Could not load image from {file_path}")
    return img


# Everything below this line stays exactly the same as before
def deskew(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.bitwise_not(gray)
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    coords = np.column_stack(np.where(thresh > 0))
    if len(coords) == 0:
        return img
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    if abs(angle) < 0.5:
        return img
    (h, w) = img.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(img, M, (w, h),
                             flags=cv2.INTER_CUBIC,
                             borderMode=cv2.BORDER_REPLICATE)
    return rotated


def denoise(img):
    return cv2.fastNlMeansDenoisingColored(img, None, h=10, hColor=10,
                                           templateWindowSize=7,
                                           searchWindowSize=21)


def binarize(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    binary = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=11,
        C=2
    )
    return binary


def enhance_contrast(img):
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    l_enhanced = clahe.apply(l)
    enhanced_lab = cv2.merge([l_enhanced, a, b])
    return cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)


def preprocess(file_path, steps=None):
    if steps is None:
        steps = ['deskew', 'denoise', 'enhance_contrast', 'binarize']

    img = load_image(file_path)
    steps_applied = []

    pipeline = {
        'deskew': deskew,
        'denoise': denoise,
        'enhance_contrast': enhance_contrast,
        'binarize': binarize,
    }

    for step in steps:
        if step in pipeline:
            img = pipeline[step](img)
            steps_applied.append(step)

    return img, steps_applied