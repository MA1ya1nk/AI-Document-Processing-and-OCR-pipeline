// src/components/ExportPanel.jsx
import { getExportUrl } from '../services/api'

const FORMATS = [
  { key: 'json',  label: 'JSON',  color: '#0369a1' },
  { key: 'csv',   label: 'CSV',   color: '#166534' },
  { key: 'excel', label: 'Excel', color: '#15803d' },
]

export default function ExportPanel({ docId }) {
  return (
    <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 12 }}>
      <span style={{ fontSize: 13, color: '#64748b', alignSelf: 'center', fontWeight: 600 }}>Export:</span>
      {FORMATS.map(fmt => (
        <a
          key={fmt.key}
          href={getExportUrl(docId, fmt.key)}
          download
          style={{
            padding: '6px 14px',
            borderRadius: 10,
            background: fmt.color,
            color: '#fff',
            fontSize: 13,
            textDecoration: 'none',
            fontWeight: 600,
            boxShadow: '0 6px 16px rgba(15, 23, 42, 0.16)'
          }}
        >
          {fmt.label}
        </a>
      ))}
    </div>
  )
}