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
      <span style={{ fontSize: 13, color: '#6b7280', alignSelf: 'center' }}>Export:</span>
      {FORMATS.map(fmt => (
        <a
          key={fmt.key}
          href={getExportUrl(docId, fmt.key)}
          download
          style={{
            padding: '6px 14px',
            borderRadius: 8,
            background: fmt.color,
            color: '#fff',
            fontSize: 13,
            textDecoration: 'none',
            fontWeight: 500
          }}
        >
          {fmt.label}
        </a>
      ))}
    </div>
  )
}