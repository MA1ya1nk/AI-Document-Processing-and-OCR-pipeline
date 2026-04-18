
// src/services/api.js
import axios from 'axios'

const BASE = 'http://localhost:5000'

export const uploadDocument = (file) => {
  const form = new FormData()
  form.append('file', file)
  return axios.post(`${BASE}/api/upload`, form)
}

export const classifyDocument = (docId) =>
  axios.post(`${BASE}/api/classify/${docId}`)

export const extractDocument = (docId, docType = null) =>
  axios.post(`${BASE}/api/extract/${docId}`, docType ? { doc_type: docType } : {})

export const updateFields = (docId, corrections) =>
  axios.put(`${BASE}/api/documents/${docId}/fields`, corrections)

export const listDocuments = () =>
  axios.get(`${BASE}/api/documents`)

export const getDocument = (docId) =>
  axios.get(`${BASE}/api/documents/${docId}`)

export const getPreviewUrl = (docId) =>
  `${BASE}/api/documents/${docId}/preview?t=${Date.now()}`

export const getExportUrl = (docId, format) =>
  `${BASE}/api/export/${docId}?format=${format}`


// export const listDocuments = () =>
//   axios.get(`${BASE}/api/documents`)

export const deleteDocument = (docId) =>
  axios.delete(`${BASE}/api/documents/${docId}`)



export const uploadBatch = (files) => {
  const form = new FormData()
  files.forEach(f => form.append('files', f))
  return axios.post(`${BASE}/api/upload/batch`, form, {
    onUploadProgress: (e) => {
      // e.loaded / e.total gives upload progress 0-1
    }
  })
}

export const getBatchStatus = (batchId) =>
  axios.get(`${BASE}/api/batch/${batchId}/status`)

export const getBatchExportUrl = (batchId, format) =>
  `${BASE}/api/batch/${batchId}/export?format=${format}`

export const approveDocument = (docId) =>
  axios.patch(`${BASE}/api/documents/${docId}/status`, { approval_status: 'approved' })