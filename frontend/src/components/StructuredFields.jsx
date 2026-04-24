
import { useEffect, useState } from 'react'
import { updateFields } from '../services/api'
import ErrorMessage from './ErrorMessage'

const CONF_STYLE = {
  high:   { bg: '#dcfce7', color: '#166534' },
  medium: { bg: '#fef9c3', color: '#854d0e' },
  low:    { bg: '#fee2e2', color: '#991b1b' },
}

function FieldRow({ fieldKey, data, onSave }) {
  const [editing, setEditing] = useState(false)
  const [value, setValue]     = useState(data?.value ?? '')
  const conf      = data?.confidence || 'medium'
  const corrected = data?.manually_corrected

  useEffect(() => {
    setValue(data?.value ?? '')
    setEditing(false)
  }, [data?.value])

  if (Array.isArray(data?.value)) return null

  return (
    <div style={{
      display: 'flex', alignItems: 'flex-start', gap: 10,
      padding: '10px 0', borderBottom: '1px solid #f3f4f6'
    }}>
      <div style={{ width: 160, flexShrink: 0 }}>
        <span style={{ fontSize: 12, color: '#6b7280' }}>
          {fieldKey.replace(/_/g, ' ')}
        </span>
      </div>

      <div style={{ flex: 1 }}>
        {editing ? (
          <div style={{ display: 'flex', gap: 6 }}>
            <input
              value={value}
              onChange={e => setValue(e.target.value)}
              className="field-input"
              style={{ flex: 1, fontSize: 13, padding: '6px 8px', borderRadius: 8 }}
              autoFocus
            />
            <button
              onClick={() => { onSave(fieldKey, value); setEditing(false) }}
              className="btn btn-primary"
              style={{ padding: '6px 12px' }}
            >
              Save
            </button>
            <button
              onClick={() => { setValue(data?.value ?? ''); setEditing(false) }}
              className="btn btn-slate"
              style={{ padding: '6px 10px' }}
            >
              Cancel
            </button>
          </div>
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span
              style={{ fontSize: 13, cursor: 'pointer', flex: 1 }}
              onClick={() => setEditing(true)}
              title="Click to edit"
            >
              {value
                ? String(value)
                : <span style={{ color: '#d1d5db', fontStyle: 'italic' }}>not found</span>
              }
            </span>
            {corrected && (
              <span style={{ fontSize: 11, color: '#7c3aed', fontStyle: 'italic' }}>
                edited
              </span>
            )}
          </div>
        )}
      </div>

      <span style={{
        padding: '2px 8px', borderRadius: 20, fontSize: 11, flexShrink: 0,
        background: CONF_STYLE[conf]?.bg || '#f3f4f6',
        color: CONF_STYLE[conf]?.color || '#374151'
      }}>
        {conf}
      </span>
    </div>
  )
}

function TableField({ fieldKey, data }) {
  const rows = data?.value
  if (!rows || !Array.isArray(rows) || rows.length === 0) return null
  const headers = Object.keys(rows[0])

  return (
    <div style={{ marginTop: 16, marginBottom: 16 }}>
      <p style={{ fontSize: 12, color: '#6b7280', margin: '0 0 8px', fontWeight: 500 }}>
        {fieldKey.replace(/_/g, ' ').toUpperCase()}
      </p>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr>
              {headers.map(h => (
                <th key={h} style={{
                  padding: '6px 10px', background: '#f1f5f9',
                  borderBottom: '1px solid #e2e8f0',
                  textAlign: 'left', fontSize: 12,
                  color: '#475569', fontWeight: 500
                }}>
                  {h.replace(/_/g, ' ')}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i} style={{ background: i % 2 === 0 ? '#fff' : '#f8fafc' }}>
                {headers.map(h => (
                  <td key={h} style={{
                    padding: '6px 10px',
                    borderBottom: '1px solid #f1f5f9',
                    color: '#334155'
                  }}>
                    {row[h] ?? ''}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default function StructuredFields({ docId, fields }) {
  const [localFields, setLocalFields] = useState(fields || {})
  const [saving, setSaving]           = useState(false)
  const [error, setError]             = useState('')

  useEffect(() => {
    setLocalFields(fields || {})
    setError('')
    setSaving(false)
  }, [fields, docId])

  const handleSave = async (fieldKey, newValue) => {
    setError('')
    setSaving(true)
    try {
      const res = await updateFields(docId, { [fieldKey]: newValue })
      setLocalFields(res.data.fields)
    } catch (err) {
      setError('Save failed: ' + (err.response?.data?.error || err.message))
    }
    setSaving(false)
  }

  // If no fields at all
  if (!localFields || Object.keys(localFields).length === 0) {
    return (
      <p style={{ color: '#9ca3af', fontSize: 13, fontStyle: 'italic' }}>
        No extracted fields available.
      </p>
    )
  }

  // Split into scalar fields and table fields
  // Works with OR without schema — reads directly from fields object
  const allEntries    = Object.entries(localFields)
  const scalarEntries = allEntries.filter(([, v]) => !Array.isArray(v?.value))
  const tableEntries  = allEntries.filter(([, v]) => Array.isArray(v?.value) && v.value.length > 0)

  return (
    <div>
      <ErrorMessage message={error} />
      {saving && (
        <p style={{ fontSize: 12, color: '#6b7280', margin: '0 0 8px' }}>Saving...</p>
      )}

      {/* Scalar fields */}
      <div>
        {scalarEntries.map(([key, data]) => (
          <FieldRow
            key={key}
            fieldKey={key}
            data={data}
            onSave={handleSave}
          />
        ))}
      </div>

      {/* Table fields */}
      {tableEntries.map(([key, data]) => (
        <TableField key={key} fieldKey={key} data={data} />
      ))}
    </div>
  )
}