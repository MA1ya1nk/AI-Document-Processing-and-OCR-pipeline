// src/components/Navbar.jsx
import { NavLink } from 'react-router-dom'

const linkStyle = ({ isActive }) => ({
  padding: '6px 14px', borderRadius: 8,
  textDecoration: 'none', fontSize: 14,
  fontWeight: isActive ? 500 : 400,
  background: isActive ? '#eff6ff' : 'transparent',
  color: isActive ? '#2563eb' : '#4b5563'
})

export default function Navbar() {
  return (
    <nav style={{
      borderBottom: '1px solid #e5e7eb',
      padding: '12px 24px',
      display: 'flex', alignItems: 'center', gap: 8,
      background: '#fff', position: 'sticky', top: 0, zIndex: 10
    }}>
      <span style={{ fontWeight: 600, fontSize: 16, marginRight: 16, color: '#111827' }}>
        DocProcessor
      </span>
      <NavLink to='/'        style={linkStyle}>Upload</NavLink>
      <NavLink to='/history' style={linkStyle}>History</NavLink>
      <NavLink to='/batch'   style={linkStyle}>Batch</NavLink>
    </nav>
  )
}