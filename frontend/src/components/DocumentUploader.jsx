import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { uploadDocument } from '../services/api'
import ErrorMessage from './ErrorMessage'

export default function DocumentUploader({ onUploaded }) {
  const [error, setError] = useState('')

  const onDrop = useCallback(async (acceptedFiles) => {
    setError('')
    for (const file of acceptedFiles) {
      try {
        const res = await uploadDocument(file)
        onUploaded(res.data.document)
      } catch (err) {
        setError('Upload failed: ' + (err.response?.data?.error || err.message))
      }
    }
  }, [onUploaded])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/*': [], 'application/pdf': [], 'application/x-pdf': [], '.pdf': [] },
    multiple: true
  })

  return (
    <div
      {...getRootProps()}
      style={{
        border: '2px dashed #93c5fd',
        borderRadius: 16,
        padding: 52,
        textAlign: 'center',
        cursor: 'pointer',
        background: isDragActive ? '#dbeafe' : '#f8fbff',
        transition: 'all 0.2s ease',
        boxShadow: '0 8px 24px rgba(37,99,235,0.08)'
      }}
    >
      <input {...getInputProps()} />
      <ErrorMessage message={error} />
      <p style={{ fontSize: 20, color: '#1e293b', margin: 0, fontWeight: 700 }}>
        {isDragActive ? 'Drop it!' : 'Drop documents here, or click to browse'}
      </p>
      <p style={{ fontSize: 13, color: '#64748b', margin: '10px 0 0' }}>
        Supports JPG, PNG, PDF
      </p>
    </div>
  )
}