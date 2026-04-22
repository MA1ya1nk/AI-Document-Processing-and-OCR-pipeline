export default function ErrorMessage({ message }) {
  if (!message) return null

  return (
    <div
      style={{
        background: '#fee2e2',
        color: '#991b1b',
        border: '1px solid #fecaca',
        borderRadius: 8,
        padding: '8px 12px',
        fontSize: 13,
        marginBottom: 10
      }}
      role="alert"
      aria-live="polite"
    >
      {message}
    </div>
  )
}
