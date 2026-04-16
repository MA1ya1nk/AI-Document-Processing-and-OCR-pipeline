import { useState } from 'react'
import { extractDocument } from '../services/api'
import ExtractionResults from './ExtractionResults'
import BboxPreview from './BboxPreview'

const STATUS_COLORS = {
  uploaded:   { bg: '#e0f2fe', color: '#0369a1' },
  processing: { bg: '#fef9c3', color: '#854d0e' },
  extracted:  { bg: '#dcfce7', color: '#166534' },
  error:      { bg: '#fee2e2', color: '#991b1b' },
}

export default function DocumentCard({ doc }) {
  const [status, setStatus]       = useState(doc.status)
  const [result, setResult]       = useState(null)
  const [showBoxes, setShowBoxes] = useState(false)
  const [loading, setLoading]     = useState(false)

  const handleExtract = async () => {
    setLoading(true)
    setStatus('processing')
    try {
      const res = await extractDocument(doc.id)
      setResult(res.data)
      setStatus('extracted')
    } catch (err) {
      setStatus('error')
      alert('Extraction failed: ' + (err.response?.data?.error || err.message))
    }
    setLoading(false)
  }

  const badge = STATUS_COLORS[status] || STATUS_COLORS.uploaded

  return (
    <div style={{
      border: '1px solid #e5e7eb',
      borderRadius: 10,
      padding: 16,
      marginBottom: 14
    }}>

      {/* Top row: filename + buttons */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <strong style={{ fontSize: 15 }}>{doc.original_filename}</strong>
          <p style={{ margin: '3px 0 0', fontSize: 12, color: '#9ca3af' }}>
            {(doc.file_size / 1024).toFixed(1)} KB
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {/* Status badge */}
          <span style={{
            padding: '3px 10px', borderRadius: 20, fontSize: 12,
            background: badge.bg, color: badge.color
          }}>
            {status}
          </span>

          {/* Extract button */}
          <button
            onClick={handleExtract}
            disabled={loading}
            style={{
              background: loading ? '#93c5fd' : '#2563eb',
              color: '#fff', border: 'none',
              borderRadius: 8, padding: '7px 14px',
              cursor: loading ? 'not-allowed' : 'pointer',
              fontSize: 13
            }}
          >
            {loading ? 'Extracting...' : 'Extract Text'}
          </button>

          {/* Show/hide boxes button — only after extraction */}
          {result && (
            <button
              onClick={() => setShowBoxes(v => !v)}
              style={{
                background: showBoxes ? '#6d28d9' : '#7c3aed',
                color: '#fff', border: 'none',
                borderRadius: 8, padding: '7px 14px',
                cursor: 'pointer', fontSize: 13
              }}
            >
              {showBoxes ? 'Hide Boxes' : 'Show Boxes'}
            </button>
          )}
        </div>
      </div>

      {/* Extraction results */}
      {result && <ExtractionResults result={result} />}

      {/* Bbox annotated image */}
      {result && showBoxes && <BboxPreview docId={doc.id} />}

    </div>
  )
}