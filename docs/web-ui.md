# Web UI

## GUI Mode

Start paxy in GUI mode (the default) and open `http://localhost:8081`.
The UI is built with [NiceGUI](https://nicegui.io/) and runs in the same Python process as the proxy.

## Layout

```
┌──────────────────────────────────────────────────────────────┐
│  toolbar: paxy ● | Filter expression | Intercept | Clear | ⚙ │
├─────────────────────────────────────────────────────────────-┤
│  Traffic | Resender | Bulk Sender | Diff                      │
├──────────────────────────┬───────────────────────────────────┤
│  Traffic list            │  Detail panel                     │
│  (left 60%)              │  (right 40%)                      │
│  click row to select     │  Request / Response               │
│  right-click for menu    │  Body view selector               │
│                          │  Replay button                    │
└──────────────────────────┴───────────────────────────────────┘
```

## Tabs

### Traffic

The main traffic list. New requests are prepended in real time.

| Column | Description |
|--------|-------------|
| ID | Sequential capture number |
| Method | HTTP method (color badge) |
| Host | Hostname |
| Path | Path including query string |
| Status | HTTP status (color badge) |
| Size | Response body size |
| ms | Response time in milliseconds |
| Proto | `http`, `https`, `ws`, `grpc` |

**Row colors** — right-click any row to assign a color for visual grouping.

**Right-click menu:**
- Send to Resender
- Send to Bulk Sender
- Set as Diff left / Diff with left
- Set color

### Resender

Edit and re-send any request. Click **+ New** or right-click a traffic row → **Send to Resender**.

- Method + URL bar
- Headers editor (raw text, one `Key: Value` per line)
- Body editor
- Response panel (status, headers, body)
- HTTP/2 supported automatically

### Bulk Sender

Send many variants of one request concurrently.

**Payload list mode:** Enter one payload per line (JSON or plain text). Each line becomes a separate request body.

**Race condition mode:** Send the same request N times simultaneously to test for race conditions.

Results table shows status code, response time, and errors per request.

### Diff

Compare two captured entries side by side.

1. Right-click entry A → **Set as Diff left**
2. Right-click entry B → **Diff with left**
3. Switch to the Diff tab — unified diff is shown for Request, Response, and Headers.

## Filter expression

The filter bar accepts a structured expression:

```
field op value
field op value && field op value
field op value || field op value
```

**Fields:** `host`, `path`, `method`, `status`, `protocol`, `request`, `response`, `full_text`

**Operators:** `==` (exact), `!=` (not equal), `contains` (substring), `~` (regex)

**Examples:**
```
host == api.example.com
method == POST && path contains /login
status ~ ^[45]
full_text contains token
```

## Body view selector

The detail panel's body section has a view mode dropdown:

| Mode | Description |
|------|-------------|
| Auto | Detect from Content-Type (default) |
| Text | Raw UTF-8 text |
| JSON | Pretty-printed JSON |
| Hex | Hex dump with ASCII column |
| Protobuf | Wire-type heuristic decode (no schema needed) |
| MessagePack | Decoded to JSON |
| CBOR | Decoded to JSON |

## Intercept toggle

Enable the **Intercept** toggle in the toolbar to pause every request for manual review.

A dialog appears with the request headers and body. You can edit them before forwarding, or drop the request entirely.

## Settings page

Click ⚙ in the toolbar to open the settings page (`/settings`).

### Rules

Add, enable/disable, and delete intercept rules from the UI.

### SSL Passthrough

Add hosts that should be tunneled without TLS interception (for certificate-pinned apps).

### DNS Overwrite

Configure the built-in DNS server to redirect specific domains to a target IP.
Start the DNS server and point devices to this machine's IP for DNS.

### Listen Ports

Change the proxy and UI port (takes effect on restart).

### Client Certificates

Import client certificates for mutual TLS. Certificates are matched to hosts by glob pattern.

## CUI Mode

```bash
uv run python main.py --mode cui
```

A rich-rendered table updates in real time inside the terminal.

| Key | Action |
|-----|--------|
| `q` / `Ctrl+C` | Quit |
| `c` | Clear traffic |

The REST API remains available at `:8081` in CUI mode.
