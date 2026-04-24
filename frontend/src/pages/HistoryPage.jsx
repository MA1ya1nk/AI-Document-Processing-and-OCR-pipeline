// src/pages/HistoryPage.jsx
import { useState, useEffect } from 'react'
import { listDocuments } from '../services/api'
import HistoryCard from '../components/HistoryCard'

const ALL_TYPES = [
  'invoice', 'receipt', 'business_card', 'form', 'id_card',
  'contract', 'report_letter', 'handwritten_note', 'whiteboard', 'table_spreadsheet'
]

export default function HistoryPage() {
  const [documents, setDocuments] = useState([])
  const [loading, setLoading]     = useState(true)
  const [search, setSearch]       = useState('')
  const [filterType, setFilterType]     = useState('')
  const [filterStatus, setFilterStatus] = useState('')

  useEffect(() => {
    listDocuments()
      .then(res => setDocuments(res.data.documents))
      .catch(err => console.error(err))
      .finally(() => setLoading(false))
  }, [])

  const handleDeleted = (docId) => {
    setDocuments(prev => prev.filter(d => d.id !== docId))
  }

  const normalizeValue = (value) => String(value || '').trim().toLowerCase()

  const filtered = documents.filter(doc => {
    const matchSearch = doc.original_filename
      .toLowerCase().includes(search.toLowerCase())
    const matchType   = !filterType   || normalizeValue(doc.doc_type) === normalizeValue(filterType)
    const matchStatus = !filterStatus || normalizeValue(doc.status) === normalizeValue(filterStatus)
    return matchSearch && matchType && matchStatus
  })

  // Stats
  const total      = documents.length
  const extracted  = documents.filter(d => d.status === 'extracted').length
  const needsReview = documents.filter(d => d.status === 'uploaded').length

  return (
    <div className="page-shell" style={{ maxWidth: 980 }}>
      <div className="page-header">
        <h1 className="page-title">Document history</h1>
        <p className="page-subtitle">
          All uploaded documents and their extraction results
        </p>
      </div>

      {/* Stats row */}
      <div style={{
        display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)',
        gap: 12, marginBottom: 24
      }}>
        {[
          { label: 'Total documents', value: total,       bg: '#f0f9ff', color: '#0369a1' },
          { label: 'Extracted',        value: extracted,   bg: '#f0fdf4', color: '#166534' },
          { label: 'Not yet extracted', value: needsReview, bg: '#fffbeb', color: '#92400e' },
        ].map(stat => (
          <div key={stat.label} style={{
            background: stat.bg, borderRadius: 14,
            padding: '16px 18px',
            border: '1px solid #dbeafe'
          }}>
            <p style={{ fontSize: 28, fontWeight: 600, margin: 0, color: stat.color }}>
              {stat.value}
            </p>
            <p style={{ fontSize: 12, margin: '4px 0 0', color: stat.color }}>
              {stat.label}
            </p>
          </div>
        ))}
      </div>

      {/* Filter bar */}
      <div style={{
        display: 'flex', gap: 10, marginBottom: 16, flexWrap: 'wrap', padding: 16,
        border: '1px solid #e2e8f0', borderRadius: 14, background: '#fff'
      }}>
        <input
          placeholder="Search by filename..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{
            flex: 1, minWidth: 200, padding: '8px 12px',
            border: '1px solid #cbd5e1', borderRadius: 10, fontSize: 13
          }}
        />
        <select
          value={filterType}
          onChange={e => setFilterType(e.target.value)}
          style={selectStyle}
        >
          <option value='' style={optionStyle}>All types</option>
          {ALL_TYPES.map(t => (
            <option key={t} value={t} style={optionStyle}>{t.replace('_', ' ')}</option>
          ))}
        </select>
        <select
          value={filterStatus}
          onChange={e => setFilterStatus(e.target.value)}
          style={selectStyle}
        >
          <option value='' style={optionStyle}>All statuses</option>
          <option value='uploaded' style={optionStyle}>Uploaded</option>
          <option value='extracted' style={optionStyle}>Extracted</option>
          <option value='error' style={optionStyle}>Error</option>
        </select>
      </div>

      {/* Results count */}
      <p style={{ fontSize: 13, color: '#6b7280', marginBottom: 12 }}>
        Showing {filtered.length} of {total} documents
      </p>

      {/* Document list */}
      {loading && <p style={{ color: '#9ca3af' }}>Loading history...</p>}

      {!loading && filtered.length === 0 && (
        <div style={{
          textAlign: 'center', padding: '48px 20px',
          color: '#9ca3af', border: '2px dashed #e5e7eb', borderRadius: 12
        }}>
          <p style={{ fontSize: 16, margin: 0 }}>No documents found</p>
          <p style={{ fontSize: 13, margin: '8px 0 0' }}>
            {search || filterType || filterStatus
              ? 'Try clearing your filters'
              : 'Upload documents from the home page'}
          </p>
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10, width: '100%' }}>
        {filtered.map(doc => (
          <HistoryCard key={doc.id} doc={doc} onDeleted={handleDeleted} />
        ))}
      </div>
    </div>
  )
}

const selectStyle = {
  padding: '8px 10px', borderRadius: 10, fontSize: 13,
  border: '1px solid #cbd5e1', cursor: 'pointer',
  backgroundColor: '#fff', color: '#111827'
}

const optionStyle = {
  backgroundColor: '#fff',
  color: '#111827'
}