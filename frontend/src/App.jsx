// src/App.jsx
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import UploadPage from './pages/UploadPage'
import DocumentReviewPage from './pages/DocumentReviewPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/"               element={<UploadPage />} />
        <Route path="/document/:id"   element={<DocumentReviewPage />} />
      </Routes>
    </BrowserRouter>
  )
}