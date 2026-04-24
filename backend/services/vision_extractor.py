
import json
import os
import time
import base64
from openai import OpenAI

SCHEMAS_DIR = os.path.join(os.path.dirname(__file__), '..', 'extraction_schemas')
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
REQUEST_TIMEOUT_SECONDS = int(os.environ.get("MISTRAL_TIMEOUT_SECONDS", "600"))
MAX_RETRIES = int(os.environ.get("MISTRAL_MAX_RETRIES", "5"))
MULTIPAGE_SINGLE_CALL_THRESHOLD = int(os.environ.get("MULTIPAGE_SINGLE_CALL_THRESHOLD", "12"))
MULTIPAGE_CHUNK_SIZE = int(os.environ.get("MULTIPAGE_CHUNK_SIZE", "8"))

def _load_schema(doc_type):
    path = os.path.join(SCHEMAS_DIR, f'{doc_type}.json')
    if not os.path.exists(path):
        path = os.path.join(SCHEMAS_DIR, 'form.json')
    with open(path) as f:
        return json.load(f)

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


def _safe_json_loads(text):
    candidates = []
    extracted = _extract_json_text(text).strip()
    if extracted:
        candidates.append(extracted)
    raw = (text or "").strip()
    if raw and raw != extracted:
        candidates.append(raw)

    decoder = json.JSONDecoder()
    last_error = None

    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError as e:
            last_error = e
            for idx, ch in enumerate(candidate):
                if ch not in "{[":
                    continue
                try:
                    parsed, _ = decoder.raw_decode(candidate[idx:])
                    return parsed
                except json.JSONDecodeError:
                    continue

    if last_error:
        raise last_error
    raise ValueError("Unable to parse JSON response")


def _file_to_base64_png(image_path):
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

