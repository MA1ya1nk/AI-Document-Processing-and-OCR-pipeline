
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

def to_utc_iso(dt):
    if not dt:
        return None
    return f"{dt.isoformat()}Z"


class Batch(db.Model):
    id              = db.Column(db.Integer, primary_key=True)
    total_count     = db.Column(db.Integer, default=0)
    processed_count = db.Column(db.Integer, default=0)
    status          = db.Column(db.String(50), default='processing')
    created_at      = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'total_count': self.total_count,
            'processed_count': self.processed_count,
            'status': self.status,
            'progress_pct': round(
                (self.processed_count / self.total_count * 100)
                if self.total_count else 0, 1
            ),
            'created_at': to_utc_iso(self.created_at)
        }


class Document(db.Model):
    id                = db.Column(db.Integer, primary_key=True)
    filename          = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path         = db.Column(db.String(500), nullable=False)
    file_size         = db.Column(db.Integer)
    mime_type         = db.Column(db.String(100))
    status            = db.Column(db.String(50), default='uploaded')
    doc_type          = db.Column(db.String(100))
    uploaded_at       = db.Column(db.DateTime, default=datetime.utcnow)
    batch_id          = db.Column(db.Integer, db.ForeignKey('batch.id'), nullable=True)
    error_message     = db.Column(db.Text, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'original_filename': self.original_filename,
            'file_size': self.file_size,
            'mime_type': self.mime_type,
            'status': self.status,
            'doc_type': self.doc_type,
            'uploaded_at': to_utc_iso(self.uploaded_at),
            'batch_id': self.batch_id
        }


class ExtractionResult(db.Model):
    id                  = db.Column(db.Integer, primary_key=True)
    document_id         = db.Column(db.Integer, db.ForeignKey('document.id'), nullable=False)
    raw_text            = db.Column(db.Text)
    detections          = db.Column(db.Text)
    preprocessing_steps = db.Column(db.Text)
    extracted_fields    = db.Column(db.Text)
    created_at          = db.Column(db.DateTime, default=datetime.utcnow)


class BatchItem(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    batch_id    = db.Column(db.Integer, db.ForeignKey('batch.id'))
    document_id = db.Column(db.Integer, db.ForeignKey('document.id'))