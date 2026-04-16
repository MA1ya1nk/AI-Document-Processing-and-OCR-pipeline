import { getPreviewUrl } from '../services/api'

export default function BboxPreview({ docId }) {
  return (
    <div style={{ marginTop: 16 }}>
      <img
        src={getPreviewUrl(docId)}
        alt="Annotated document preview"
        style={{
          width: '100%',
          borderRadius: 8,
          border: '1px solid #e0e0e0'
        }}
      />
      <p style={{ fontSize: 12, color: '#888', marginTop: 6 }}>
        Green = high confidence · Yellow = medium · Red = low
      </p>
    </div>
  )
}