# API Reference

The API server runs on `http://localhost:8081` by default.

## Traffic

### `GET /api/traffic`

List captured entries.

**Query params:**

| Param | Description |
|-------|-------------|
| `offset` | Pagination offset (default 0) |
| `limit` | Max results (default 100) |
| `method` | Filter by HTTP method |
| `host` | Filter by exact host |
| `search` | Free-text search on host+path |
| `protocol` | Filter by protocol (`http`, `https`, `ws`, `grpc`) |

**Response:**

```json
{
  "entries": [ ... ],
  "total": 42,
  "offset": 0,
  "limit": 100
}
```

### `GET /api/traffic/:id`

Get a single entry by ID.

**Response:** `Entry` object (see schema below).

## Rules

### `GET /api/rules`

List all rules.

### `POST /api/rules`

Create a rule. Body: `Rule` object (without `id`).

### `PUT /api/rules/:id`

Update a rule. Body: full `Rule` object.

### `DELETE /api/rules/:id`

Delete a rule. Returns `204 No Content`.

## Replay

### `POST /api/replay`

Replay a captured entry.

**Body:**

```json
{
  "entry_id": 42,
  "options": {
    "override_host": "staging.example.com",
    "extra_headers": { "X-Test": "1" },
    "timeout_seconds": 30,
    "count": 1
  }
}
```

**Response:** Array of `ReplayResult` objects.

## Misc

### `POST /api/clear`

Delete all captured entries. Returns `204 No Content`.

## WebSocket

### `GET /ws`

Upgrade to WebSocket. Receives a stream of `Entry` JSON objects in real time as traffic is captured.

```javascript
const ws = new WebSocket('ws://localhost:8081/ws')
ws.onmessage = (e) => {
  const entry = JSON.parse(e.data)
  console.log(entry.method, entry.host, entry.path, entry.status_code)
}
```

## Schemas

### Entry

```typescript
{
  id:           number
  created_at:   string        // ISO 8601
  method:       string
  scheme:       string        // "http" | "https" | "ws" | "wss"
  host:         string
  path:         string
  query?:       string
  req_header?:  Record<string, string[]>
  req_body?:    string        // base64
  status_code?: number
  resp_header?: Record<string, string[]>
  resp_body?:   string        // base64
  duration_ms?: number
  protocol:     string
  tags?:        string[]
  modified?:    boolean
}
```

### Rule

```typescript
{
  id:             number
  name:           string
  enabled:        boolean
  priority:       number
  conditions:     Condition[]
  action:         "passthrough" | "modify" | "block" | "redirect"
  modifications?: Modification[]
  redirect_url?:  string
}
```

### ReplayResult

```typescript
{
  entry_id:    number
  status_code: number
  body?:       string   // base64
  duration_ms: number
  error?:      string
}
```
