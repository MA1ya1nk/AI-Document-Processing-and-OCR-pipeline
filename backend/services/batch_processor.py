
import threading
import json
import traceback  # ← add this
from models.database import db, Document, ExtractionResult, Batch, BatchItem
from services.image_preprocessor import preprocess, preprocess_pages
from services.ocr_engine import extract_text, get_full_text, extract_text_pages, get_full_text_pages
from services.document_classifier import classify_document
from services.vision_extractor import extract_fields, extract_fields_pages


def process_batch_item(app, doc_id):
    with app.app_context():
        doc = Document.query.get(doc_id)
        if not doc:
            return
        try:
            doc.status = 'processing'
            db.session.commit()

            ext = doc.file_path.rsplit('.', 1)[-1].lower()
            if ext == 'pdf':
                preprocessed_pages, pages_steps = preprocess_pages(doc.file_path)
                detections_pages = extract_text_pages(preprocessed_pages)
                page_texts, full_text = get_full_text_pages(detections_pages)
                detections = {"pages": detections_pages}
                steps = {"pages": pages_steps}
            else:
                preprocessed_img, steps_list = preprocess(doc.file_path)
                detections_list = extract_text(preprocessed_img)
                full_text = get_full_text(detections_list)
                detections = detections_list
                steps = steps_list
                page_texts = [full_text]

            if not doc.doc_type:
                classification = classify_document(doc.file_path)
                doc.doc_type = classification['doc_type']

            if ext == 'pdf':
                structured_fields, schema, page_results = extract_fields_pages(
                    doc.file_path, doc.doc_type, ocr_text_pages=page_texts, ocr_raw_text=full_text
                )
            else:
                structured_fields, schema = extract_fields(doc.file_path, doc.doc_type, full_text)
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


def start_batch(app, batch_id, doc_ids, max_workers=3):
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