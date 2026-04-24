
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { classifyDocument, extractDocument, getExtractStatus, runOcrPreview } from '../services/api'
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
  uploaded: 'status-uploaded',
  processing: 'status-processing',
  extracted: 'status-extracted',
  error: 'status-error',
}

export default function DocumentCard({ doc }) {
  const navigate = useNavigate()
  const [status, setStatus]         = useState(doc.status)
  const [docType, setDocType]       = useState(doc.doc_type || '')
  const [typeOverride, setOverride] = useState('')
  const [result, setResult]         = useState(null)
  const [classifying, setClassifying] = useState(false)
  const [extracting, setExtracting]   = useState(false)
  const [ocrLoading, setOcrLoading]   = useState(false)
  const [showBoxes, setShowBoxes]     = useState(false)
  const [error, setError]             = useState('')
  const [ocrPreview, setOcrPreview]   = useState(null)
  const [showOcrPanel, setShowOcrPanel] = useState(false)

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

  const handleOcrPreview = async () => {
    setError('')
    setOcrLoading(true)
    try {
      const res = await runOcrPreview(doc.id)
      setOcrPreview(res.data)
      setShowOcrPanel(true)
    } catch (err) {
      setError('OCR preview failed: ' + (err.response?.data?.error || err.message))
    } finally {
      setOcrLoading(false)
    }
  }

  const badge = STATUS_STYLE[status] || STATUS_STYLE.uploaded

  return (
    <div className="card" style={{ marginBottom: 14 }}>
      <ErrorMessage message={error} />

      {/* Top row */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8 }}>
        <div style={{ flex: 1 }}>
          <strong style={{ fontSize: 15 }}>{doc.original_filename}</strong>
          <div style={{ display: 'flex', gap: 6, marginTop: 6, flexWrap: 'wrap' }}>
            <span className={`pill ${badge}`}>
              {status}
            </span>
            {docType && (
              <span className="pill doc-type-pill">
                {docType.replace('_', ' ')}
              </span>
            )}
          </div>
        </div>

        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
          {/* Classify */}
          <button onClick={handleClassify} disabled={classifying} className="btn btn-violet">
            {classifying ? 'Classifying...' : 'Classify'}
          </button>

          {/* Type override dropdown */}
          <select
            value={typeOverride}
            onChange={e => setOverride(e.target.value)}
            className="field-select"
          >
            <option value=''>Auto type</option>
            {DOC_TYPES.map(t => (
              <option key={t} value={t}>{t.replace('_', ' ')}</option>
            ))}
          </select>

          <button onClick={handleOcrPreview} disabled={ocrLoading} className="btn btn-violet">
            {ocrLoading ? 'Reading OCR...' : 'Preview OCR text'}
          </button>

          {/* Extract */}
          <button
            onClick={handleExtract}
            disabled={extracting || !ocrPreview}
            className="btn btn-primary"
            title={!ocrPreview ? 'Preview OCR text first' : 'Run structured extraction with LLM'}
          >
            {extracting ? 'Extracting...' : 'Extract with LLM'}
          </button>

          {/* Review page */}
          {result && (
            <button
              onClick={() => navigate(`/document/${doc.id}`, { state: { result, doc: { ...doc, doc_type: docType } } })}
              className="btn btn-teal"
            >
              Review
            </button>
          )}

          {/* Toggle bbox */}
          {result && (
            <button onClick={() => setShowBoxes(v => !v)} className="btn btn-amber">
              {showBoxes ? 'Hide boxes' : 'Show boxes'}
            </button>
          )}
        </div>
      </div>

      {showOcrPanel && ocrPreview && (
        <div style={{
          marginTop: 14,
          border: '1px solid #c7d2fe',
          borderRadius: 12,
          background: 'linear-gradient(180deg, #f8faff 0%, #ffffff 100%)',
          padding: 14
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <div>
              <p style={{ margin: 0, fontSize: 13, fontWeight: 700, color: '#1e3a8a' }}>
                EasyOCR preview
              </p>
              <p style={{ margin: '2px 0 0', fontSize: 12, color: '#64748b' }}>
                {ocrPreview.total_detections || 0} text regions detected
              </p>
            </div>
            <button
              className="btn btn-ghost"
              onClick={() => setShowOcrPanel(v => !v)}
              style={{ fontSize: 12, padding: '5px 10px' }}
            >
              {showOcrPanel ? 'Hide' : 'Show'}
            </button>
          </div>
          <div style={{
            maxHeight: 180,
            overflowY: 'auto',
            border: '1px solid #e2e8f0',
            borderRadius: 10,
            background: '#f8fafc',
            padding: 10,
            fontSize: 13,
            lineHeight: 1.6,
            whiteSpace: 'pre-wrap'
          }}>
            {ocrPreview.full_text || 'No OCR text detected.'}
          </div>
        </div>
      )}

      {/* Extraction results */}
      {result && <ExtractionResults result={result} docId={doc.id} />}
      {result && <ExportPanel docId={doc.id} />}
      {result && showBoxes && <BboxPreview docId={doc.id} />}
    </div>
  )
}
