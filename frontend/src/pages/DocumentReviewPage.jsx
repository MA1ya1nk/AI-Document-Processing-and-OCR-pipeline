// src/pages/DocumentReviewPage.jsx
import { useParams, useLocation, useNavigate } from 'react-router-dom'
import StructuredFields from '../components/StructuredFields'
import ExportPanel from '../components/ExportPanel'
import { getPreviewUrl } from '../services/api'
import { useState } from 'react'

export default function DocumentReviewPage() {
  const { id } = useParams()
  const { state } = useLocation()
  const navigate = useNavigate()
  const [showAnnotated, setShowAnnotated] = useState(false)

  if (!state?.result) {
    return (
      <div style={{ maxWidth: 600, margin: '60px auto', textAlign: 'center' }}>
        <p style={{ color: '#6b7280' }}>No extraction data. Go back and extract first.</p>
        <button onClick={() => navigate('/')} style={{
          marginTop: 12, padding: '8px 20px', borderRadius: 8,
          background: '#2563eb', color: '#fff', border: 'none', cursor: 'pointer'
        }}>
          Back to upload
        </button>
      </div>
    )
  }

  const { result, doc } = state

  return (
    <div style={{ maxWidth: 1280, margin: '0 auto', padding: 20 }}>

      {/* Top bar */}
      <div style={{
        display: 'flex', justifyContent: 'space-between',
        alignItems: 'center', marginBottom: 20
      }}>
        <div>
          <button
            onClick={() => navigate('/')}
            style={{ background: 'none', border: 'none', cursor: 'pointer',
                     color: '#6b7280', fontSize: 13, padding: 0 }}
          >
            ← Back
          </button>
          <h1 style={{ margin: '4px 0 0', fontSize: 20 }}>
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
          border: '1px solid #e5e7eb', borderRadius: 12,
          overflow: 'hidden', background: '#f9fafb'
        }}>
          <div style={{
            display: 'flex', justifyContent: 'space-between',
            alignItems: 'center', padding: '12px 16px',
            borderBottom: '1px solid #e5e7eb', background: '#fff'
          }}>
            <span style={{ fontSize: 14, fontWeight: 500 }}>Document image</span>
            <button
              onClick={() => setShowAnnotated(v => !v)}
              style={{
                padding: '5px 12px', borderRadius: 8, fontSize: 12, cursor: 'pointer',
                background: showAnnotated ? '#7c3aed' : '#f3f4f6',
                color: showAnnotated ? '#fff' : '#374151', border: 'none'
              }}
            >
              {showAnnotated ? 'Original' : 'Show OCR boxes'}
            </button>
          </div>
          <div style={{ padding: 12, maxHeight: '80vh', overflowY: 'auto' }}>
            <img
              src={showAnnotated ? getPreviewUrl(id) : `/api-passthrough/${id}`}
              alt="Document"
              style={{ width: '100%', borderRadius: 8 }}
              onError={e => {
                // fallback: show annotated if original fails
                e.target.src = getPreviewUrl(id)
              }}
            />
          </div>
        </div>

        {/* Right: extracted fields */}
        <div style={{
          border: '1px solid #e5e7eb', borderRadius: 12,
          background: '#fff', display: 'flex', flexDirection: 'column'
        }}>
          <div style={{
            padding: '12px 16px', borderBottom: '1px solid #e5e7eb'
          }}>
            <span style={{ fontSize: 14, fontWeight: 500 }}>Extracted fields</span>
            <span style={{
              marginLeft: 10, fontSize: 12, color: '#6b7280'
            }}>
              Click any value to edit
            </span>
          </div>
          <div style={{ padding: 16, overflowY: 'auto', maxHeight: '80vh' }}>
            <StructuredFields
              docId={id}
              fields={result.extracted_fields}
              schema={result.schema}
            />
          </div>
        </div>

      </div>
    </div>
  )
}