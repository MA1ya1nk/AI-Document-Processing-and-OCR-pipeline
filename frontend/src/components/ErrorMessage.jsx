export default function ErrorMessage({ message }) {
  if (!message) return null

  return (
    <div
      style={{
        background: '#fef2f2',
        color: '#991b1b',
        border: '1px solid #fecaca',
        borderRadius: 10,
        padding: '10px 12px',
        fontSize: 13,
        marginBottom: 10,
        boxShadow: '0 4px 12px rgba(220, 38, 38, 0.1)'
      }}
      role="alert"
      aria-live="polite"
    >
      {message}
    </div>
  )
}
