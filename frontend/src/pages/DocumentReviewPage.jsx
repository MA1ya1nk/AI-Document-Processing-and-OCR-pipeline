// src/pages/DocumentReviewPage.jsx
import { useParams, useLocation, useNavigate } from 'react-router-dom'
import StructuredFields from '../components/StructuredFields'
import ExportPanel from '../components/ExportPanel'
import { getPreviewUrl, getPageImageUrl } from '../services/api'
import { useState } from 'react'

export default function DocumentReviewPage() {
  const { id } = useParams()
  const { state } = useLocation()
  const navigate = useNavigate()
  const [showAnnotated, setShowAnnotated] = useState(false)
  const [pageIndex, setPageIndex] = useState(0)

  if (!state?.result) {
    return (
      <div className="page-shell" style={{ maxWidth: 700, textAlign: 'center', marginTop: 32 }}>
        <p style={{ color: '#6b7280' }}>No extraction data. Go back and extract first.</p>
        <button onClick={() => navigate('/')} className="btn btn-primary" style={{ marginTop: 12 }}>
          Back to upload
        </button>
      </div>
    )
  }

  const { result, doc } = state
  const pageResults = result.page_results || []
  const hasMultiPage = pageResults.length > 1
  const totalPages = pageResults.length > 0 ? pageResults.length : 1
  const pageResultByIndex = pageResults.find(p => p.page_index === pageIndex)
  const pageResultByOrder = pageResults[pageIndex]
  const currentPage = pageResultByIndex || pageResultByOrder || null
  const currentFields = hasMultiPage
    ? (currentPage?.extracted_fields || {})
    : (result.extracted_fields || {})

  return (
    <div className="page-shell" style={{ maxWidth: 1320 }}>

      {/* Top bar */}
      <div style={{
        display: 'flex', justifyContent: 'space-between',
        alignItems: 'center', marginBottom: 20
      }}>
        <div>
          <button
            onClick={() => navigate('/')}
            style={{ background: 'none', border: 'none', cursor: 'pointer',
                     color: '#64748b', fontSize: 13, padding: 0 }}
          >
            ← Back
          </button>
          <h1 style={{ margin: '6px 0 0', fontSize: 24 }}>
            {doc.original_filename}
          </h1>
          <span style={{
            display: 'inline-block', marginTop: 4,
            padding: '2px 10px', borderRadius: 20, fontSize: 12,
            background: '#ede9fe', color: '#5b21b6'
          }}>
            {doc.doc_type?.replace('_', ' ')}
          </span>
        </div>
        <ExportPanel docId={id} />
      </div>

      {/* Split view */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>

        {/* Left: document image */}
        <div style={{
          border: '1px solid #e2e8f0', borderRadius: 14,
          overflow: 'hidden', background: '#f8fafc', boxShadow: '0 2px 8px rgba(15,23,42,0.06)'
        }}>
          <div style={{
            display: 'flex', justifyContent: 'space-between',
            alignItems: 'center', padding: '12px 16px',
            borderBottom: '1px solid #e5e7eb', background: '#fff'
          }}>
            <span style={{ fontSize: 14, fontWeight: 500 }}>Document image</span>
            <button
              onClick={() => setShowAnnotated(v => !v)}
              className={`btn ${showAnnotated ? 'btn-violet' : 'btn-slate'}`}
              style={{ padding: '6px 12px', fontSize: 12 }}
            >
              {showAnnotated ? 'Original' : 'Show OCR boxes'}
            </button>
          </div>
          {hasMultiPage && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '10px 12px',
              borderBottom: '1px solid #e5e7eb',
              background: '#f8fafc'
            }}>
              <button
                onClick={() => setPageIndex(p => Math.max(0, p - 1))}
                disabled={pageIndex === 0}
                className="btn btn-slate"
                style={{ padding: '6px 10px', opacity: pageIndex === 0 ? 0.65 : 1 }}
              >
                Prev page
              </button>
              <span style={{ fontSize: 12, color: '#64748b' }}>
                Page {pageIndex + 1} / {totalPages}
              </span>
              <button
                onClick={() => setPageIndex(p => Math.min(totalPages - 1, p + 1))}
                disabled={pageIndex >= totalPages - 1}
                className="btn btn-slate"
                style={{ padding: '6px 10px', opacity: pageIndex >= totalPages - 1 ? 0.65 : 1 }}
              >
                Next page
              </button>
            </div>
          )}
          <div style={{ padding: 12, maxHeight: '80vh', overflowY: 'auto' }}>
            <img
              src={showAnnotated ? getPreviewUrl(id, pageIndex) : getPageImageUrl(id, pageIndex)}
              alt="Document"
              style={{ width: '100%', borderRadius: 8 }}
              onError={e => {
                // fallback: show annotated if original fails
                e.target.src = getPreviewUrl(id, pageIndex)
              }}
            />
          </div>
        </div>

        {/* Right: extracted fields */}
        <div style={{
          border: '1px solid #e2e8f0', borderRadius: 14,
          background: '#fff', display: 'flex', flexDirection: 'column',
          boxShadow: '0 2px 8px rgba(15,23,42,0.06)'
        }}>
          <div style={{
            padding: '12px 16px', borderBottom: '1px solid #e5e7eb'
          }}>
            <span style={{ fontSize: 14, fontWeight: 500 }}>Extracted fields</span>
            <span style={{
              marginLeft: 10, fontSize: 12, color: '#6b7280'
            }}>
              {hasMultiPage ? `Showing page ${pageIndex + 1} fields` : 'Click any value to edit'}
            </span>
          </div>
          <div style={{ padding: 16, overflowY: 'auto', maxHeight: '80vh' }}>
            <StructuredFields
              key={`${id}-${pageIndex}`}
              docId={id}
              fields={currentFields}
              schema={result.schema}
            />
          </div>
        </div>

      </div>
    </div>
  )
}