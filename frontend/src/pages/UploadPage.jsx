
import { useState } from 'react'
import DocumentUploader from '../components/DocumentUploader'
import DocumentCard from '../components/DocumentCard'

export default function UploadPage() {
  const [documents, setDocuments] = useState([])

  const handleUploaded = (newDoc) => {
    setDocuments(prev => [newDoc, ...prev])
  }

  return (
    <div style={{ maxWidth: 760, margin: '40px auto', padding: '0 20px' }}>
      <h1 style={{ margin: '0 0 9px', lineHeight: 1.2 }}>Document Processor</h1>
      <p style={{ color: '#6b7280', margin: '0 0 28px', fontSize: 14, lineHeight: 1.5 }}>
        Upload images or PDFs — extract text with OCR and bounding box visualization.
      </p>

      <DocumentUploader onUploaded={handleUploaded} />

      {documents.length > 0 && (
        <div style={{ marginTop: 36 }}>
          <h2 style={{ marginBottom: 16, fontSize: 18 }}>
            Uploaded Documents ({documents.length})
          </h2>
          {documents.map(doc => (
            <DocumentCard key={doc.id} doc={doc} />
          ))}
        </div>
      )}

      {documents.length === 0 && (
        <p style={{ textAlign: 'center', color: '#9ca3af', marginTop: 48 }}>
          No documents uploaded yet.
        </p>
      )}
    </div>
  )
}