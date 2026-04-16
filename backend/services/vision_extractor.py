# backend/services/vision_extractor.py
import google.generativeai as genai
import base64, json, os

SCHEMAS_DIR = os.path.join(os.path.dirname(__file__), '..', 'extraction_schemas')

def _load_schema(doc_type):
    """Load the JSON schema for a given doc type."""
    path = os.path.join(SCHEMAS_DIR, f'{doc_type}.json')
    if not os.path.exists(path):
        path = os.path.join(SCHEMAS_DIR, 'form.json')  # fallback
    with open(path) as f:
        return json.load(f)

def _image_to_base64(image_path):
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

def _get_mime_type(image_path):
    ext = image_path.rsplit('.', 1)[-1].lower()
    return {'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
            'png': 'image/png', 'tiff': 'image/tiff',
            'webp': 'image/webp'}.get(ext, 'image/jpeg')

def _build_prompt(schema, ocr_text):
    """
    Build the extraction prompt using the schema field list
    and the OCR raw text as a hint.
    """
    field_list = []
    for f in schema['fields']:
        if f['type'] == 'table':
            cols = ', '.join(f['columns'])
            field_list.append(
                f'  "{f["key"]}": [{{"' + '": "", "'.join(f['columns']) + '": ""}}]  // array of objects'
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

Important rules:
- Use the OCR text as a starting hint but trust the image for accuracy
- Numbers should be strings (preserve formatting like "$1,234.00")
- Dates in ISO format: YYYY-MM-DD
- Do not add any keys not listed above
- Return only the JSON, no explanation"""

def extract_fields(image_path, doc_type, ocr_raw_text=''):
    """
    Main function: takes image + doc_type + OCR text,
    returns structured field dict from Gemini.

    Returns:
    {
      "vendor_name": { "value": "Acme Corp", "confidence": "high" },
      "total": { "value": "$1,200.00", "confidence": "high" },
      "line_items": { "value": [...], "confidence": "medium" },
      ...
    }
    """
    genai.configure(api_key=os.environ['GEMINI_API_KEY'])
    model = genai.GenerativeModel('gemini-2.5-flash')

    schema = _load_schema(doc_type)
    prompt = _build_prompt(schema, ocr_raw_text)

    image_data = _image_to_base64(image_path)
    mime = _get_mime_type(image_path)

    response = model.generate_content([
        {'mime_type': mime, 'data': image_data},
        prompt
    ])

    text = response.text.strip()
    if text.startswith('```'):
        text = text.split('```')[1]
        if text.startswith('json'):
            text = text[4:]

    raw_fields = json.loads(text.strip())

    # Normalise: wrap plain values into { value, confidence } dicts
    # Gemini sometimes returns just the value, sometimes already wrapped
    normalised = {}
    for key, val in raw_fields.items():
        if isinstance(val, dict) and 'value' in val:
            normalised[key] = val
        else:
            normalised[key] = {
                'value': val,
                'confidence': 'medium'  # default when not specified
            }

    return normalised, schema