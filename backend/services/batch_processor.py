
import threading
import json
import os
import time
import traceback
from models.database import db, Document, ExtractionResult, Batch
from services.image_preprocessor import preprocess, preprocess_pages
from services.ocr_engine import extract_text, get_full_text, extract_text_pages, get_full_text_pages
from services.document_classifier import classify_document
from services.vision_extractor import extract_fields, extract_fields_pages


DEFAULT_BATCH_STEPS = ['deskew', 'binarize']
DEFAULT_DOC_TIMEOUT_SECONDS = 600


def _get_batch_preprocess_steps():
    """
    Faster defaults for batch throughput.
    Can be overridden via BATCH_PREPROCESS_STEPS="deskew,denoise,..."
    """
    configured = (os.environ.get('BATCH_PREPROCESS_STEPS') or '').strip()
    if not configured:
        return DEFAULT_BATCH_STEPS
    steps = [s.strip() for s in configured.split(',') if s.strip()]
    return steps or DEFAULT_BATCH_STEPS


def _is_batch_stopping(batch_id):
    batch = Batch.query.get(batch_id)
    return bool(batch and batch.status in {'stopping', 'stopped'})


def _save_extraction_result(doc_id, full_text, page_texts, detections, steps, structured_fields, page_results):
    ex_row = ExtractionResult.query.filter_by(document_id=doc_id).first()
    payload = {
        "document": structured_fields or {},
        "pages": page_results or []
    }
    raw_payload = {
        "full_text": full_text or "",
        "pages": page_texts or []
    }
    if ex_row:
        ex_row.raw_text = json.dumps(raw_payload)
        ex_row.detections = json.dumps(detections)
        ex_row.preprocessing_steps = json.dumps(steps)
        ex_row.extracted_fields = json.dumps(payload)
    else:
        ex_row = ExtractionResult(
            document_id=doc_id,
            raw_text=json.dumps(raw_payload),
            detections=json.dumps(detections),
            preprocessing_steps=json.dumps(steps),
            extracted_fields=json.dumps(payload)
        )
        db.session.add(ex_row)


