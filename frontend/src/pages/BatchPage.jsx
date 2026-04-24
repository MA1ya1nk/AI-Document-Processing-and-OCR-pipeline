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
    <div className="page-shell" style={{ maxWidth: 960 }}>
      <div className="page-header">
        <h1 className="page-title">Batch processing</h1>
        <p className="page-subtitle">
        Upload many documents at once. Processing happens in the background.
        </p>
      </div>

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
          marginTop: 28, textAlign: 'center',
          color: '#94a3b8', fontSize: 14
        }}>
          No batches yet. Upload files above to start.
        </div>
      )}
    </div>
  )
}