// src/components/BatchDashboard.jsx
import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { getBatchStatus, getBatchExportUrl, getPreviewUrl } from '../services/api'

const STATUS_COLOR = {
  uploaded:   { bg: '#dbeafe33', border: '#93c5fd' },
  processing: { bg: '#fef9c333', border: '#fcd34d' },
  extracted:  { bg: '#dcfce733', border: '#6ee7b7' },
  error:      { bg: '#fee2e233', border: '#fca5a5' },
}

const CONF_STYLE = {
  high:   { bg: '#dcfce7', color: '#166534' },
  medium: { bg: '#fef9c3', color: '#854d0e' },
  low:    { bg: '#fee2e2', color: '#991b1b' },
}

// ── Single extracted document result panel ──────────────────────────────────
function DocResultPanel({ doc }) {
  const navigate = useNavigate()
  const [expanded, setExpanded] = useState(false)
  const [showImg, setShowImg]   = useState(false)
  const [pageIndex, setPageIndex] = useState(0)

  const colors = STATUS_COLOR[doc.status] || STATUS_COLOR.uploaded
  const pageResults = doc.page_results || []
  const currentPageResult = pageResults.find(p => p.page_index === pageIndex)
  const fields = (currentPageResult?.extracted_fields || doc.extracted_fields || {})
  const totalPages = pageResults.length > 0 ? pageResults.length : 1
  const scalarFields = Object.entries(fields).filter(
    ([, v]) => v?.value !== null && v?.value !== undefined && !Array.isArray(v?.value)
  )
  const tableFields = Object.entries(fields).filter(
    ([, v]) => Array.isArray(v?.value) && v.value.length > 0
  )

  return (
    <div style={{
      border: `1px solid ${colors.border}`,
      borderRadius: 10,
      marginBottom: 12,
      overflow: 'hidden',
      background: '#fff'
    }}>

      {/* ── Header row ── */}
      <div
        onClick={() => doc.status === 'extracted' && setExpanded(v => !v)}
        style={{
          display: 'flex', justifyContent: 'space-between',
          alignItems: 'center', padding: '12px 16px',
          background: colors.bg,
          cursor: doc.status === 'extracted' ? 'pointer' : 'default'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {/* Expand arrow */}
          {doc.status === 'extracted' && (
            <span style={{
              fontSize: 12, color: '#6b7280',
              transform: expanded ? 'rotate(90deg)' : 'rotate(0deg)',
              display: 'inline-block', transition: 'transform 0.2s'
            }}>▶</span>
          )}
          <div>
            <strong style={{ fontSize: 14 }}>{doc.original_filename}</strong>
            <div style={{ display: 'flex', gap: 6, marginTop: 4 }}>
              <span style={{
                fontSize: 11, padding: '2px 8px', borderRadius: 20,
                background: colors.bg, border: `1px solid ${colors.border}`,
                color: '#374151'
              }}>
                {doc.status}
              </span>
              {doc.doc_type && (
                <span style={{
                  fontSize: 11, padding: '2px 8px', borderRadius: 20,
                  background: '#ede9fe', color: '#5b21b6'
                }}>
                  {doc.doc_type.replace('_', ' ')}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Right side buttons */}
        <div style={{ display: 'flex', gap: 8 }} onClick={e => e.stopPropagation()}>
          {doc.status === 'extracted' && (
            <>
              <button
                onClick={() => setShowImg(v => !v)}
                style={smallBtn('#92400e')}
              >
                {showImg ? 'Hide image' : 'Show image'}
              </button>
              <button
                onClick={() => navigate(`/document/${doc.id}`, {
                  state: {
                    doc,
                    result: {
                      doc_type: doc.doc_type,
                      extracted_fields: doc.extracted_fields,
                      detections: doc.detections || [],
                      full_text: doc.raw_text || '',
                      preprocessing_steps: doc.preprocessing_steps || [],
                      total_detections: doc.detections?.length || 0,
                      schema: null
                    }
                  }
                })}
                style={smallBtn('#0f766e')}
              >
                Full review
              </button>
            </>
          )}
          {doc.status === 'processing' && (
            <span style={{ fontSize: 12, color: '#92400e' }}>Processing...</span>
          )}
          {doc.status === 'error' && (
            <span style={{ fontSize: 12, color: '#991b1b' }}>Failed</span>
          )}
        </div>
      </div>

      {/* ── Annotated image ── */}
      {showImg && doc.status === 'extracted' && (
        <div style={{ padding: '12px 16px', borderBottom: '1px solid #f3f4f6' }}>
          {totalPages > 1 && (
            <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
              <button
                onClick={() => setPageIndex(p => Math.max(0, p - 1))}
                disabled={pageIndex === 0}
                style={smallBtn(pageIndex === 0 ? '#9ca3af' : '#475569')}
              >
                Prev page
              </button>
              <span style={{ fontSize: 12, color: '#6b7280', alignSelf: 'center' }}>
                Page {pageIndex + 1} / {totalPages}
              </span>
              <button
                onClick={() => setPageIndex(p => Math.min(totalPages - 1, p + 1))}
                disabled={pageIndex >= totalPages - 1}
                style={smallBtn(pageIndex >= totalPages - 1 ? '#9ca3af' : '#475569')}
              >
                Next page
              </button>
            </div>
          )}
          <img
            src={getPreviewUrl(doc.id, pageIndex)}
            alt="annotated"
            style={{ width: '100%', borderRadius: 8, border: '1px solid #e5e7eb' }}
          />
          <p style={{ fontSize: 11, color: '#9ca3af', marginTop: 6 }}>
            Green = high · Yellow = medium · Red = low confidence
          </p>
        </div>
      )}

      {/* ── Extracted fields (expanded) ── */}
      {expanded && doc.status === 'extracted' && (
        <div style={{ padding: '16px' }}>

          {/* Scalar fields */}
          {scalarFields.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <p style={{ fontSize: 12, color: '#9ca3af', margin: '0 0 8px', fontWeight: 500 }}>
                EXTRACTED FIELDS{totalPages > 1 ? ` (Page ${pageIndex + 1})` : ''}
              </p>
              {scalarFields.map(([key, data]) => (
                <div key={key} style={{
                  display: 'flex', justifyContent: 'space-between',
                  alignItems: 'center', padding: '8px 0',
                  borderBottom: '1px solid #f9fafb'
                }}>
                  <span style={{ fontSize: 12, color: '#6b7280', width: 160, flexShrink: 0 }}>
                    {key.replace(/_/g, ' ')}
                  </span>
                  <span style={{ fontSize: 13, flex: 1, color: '#111827' }}>
                    {data?.value !== null && data?.value !== undefined
                      ? String(data.value)
                      : <span style={{ color: '#d1d5db', fontStyle: 'italic' }}>not found</span>
                    }
                  </span>
                  {data?.confidence && (
                    <span style={{
                      fontSize: 11, padding: '2px 8px', borderRadius: 20, flexShrink: 0,
                      background: CONF_STYLE[data.confidence]?.bg || '#f3f4f6',
                      color: CONF_STYLE[data.confidence]?.color || '#374151'
                    }}>
                      {data.confidence}
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Table fields (line items etc) */}
          {tableFields.map(([key, data]) => (
            <div key={key} style={{ marginBottom: 16 }}>
              <p style={{ fontSize: 12, color: '#9ca3af', margin: '0 0 8px', fontWeight: 500 }}>
                {key.replace(/_/g, ' ').toUpperCase()}
              </p>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                  <thead>
                    <tr>
                      {Object.keys(data.value[0]).map(col => (
                        <th key={col} style={{
                          padding: '6px 10px', background: '#f8fafc',
                          borderBottom: '1px solid #e2e8f0',
                          textAlign: 'left', fontSize: 12,
                          color: '#475569', fontWeight: 500
                        }}>
                          {col.replace(/_/g, ' ')}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {data.value.map((row, i) => (
                      <tr key={i} style={{ background: i % 2 === 0 ? '#fff' : '#f8fafc' }}>
                        {Object.keys(data.value[0]).map(col => (
                          <td key={col} style={{
                            padding: '6px 10px',
                            borderBottom: '1px solid #f1f5f9',
                            color: '#334155'
                          }}>
                            {row[col] ?? ''}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}

          {/* Raw text */}
          {doc.raw_text && (
            <div>
              <p style={{ fontSize: 12, color: '#9ca3af', margin: '0 0 8px', fontWeight: 500 }}>
                RAW OCR TEXT
              </p>
              <div style={{
                background: '#f8f8f8', borderRadius: 8, padding: 12,
                fontSize: 12, color: '#374151', whiteSpace: 'pre-wrap',
                maxHeight: 150, overflowY: 'auto', lineHeight: 1.6
              }}>
                {doc.raw_text}
              </div>
            </div>
          )}

        </div>
      )}
    </div>
  )
}


// ── Main BatchDashboard ─────────────────────────────────────────────────────
export default function BatchDashboard({ batchId, initialDocs }) {
  const [batch, setBatch] = useState(null)
  const [docs, setDocs]   = useState(initialDocs || [])
  const intervalRef       = useRef(null)

  useEffect(() => {
    if (!batchId) return

    const poll = async () => {
      try {
        const res = await getBatchStatus(batchId)
        setBatch(res.data.batch)
        setDocs(res.data.documents)
        if (res.data.batch.status === 'done') {
          clearInterval(intervalRef.current)
        }
      } catch (err) {
        console.error(err)
      }
    }

    poll()
    intervalRef.current = setInterval(poll, 2000)
    return () => clearInterval(intervalRef.current)
  }, [batchId])

  if (!batch) return (
    <p style={{ color: '#9ca3af', fontSize: 14, marginTop: 16 }}>Starting batch...</p>
  )

  const pct        = batch.progress_pct
  const succeeded  = docs.filter(d => d.status === 'extracted').length
  const failed     = docs.filter(d => d.status === 'error').length
  const inprogress = docs.filter(d => d.status === 'processing').length

  return (
    <div style={{
      border: '1px solid #e5e7eb', borderRadius: 12,
      padding: 20, marginTop: 20, background: '#fff'
    }}>

      {/* ── Batch header ── */}
      <div style={{
        display: 'flex', justifyContent: 'space-between',
        alignItems: 'center', marginBottom: 16
      }}>
        <div>
          <strong style={{ fontSize: 16 }}>Batch #{batchId}</strong>
          <span style={{
            marginLeft: 10, fontSize: 12, padding: '2px 8px', borderRadius: 20,
            background: batch.status === 'done' ? '#dcfce7' : '#fef9c3',
            color: batch.status === 'done' ? '#166534' : '#854d0e'
          }}>
            {batch.status === 'done' ? 'Complete' : 'Processing...'}
          </span>
        </div>

        {batch.status === 'done' && (
          <div style={{ display: 'flex', gap: 8 }}>
            <a href={getBatchExportUrl(batchId, 'csv')} download style={exportBtn('#166534')}>
              CSV
            </a>
            <a href={getBatchExportUrl(batchId, 'zip')} download style={exportBtn('#0369a1')}>
              ZIP
            </a>
          </div>
        )}
      </div>

      {/* ── Progress bar ── */}
      <div style={{ background: '#f3f4f6', borderRadius: 999, height: 10, marginBottom: 12 }}>
        <div style={{
          width: `${pct}%`, background: '#2563eb',
          borderRadius: 999, height: 10, transition: 'width 0.4s ease'
        }} />
      </div>

      {/* ── Stats row ── */}
      <div style={{ display: 'flex', gap: 16, marginBottom: 20, fontSize: 13 }}>
        <span style={{ color: '#6b7280' }}>
          {batch.processed_count} / {batch.total_count} processed
        </span>
        <span style={{ color: '#166534', fontWeight: 500 }}>{succeeded} done</span>
        <span style={{ color: '#854d0e' }}>{inprogress} in progress</span>
        <span style={{ color: '#991b1b' }}>{failed} failed</span>
      </div>

      {/* ── Document result panels ── */}
      <div>
        {docs.map(doc => (
          <DocResultPanel key={doc.id} doc={doc} />
        ))}
      </div>

    </div>
  )
}

const exportBtn = (color) => ({
  background: color, color: '#fff',
  padding: '6px 14px', borderRadius: 8,
  fontSize: 12, textDecoration: 'none', fontWeight: 500,
  border: 'none', cursor: 'pointer'
})

const smallBtn = (bg) => ({
  background: bg, color: '#fff', border: 'none',
  borderRadius: 8, padding: '5px 12px',
  cursor: 'pointer', fontSize: 12
})