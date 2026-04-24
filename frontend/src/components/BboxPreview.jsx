import { getPreviewUrl } from '../services/api'

export default function BboxPreview({ docId }) {
  return (
    <div style={{ marginTop: 16 }}>
      <img
        src={getPreviewUrl(docId)}
        alt="Annotated document preview"
        style={{
          width: '100%',
          borderRadius: 12,
          border: '1px solid #e2e8f0',
          boxShadow: '0 10px 24px rgba(15,23,42,0.08)'
        }}
      />
      <p style={{ fontSize: 12, color: '#64748b', marginTop: 8 }}>
        Green = high confidence · Yellow = medium · Red = low
      </p>
    </div>
  )
}