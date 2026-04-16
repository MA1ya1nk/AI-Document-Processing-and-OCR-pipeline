# backend/services/document_classifier.py
import google.generativeai as genai
import base64, json, os
from PIL import Image

SUPPORTED_TYPES = [
    "invoice", "receipt", "business_card",
    "form", "id_card", "contract",
    "report_letter", "handwritten_note",
    "whiteboard", "table_spreadsheet"
]

def _image_to_base64(image_path):
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

def _get_mime_type(image_path):
    ext = image_path.rsplit('.', 1)[-1].lower()
    return {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
            'png': 'image/png', 'pdf': 'application/pdf',
            'tiff': 'image/tiff', 'webp': 'image/webp'}.get(ext, 'image/jpeg')

def classify_document(image_path):
    """
    Send image to Gemini Vision and get back:
    { doc_type: str, confidence: float, reasoning: str }
    """
    genai.configure(api_key=os.environ['GEMINI_API_KEY'])
    model = genai.GenerativeModel('gemini-2.5-flash')

    prompt = f"""Classify this document into exactly one of these categories:
{', '.join(SUPPORTED_TYPES)}

Return ONLY a JSON object with these exact keys:
{{
  "doc_type": "<one of the categories above>",
  "confidence": <float between 0 and 1>,
  "reasoning": "<one sentence explaining why>"
}}

Do not include any text outside the JSON."""

    image_data = _image_to_base64(image_path)
    mime = _get_mime_type(image_path)

    response = model.generate_content([
        {'mime_type': mime, 'data': image_data},
        prompt
    ])

    text = response.text.strip()
    # Strip markdown code fences if Gemini wraps in them
    if text.startswith('```'):
        text = text.split('```')[1]
        if text.startswith('json'):
            text = text[4:]

    result = json.loads(text.strip())

    # Normalise: ensure doc_type is in our supported list
    if result.get('doc_type') not in SUPPORTED_TYPES:
        result['doc_type'] = 'form'
        result['confidence'] = 0.3

    return result