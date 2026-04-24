// src/components/BatchUploader.jsx
import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { uploadBatch } from '../services/api'
import ErrorMessage from './ErrorMessage'

export default function BatchUploader({ onBatchStarted }) {
  const [files, setFiles]     = useState([])
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')

  const onDrop = useCallback((accepted) => {
    setFiles(accepted)
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/*': [], 'application/pdf': [], 'application/x-pdf': [], '.pdf': [] },
    multiple: true
  })

  const handleUpload = async () => {
    if (!files.length) return
    setUploading(true)
    setError('')

    try {
      const res = await uploadBatch(files)
      const data = res.data
      onBatchStarted(data.batch_id, data.documents)
      setFiles([])
    } catch (err) {
      setError('Batch upload failed: ' + (err.response?.data?.error || err.message))
    }
    setUploading(false)
  }

  return (
    <div>
      <ErrorMessage message={error} />
      <div
        {...getRootProps()}
        style={{
          border: '2px dashed #93c5fd',
          borderRadius: 16,
          padding: 36,
          textAlign: 'center',
          cursor: 'pointer',
          background: isDragActive ? '#dbeafe' : '#f8faff',
          boxShadow: '0 8px 24px rgba(37,99,235,0.08)'
        }}
      >
        <input {...getInputProps()} />
        <p style={{ fontSize: 18, color: '#2563eb', margin: 0, fontWeight: 700 }}>
          {isDragActive
            ? 'Drop all files!'
            : 'Drop 10–50 documents here for batch processing'}
        </p>
        <p style={{ fontSize: 13, color: '#93c5fd', margin: '8px 0 0' }}>
          All files will be processed automatically in the background
        </p>
      </div>

      {files.length > 0 && (
        <div style={{ marginTop: 14 }} className="card">
          <p style={{ fontSize: 13, color: '#374151' }}>
            {files.length} file{files.length > 1 ? 's' : ''} selected:
          </p>
          <div style={{
            maxHeight: 120, overflowY: 'auto',
            border: '1px solid #e5e7eb', borderRadius: 8, padding: 8
          }}>
            {files.map((f, i) => (
              <div key={i} style={{
                fontSize: 12, padding: '3px 0',
                borderBottom: '1px solid #f3f4f6', color: '#374151'
              }}>
                {f.name} · {(f.size / 1024).toFixed(1)} KB
              </div>
            ))}
          </div>
          <button
            onClick={handleUpload}
            disabled={uploading}
            className="btn btn-primary"
            style={{ marginTop: 10, fontSize: 14 }}
          >
            {uploading ? 'Uploading...' : `Process ${files.length} documents`}
          </button>
        </div>
      )}
    </div>
  )
}