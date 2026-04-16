// // src/components/ExtractionResults.jsx

// const BG  = { high: '#dcfce7', medium: '#fef9c3', low: '#fee2e2' }
// const CLR = { high: '#166534', medium: '#854d0e', low: '#991b1b' }

// function ConfidenceBadge({ label, score }) {
//   return (
//     <span style={{
//       padding: '2px 8px',
//       borderRadius: 12,
//       fontSize: 11,
//       background: BG[label] || '#f3f4f6',
//       color: CLR[label] || '#374151'
//     }}>
//       {label} ({(score * 100).toFixed(0)}%)
//     </span>
//   )
// }

// export default function ExtractionResults({ result }) {
//   return (
//     <div style={{ marginTop: 16 }}>

//       {/* Summary line */}
//       <p style={{ fontSize: 13, color: '#555', margin: '0 0 10px' }}>
//         Found <strong>{result.total_detections}</strong> text regions ·
//         Preprocessing: {result.preprocessing_steps.join(' → ')}
//       </p>

//       {/* Full raw text */}
//       <div style={{
//         background: '#f8f8f8',
//         borderRadius: 8,
//         padding: 12,
//         marginBottom: 12
//       }}>
//         <p style={{ fontSize: 12, color: '#888', margin: '0 0 6px' }}>
//           Full extracted text:
//         </p>
//         <p style={{ fontSize: 13, margin: 0, whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>
//           {result.full_text}
//         </p>
//       </div>

//       {/* Per-detection table */}
//       <p style={{ fontSize: 12, color: '#888', margin: '0 0 6px' }}>
//         Individual detections:
//       </p>
//       <div style={{ maxHeight: 220, overflowY: 'auto', border: '1px solid #f0f0f0', borderRadius: 8 }}>
//         {result.detections.map((det, i) => (
//           <div key={i} style={{
//             display: 'flex',
//             justifyContent: 'space-between',
//             alignItems: 'center',
//             padding: '6px 10px',
//             borderBottom: '1px solid #f5f5f5',
//             fontSize: 13
//           }}>
//             <span style={{ flex: 1, marginRight: 12 }}>{det.text}</span>
//             <ConfidenceBadge label={det.confidence_label} score={det.confidence} />
//           </div>
//         ))}
//       </div>

//     </div>
//   )
// }


// src/components/ExtractionResults.jsx
import { useState } from 'react'
import StructuredFields from './StructuredFields'

const CONF = {
  high:   { bg: '#dcfce7', color: '#166534' },
  medium: { bg: '#fef9c3', color: '#854d0e' },
  low:    { bg: '#fee2e2', color: '#991b1b' },
}

export default function ExtractionResults({ result, docId }) {
  const [tab, setTab] = useState('structured')

  const tabStyle = (active) => ({
    padding: '6px 16px',
    border: 'none',
    borderBottom: active ? '2px solid #2563eb' : '2px solid transparent',
    background: 'none',
    cursor: 'pointer',
    fontSize: 13,
    color: active ? '#2563eb' : '#6b7280',
    fontWeight: active ? 500 : 400
  })

  return (
    <div style={{ marginTop: 16 }}>
      {/* Tab bar */}
      <div style={{ display: 'flex', borderBottom: '1px solid #e5e7eb', marginBottom: 12 }}>
        <button style={tabStyle(tab === 'structured')} onClick={() => setTab('structured')}>
          Structured fields
        </button>
        <button style={tabStyle(tab === 'raw')} onClick={() => setTab('raw')}>
          Raw OCR ({result.total_detections} regions)
        </button>
      </div>

      {tab === 'structured' && (
        <StructuredFields
          docId={docId}
          fields={result.extracted_fields}
          schema={result.schema}
        />
      )}

      {tab === 'raw' && (
        <div>
          <div style={{
            background: '#f8f8f8', borderRadius: 8,
            padding: 12, marginBottom: 12, fontSize: 13,
            whiteSpace: 'pre-wrap', lineHeight: 1.6, maxHeight: 200, overflowY: 'auto'
          }}>
            {result.full_text}
          </div>
          <div style={{ maxHeight: 220, overflowY: 'auto' }}>
            {result.detections.map((det, i) => (
              <div key={i} style={{
                display: 'flex', justifyContent: 'space-between',
                alignItems: 'center', padding: '5px 8px',
                borderBottom: '1px solid #f5f5f5', fontSize: 13
              }}>
                <span style={{ flex: 1, marginRight: 12 }}>{det.text}</span>
                <span style={{
                  padding: '2px 8px', borderRadius: 12, fontSize: 11,
                  background: CONF[det.confidence_label]?.bg,
                  color: CONF[det.confidence_label]?.color
                }}>
                  {det.confidence_label} ({(det.confidence * 100).toFixed(0)}%)
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}