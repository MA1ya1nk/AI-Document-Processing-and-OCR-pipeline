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
        border: '2px dashed #aaa',
        borderRadius: 12,
        padding: 48,
        textAlign: 'center',
        cursor: 'pointer',
        background: isDragActive ? '#f0f4ff' : '#fafafa',
        transition: 'background 0.2s'
      }}
    >
      <input {...getInputProps()} />
      <ErrorMessage message={error} />
      <p style={{ fontSize: 18, color: '#555', margin: 0 }}>
        {isDragActive ? 'Drop it!' : 'Drop documents here, or click to browse'}
      </p>
      <p style={{ fontSize: 13, color: '#999', margin: '8px 0 0' }}>
        Supports JPG, PNG, PDF
      </p>
    </div>
  )
}