Use ONLY this OCR text as the source of truth and extract the following fields.
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
- Do not infer values not present in OCR text; use null when unsure
- Return only the JSON, no explanation"""


def _build_multipage_prompt(schema, page_texts, start_page_index, include_document):
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

    pages_payload = [
        {"page_index": start_page_index + i, "ocr_text": txt or ""}
        for i, txt in enumerate(page_texts)
    ]

    document_part = (
        ',\n  "document": {\n' + fields_json + '\n  }'
        if include_document else ''
    )

    return (
        "You are an expert document data extractor.\n\n"
        "Extract structured fields for EACH page using OCR text only.\n"
        "Do not invent values; use null when missing.\n"
        "Return STRICT JSON only in this exact shape:\n"
        "{\n"
        "  \"pages\": [\n"
        "    {\n"
        "      \"page_index\": <int>,\n"
        "      \"extracted_fields\": {\n"
        f"{fields_json}\n"
        "      }\n"
        "    }\n"
        "  ]"
        f"{document_part}\n"
        "}\n\n"
        "Each field value should be either:\n"
        "- {\"value\": <value>, \"confidence\": \"high|medium|low\"}\n"
        "- or a raw value (it will be normalized)\n\n"
        "OCR pages JSON:\n"
        f"{json.dumps(pages_payload, ensure_ascii=True)}"
    )


def _normalise_fields(raw_fields):
    normalised = {}
    for key, val in raw_fields.items():
        if isinstance(val, dict) and 'value' in val:
            normalised[key] = val
        else:
            normalised[key] = {'value': val, 'confidence': 'medium'}
    return normalised


def _merge_field_dicts(field_dicts):
    confidence_rank = {"high": 3, "medium": 2, "low": 1}
    merged = {}

    def is_present(value):
        return value not in (None, "", [], {})

    for fields in field_dicts:
        if not isinstance(fields, dict):
            continue
        for key, entry in fields.items():
            candidate = entry if isinstance(entry, dict) else {"value": entry, "confidence": "medium"}
            cand_value = candidate.get("value")
            cand_conf = candidate.get("confidence", "medium")

            if key not in merged:
                merged[key] = {"value": cand_value, "confidence": cand_conf}
                continue

            current = merged[key]
            cur_value = current.get("value")
            cur_conf = current.get("confidence", "medium")

            if is_present(cand_value) and not is_present(cur_value):
                merged[key] = {"value": cand_value, "confidence": cand_conf}
                continue

            if is_present(cand_value) and is_present(cur_value):
                if confidence_rank.get(cand_conf, 0) > confidence_rank.get(cur_conf, 0):
                    merged[key] = {"value": cand_value, "confidence": cand_conf}

    return merged


def _extract_multipage_text_bundle(client, model, schema, page_texts, start_page_index, include_document):
    prompt = _build_multipage_prompt(schema, page_texts, start_page_index, include_document)
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
    }
    response = _create_chat_completion_with_retry(client, payload)
    parsed = _safe_json_loads(response.choices[0].message.content or "")

    raw_pages = parsed.get("pages", []) if isinstance(parsed, dict) else []
    page_results = []
    for idx, page_obj in enumerate(raw_pages):
        page_index = page_obj.get("page_index", start_page_index + idx)
        fields = _normalise_fields(page_obj.get("extracted_fields", {}))
        local_idx = page_index - start_page_index
        ocr_text = page_texts[local_idx] if 0 <= local_idx < len(page_texts) else ""
        page_results.append({
            "page_index": page_index,
            "ocr_text": ocr_text,
            "extracted_fields": fields,
        })

    if len(page_results) != len(page_texts):
        # Fallback alignment when model returns incomplete page list.
        fallback = []
        by_index = {p["page_index"]: p for p in page_results}
        for i, txt in enumerate(page_texts):
            pg = start_page_index + i
            fallback.append(by_index.get(pg, {
                "page_index": pg,
                "ocr_text": txt,
                "extracted_fields": {},
            }))
        page_results = fallback

    raw_document = parsed.get("document", {}) if isinstance(parsed, dict) else {}
    document_fields = _normalise_fields(raw_document) if raw_document else {}
    return page_results, document_fields


def _extract_from_text(client, model, schema, ocr_text):
    prompt = _build_prompt(schema, ocr_text)
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}]}],
    }
    response = _create_chat_completion_with_retry(client, payload)
    raw_fields = _safe_json_loads(response.choices[0].message.content or "")
    return _normalise_fields(raw_fields)


def _extract_from_image_and_text(client, model, schema, image_b64, mime_type, ocr_text):
    prompt = _build_prompt(schema, ocr_text)
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{image_b64}"}},
                ],
            }
        ],
    }
    response = _create_chat_completion_with_retry(client, payload)
    raw_fields = _safe_json_loads(response.choices[0].message.content or "")
    return _normalise_fields(raw_fields)


def extract_fields(image_path, doc_type, ocr_raw_text='', use_image_input=True):
    api_key = os.environ["MISTRAL_API_KEY"]
    model = os.environ.get("MISTRAL_MODEL", "pixtral-12b-2409")
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.mistral.ai/v1",
        timeout=REQUEST_TIMEOUT_SECONDS
    )

    schema = _load_schema(doc_type)
    if use_image_input:
        image_b64, mime_type = _file_to_base64_png(image_path)
        normalised = _extract_from_image_and_text(
            client, model, schema, image_b64, mime_type, ocr_raw_text
        )
    else:
        normalised = _extract_from_text(client, model, schema, ocr_raw_text)
    return normalised, schema


def extract_fields_pages(image_path, doc_type, ocr_text_pages, ocr_raw_text='', use_image_input=True):
    """Extract one structured output per page and a merged document output."""
    api_key = os.environ["MISTRAL_API_KEY"]
    model = os.environ.get("MISTRAL_MODEL", "pixtral-12b-2409")
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.mistral.ai/v1",
        timeout=REQUEST_TIMEOUT_SECONDS
    )
    schema = _load_schema(doc_type)

    # Batch text-only optimized path:
    # <= threshold: one call for all pages
    # > threshold: chunked calls + deterministic local merge.
    if not use_image_input:
        page_texts = list(ocr_text_pages or [])
        if not page_texts:
            page_texts = [ocr_raw_text or ""]

        all_page_results = []
        document_candidates = []

        if len(page_texts) <= MULTIPAGE_SINGLE_CALL_THRESHOLD:
            page_results, document_fields = _extract_multipage_text_bundle(
                client=client,
                model=model,
                schema=schema,
                page_texts=page_texts,
                start_page_index=0,
                include_document=True,
            )
            all_page_results.extend(page_results)
            if document_fields:
                document_candidates.append(document_fields)
        else:
            for start in range(0, len(page_texts), MULTIPAGE_CHUNK_SIZE):
                chunk = page_texts[start:start + MULTIPAGE_CHUNK_SIZE]
                page_results, chunk_document = _extract_multipage_text_bundle(
                    client=client,
                    model=model,
                    schema=schema,
                    page_texts=chunk,
                    start_page_index=start,
                    include_document=True,
                )
                all_page_results.extend(page_results)
                if chunk_document:
                    document_candidates.append(chunk_document)

        all_page_results.sort(key=lambda p: p.get("page_index", 0))
        page_field_dicts = [p.get("extracted_fields", {}) for p in all_page_results]
        merged_normalised = _merge_field_dicts(document_candidates + page_field_dicts)
        return merged_normalised, schema, all_page_results

    page_results = []
    pages_b64, mime_type = _file_to_base64_pages(image_path) if use_image_input else ([], None)

    for idx, ocr_page_text in enumerate(ocr_text_pages):
        if use_image_input and idx < len(pages_b64):
            normalised = _extract_from_image_and_text(
                client, model, schema, pages_b64[idx], mime_type, ocr_page_text
            )
        else:
            normalised = _extract_from_text(client, model, schema, ocr_page_text)
        page_results.append({
            "page_index": idx,
            "ocr_text": ocr_page_text,
            "extracted_fields": normalised,
        })

    if not page_results:
        ocr_page_text = ocr_raw_text or ""
        if use_image_input and len(pages_b64) > 0:
            first_page = _extract_from_image_and_text(
                client, model, schema, pages_b64[0], mime_type, ocr_page_text
            )
        else:
            first_page = _extract_from_text(client, model, schema, ocr_page_text)
        page_results.append({
            "page_index": 0,
            "ocr_text": ocr_page_text,
            "extracted_fields": first_page,
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
    merged_raw = _safe_json_loads(merge_response.choices[0].message.content or "")
    merged_normalised = _normalise_fields(merged_raw)

    return merged_normalised, schema, page_results