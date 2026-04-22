
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { classifyDocument, extractDocument, getExtractStatus } from '../services/api'
import ExtractionResults from './ExtractionResults'
import BboxPreview from './BboxPreview'
import ExportPanel from './ExportPanel'
import ErrorMessage from './ErrorMessage'

const DOC_TYPES = [
  'invoice', 'receipt', 'business_card', 'form',
  'id_card', 'contract', 'report_letter', 'handwritten_note',
  'whiteboard', 'table_spreadsheet'
]

const STATUS_STYLE = {
  uploaded:   { bg: '#e0f2fe', color: '#0369a1' },
  processing: { bg: '#fef9c3', color: '#854d0e' },
  extracted:  { bg: '#dcfce7', color: '#166534' },
  error:      { bg: '#fee2e2', color: '#991b1b' },
}

export default function DocumentCard({ doc }) {
  const navigate = useNavigate()
  const [status, setStatus]         = useState(doc.status)
  const [docType, setDocType]       = useState(doc.doc_type || '')
  const [typeOverride, setOverride] = useState('')
  const [result, setResult]         = useState(null)
  const [classifying, setClassifying] = useState(false)
  const [extracting, setExtracting]   = useState(false)
  const [showBoxes, setShowBoxes]     = useState(false)
  const [error, setError]             = useState('')

  const applyExtractedResult = (payload) => {
    setResult(payload)
    setDocType(payload.doc_type || docType)
    setStatus('extracted')
  }

  const handleClassify = async () => {
    setError('')
    setClassifying(true)
    try {
      const res = await classifyDocument(doc.id)
      setDocType(res.data.doc_type)
    } catch (err) {
      setError('Classification failed: ' + (err.response?.data?.error || err.message))
    }
    setClassifying(false)
  }

  const handleExtract = async () => {
    setError('')
    setExtracting(true)
    setStatus('processing')
    try {
      await extractDocument(doc.id, typeOverride || docType || null)
      const maxAttempts = 180
      const pollDelayMs = 2000

      for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
        await new Promise(resolve => setTimeout(resolve, pollDelayMs))
        const pollRes = await getExtractStatus(doc.id)
        const { status, result: extractedResult, error_message: errorMessage, doc_type: polledDocType } = pollRes.data

        if (polledDocType) setDocType(polledDocType)

        if (status === 'extracted' && extractedResult) {
          applyExtractedResult(extractedResult)
          return
        }

        if (status === 'error') {
          setStatus('error')
          setError('Extraction failed: ' + (errorMessage || 'Unknown processing error'))
          return
        }
      }

      setStatus('error')
      setError('Extraction timed out while waiting for background processing.')
    } catch (err) {
      setStatus('error')
      setError('Extraction failed: ' + (err.response?.data?.error || err.message))
    } finally {
      setExtracting(false)
    }
  }

  const badge = STATUS_STYLE[status] || STATUS_STYLE.uploaded

  return (
    <div style={{
      border: '1px solid #e5e7eb', borderRadius: 10,
      padding: 16, marginBottom: 14
    }}>
      <ErrorMessage message={error} />

      {/* Top row */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
        <div style={{ flex: 1 }}>
          <strong style={{ fontSize: 15 }}>{doc.original_filename}</strong>
          <div style={{ display: 'flex', gap: 6, marginTop: 6, flexWrap: 'wrap' }}>
            <span style={{
              padding: '2px 10px', borderRadius: 20, fontSize: 12,
              background: badge.bg, color: badge.color
            }}>
              {status}
            </span>
            {docType && (
              <span style={{
                padding: '2px 10px', borderRadius: 20, fontSize: 12,
                background: '#ede9fe', color: '#5b21b6'
              }}>
                {docType.replace('_', ' ')}
              </span>
            )}
          </div>
        </div>

        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
          {/* Classify */}
          <button onClick={handleClassify} disabled={classifying} style={btn('#6d28d9')}>
            {classifying ? 'Classifying...' : 'Classify'}
          </button>

          {/* Type override dropdown */}
          <select
            value={typeOverride}
            onChange={e => setOverride(e.target.value)}
            style={{
              padding: '6px 10px', borderRadius: 8, fontSize: 13,
              border: '1px solid #d1d5db', cursor: 'pointer'
            }}
          >
            <option value=''>Auto type</option>
            {DOC_TYPES.map(t => (
              <option key={t} value={t}>{t.replace('_', ' ')}</option>
            ))}
          </select>

          {/* Extract */}
          <button onClick={handleExtract} disabled={extracting} style={btn('#2563eb')}>
            {extracting ? 'Extracting...' : 'Extract'}
          </button>

          {/* Review page */}
          {result && (
            <button
              onClick={() => navigate(`/document/${doc.id}`, { state: { result, doc: { ...doc, doc_type: docType } } })}
              style={btn('#0f766e')}
            >
              Review
            </button>
          )}

          {/* Toggle bbox */}
          {result && (
            <button onClick={() => setShowBoxes(v => !v)} style={btn('#92400e')}>
              {showBoxes ? 'Hide boxes' : 'Show boxes'}
            </button>
          )}
        </div>
      </div>

      {/* Extraction results */}
      {result && <ExtractionResults result={result} docId={doc.id} />}
      {result && <ExportPanel docId={doc.id} />}
      {result && showBoxes && <BboxPreview docId={doc.id} />}
    </div>
  )
}

const btn = (bg) => ({
  background: bg, color: '#fff', border: 'none',
  borderRadius: 8, padding: '7px 13px',
  cursor: 'pointer', fontSize: 13, whiteSpace: 'nowrap'
})