
import base64
import json
import os
import time
from openai import OpenAI

SUPPORTED_TYPES = [
    "invoice", "receipt", "business_card",
    "form", "id_card", "contract",
    "report_letter", "handwritten_note",
    "whiteboard", "table_spreadsheet"
]

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
REQUEST_TIMEOUT_SECONDS = int(os.environ.get("MISTRAL_TIMEOUT_SECONDS", "600"))
MAX_RETRIES = int(os.environ.get("MISTRAL_MAX_RETRIES", "5"))

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


def _create_chat_completion_with_retry(client, payload, max_attempts=MAX_RETRIES):
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


def classify_document(image_path):
    api_key = os.environ["MISTRAL_API_KEY"]
    model = os.environ.get("MISTRAL_MODEL", "pixtral-12b-2409")
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.mistral.ai/v1",
        timeout=REQUEST_TIMEOUT_SECONDS
    )

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

    result = json.loads(json_text.strip())

    if result.get('doc_type') not in SUPPORTED_TYPES:
        result['doc_type'] = 'form'
        result['confidence'] = 0.3

    return result