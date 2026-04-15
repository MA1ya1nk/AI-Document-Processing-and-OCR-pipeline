// src/App.jsx
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import UploadPage from './pages/UploadPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<UploadPage />} />
        {/* Phase 3+ will add:
            <Route path="/library" element={<LibraryPage />} />
            <Route path="/batch"   element={<BatchPage />} />
            <Route path="/document/:id" element={<DocumentReviewPage />} />
        */}
      </Routes>
    </BrowserRouter>
  )
}