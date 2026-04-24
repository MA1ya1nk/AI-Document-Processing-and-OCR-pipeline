// src/components/Navbar.jsx
import { NavLink } from 'react-router-dom'

const linkStyle = ({ isActive }) => ({
  padding: '8px 14px', borderRadius: 10,
  textDecoration: 'none', fontSize: 14,
  fontWeight: isActive ? 600 : 500,
  background: isActive ? '#dbeafe' : 'transparent',
  color: isActive ? '#1d4ed8' : '#64748b'
})

export default function Navbar() {
  return (
    <nav style={{
      borderBottom: '1px solid #e2e8f0',
      padding: '14px 24px',
      display: 'flex', alignItems: 'center', gap: 8,
      background: 'rgba(255,255,255,0.88)',
      backdropFilter: 'blur(10px)',
      position: 'sticky', top: 0, zIndex: 10
    }}>
      <span style={{ fontWeight: 700, fontSize: 16, marginRight: 16, color: '#0f172a' }}>
        DocProcessor
      </span>
      <NavLink to='/'        style={linkStyle}>Upload</NavLink>
      <NavLink to='/history' style={linkStyle}>History</NavLink>
      <NavLink to='/batch'   style={linkStyle}>Batch</NavLink>
    </nav>
  )
}