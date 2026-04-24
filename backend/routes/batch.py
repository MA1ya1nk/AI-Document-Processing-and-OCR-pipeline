
from flask import Blueprint, request, jsonify, send_file, current_app
# from models.database import db, Document, ExtractionResult, Batch, BatchItem
from models.database import db, Document, ExtractionResult, Batch, BatchItem
from services.batch_processor import start_batch
import os, uuid, json, io, zipfile
from datetime import datetime, timedelta

batch_bp = Blueprint('batch', __name__)

def _allowed_upload(file_obj, allowed_exts):
    filename = file_obj.filename or ''
    if '.' in filename and filename.rsplit('.', 1)[-1].lower() in allowed_exts:
        return True
    mime = (file_obj.content_type or '').lower()
    return mime in {'application/pdf', 'application/x-pdf'}


def _serialize_batch_documents(batch_id):
    items = BatchItem.query.filter_by(batch_id=batch_id).all()
    doc_ids = [i.document_id for i in items]
    docs = Document.query.filter(Document.id.in_(doc_ids)).all() if doc_ids else []
    docs_out = []
    for doc in docs:
        d = doc.to_dict()
        ex = ExtractionResult.query.filter_by(document_id=doc.id).first()
        if ex:
            extracted_payload = json.loads(ex.extracted_fields or '{}')
            raw_payload = json.loads(ex.raw_text or '{}') if (ex.raw_text or '').startswith('{') else {'full_text': ex.raw_text or '', 'pages': []}
            detections_payload = json.loads(ex.detections or '[]')
            preprocessing_payload = json.loads(ex.preprocessing_steps or '[]')

            if isinstance(extracted_payload, dict) and 'document' in extracted_payload:
                d['extracted_fields'] = extracted_payload.get('document') or {}
                d['page_results'] = extracted_payload.get('pages') or []
            else:
                d['extracted_fields'] = extracted_payload
                d['page_results'] = [{
                    'page_index': 0,
                    'ocr_text': raw_payload.get('full_text', ''),
                    'extracted_fields': extracted_payload
                }]

            d['raw_text'] = raw_payload.get('full_text', '')
            d['page_texts'] = raw_payload.get('pages', [])
            d['detections'] = detections_payload
            d['preprocessing_steps'] = preprocessing_payload
        else:
            d['extracted_fields'] = {}
            d['raw_text'] = ''
            d['detections'] = []
            d['preprocessing_steps'] = []
            d['page_results'] = []
            d['page_texts'] = []
        docs_out.append(d)
    return docs_out


@batch_bp.route('/api/upload/batch', methods=['POST'])
def upload_batch():
    # Reconcile stale active batches that no longer have running documents.
    candidate_batches = Batch.query.filter(Batch.status.in_(['processing', 'stopping'])).all()
    for b in candidate_batches:
        items = BatchItem.query.filter_by(batch_id=b.id).all()
        doc_ids = [i.document_id for i in items]
        running_docs = []
        if doc_ids:
            running_docs = Document.query.filter(
                Document.id.in_(doc_ids),
                Document.status.in_(['processing', 'uploaded'])
            ).all()
        if not running_docs:
            b.status = 'stopped'

    # Reconcile stale single-doc processing rows older than timeout window.
    stale_cutoff = datetime.utcnow() - timedelta(
        seconds=int(os.environ.get('BATCH_DOC_TIMEOUT_SECONDS', '600')) + 120
    )
    stale_single_docs = Document.query.filter(
        Document.status == 'processing',
        Document.batch_id.is_(None),
        Document.uploaded_at < stale_cutoff
    ).all()
    for d in stale_single_docs:
        d.status = 'error'
        d.error_message = 'Marked stale and auto-recovered'

    if candidate_batches or stale_single_docs:
        db.session.commit()

    active_batch = Batch.query.filter(Batch.status.in_(['processing', 'stopping'])).first()
    active_single_doc = Document.query.filter(
        Document.status == 'processing',
        Document.batch_id.is_(None)
    ).first()
    if active_batch or active_single_doc:
        return jsonify({
            'error': 'A batch/document is already processing. Wait for completion before starting another batch.'
        }), 409

    files = request.files.getlist('files')
    if not files:
        return jsonify({'error': 'No files'}), 400

    from config import Config
    allowed = Config.ALLOWED_EXTENSIONS

    batch = Batch(total_count=len(files))
    db.session.add(batch)
    db.session.flush()

    doc_ids = []
    docs_out = []

    for file in files:
        if not file.filename:
            continue
        if not _allowed_upload(file, allowed):
            continue
        ext = file.filename.rsplit('.', 1)[-1].lower()
        if ext not in allowed:
            ext = 'pdf' if (file.content_type or '').lower() in {'application/pdf', 'application/x-pdf'} else ext

        unique_name = f"{uuid.uuid4().hex}.{ext}"
        file_path = os.path.join(Config.UPLOAD_FOLDER, unique_name)
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        file.save(file_path)

        doc = Document(
            filename=unique_name,
            original_filename=file.filename,
            file_path=file_path,
            file_size=os.path.getsize(file_path),
            mime_type=file.content_type,
            status='uploaded',
            batch_id=batch.id
        )
        db.session.add(doc)
        db.session.flush()

        item = BatchItem(batch_id=batch.id, document_id=doc.id)
        db.session.add(item)
        doc_ids.append(doc.id)
        docs_out.append(doc.to_dict())

    db.session.commit()

    app = current_app._get_current_object()
    start_batch(app, batch.id, doc_ids)

    return jsonify({
        'batch_id': batch.id,
        'total': len(doc_ids),
        'documents': docs_out,
        'message': f'Processing {len(doc_ids)} documents in background'
    }), 202


