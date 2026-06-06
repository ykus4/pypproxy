# Web UI

## GUI Mode

Start pypproxy in GUI mode (the default) and open `http://localhost:8081`.

```bash
pypproxy            # or
pypproxy --mode gui
```

## Layout

```
┌──────────────────────────────────────────────────────────────────┐
│  sidebar (220px)  │  toolbar: filter | Intercept | Clear | ⚙ ☀  │
│                   ├──────────────────────────────────────────────┤
│  Traffic          │                                              │
│  ─── Tools ───    │  Traffic list (left)  │  Detail panel        │
│  Resender         │  click row to select  │  Request / Response  │
│  Bulk Sender      │  right-click for menu │  Body view selector  │
│  Macro            │                       │  Replay button       │
│  Diff             │                                              │
│  A/B Test         │                                              │
│  ─── Security ─── │                                              │
│  Security         │                                              │
│  Adv Security     │                                              │
│  Scan             │                                              │
│  ─── Analysis ─── │                                              │
│  GraphQL          │                                              │
│  Analytics        │                                              │
│  OpenAPI          │                                              │
│  ─── Dev ───      │                                              │
│  Code Gen         │                                              │
│  Frida            │                                              │
│  Sessions         │                                              │
│  Report           │                                              │
│  ─── Data ───     │                                              │
│  Import/Search    │                                              │
│  Settings (⚙)     │                                              │
└───────────────────┴──────────────────────────────────────────────┘
```

## Sidebar navigation

Click any item in the sidebar to switch pages. The active item is highlighted with a blue left border.

## Light / Dark mode

Click the **☀ / 🌙 button** in the toolbar to toggle between light and dark mode. The preference is saved to `localStorage` and restored on next visit.

## Traffic list

New requests appear in real time at the top.

| Column | Description |
|--------|-------------|
| # | Sequential capture ID |
| Method | HTTP method (color pill) |
| Host | Hostname |
| Path | Path + query string |
| Status | HTTP status (color pill) |
| Size | Response body size |
| ms | Response time |

**Right-click menu:**

| Action | Description |
|--------|-------------|
| Send to Resender | Open in editor |
| Send to Bulk Sender | Parallel payload testing |
| Add to Macro | Append to macro chain |
| A/B Test | Compare against another host |
| Generate Code | curl / requests / fetch / HTTPie |
| Security Check | JWT, header, randomness checks |
| Adv Security | CORS, SSRF, redirect, rate limit |
| Active Scan | XSS/SQLi/SSRF/CMDi auto-scan |
| Frida Hook | Generate and inject Frida script |
| Add to Session | Assign to active session |
| Set Diff left / Diff with left | Compare two entries |
| Set color | Highlight row |

## Filter expression

```
host == api.example.com
method == POST && path contains /login
status ~ ^[45]
full_text contains Authorization
```

**Fields:** `host`, `path`, `method`, `status`, `protocol`, `request`, `response`, `full_text`
**Operators:** `==`, `!=`, `contains`, `~` (regex)
**Logic:** `&&`, `||`

## Body view selector

| Mode | Description |
|------|-------------|
| Auto | Detect from Content-Type |
| Text | Raw UTF-8 |
| JSON | Pretty-print |
| XML/HTML | minidom pretty-print |
| Hex | Hexdump with ASCII |
| URL-encoded | `key = value` per line |
| Multipart | Part-by-part display |
| Base64 | Decode standard or URL-safe |
| JWT | Header + payload as JSON |
| Protobuf | Wire-type heuristic decode |
| MessagePack | Decoded to JSON |
| CBOR | Decoded to JSON |

## Intercept toggle

Enable the **Intercept** switch in the toolbar to pause every request for manual review.

## CUI Mode

```bash
pypproxy --mode cui
```

| Key | Action |
|-----|--------|
| `q` / `Ctrl+C` | Quit |
| `c` | Clear traffic |
