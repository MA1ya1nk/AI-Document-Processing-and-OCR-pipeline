// src/pages/BatchPage.jsx
import { useState } from 'react'
import BatchUploader from '../components/BatchUploader'
import BatchDashboard from '../components/BatchDashboard'

export default function BatchPage() {
  const [batches, setBatches] = useState([])  // [{batchId, initialDocs}]

  const handleBatchStarted = (batchId, docs) => {
    setBatches(prev => [{ batchId, docs }, ...prev])
  }

  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: '24px 20px' }}>
      <h1 style={{ margin: '0 0 9px', lineHeight: 1.2 }}>Batch processing</h1>
      <p style={{ color: '#6b7280', fontSize: 14, margin: '0 0 24px', lineHeight: 1.5 }}>
        Upload many documents at once. Processing happens in the background.
      </p>

      <BatchUploader onBatchStarted={handleBatchStarted} />

      {batches.map(({ batchId, docs }) => (
        <BatchDashboard
          key={batchId}
          batchId={batchId}
          initialDocs={docs}
        />
      ))}

      {batches.length === 0 && (
        <div style={{
          marginTop: 40, textAlign: 'center',
          color: '#d1d5db', fontSize: 14
        }}>
          No batches yet. Upload files above to start.
        </div>
      )}
    </div>
  )
}