
from google import genai
from google.genai import types
import base64, json, os

SUPPORTED_TYPES = [
    "invoice", "receipt", "business_card",
    "form", "id_card", "contract",
    "report_letter", "handwritten_note",
    "whiteboard", "table_spreadsheet"
]

def _file_to_base64_png(image_path):
    """Same helper — converts PDF or image to PNG base64."""
    ext = image_path.rsplit('.', 1)[-1].lower()

    if ext == 'pdf':
        import fitz
        pdf_doc = fitz.open(image_path)
        page = pdf_doc[0]
        mat = fitz.Matrix(2.0, 2.0)
        pix = page.get_pixmap(matrix=mat)
        img_bytes = pix.tobytes("png")
        pdf_doc.close()
        return base64.b64encode(img_bytes).decode('utf-8'), 'image/png'

    with open(image_path, 'rb') as f:
        data = f.read()
    mime = {
        'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
        'png': 'image/png',  'tiff': 'image/tiff',
        'webp': 'image/webp'
    }.get(ext, 'image/jpeg')
    return base64.b64encode(data).decode('utf-8'), mime


def classify_document(image_path):
    client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])

    prompt = f"""Classify this document into exactly one of these categories:
{', '.join(SUPPORTED_TYPES)}

Return ONLY a JSON object with these exact keys:
{{
  "doc_type": "<one of the categories above>",
  "confidence": <float between 0 and 1>,
  "reasoning": "<one sentence explaining why>"
}}

Do not include any text outside the JSON."""

    image_b64, mime_type = _file_to_base64_png(image_path)

    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=[
            types.Part.from_bytes(
                data=base64.b64decode(image_b64),
                mime_type=mime_type          # image/png for PDFs now
            ),
            prompt
        ]
    )

    text = response.text.strip()
    if text.startswith('```'):
        text = text.split('```')[1]
        if text.startswith('json'):
            text = text[4:]

    result = json.loads(text.strip())

    if result.get('doc_type') not in SUPPORTED_TYPES:
        result['doc_type'] = 'form'
        result['confidence'] = 0.3

    return result