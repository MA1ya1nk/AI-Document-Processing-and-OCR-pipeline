
import threading
import json
import traceback  # ← add this
from models.database import db, Document, ExtractionResult, Batch, BatchItem
from services.image_preprocessor import preprocess
from services.ocr_engine import extract_text, get_full_text
from services.document_classifier import classify_document
from services.vision_extractor import extract_fields


def process_batch_item(app, doc_id):
    with app.app_context():
        doc = Document.query.get(doc_id)
        if not doc:
            return
        try:
            doc.status = 'processing'
            db.session.commit()

            preprocessed_img, steps = preprocess(doc.file_path)
            detections = extract_text(preprocessed_img)
            full_text = get_full_text(detections)

            if not doc.doc_type:
                classification = classify_document(doc.file_path)
                doc.doc_type = classification['doc_type']

            structured_fields, schema = extract_fields(
                doc.file_path, doc.doc_type, full_text
            )

            ex = ExtractionResult.query.filter_by(document_id=doc_id).first()
            if ex:
                ex.raw_text = full_text
                ex.detections = json.dumps(detections)
                ex.preprocessing_steps = json.dumps(steps)
                ex.extracted_fields = json.dumps(structured_fields)
            else:
                ex = ExtractionResult(
                    document_id=doc_id,
                    raw_text=full_text,
                    detections=json.dumps(detections),
                    preprocessing_steps=json.dumps(steps),
                    extracted_fields=json.dumps(structured_fields)
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