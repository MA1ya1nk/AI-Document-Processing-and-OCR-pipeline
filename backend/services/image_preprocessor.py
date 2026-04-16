import cv2
import numpy as np


def load_image(file_path):
    
    img = cv2.imread(file_path)
    if img is None:
        raise ValueError(f"Could not load image from {file_path}")
    return img


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

    # Rotate the image around its center
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
    """
    Convert to black and white using adaptive thresholding.
    Adaptive means it adjusts the threshold per small region —
    this handles uneven lighting (common in phone photos).
    Returns a single-channel (grayscale) image.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    binary = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=11,   # Size of neighborhood area
        C=2             # Constant subtracted from mean
    )
    return binary


def enhance_contrast(img):
    """
    Apply CLAHE (Contrast Limited Adaptive Histogram Equalization).
    Makes faded text on old documents much more readable.
    Works per channel in LAB color space for better results.
    """
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