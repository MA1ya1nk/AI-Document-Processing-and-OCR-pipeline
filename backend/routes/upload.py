
from flask import Blueprint, request, jsonify
import os, uuid
from models.database import db, Document, ExtractionResult   
from config import Config

upload_bp = Blueprint('upload', __name__)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

@upload_bp.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in request'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed'}), 400

    # Generate a unique filename to avoid collisions
    ext = file.filename.rsplit('.', 1)[1].lower()
    unique_filename = f"{uuid.uuid4().hex}.{ext}"
    file_path = os.path.join(Config.UPLOAD_FOLDER, unique_filename)

    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    file.save(file_path)

    # Save record to DB
    doc = Document(
        filename=unique_filename,
        original_filename=file.filename,
        file_path=file_path,
        file_size=os.path.getsize(file_path),
        mime_type=file.content_type,
        status='uploaded'
    )
    db.session.add(doc)
    db.session.commit()

    return jsonify({'message': 'File uploaded successfully', 'document': doc.to_dict()}), 201


# @upload_bp.route('/api/documents', methods=['GET'])
# def list_documents():
#     docs = Document.query.order_by(Document.uploaded_at.desc()).all()
#     return jsonify({'documents': [d.to_dict() for d in docs]})


@upload_bp.route('/api/documents', methods=['GET'])
def list_documents():
    """Return all documents with their extraction results if available."""
    docs = Document.query.order_by(Document.uploaded_at.desc()).all()
    result_list = []
    for doc in docs:
        d = doc.to_dict()
        ex = ExtractionResult.query.filter_by(document_id=doc.id).first()
        if ex:
            import json
            d['has_extraction'] = True
            d['extracted_fields'] = json.loads(ex.extracted_fields or '{}')
            d['detections'] = json.loads(ex.detections or '[]')
            d['preprocessing_steps'] = json.loads(ex.preprocessing_steps or '[]')
            d['raw_text'] = ex.raw_text or ''
        else:
            d['has_extraction'] = False
        result_list.append(d)
    return jsonify({'documents': result_list})    



@upload_bp.route('/api/documents/<int:doc_id>', methods=['DELETE'])
def delete_document(doc_id):
    doc = Document.query.get_or_404(doc_id)
    ex = ExtractionResult.query.filter_by(document_id=doc_id).first()
    if ex:
        db.session.delete(ex)
    # delete file from disk
    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)
    db.session.delete(doc)
    db.session.commit()
    return jsonify({'deleted': True})
