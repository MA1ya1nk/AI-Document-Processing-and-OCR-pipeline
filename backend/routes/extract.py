
from flask import Blueprint, jsonify, send_file, request
from models.database import db, Document, ExtractionResult
from services.image_preprocessor import preprocess, preprocess_pages
from services.ocr_engine import extract_text, get_full_text, extract_text_pages, get_full_text_pages
from services.document_classifier import classify_document
from services.vision_extractor import extract_fields, extract_fields_pages
from services.bbox_renderer import draw_bboxes
from services.export_service import to_json, to_csv_string, to_excel_bytes
import os, json, io

extract_bp = Blueprint('extract', __name__)


@extract_bp.route('/api/classify/<int:doc_id>', methods=['POST'])
def classify(doc_id):
    """Step 1: just classify the document type."""
    doc = Document.query.get_or_404(doc_id)
    try:
        result = classify_document(doc.file_path)
        doc.doc_type = result['doc_type']
        db.session.commit()
        return jsonify({
            'document_id': doc_id,
            'doc_type': result['doc_type'],
            'confidence': result['confidence'],
            'reasoning': result['reasoning']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@extract_bp.route('/api/extract/<int:doc_id>', methods=['POST'])
def extract(doc_id):
    """
    Full pipeline:
    1. Preprocess image
    2. Run EasyOCR
    3. Classify doc type (if not already set)
    4. Run Groq Vision extraction
    5. Save everything to DB
    """
    doc = Document.query.get_or_404(doc_id)

    # Allow caller to pass doc_type override
    body = request.get_json(silent=True) or {}
    override_type = body.get('doc_type')

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

        # Step 3: classify if no type yet
        classification = None
        if override_type:
            doc.doc_type = override_type
        elif not doc.doc_type:
            classification = classify_document(doc.file_path)
            doc.doc_type = classification['doc_type']

        # Step 4: Groq structured extraction
        if ext == 'pdf':
            structured_fields, schema, page_results = extract_fields_pages(
                doc.file_path,
                doc.doc_type,
                ocr_text_pages=page_texts,
                ocr_raw_text=full_text,
            )
        else:
            structured_fields, schema = extract_fields(
                doc.file_path,
                doc.doc_type,
                ocr_raw_text=full_text
            )
            page_results = [{
                "page_index": 0,
                "ocr_text": full_text,
                "extracted_fields": structured_fields,
            }]

        # Step 5: save
        existing = ExtractionResult.query.filter_by(document_id=doc_id).first()
        if existing:
            existing.raw_text = json.dumps({"full_text": full_text, "pages": page_texts})
            existing.detections = json.dumps(detections)
            existing.preprocessing_steps = json.dumps(steps)
            existing.extracted_fields = json.dumps({
                "document": structured_fields,
                "pages": page_results
            })
        else:
            result_row = ExtractionResult(
                document_id=doc_id,
                raw_text=json.dumps({"full_text": full_text, "pages": page_texts}),
                detections=json.dumps(detections),
                preprocessing_steps=json.dumps(steps),
                extracted_fields=json.dumps({
                    "document": structured_fields,
                    "pages": page_results
                })
            )
            db.session.add(result_row)

        doc.status = 'extracted'
        db.session.commit()

        return jsonify({
            'document_id': doc_id,
            'doc_type': doc.doc_type,
            'classification': classification,
            'status': 'extracted',
            'full_text': full_text,
            'page_texts': page_texts,
            'detections': detections,
            'extracted_fields': structured_fields,
            'page_results': page_results,
            'schema': schema,
            'preprocessing_steps': steps,
            'total_detections': (
                sum(len(p) for p in detections.get('pages', []))
                if isinstance(detections, dict)
                else len(detections)
            )
        })

    except Exception as e:
        import traceback
        print("\n" + "="*60)
        print(f"❌ EXTRACTION ERROR doc_id={doc_id}")
        print(f"   Type: {type(e).__name__}")
        print(f"   Message: {str(e)}")
        print("   Traceback:")
        print(traceback.format_exc())
        print("="*60 + "\n")
        doc.status = 'error'
        db.session.commit()
        return jsonify({'error': str(e)}), 500


@extract_bp.route('/api/documents/<int:doc_id>/fields', methods=['PUT'])
def update_fields(doc_id):
    """Let the user correct extracted field values from the UI."""
    body = request.get_json()
    result_row = ExtractionResult.query.filter_by(document_id=doc_id).first_or_404()
    payload = json.loads(result_row.extracted_fields or '{}')
    fields = payload.get('document', payload) if isinstance(payload, dict) else {}

    for key, new_value in body.items():
        if key in fields:
            fields[key]['value'] = new_value
            fields[key]['manually_corrected'] = True

    if isinstance(payload, dict) and 'document' in payload:
        payload['document'] = fields
        result_row.extracted_fields = json.dumps(payload)
    else:
        result_row.extracted_fields = json.dumps(fields)
    db.session.commit()
    return jsonify({'updated': True, 'fields': fields})


@extract_bp.route('/api/documents/<int:doc_id>/preview', methods=['GET'])
def preview_with_bboxes(doc_id):
    doc = Document.query.get_or_404(doc_id)
    result_row = ExtractionResult.query.filter_by(document_id=doc_id).first()
    if not result_row:
        return jsonify({'error': 'No extraction yet'}), 404
    page = request.args.get('page', default=0, type=int)
    detections_payload = json.loads(result_row.detections)
    if isinstance(detections_payload, dict) and 'pages' in detections_payload:
        pages = detections_payload.get('pages') or []
        page_detections = pages[page] if 0 <= page < len(pages) else []
    else:
        page_detections = detections_payload
    annotated_path = draw_bboxes(doc.file_path, page_detections, page=page)
    return send_file(annotated_path, mimetype='image/jpeg')


@extract_bp.route('/api/export/<int:doc_id>', methods=['GET'])
def export_document(doc_id):
    fmt = request.args.get('format', 'json')
    doc = Document.query.get_or_404(doc_id)
    result_row = ExtractionResult.query.filter_by(document_id=doc_id).first_or_404()

    if fmt == 'json':
        return jsonify(to_json(doc, result_row))

    elif fmt == 'csv':
        csv_str = to_csv_string(doc, result_row)
        buf = io.BytesIO(csv_str.encode())
        return send_file(buf, mimetype='text/csv',
                         download_name=f'doc_{doc_id}.csv', as_attachment=True)

    elif fmt == 'excel':
        excel_bytes = to_excel_bytes(doc, result_row)
        buf = io.BytesIO(excel_bytes)
        return send_file(buf,
                         mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                         download_name=f'doc_{doc_id}.xlsx', as_attachment=True)

    return jsonify({'error': 'Unknown format'}), 400