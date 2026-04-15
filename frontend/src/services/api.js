import axios from 'axios'

const BASE = 'http://localhost:5000'

export const uploadDocument = (file) => {
  const form = new FormData()
  form.append('file', file)
  return axios.post(`${BASE}/api/upload`, form)
}

export const extractDocument = (docId) =>
  axios.post(`${BASE}/api/extract/${docId}`)

export const listDocuments = () =>
  axios.get(`${BASE}/api/documents`)

export const getPreviewUrl = (docId) =>
  `${BASE}/api/documents/${docId}/preview?t=${Date.now()}`