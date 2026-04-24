
import threading
import json
import os
import traceback  # ← add this
from models.database import db, Document, ExtractionResult, Batch, BatchItem
from services.image_preprocessor import preprocess, preprocess_pages
from services.ocr_engine import extract_text, get_full_text, extract_text_pages, get_full_text_pages
from services.document_classifier import classify_document
from services.vision_extractor import extract_fields, extract_fields_pages


DEFAULT_BATCH_STEPS = ['deskew', 'binarize']


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


def process_batch_item(app, doc_id):
    with app.app_context():
        doc = Document.query.get(doc_id)
        if not doc:
            return
        try:
            doc.status = 'processing'
            db.session.commit()

            batch_steps = _get_batch_preprocess_steps()
            ext = doc.file_path.rsplit('.', 1)[-1].lower()
            if ext == 'pdf':
                text_layer_pages = _extract_pdf_text_layer(doc.file_path)
                if text_layer_pages is not None:
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
                    detections_pages = extract_text_pages(preprocessed_pages)
                    page_texts, full_text = get_full_text_pages(detections_pages)
                    detections = {"pages": detections_pages}
                    steps = {"pages": pages_steps, "pdf_render_scale": pdf_zoom}
            else:
                preprocessed_img, steps_list = preprocess(doc.file_path, steps=batch_steps)
                detections_list = extract_text(preprocessed_img)
                full_text = get_full_text(detections_list)
                detections = detections_list
                steps = steps_list
                page_texts = [full_text]

            if not doc.doc_type:
                classification = classify_document(doc.file_path)
                doc.doc_type = classification['doc_type']

            def _write_partial_snapshot(partial_pages, partial_document):
                ex_row = ExtractionResult.query.filter_by(document_id=doc_id).first()
                payload = {
                    "document": partial_document or {},
                    "pages": partial_pages or []
                }
                if ex_row:
                    ex_row.raw_text = json.dumps({"full_text": full_text, "pages": page_texts})
                    ex_row.detections = json.dumps(detections)
                    ex_row.preprocessing_steps = json.dumps(steps)
                    ex_row.extracted_fields = json.dumps(payload)
                else:
                    ex_row = ExtractionResult(
                        document_id=doc_id,
                        raw_text=json.dumps({"full_text": full_text, "pages": page_texts}),
                        detections=json.dumps(detections),
                        preprocessing_steps=json.dumps(steps),
                        extracted_fields=json.dumps(payload)
                    )
                    db.session.add(ex_row)
                # Keep document in processing state while partial pages stream in.
                doc.status = 'processing'
                db.session.commit()

            if ext == 'pdf':
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

            ex = ExtractionResult.query.filter_by(document_id=doc_id).first()
            if ex:
                ex.raw_text = json.dumps({"full_text": full_text, "pages": page_texts})
                ex.detections = json.dumps(detections)
                ex.preprocessing_steps = json.dumps(steps)
                ex.extracted_fields = json.dumps({
                    "document": structured_fields,
                    "pages": page_results
                })
            else:
                ex = ExtractionResult(
                    document_id=doc_id,
                    raw_text=json.dumps({"full_text": full_text, "pages": page_texts}),
                    detections=json.dumps(detections),
                    preprocessing_steps=json.dumps(steps),
                    extracted_fields=json.dumps({
                        "document": structured_fields,
                        "pages": page_results
                    })
                )
                db.session.add(ex)

            doc.status = 'extracted'
            db.session.commit()

        except Exception as e:
            print(f"\n❌ BATCH ERROR for doc_id={doc_id}")
            print(f"   File: {doc.file_path}")
            print(f"   Error: {str(e)}")
            print(f"   Traceback:\n{traceback.format_exc()}")  # ← this shows full error
            doc.status = 'error'
            doc.error_message = str(e)
            db.session.commit()


def start_batch(app, batch_id, doc_ids, max_workers=None):
    if max_workers is None:
        max_workers = int(os.environ.get('BATCH_MAX_WORKERS', '4'))
    semaphore = threading.Semaphore(max_workers)

    def worker(doc_id):
        with semaphore:
            process_batch_item(app, doc_id)
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
                batch.status = 'done'
                db.session.commit()

    threading.Thread(target=finalise).start()