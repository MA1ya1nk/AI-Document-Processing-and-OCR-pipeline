
from flask import Blueprint, jsonify, send_file, request
from models.database import db, Document, ExtractionResult
from services.image_preprocessor import preprocess
from services.ocr_engine import extract_text, get_full_text
from services.document_classifier import classify_document
from services.vision_extractor import extract_fields
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
    4. Run Gemini Vision extraction
    5. Save everything to DB
    """
    doc = Document.query.get_or_404(doc_id)

    # Allow caller to pass doc_type override
    body = request.get_json(silent=True) or {}
    override_type = body.get('doc_type')

    try:
        doc.status = 'processing'
        db.session.commit()

        # Step 1: preprocess
        preprocessed_img, steps = preprocess(doc.file_path)

        # Step 2: OCR
        detections = extract_text(preprocessed_img)
        full_text = get_full_text(detections)

        # Step 3: classify if no type yet
        classification = None
        if override_type:
            doc.doc_type = override_type
        elif not doc.doc_type:
            classification = classify_document(doc.file_path)
            doc.doc_type = classification['doc_type']

        # Step 4: Gemini structured extraction
        structured_fields, schema = extract_fields(
            doc.file_path,
            doc.doc_type,
            ocr_raw_text=full_text
        )

        # Step 5: save
        existing = ExtractionResult.query.filter_by(document_id=doc_id).first()
        if existing:
            existing.raw_text = full_text
            existing.detections = json.dumps(detections)
            existing.preprocessing_steps = json.dumps(steps)
            existing.extracted_fields = json.dumps(structured_fields)
        else:
            result_row = ExtractionResult(
                document_id=doc_id,
                raw_text=full_text,
                detections=json.dumps(detections),
                preprocessing_steps=json.dumps(steps),
                extracted_fields=json.dumps(structured_fields)
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
            'detections': detections,
            'extracted_fields': structured_fields,
            'schema': schema,
            'preprocessing_steps': steps,
            'total_detections': len(detections)
        })

    except Exception as e:
        doc.status = 'error'
        db.session.commit()
        return jsonify({'error': str(e)}), 500


@extract_bp.route('/api/documents/<int:doc_id>/fields', methods=['PUT'])
def update_fields(doc_id):
    """Let the user correct extracted field values from the UI."""
    body = request.get_json()
    result_row = ExtractionResult.query.filter_by(document_id=doc_id).first_or_404()
    fields = json.loads(result_row.extracted_fields or '{}')

    for key, new_value in body.items():
        if key in fields:
            fields[key]['value'] = new_value
            fields[key]['manually_corrected'] = True

    result_row.extracted_fields = json.dumps(fields)
    db.session.commit()
    return jsonify({'updated': True, 'fields': fields})


@extract_bp.route('/api/documents/<int:doc_id>/preview', methods=['GET'])
def preview_with_bboxes(doc_id):
    doc = Document.query.get_or_404(doc_id)
    result_row = ExtractionResult.query.filter_by(document_id=doc_id).first()
    if not result_row:
        return jsonify({'error': 'No extraction yet'}), 404
    detections = json.loads(result_row.detections)
    annotated_path = draw_bboxes(doc.file_path, detections)
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