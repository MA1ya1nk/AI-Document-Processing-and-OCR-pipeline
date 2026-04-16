from flask import Blueprint, jsonify, send_file
from models.database import db, Document, ExtractionResult
from services.image_preprocessor import preprocess
from services.ocr_engine import extract_text, get_full_text
from services.bbox_renderer import draw_bboxes
import os, json, tempfile

extract_bp = Blueprint('extract', __name__)


@extract_bp.route('/api/extract/<int:doc_id>', methods=['POST'])
def extract(doc_id):
    doc = Document.query.get_or_404(doc_id)

    try:
        doc.status = 'processing'
        db.session.commit()

        # 1. Preprocess the image
        preprocessed_img, steps = preprocess(doc.file_path)

        # 2. Run OCR
        detections = extract_text(preprocessed_img)
        full_text = get_full_text(detections)

        # 3. Save result
        existing = ExtractionResult.query.filter_by(document_id=doc_id).first()
        if existing:
            existing.raw_text = full_text
            existing.detections = json.dumps(detections)
            existing.preprocessing_steps = json.dumps(steps)
        else:
            result = ExtractionResult(
                document_id=doc_id,
                raw_text=full_text,
                detections=json.dumps(detections),
                preprocessing_steps=json.dumps(steps)
            )
            db.session.add(result)

        doc.status = 'extracted'
        db.session.commit()

        return jsonify({
            'document_id': doc_id,
            'status': 'extracted',
            'full_text': full_text,
            'detections': detections,
            'preprocessing_steps': steps,
            'total_detections': len(detections)
        })

    except Exception as e:
        doc.status = 'error'
        db.session.commit()
        return jsonify({'error': str(e)}), 500


@extract_bp.route('/api/documents/<int:doc_id>/preview', methods=['GET'])
def preview_with_bboxes(doc_id):
    """Return the document image with bounding boxes drawn on it."""
    doc = Document.query.get_or_404(doc_id)
    result = ExtractionResult.query.filter_by(document_id=doc_id).first()

    if not result:
        return jsonify({'error': 'No extraction result yet'}), 404

    detections = json.loads(result.detections)

    # Draw boxes on a temp copy of the image
    annotated_path = draw_bboxes(doc.file_path, detections)
    return send_file(annotated_path, mimetype='image/jpeg')