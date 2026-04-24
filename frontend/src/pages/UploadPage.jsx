
import { useState } from 'react'
import DocumentUploader from '../components/DocumentUploader'
import DocumentCard from '../components/DocumentCard'

export default function UploadPage() {
  const [documents, setDocuments] = useState([])

  const handleUploaded = (newDoc) => {
    // Keep only the latest upload visible on this page.
    setDocuments([newDoc])
  }

  return (
    <div className="page-shell" style={{ maxWidth: 820 }}>
      <div className="page-header">
        <h1 className="page-title">Document Processor</h1>
        <p className="page-subtitle">
        Upload images or PDFs — extract text with OCR and bounding box visualization.
        </p>
      </div>

      <DocumentUploader onUploaded={handleUploaded} />

      {documents.length > 0 && (
        <div style={{ marginTop: 28 }}>
          <h2 style={{ marginBottom: 14, fontSize: 20 }}>
            Uploaded Documents ({documents.length})
          </h2>
          {documents.map(doc => (
            <DocumentCard key={doc.id} doc={doc} />
          ))}
        </div>
      )}

      {documents.length === 0 && (
        <p style={{ textAlign: 'center', color: '#94a3b8', marginTop: 36 }}>
          No documents uploaded yet.
        </p>
      )}
    </div>
  )
}