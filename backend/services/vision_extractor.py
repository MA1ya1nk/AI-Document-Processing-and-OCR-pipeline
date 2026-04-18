
from google import genai
from google.genai import types
import base64, json, os, tempfile, cv2

SCHEMAS_DIR = os.path.join(os.path.dirname(__file__), '..', 'extraction_schemas')

def _load_schema(doc_type):
    path = os.path.join(SCHEMAS_DIR, f'{doc_type}.json')
    if not os.path.exists(path):
        path = os.path.join(SCHEMAS_DIR, 'form.json')
    with open(path) as f:
        return json.load(f)

def _file_to_base64_png(image_path):
    """
    Convert any file (jpg, png, PDF) to a PNG base64 string.
    For PDFs we use PyMuPDF to render first page.
    For images we just read and encode directly.
    """
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

    # Normal image — read and encode
    with open(image_path, 'rb') as f:
        data = f.read()
    mime = {
        'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
        'png': 'image/png',  'tiff': 'image/tiff',
        'webp': 'image/webp'
    }.get(ext, 'image/jpeg')
    return base64.b64encode(data).decode('utf-8'), mime


def _build_prompt(schema, ocr_text):
    field_list = []
    for f in schema['fields']:
        if f['type'] == 'table':
            cols = '", "'.join(f['columns'])
            field_list.append(
                f'  "{f["key"]}": [{{"' + cols + '": ""}}]'
            )
        else:
            field_list.append(f'  "{f["key"]}": ""')
    fields_json = ',\n'.join(field_list)

    return f"""You are an expert document data extractor.

The OCR engine already extracted this raw text from the document:
---
{ocr_text}
---

Now look at the document image carefully and extract the following fields.
Return ONLY a JSON object with these exact keys.
For missing fields use null. For tables return an array of objects.
Add a "confidence" key per field: "high", "medium", or "low".

{{
{fields_json}
}}

Rules:
- Numbers should be strings (preserve formatting like "$1,234.00")
- Dates in ISO format: YYYY-MM-DD
- Do not add any keys not listed above
- Return only the JSON, no explanation"""


def extract_fields(image_path, doc_type, ocr_raw_text=''):
    client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])

    schema = _load_schema(doc_type)
    prompt = _build_prompt(schema, ocr_raw_text)

    # Convert file to base64 PNG — handles both PDF and images
    image_b64, mime_type = _file_to_base64_png(image_path)

    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=[
            types.Part.from_bytes(
                data=base64.b64decode(image_b64),
                mime_type=mime_type          # always image/png for PDFs now
            ),
            prompt
        ]
    )

    text = response.text.strip()
    if text.startswith('```'):
        text = text.split('```')[1]
        if text.startswith('json'):
            text = text[4:]

    raw_fields = json.loads(text.strip())

    normalised = {}
    for key, val in raw_fields.items():
        if isinstance(val, dict) and 'value' in val:
            normalised[key] = val
        else:
            normalised[key] = {'value': val, 'confidence': 'medium'}

    return normalised, schema