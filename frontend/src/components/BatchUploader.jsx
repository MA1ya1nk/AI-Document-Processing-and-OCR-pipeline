// src/components/BatchUploader.jsx
import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { uploadBatch } from '../services/api'
import ErrorMessage from './ErrorMessage'

export default function BatchUploader({ onBatchStarted, disabled = false, disabledReason = '' }) {
  const [files, setFiles]     = useState([])
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')

  const onDrop = useCallback((accepted) => {
    if (disabled) return
    setFiles(accepted)
  }, [disabled])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/*': [], 'application/pdf': [], 'application/x-pdf': [], '.pdf': [] },
    multiple: true
  })

  const handleUpload = async () => {
    if (disabled) return
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
      {disabled && (
        <div style={{
          marginBottom: 10,
          background: '#fffbeb',
          border: '1px solid #fde68a',
          color: '#92400e',
          borderRadius: 10,
          padding: '10px 12px',
          fontSize: 13
        }}>
          {disabledReason || 'A batch is currently processing. Please wait until it finishes.'}
        </div>
      )}
      <div
        {...getRootProps()}
        style={{
          border: '2px dashed #93c5fd',
          borderRadius: 16,
          padding: 36,
          textAlign: 'center',
          cursor: disabled ? 'not-allowed' : 'pointer',
          opacity: disabled ? 0.65 : 1,
          background: isDragActive ? '#dbeafe' : '#f8faff',
          boxShadow: '0 8px 24px rgba(37,99,235,0.08)'
        }}
      >
        <input {...getInputProps({ disabled })} />
        <p style={{ fontSize: 18, color: '#2563eb', margin: 0, fontWeight: 700 }}>
          {isDragActive
            ? 'Drop all files!'
            : 'Upload documents to start batch extraction'}
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
            disabled={uploading || disabled}
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