def _extract_pdf_text_layer(file_path):
    """
    Fast path for digital PDFs with embedded text.
    Returns per-page texts when enough text is available, else None.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return None

    min_chars = int(os.environ.get('BATCH_PDF_TEXT_MIN_CHARS', '40'))
    min_ratio = float(os.environ.get('BATCH_PDF_TEXT_MIN_RATIO', '0.8'))

    doc = fitz.open(file_path)
    try:
        page_texts = []
        non_empty_pages = 0
        for i in range(len(doc)):
            text = (doc[i].get_text("text") or "").strip()
            page_texts.append(text)
            if len(text) >= min_chars:
                non_empty_pages += 1

        if not page_texts:
            return None

        ratio = non_empty_pages / len(page_texts)
        if ratio < min_ratio:
            return None
        return page_texts
    finally:
        doc.close()


def process_batch_item(app, batch_id, doc_id):
    with app.app_context():
        doc = Document.query.get(doc_id)
        if not doc:
            return
        try:
            if _is_batch_stopping(batch_id):
                doc.status = 'error'
                doc.error_message = 'Stopped by user'
                db.session.commit()
                return

            doc.status = 'processing'
            doc.error_message = None
            db.session.commit()

            started_at = time.time()
            timeout_seconds = int(os.environ.get('BATCH_DOC_TIMEOUT_SECONDS', str(DEFAULT_DOC_TIMEOUT_SECONDS)))
            batch_steps = _get_batch_preprocess_steps()
            ext = doc.file_path.rsplit('.', 1)[-1].lower()
            if ext == 'pdf':
                text_layer_pages = _extract_pdf_text_layer(doc.file_path)
                if text_layer_pages is not None:
                    if _is_batch_stopping(batch_id):
                        raise InterruptedError("Stopped by user")
                    page_texts = text_layer_pages
                    full_text = " ".join(t for t in page_texts if t)
                    detections = {"pages": [[] for _ in page_texts]}
                    steps = {"mode": "pdf_text_layer", "pages": [[] for _ in page_texts]}
                else:
                    pdf_zoom = float(os.environ.get('BATCH_PDF_RENDER_SCALE', '1.35'))
                    preprocessed_pages, pages_steps = preprocess_pages(
                        doc.file_path,
                        steps=batch_steps,
                        pdf_zoom=pdf_zoom
                    )
                    detections_pages = []
                    for page_img in preprocessed_pages:
                        if _is_batch_stopping(batch_id):
                            raise InterruptedError("Stopped by user")
                        if (time.time() - started_at) > timeout_seconds:
                            raise TimeoutError(f"Processing exceeded {timeout_seconds}s")
                        detections_pages.append(extract_text(page_img))
                    page_texts, full_text = get_full_text_pages(detections_pages)
                    detections = {"pages": detections_pages}
                    steps = {"pages": pages_steps, "pdf_render_scale": pdf_zoom}
            else:
                if _is_batch_stopping(batch_id):
                    raise InterruptedError("Stopped by user")
                if (time.time() - started_at) > timeout_seconds:
                    raise TimeoutError(f"Processing exceeded {timeout_seconds}s")
                preprocessed_img, steps_list = preprocess(doc.file_path, steps=batch_steps)
                detections_list = extract_text(preprocessed_img)
                full_text = get_full_text(detections_list)
                detections = detections_list
                steps = steps_list
                page_texts = [full_text]

            if _is_batch_stopping(batch_id):
                raise InterruptedError("Stopped by user")
            if (time.time() - started_at) > timeout_seconds:
                raise TimeoutError(f"Processing exceeded {timeout_seconds}s")
            if not doc.doc_type:
                classification = classify_document(doc.file_path)
                doc.doc_type = classification['doc_type']

            if ext == 'pdf':
                partial_page_results = []
                partial_doc_fields = {}

                def _write_partial_snapshot(partial_pages, partial_document):
                    nonlocal partial_page_results, partial_doc_fields
                    partial_page_results = list(partial_pages or [])
                    partial_doc_fields = dict(partial_document or {})
                    _save_extraction_result(
                        doc_id=doc_id,
                        full_text=full_text,
                        page_texts=page_texts,
                        detections=detections,
                        steps=steps,
                        structured_fields=partial_doc_fields,
                        page_results=partial_page_results
                    )
                    doc.status = 'processing'
                    db.session.commit()
                    if _is_batch_stopping(batch_id):
                        raise InterruptedError("Stopped by user")
                    if (time.time() - started_at) > timeout_seconds:
                        raise TimeoutError(f"Processing exceeded {timeout_seconds}s")

                structured_fields, schema, page_results = extract_fields_pages(
                    doc.file_path,
                    doc.doc_type,
                    ocr_text_pages=page_texts,
                    ocr_raw_text=full_text,
                    use_image_input=False,
                    progress_callback=_write_partial_snapshot
                )
            else:
                structured_fields, schema = extract_fields(
                    doc.file_path,
                    doc.doc_type,
                    ocr_raw_text=full_text,
                    use_image_input=False
                )
                page_results = [{
                    "page_index": 0,
                    "ocr_text": full_text,
                    "extracted_fields": structured_fields
                }]

            _save_extraction_result(
                doc_id=doc_id,
                full_text=full_text,
                page_texts=page_texts,
                detections=detections,
                steps=steps,
                structured_fields=structured_fields,
                page_results=page_results
            )
            doc.status = 'extracted'
            doc.error_message = None
            db.session.commit()

        except (TimeoutError, InterruptedError) as e:
            if ext == 'pdf' and 'partial_page_results' in locals() and partial_page_results:
                partial_indexes = [p.get("page_index") for p in partial_page_results if isinstance(p, dict)]
                partial_page_texts = [
                    page_texts[idx] for idx in partial_indexes
                    if isinstance(idx, int) and 0 <= idx < len(page_texts)
                ]
                if isinstance(detections, dict) and isinstance(detections.get("pages"), list):
                    partial_detections = {
                        "pages": [
                            detections["pages"][idx] for idx in partial_indexes
                            if isinstance(idx, int) and 0 <= idx < len(detections["pages"])
                        ]
                    }
                else:
                    partial_detections = detections

                _save_extraction_result(
                    doc_id=doc_id,
                    full_text=" ".join(t for t in partial_page_texts if t),
                    page_texts=partial_page_texts,
                    detections=partial_detections,
                    steps=steps,
                    structured_fields=partial_doc_fields,
                    page_results=partial_page_results
                )
                doc.status = 'extracted'
                doc.error_message = f"Partial extraction: {str(e)}"
            else:
                doc.status = 'error'
                doc.error_message = str(e)
            db.session.commit()

        except Exception as e:
            print(f"\n❌ BATCH ERROR for doc_id={doc_id}")
            print(f"   File: {doc.file_path}")
            print(f"   Error: {str(e)}")
            print(f"   Traceback:\n{traceback.format_exc()}")
            doc.status = 'error'
            doc.error_message = str(e)
            db.session.commit()


def start_batch(app, batch_id, doc_ids, max_workers=None):
    if max_workers is None:
        max_workers = int(os.environ.get('BATCH_MAX_WORKERS', '4'))
    semaphore = threading.Semaphore(max_workers)

    def worker(doc_id):
        with semaphore:
            process_batch_item(app, batch_id, doc_id)
            with app.app_context():
                batch = Batch.query.get(batch_id)
                if batch:
                    batch.processed_count += 1
                    db.session.commit()

    threads = []
    for doc_id in doc_ids:
        t = threading.Thread(target=worker, args=(doc_id,))
        t.start()
        threads.append(t)

    def finalise():
        for t in threads:
            t.join()
        with app.app_context():
            batch = Batch.query.get(batch_id)
            if batch:
                docs = Document.query.filter(Document.id.in_(doc_ids)).all() if doc_ids else []
                success = sum(1 for d in docs if d.status == 'extracted')
                failed = sum(1 for d in docs if d.status == 'error')
                if batch.status in {'stopping', 'stopped'}:
                    batch.status = 'stopped'
                elif failed == 0:
                    batch.status = 'done'
                elif success == 0:
                    batch.status = 'failed'
                else:
                    batch.status = 'done_with_errors'
                db.session.commit()

    threading.Thread(target=finalise).start()