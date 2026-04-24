// src/pages/BatchPage.jsx
import { useEffect, useMemo, useState } from 'react'
import BatchUploader from '../components/BatchUploader'
import BatchDashboard from '../components/BatchDashboard'
import { getActiveBatches } from '../services/api'

export default function BatchPage() {
  const [batches, setBatches] = useState([])  // [{batchId, initialDocs}]
  const [loadingActive, setLoadingActive] = useState(true)

  const handleBatchStarted = (batchId, docs) => {
    setBatches(prev => {
      const existing = prev.find(b => b.batchId === batchId)
      if (existing) {
        return prev.map(b => (b.batchId === batchId ? { ...b, docs } : b))
      }
      return [{ batchId, docs }, ...prev]
    })
  }

  useEffect(() => {
    let mounted = true
    const loadActive = async () => {
      try {
        const res = await getActiveBatches()
        if (!mounted) return
        const active = (res.data?.batches || []).map(item => ({
          batchId: item.batch?.id,
          docs: item.documents || []
        })).filter(b => b.batchId)
        setBatches(active)
      } catch {
        // Keep empty state if loading active batches fails.
      } finally {
        if (mounted) setLoadingActive(false)
      }
    }
    loadActive()
    return () => { mounted = false }
  }, [])

  const hasRunningBatch = useMemo(
    () => batches.some(b => (b.docs || []).some(d => d.status === 'processing')),
    [batches]
  )

  return (
    <div className="page-shell" style={{ maxWidth: 960 }}>
      <div className="page-header">
        <h1 className="page-title">Batch processing</h1>
        <p className="page-subtitle">
        Upload many documents at once. Processing happens in the background.
        </p>
      </div>

      <BatchUploader
        onBatchStarted={handleBatchStarted}
        disabled={hasRunningBatch}
        disabledReason="Another batch is currently processing. Start a new one after it completes."
      />

      {batches.map(({ batchId, docs }) => (
        <BatchDashboard
          key={batchId}
          batchId={batchId}
          initialDocs={docs}
        />
      ))}

      {loadingActive && (
        <div style={{ marginTop: 20, color: '#94a3b8', fontSize: 14 }}>
          Loading active batches...
        </div>
      )}

      {!loadingActive && batches.length === 0 && (
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