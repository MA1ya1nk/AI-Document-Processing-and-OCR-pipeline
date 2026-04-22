
import base64
import json
import os
import time
from openai import OpenAI

SCHEMAS_DIR = os.path.join(os.path.dirname(__file__), '..', 'extraction_schemas')
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

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


def _file_to_base64_pages(image_path):
    ext = image_path.rsplit('.', 1)[-1].lower()
    if ext == 'pdf':
        import fitz
        pdf_doc = fitz.open(image_path)
        pages = []
        for i in range(len(pdf_doc)):
            page = pdf_doc[i]
            mat = fitz.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=mat)
            pages.append(base64.b64encode(pix.tobytes("png")).decode('utf-8'))
        pdf_doc.close()
        return pages, 'image/png'
    one, mime = _file_to_base64_png(image_path)
    return [one], mime


def _extract_json_text(text):
    text = (text or "").strip()
    if text.startswith("```"):
        parts = text.split("```")
        if len(parts) > 1:
            text = parts[1].strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end >= start:
        return text[start:end + 1]
    return text


def _create_chat_completion_with_retry(client, payload, max_attempts=4):
    wait_seconds = 2
    for attempt in range(max_attempts):
        try:
            return client.chat.completions.create(**payload)
        except Exception as e:
            status_code = getattr(e, "status_code", None)
            is_last_attempt = attempt == max_attempts - 1
            if status_code not in RETRYABLE_STATUS_CODES or is_last_attempt:
                raise
            time.sleep(wait_seconds)
            wait_seconds *= 2


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
    api_key = os.environ["MISTRAL_API_KEY"]
    model = os.environ.get("MISTRAL_MODEL", "pixtral-12b-2409")
    client = OpenAI(api_key=api_key, base_url="https://api.mistral.ai/v1")

    schema = _load_schema(doc_type)
    prompt = _build_prompt(schema, ocr_raw_text)

    # Convert file to base64 PNG — handles both PDF and images
    image_b64, mime_type = _file_to_base64_png(image_path)

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{image_b64}"},
                    },
                ],
            }
        ]
    }
    response = _create_chat_completion_with_retry(client, payload)

    text = response.choices[0].message.content or ""
    json_text = _extract_json_text(text)

    raw_fields = json.loads(json_text.strip())

    normalised = {}
    for key, val in raw_fields.items():
        if isinstance(val, dict) and 'value' in val:
            normalised[key] = val
        else:
            normalised[key] = {'value': val, 'confidence': 'medium'}

    return normalised, schema


def extract_fields_pages(image_path, doc_type, ocr_text_pages, ocr_raw_text=''):
    """Extract one structured output per page and a merged document output."""
    api_key = os.environ["MISTRAL_API_KEY"]
    model = os.environ.get("MISTRAL_MODEL", "pixtral-12b-2409")
    client = OpenAI(api_key=api_key, base_url="https://api.mistral.ai/v1")
    schema = _load_schema(doc_type)

    pages_b64, mime_type = _file_to_base64_pages(image_path)
    page_results = []

    for idx, image_b64 in enumerate(pages_b64):
        ocr_page_text = ocr_text_pages[idx] if idx < len(ocr_text_pages) else ""
        page_prompt = _build_prompt(schema, ocr_page_text)
        payload = {
            "model": model,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": page_prompt},
                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_b64}"}},
                ],
            }],
        }
        response = _create_chat_completion_with_retry(client, payload)
        text = response.choices[0].message.content or ""
        raw_fields = json.loads(_extract_json_text(text).strip())
        normalised = {}
        for key, val in raw_fields.items():
            if isinstance(val, dict) and 'value' in val:
                normalised[key] = val
            else:
                normalised[key] = {'value': val, 'confidence': 'medium'}
        page_results.append({
            "page_index": idx,
            "ocr_text": ocr_page_text,
            "extracted_fields": normalised,
        })

    # Use full OCR text + all page fields to produce a merged document output.
    merged_context = {
        "page_fields": [p["extracted_fields"] for p in page_results]
    }
    merge_prompt = (
        _build_prompt(schema, ocr_raw_text) +
        "\n\nPage-wise extracted JSON candidates:\n" +
        json.dumps(merged_context, ensure_ascii=True) +
        "\n\nMerge these into one final best JSON output for the whole document."
    )
    merge_payload = {
        "model": model,
        "messages": [{"role": "user", "content": [{"type": "text", "text": merge_prompt}]}],
    }
    merge_response = _create_chat_completion_with_retry(client, merge_payload)
    merged_text = merge_response.choices[0].message.content or ""
    merged_raw = json.loads(_extract_json_text(merged_text).strip())
    merged_normalised = {}
    for key, val in merged_raw.items():
        if isinstance(val, dict) and 'value' in val:
            merged_normalised[key] = val
        else:
            merged_normalised[key] = {'value': val, 'confidence': 'medium'}

    return merged_normalised, schema, page_results