@batch_bp.route('/api/batch/<int:batch_id>/status', methods=['GET'])
def batch_status(batch_id):
    batch = Batch.query.get_or_404(batch_id)
    docs_out = _serialize_batch_documents(batch_id)
    return jsonify({
        'batch': batch.to_dict(),
        'documents': docs_out
    })


@batch_bp.route('/api/batch/<int:batch_id>/stop', methods=['POST'])
def stop_batch(batch_id):
    batch = Batch.query.get_or_404(batch_id)
    if batch.status in {'done', 'failed', 'done_with_errors', 'stopped'}:
        return jsonify({'stopped': False, 'message': 'Batch already finished', 'batch': batch.to_dict()}), 200

    # Hard stop immediately: mark batch terminal and fail running docs.
    batch.status = 'stopped'
    items = BatchItem.query.filter_by(batch_id=batch_id).all()
    doc_ids = [i.document_id for i in items]
    if doc_ids:
        processing_docs = Document.query.filter(
            Document.id.in_(doc_ids),
            Document.status.in_(['processing', 'uploaded'])
        ).all()
        for doc in processing_docs:
            doc.status = 'error'
            doc.error_message = 'Stopped by user'
    db.session.commit()
    return jsonify({'stopped': True, 'batch': batch.to_dict()}), 202


@batch_bp.route('/api/batch/<int:batch_id>/force-stop', methods=['POST'])
def force_stop_batch(batch_id):
    batch = Batch.query.get_or_404(batch_id)
    if batch.status in {'done', 'failed', 'done_with_errors', 'stopped'}:
        return jsonify({'stopped': False, 'message': 'Batch already finished', 'batch': batch.to_dict()}), 200

    batch.status = 'stopped'
    items = BatchItem.query.filter_by(batch_id=batch_id).all()
    doc_ids = [i.document_id for i in items]
    if doc_ids:
        running_docs = Document.query.filter(
            Document.id.in_(doc_ids),
            Document.status.in_(['processing', 'uploaded'])
        ).all()
        for doc in running_docs:
            doc.status = 'error'
            doc.error_message = 'Force-stopped by user'

    db.session.commit()
    return jsonify({'stopped': True, 'forced': True, 'batch': batch.to_dict()}), 202


@batch_bp.route('/api/batch/active', methods=['GET'])
def list_active_batches():
    active_batches = Batch.query.filter(Batch.status.in_(['processing', 'stopping'])).order_by(Batch.created_at.desc()).all()
    payload = []
    for batch in active_batches:
        payload.append({
            'batch': batch.to_dict(),
            'documents': _serialize_batch_documents(batch.id)
        })
    return jsonify({'batches': payload})


@batch_bp.route('/api/batch/<int:batch_id>/export', methods=['GET'])
def export_batch(batch_id):
    fmt = request.args.get('format', 'zip')
    items = BatchItem.query.filter_by(batch_id=batch_id).all()
    doc_ids = [i.document_id for i in items]

    if fmt == 'csv':
        import csv
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['id', 'filename', 'doc_type', 'status'])
        for doc_id in doc_ids:
            doc = Document.query.get(doc_id)
            ex = ExtractionResult.query.filter_by(document_id=doc_id).first()
            if doc:
                fields = json.loads(ex.extracted_fields or '{}') if ex else {}
                row = [doc.id, doc.original_filename, doc.doc_type, doc.status]
                for key, data in list(fields.items())[:10]:
                    if not isinstance(data.get('value'), list):
                        row.append(str(data.get('value', '')))
                writer.writerow(row)
        buf = io.BytesIO(output.getvalue().encode())
        return send_file(buf, mimetype='text/csv',
                         download_name=f'batch_{batch_id}.csv', as_attachment=True)

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        for doc_id in doc_ids:
            doc = Document.query.get(doc_id)
            ex = ExtractionResult.query.filter_by(document_id=doc_id).first()
            if doc and ex:
                payload = json.loads(ex.extracted_fields or '{}')
                fields = payload.get('document', payload) if isinstance(payload, dict) else {}
                data = {
                    'document_id': doc.id,
                    'filename': doc.original_filename,
                    'doc_type': doc.doc_type,
                    'fields': fields
                }
                zf.writestr(
                    f'{doc.original_filename}_{doc_id}.json',
                    json.dumps(data, indent=2)
                )
    zip_buf.seek(0)
    return send_file(zip_buf, mimetype='application/zip',
                     download_name=f'batch_{batch_id}.zip', as_attachment=True)