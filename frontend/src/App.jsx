// src/App.jsx
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar'
import UploadPage from './pages/UploadPage'
import DocumentReviewPage from './pages/DocumentReviewPage'
import HistoryPage from './pages/HistoryPage'
import BatchPage from './pages/BatchPage'

export default function App() {
  return (
    <BrowserRouter>
      <Navbar />
      <Routes>
        <Route path='/'             element={<UploadPage />} />
        <Route path='/history'      element={<HistoryPage />} />
        <Route path='/batch'        element={<BatchPage />} />
        <Route path='/document/:id' element={<DocumentReviewPage />} />
      </Routes>
    </BrowserRouter>
  )
}