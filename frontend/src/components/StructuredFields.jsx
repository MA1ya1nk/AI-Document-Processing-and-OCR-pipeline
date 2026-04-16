// src/components/StructuredFields.jsx
import { useState } from 'react'
import { updateFields } from '../services/api'

const CONFIDENCE_STYLE = {
  high:   { bg: '#dcfce7', color: '#166534' },
  medium: { bg: '#fef9c3', color: '#854d0e' },
  low:    { bg: '#fee2e2', color: '#991b1b' },
}

function FieldRow({ fieldKey, label, data, onSave }) {
  const [editing, setEditing] = useState(false)
  const [value, setValue] = useState(data?.value ?? '')
  const conf = data?.confidence || 'medium'
  const style = CONFIDENCE_STYLE[conf] || CONFIDENCE_STYLE.medium
  const corrected = data?.manually_corrected

  // Tables get rendered separately
  if (Array.isArray(data?.value)) return null

  return (
    <div style={{
      display: 'flex', alignItems: 'flex-start', gap: 10,
      padding: '10px 0', borderBottom: '1px solid #f3f4f6'
    }}>
      <div style={{ width: 160, flexShrink: 0 }}>
        <span style={{ fontSize: 12, color: '#6b7280' }}>{label}</span>
      </div>

      <div style={{ flex: 1 }}>
        {editing ? (
          <div style={{ display: 'flex', gap: 6 }}>
            <input
              value={value}
              onChange={e => setValue(e.target.value)}
              style={{
                flex: 1, padding: '4px 8px', fontSize: 13,
                border: '1px solid #d1d5db', borderRadius: 6, outline: 'none'
              }}
              autoFocus
            />
            <button
              onClick={() => { onSave(fieldKey, value); setEditing(false) }}
              style={{ background: '#2563eb', color: '#fff', border: 'none',
                       borderRadius: 6, padding: '4px 12px', cursor: 'pointer', fontSize: 12 }}
            >
              Save
            </button>
            <button
              onClick={() => { setValue(data?.value ?? ''); setEditing(false) }}
              style={{ background: '#e5e7eb', color: '#374151', border: 'none',
                       borderRadius: 6, padding: '4px 10px', cursor: 'pointer', fontSize: 12 }}
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
              {value || <span style={{ color: '#d1d5db', fontStyle: 'italic' }}>not found</span>}
            </span>
            {corrected && (
              <span style={{ fontSize: 11, color: '#7c3aed', fontStyle: 'italic' }}>edited</span>
            )}
          </div>
        )}
      </div>

      <span style={{
        padding: '2px 8px', borderRadius: 20, fontSize: 11,
        background: style.bg, color: style.color, flexShrink: 0
      }}>
        {conf}
      </span>
    </div>
  )
}

function TableField({ label, data }) {
  const rows = data?.value
  if (!rows || !rows.length) return null
  const headers = Object.keys(rows[0])

  return (
    <div style={{ marginTop: 16 }}>
      <p style={{ fontSize: 12, color: '#6b7280', margin: '0 0 8px' }}>{label}</p>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr>
              {headers.map(h => (
                <th key={h} style={{
                  padding: '6px 10px', background: '#f1f5f9',
                  borderBottom: '1px solid #e2e8f0', textAlign: 'left',
                  fontSize: 12, color: '#475569', fontWeight: 500
                }}>
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i} style={{ background: i % 2 === 0 ? '#fff' : '#f8fafc' }}>
                {headers.map(h => (
                  <td key={h} style={{
                    padding: '6px 10px', borderBottom: '1px solid #f1f5f9', color: '#334155'
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

export default function StructuredFields({ docId, fields, schema }) {
  const [localFields, setLocalFields] = useState(fields)
  const [saving, setSaving] = useState(false)

  const handleSave = async (fieldKey, newValue) => {
    setSaving(true)
    try {
      const res = await updateFields(docId, { [fieldKey]: newValue })
      setLocalFields(res.data.fields)
    } catch (err) {
      alert('Save failed: ' + err.message)
    }
    setSaving(false)
  }

  if (!fields || !schema) return null

  const schemaFields = schema.fields || []
  const tableFields = schemaFields.filter(f => f.type === 'table')
  const scalarFields = schemaFields.filter(f => f.type !== 'table')

  return (
    <div>
      {saving && (
        <p style={{ fontSize: 12, color: '#6b7280', margin: '0 0 8px' }}>Saving...</p>
      )}

      {/* Scalar fields */}
      <div>
        {scalarFields.map(f => (
          <FieldRow
            key={f.key}
            fieldKey={f.key}
            label={f.label}
            data={localFields[f.key]}
            onSave={handleSave}
          />
        ))}
      </div>

      {/* Table fields */}
      {tableFields.map(f => (
        <TableField
          key={f.key}
          label={f.label}
          data={localFields[f.key]}
        />
      ))}
    </div>
  )
}