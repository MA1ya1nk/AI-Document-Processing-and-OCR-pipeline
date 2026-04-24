// src/components/HistoryCard.jsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { deleteDocument } from '../services/api'
import ExportPanel from './ExportPanel'
import ErrorMessage from './ErrorMessage'

const STATUS_STYLE = {
  uploaded: 'status-uploaded',
  processing: 'status-processing',
  extracted: 'status-extracted',
  error: 'status-error',
}

const TYPE_ICONS = {
  invoice: '🧾', receipt: '🏪', business_card: '💼',
  form: '📋', id_card: '🪪', contract: '📄',
  report_letter: '✉️', handwritten_note: '✍️',
  whiteboard: '🖊️', table_spreadsheet: '📊'
}

const formatUtcTimestamp = (isoLike) => {
  if (!isoLike) return ''
  const hasTimezone = /([zZ]|[+-]\d{2}:\d{2})$/.test(isoLike)
  const normalized = hasTimezone ? isoLike : `${isoLike}Z`
  const parsed = new Date(normalized)
  return Number.isNaN(parsed.getTime()) ? String(isoLike) : parsed.toLocaleString()
}

export default function HistoryCard({ doc, onDeleted }) {
  const navigate = useNavigate()
  const badge = STATUS_STYLE[doc.status] || STATUS_STYLE.uploaded
  const icon = TYPE_ICONS[doc.doc_type] || '📁'
  const [error, setError] = useState('')

  const handleDelete = async () => {
    setError('')
    if (!confirm(`Delete ${doc.original_filename}?`)) return
    try {
      await deleteDocument(doc.id)
      onDeleted(doc.id)
    } catch (err) {
      setError('Delete failed: ' + (err.response?.data?.error || err.message))
    }
  }

  const handleReview = () => {
    if (!doc.has_extraction) return
    navigate(`/document/${doc.id}`, {
      state: {
        returnTo: '/history',
        doc,
        result: {
          doc_type: doc.doc_type,
          extracted_fields: doc.extracted_fields,
          detections: doc.detections,
          full_text: doc.raw_text,
          page_texts: doc.page_texts || [],
          page_results: doc.page_results || [],
          preprocessing_steps: doc.preprocessing_steps,
          total_detections: Array.isArray(doc.detections)
            ? doc.detections.length
            : ((doc.detections?.pages || []).reduce((sum, page) => sum + page.length, 0)),
          schema: null
        }
      }
    })
  }

  // Top 3 key fields to preview
  const fieldPreview = doc.extracted_fields
    ? Object.entries(doc.extracted_fields)
        .filter(([, v]) => v?.value && !Array.isArray(v?.value))
        .slice(0, 3)
    : []

  return (
    <div className="card" style={{ display: 'flex', width: '100%', gap: 16, alignItems: 'flex-start' }}>
      {/* Icon */}
      <div style={{
        width: 48, height: 48, borderRadius: 10,
        background: '#f3f4f6', display: 'flex',
        alignItems: 'center', justifyContent: 'center',
        fontSize: 22, flexShrink: 0
      }}>
        {icon}
      </div>

      {/* Main content */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <ErrorMessage message={error} />
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <strong style={{
            fontSize: 14, overflow: 'hidden',
            textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 260
          }}>
            {doc.original_filename}
          </strong>
          <span className={`pill ${badge}`}>
            {doc.status}
          </span>
          {doc.doc_type && (
            <span className="pill doc-type-pill">
              {doc.doc_type.replace('_', ' ')}
            </span>
          )}
        </div>

        {/* Date + size */}
        <p style={{ fontSize: 12, color: '#9ca3af', margin: '4px 0 8px' }}>
          {formatUtcTimestamp(doc.uploaded_at)} ·{' '}
          {(doc.file_size / 1024).toFixed(1)} KB
        </p>

        {/* Field preview */}
        {fieldPreview.length > 0 && (
          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
            {fieldPreview.map(([key, data]) => (
              <div key={key}>
                <span style={{ fontSize: 11, color: '#9ca3af' }}>
                  {key.replace('_', ' ')}
                </span>
                <p style={{ fontSize: 13, margin: '2px 0 0', color: '#111827' }}>
                  {String(data.value).slice(0, 40)}
                </p>
              </div>
            ))}
          </div>
        )}

        {/* Export */}
        {doc.has_extraction && <ExportPanel docId={doc.id} />}
      </div>

      {/* Actions */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6, flexShrink: 0 }}>
        {doc.has_extraction && (
          <button onClick={handleReview} className="btn btn-primary">
            Review
          </button>
        )}
        <button onClick={handleDelete} className="btn btn-danger">
          Delete
        </button>
      </div>
    </div>
  )
}