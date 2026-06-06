import { useState } from 'react'
import type { Entry, Filter } from './types'
import { useTraffic } from './hooks/useTraffic'

// ---- Color helpers ----

function methodColor(method: string): string {
  switch (method.toUpperCase()) {
    case 'GET':    return '#2563eb'
    case 'POST':   return '#16a34a'
    case 'PUT':    return '#ea580c'
    case 'DELETE': return '#dc2626'
    default:       return '#6b7280'
  }
}

function statusColor(code: number | undefined): string {
  if (code === undefined) return '#6b7280'
  if (code < 300) return '#16a34a'
  if (code < 400) return '#2563eb'
  if (code < 500) return '#ea580c'
  return '#dc2626'
}

// ---- Utilities ----

function decodeBody(b64: string | undefined): string {
  if (!b64) return ''
  try {
    return atob(b64)
  } catch {
    return b64
  }
}

function formatBody(raw: string): string {
  try {
    return JSON.stringify(JSON.parse(raw), null, 2)
  } catch {
    return raw
  }
}

// ---- Sub-components ----

interface HeadersTableProps {
  headers: Record<string, string[]> | undefined
}

function HeadersTable({ headers }: HeadersTableProps) {
  if (!headers || Object.keys(headers).length === 0) {
    return <p style={{ color: '#9ca3af', fontSize: 13 }}>No headers</p>
  }
  return (
    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
      <tbody>
        {Object.entries(headers).map(([key, values]) => (
          <tr key={key} style={{ borderBottom: '1px solid #1f2937' }}>
            <td style={{ padding: '3px 8px 3px 0', color: '#9ca3af', verticalAlign: 'top', whiteSpace: 'nowrap', width: '35%' }}>{key}</td>
            <td style={{ padding: '3px 0', color: '#e5e7eb', wordBreak: 'break-all' }}>{values.join(', ')}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

interface BodyBlockProps {
  raw: string | undefined
}

function BodyBlock({ raw }: BodyBlockProps) {
  const decoded = decodeBody(raw)
  if (!decoded) return <p style={{ color: '#9ca3af', fontSize: 13 }}>No body</p>
  const formatted = formatBody(decoded)
  return (
    <pre style={{
      margin: 0,
      padding: '8px',
      background: '#111827',
      borderRadius: 4,
      fontSize: 12,
      color: '#d1fae5',
      overflowX: 'auto',
      whiteSpace: 'pre-wrap',
      wordBreak: 'break-all',
      maxHeight: 240,
      overflowY: 'auto',
    }}>
      {formatted}
    </pre>
  )
}

// ---- TrafficList ----

interface TrafficListProps {
  entries: Entry[]
  selectedId: number | null
  onSelect: (entry: Entry) => void
}

function TrafficList({ entries, selectedId, onSelect }: TrafficListProps) {
  const thStyle: React.CSSProperties = {
    padding: '6px 8px',
    textAlign: 'left',
    fontSize: 12,
    color: '#9ca3af',
    borderBottom: '1px solid #374151',
    whiteSpace: 'nowrap',
    userSelect: 'none',
  }

  return (
    <div style={{ overflowY: 'auto', flex: 1, minHeight: 0 }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', tableLayout: 'fixed' }}>
        <colgroup>
          <col style={{ width: 50 }} />
          <col style={{ width: 68 }} />
          <col />
          <col style={{ width: 60 }} />
          <col style={{ width: 70 }} />
          <col style={{ width: 72 }} />
          <col style={{ width: 80 }} />
        </colgroup>
        <thead style={{ position: 'sticky', top: 0, background: '#111827', zIndex: 1 }}>
          <tr>
            <th style={thStyle}>ID</th>
            <th style={thStyle}>Method</th>
            <th style={thStyle}>Host / Path</th>
            <th style={thStyle}>Status</th>
            <th style={{ ...thStyle, textAlign: 'right' }}>Duration</th>
            <th style={thStyle}>Protocol</th>
            <th style={thStyle}>Tags</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((entry) => {
            const isSelected = entry.id === selectedId
            const isBlocked = entry.tags?.includes('blocked')
            const isModified = entry.modified === true

            let rowBg = isSelected ? '#1e3a5f' : 'transparent'
            if (!isSelected && isBlocked) rowBg = '#3b1010'
            else if (!isSelected && isModified) rowBg = '#2e2a00'

            const hostPath = entry.host + (entry.path || '/') + (entry.query ? `?${entry.query}` : '')
            const durationText = entry.duration_ms !== undefined ? `${entry.duration_ms}ms` : '—'

            return (
              <tr
                key={entry.id}
                onClick={() => onSelect(entry)}
                style={{
                  background: rowBg,
                  cursor: 'pointer',
                  borderBottom: '1px solid #1f2937',
                }}
                onMouseEnter={(e) => {
                  if (!isSelected) (e.currentTarget as HTMLTableRowElement).style.background = isBlocked ? '#4c1515' : isModified ? '#3d3800' : '#1f2937'
                }}
                onMouseLeave={(e) => {
                  if (!isSelected) (e.currentTarget as HTMLTableRowElement).style.background = rowBg
                }}
              >
                <td style={{ padding: '5px 8px', fontSize: 12, color: '#6b7280' }}>{entry.id}</td>
                <td style={{ padding: '5px 8px' }}>
                  <span style={{
                    background: methodColor(entry.method),
                    color: '#fff',
                    borderRadius: 3,
                    padding: '1px 5px',
                    fontSize: 11,
                    fontWeight: 600,
                    letterSpacing: '0.02em',
                  }}>
                    {entry.method}
                  </span>
                </td>
                <td style={{ padding: '5px 8px', fontSize: 12, color: '#e5e7eb', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={hostPath}>
                  {hostPath}
                </td>
                <td style={{ padding: '5px 8px', fontSize: 12, color: statusColor(entry.status_code), fontWeight: 600 }}>
                  {entry.status_code ?? '—'}
                </td>
                <td style={{ padding: '5px 8px', fontSize: 12, color: '#9ca3af', textAlign: 'right' }}>{durationText}</td>
                <td style={{ padding: '5px 8px', fontSize: 12, color: '#6b7280' }}>{entry.protocol}</td>
                <td style={{ padding: '5px 8px', fontSize: 11, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {entry.tags?.map((tag) => (
                    <span key={tag} style={{
                      marginRight: 3,
                      background: tag === 'blocked' ? '#7f1d1d' : '#374151',
                      color: tag === 'blocked' ? '#fca5a5' : '#9ca3af',
                      borderRadius: 3,
                      padding: '1px 4px',
                    }}>
                      {tag}
                    </span>
                  ))}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
      {entries.length === 0 && (
        <div style={{ textAlign: 'center', padding: '40px 0', color: '#4b5563', fontSize: 14 }}>
          No traffic captured yet
        </div>
      )}
    </div>
  )
}

// ---- TrafficDetail ----

interface TrafficDetailProps {
  entry: Entry
}

function TrafficDetail({ entry }: TrafficDetailProps) {
  const [replayResult, setReplayResult] = useState<string | null>(null)
  const [replaying, setReplaying] = useState(false)

  async function handleReplay() {
    setReplaying(true)
    setReplayResult(null)
    try {
      const res = await fetch('/api/replay', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ entry_id: entry.id }),
      })
      const data = await res.json()
      if (data.error) {
        setReplayResult(`Error: ${data.error}`)
      } else {
        setReplayResult(`Replayed — status ${data.status_code} in ${data.duration_ms}ms`)
      }
    } catch (err) {
      setReplayResult(`Request failed: ${err instanceof Error ? err.message : String(err)}`)
    } finally {
      setReplaying(false)
    }
  }

  const sectionHeader: React.CSSProperties = {
    fontSize: 13,
    fontWeight: 700,
    color: '#9ca3af',
    textTransform: 'uppercase',
    letterSpacing: '0.06em',
    marginBottom: 6,
    marginTop: 0,
  }

  const sectionBox: React.CSSProperties = {
    background: '#1f2937',
    borderRadius: 6,
    padding: '12px 14px',
    marginBottom: 12,
  }

  const labelStyle: React.CSSProperties = {
    fontSize: 12,
    color: '#6b7280',
    marginBottom: 2,
  }

  const valueStyle: React.CSSProperties = {
    fontSize: 13,
    color: '#e5e7eb',
    marginBottom: 10,
    wordBreak: 'break-all',
  }

  const url = `${entry.scheme}://${entry.host}${entry.path || '/'}${entry.query ? `?${entry.query}` : ''}`

  return (
    <div style={{ overflowY: 'auto', flex: 1, minHeight: 0, padding: '12px 14px' }}>
      {/* Replay button */}
      <div style={{ marginBottom: 12, display: 'flex', alignItems: 'center', gap: 10 }}>
        <button
          onClick={handleReplay}
          disabled={replaying}
          style={{
            background: replaying ? '#374151' : '#2563eb',
            color: '#fff',
            border: 'none',
            borderRadius: 5,
            padding: '6px 16px',
            fontSize: 13,
            fontWeight: 600,
            cursor: replaying ? 'not-allowed' : 'pointer',
          }}
        >
          {replaying ? 'Replaying…' : 'Replay'}
        </button>
        {replayResult && (
          <span style={{ fontSize: 12, color: replayResult.startsWith('Error') ? '#f87171' : '#6ee7b7' }}>
            {replayResult}
          </span>
        )}
      </div>

      {/* Request */}
      <div style={sectionBox}>
        <p style={sectionHeader}>Request</p>
        <p style={labelStyle}>Method</p>
        <p style={{ ...valueStyle, color: methodColor(entry.method), fontWeight: 700 }}>{entry.method}</p>
        <p style={labelStyle}>URL</p>
        <p style={valueStyle}>{url}</p>
        <p style={{ ...labelStyle, marginTop: 4 }}>Headers</p>
        <div style={{ marginBottom: 10 }}>
          <HeadersTable headers={entry.req_header} />
        </div>
        <p style={{ ...labelStyle, marginTop: 4 }}>Body</p>
        <BodyBlock raw={entry.req_body} />
      </div>

      {/* Response */}
      <div style={sectionBox}>
        <p style={sectionHeader}>Response</p>
        <p style={labelStyle}>Status</p>
        <p style={{ ...valueStyle, color: statusColor(entry.status_code), fontWeight: 700 }}>
          {entry.status_code ?? '—'}
        </p>
        <p style={{ ...labelStyle, marginTop: 4 }}>Headers</p>
        <div style={{ marginBottom: 10 }}>
          <HeadersTable headers={entry.resp_header} />
        </div>
        <p style={{ ...labelStyle, marginTop: 4 }}>Body</p>
        <BodyBlock raw={entry.resp_body} />
      </div>
    </div>
  )
}

// ---- App ----

export default function App() {
  const { entries, total, loading, error, clear, filter, setFilter } = useTraffic()
  const [selectedEntry, setSelectedEntry] = useState<Entry | null>(null)

  function updateFilter(partial: Partial<Filter>) {
    setFilter({ ...filter, ...partial })
  }

  const toolbarStyle: React.CSSProperties = {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    padding: '8px 14px',
    background: '#111827',
    borderBottom: '1px solid #374151',
    flexShrink: 0,
  }

  const inputStyle: React.CSSProperties = {
    background: '#1f2937',
    border: '1px solid #374151',
    borderRadius: 4,
    color: '#e5e7eb',
    fontSize: 13,
    padding: '4px 8px',
    outline: 'none',
  }

  const selectStyle: React.CSSProperties = {
    ...inputStyle,
    cursor: 'pointer',
  }

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100vh',
      background: '#0f172a',
      color: '#e5e7eb',
      fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
    }}>
      {/* Toolbar */}
      <div style={toolbarStyle}>
        <span style={{ fontWeight: 800, fontSize: 18, color: '#f9fafb', letterSpacing: '-0.02em', marginRight: 4 }}>
          paxy
        </span>
        {/* Proxy status indicator */}
        <span title="Proxy active" style={{
          display: 'inline-block',
          width: 9,
          height: 9,
          borderRadius: '50%',
          background: '#22c55e',
          boxShadow: '0 0 6px #22c55e',
          marginRight: 6,
        }} />
        <span style={{ fontSize: 12, color: '#6b7280', marginRight: 8 }}>
          {total} entries
        </span>
        <button
          onClick={clear}
          style={{
            background: '#374151',
            color: '#d1d5db',
            border: 'none',
            borderRadius: 4,
            padding: '4px 12px',
            fontSize: 13,
            cursor: 'pointer',
            marginRight: 8,
          }}
        >
          Clear
        </button>
        <input
          type="text"
          placeholder="Search…"
          value={filter.search ?? ''}
          onChange={(e) => updateFilter({ search: e.target.value || undefined })}
          style={{ ...inputStyle, width: 180 }}
        />
        <select
          value={filter.method ?? ''}
          onChange={(e) => updateFilter({ method: e.target.value || undefined })}
          style={{ ...selectStyle, width: 100 }}
        >
          <option value="">All methods</option>
          {['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'].map((m) => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>
        <select
          value={filter.protocol ?? ''}
          onChange={(e) => updateFilter({ protocol: e.target.value || undefined })}
          style={{ ...selectStyle, width: 110 }}
        >
          <option value="">All protocols</option>
          <option value="HTTP/1.1">HTTP/1.1</option>
          <option value="HTTP/2">HTTP/2</option>
          <option value="HTTPS">HTTPS</option>
          <option value="HTTP">HTTP</option>
        </select>
        {loading && <span style={{ fontSize: 12, color: '#6b7280', marginLeft: 4 }}>Loading…</span>}
        {error && <span style={{ fontSize: 12, color: '#f87171', marginLeft: 4 }}>{error}</span>}
      </div>

      {/* Main panels */}
      <div style={{ display: 'flex', flex: 1, minHeight: 0 }}>
        {/* Left: Traffic list (60%) */}
        <div style={{
          width: '60%',
          display: 'flex',
          flexDirection: 'column',
          borderRight: '1px solid #374151',
          minHeight: 0,
        }}>
          <TrafficList
            entries={entries}
            selectedId={selectedEntry?.id ?? null}
            onSelect={setSelectedEntry}
          />
        </div>

        {/* Right: Traffic detail (40%) */}
        <div style={{
          width: '40%',
          display: 'flex',
          flexDirection: 'column',
          minHeight: 0,
        }}>
          {selectedEntry ? (
            <TrafficDetail entry={selectedEntry} />
          ) : (
            <div style={{
              flex: 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#4b5563',
              fontSize: 14,
            }}>
              Select a request to inspect
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
