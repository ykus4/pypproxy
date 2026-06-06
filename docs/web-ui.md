# Web UI

The web UI runs on `http://localhost:8081` by default. Open it in any browser after starting paxy.

## Layout

```
┌─────────────────────────────────────────────────────┐
│  toolbar: title · status · filter bar · clear       │
├──────────────────────────┬──────────────────────────┤
│  Traffic List (left)     │  Traffic Detail (right)  │
│  scrollable table        │  request / response      │
│  click row to select     │  headers + body          │
│                          │  replay button           │
└──────────────────────────┴──────────────────────────┘
```

## Traffic list

Each row shows:

| Column | Description |
|--------|-------------|
| ID | Sequential capture ID |
| Method | HTTP method with color badge |
| Host + Path | Destination |
| Status | HTTP status with color badge |
| Duration | Round-trip time in ms |
| Protocol | `http`, `https`, `ws`, `grpc` |
| Tags | `blocked`, `modified`, `websocket`, etc. |

Row colors:
- **Yellow tint** — request or response was modified by a rule
- **Red tint** — request was blocked by a rule

## Filtering

The toolbar provides four filters applied instantly:

| Filter | Description |
|--------|-------------|
| Search | Free-text match on host + path |
| Method | Exact method filter (GET, POST, …) |
| Protocol | `http`, `https`, `ws`, `grpc` |

## Traffic detail

Click any row to open the detail panel on the right.

**Request section**
- Method and full URL
- Request headers as a key/value table
- Request body (decoded from base64; pretty-printed if JSON)

**Response section**
- Status code
- Response headers as a key/value table
- Response body (decoded; pretty-printed if JSON)

**Replay button** — sends the original request again and shows the result inline.

## Real-time updates

The UI connects to `ws://localhost:8081/ws` and receives new entries as they are captured. No manual refresh needed.

## Clear

The **Clear** button in the toolbar deletes all captured entries from memory and resets the list.
