
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)
    mime_type = db.Column(db.String(100))
    status = db.Column(db.String(50), default='uploaded')
    doc_type = db.Column(db.String(100))
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'filename': self.filename,
            'original_filename': self.original_filename,
            'file_size': self.file_size,
            'mime_type': self.mime_type,
            'status': self.status,
            'doc_type': self.doc_type,
            'uploaded_at': self.uploaded_at.isoformat()
        }


class ExtractionResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('document.id'), nullable=False)
    raw_text = db.Column(db.Text)
    detections = db.Column(db.Text)           # JSON list — OCR bboxes
    preprocessing_steps = db.Column(db.Text)  # JSON list
    extracted_fields = db.Column(db.Text)     # JSON dict — structured output
    created_at = db.Column(db.DateTime, default=datetime.utcnow)        