# Architecture

## Overview

```
┌──────────────────────────────────────────────────────────┐
│  Client (browser / mobile app)                           │
└────────────────────────┬─────────────────────────────────┘
                         │ HTTP or CONNECT
┌────────────────────────▼─────────────────────────────────┐
│  internal/proxy  (port :8080)                            │
│  ├─ HTTP handler → intercept → upstream                  │
│  └─ CONNECT handler → TLS termination (MITM)            │
│       ├─ HTTP/HTTPS → intercept → upstream               │
│       ├─ WebSocket → internal/proto/ws                   │
│       └─ gRPC → internal/proto/grpc                      │
└─────────────┬────────────────────────┬───────────────────┘
              │                        │
┌─────────────▼──────┐    ┌────────────▼──────────────────┐
│  internal/cert     │    │  internal/interceptor          │
│  CA + per-host TLS │    │  apply rules + record traffic  │
└────────────────────┘    └────────────┬───────────────────┘
                                       │
                          ┌────────────▼───────────────────┐
                          │  internal/store                │
                          │  in-memory traffic store       │
                          │  Pub/Sub for live updates      │
                          └────────────┬───────────────────┘
                                       │
┌──────────────────────────────────────▼───────────────────┐
│  internal/api  (port :8081)                              │
│  ├─ REST API  /api/traffic, /api/rules, /api/replay      │
│  └─ WebSocket /ws  (streams new entries to browser)      │
└──────────────────────────────────────────────────────────┘
```

## Packages

| Package | Responsibility |
|---------|----------------|
| `cmd/paxy` | CLI entry point; wires all packages |
| `internal/proxy` | HTTP server; plain HTTP forwarding; MITM for CONNECT |
| `internal/cert` | Root CA generation; per-host certificate cache |
| `internal/interceptor` | Reads request/response bodies; applies rule engine; records to store |
| `internal/rule` | Rule evaluation engine; condition matching; priority ordering |
| `internal/store` | In-memory traffic store; pub/sub for live WebSocket streaming |
| `internal/api` | REST API + WebSocket server |
| `internal/proto/ws` | WebSocket frame relay and logging |
| `internal/proto/grpc` | gRPC length-prefix frame decoding |
| `internal/script` | Lua scripting engine (gopher-lua) |
| `internal/replay` | HTTP client for replaying captured entries |
| `internal/config` | YAML config loading/saving |

## Key design decisions

### TLS termination per connection

paxy generates a unique certificate for every hostname on first connection, signed by the local CA. Certificates are cached in memory for the process lifetime, so subsequent connections to the same host reuse the cached cert.

### In-memory store with Pub/Sub

All captured traffic lives in memory. Subscribers (WebSocket connections) receive a pointer to each entry as it is added or updated. This makes the live UI update latency near-zero, at the cost of losing history on restart.

### Rule engine is evaluated twice

Rules are evaluated on both the request and the response. A modify rule can change request headers before forwarding and also change response bodies on the way back. The same rule set handles both passes; the `target` field on each modification (`req_header`, `resp_header`, `req_body`, `resp_body`) determines which pass it takes effect on.

### bufResponseWriter for HTTPS connections

Inside a CONNECT tunnel, paxy is handed a raw `net.Conn` — not an `http.ResponseWriter`. `bufResponseWriter` wraps the conn to satisfy the `http.ResponseWriter` and `http.Hijacker` interfaces, letting the same `handleHTTP` function serve both plain HTTP and decrypted HTTPS connections.

### Lua runs in a single state

The Lua engine is not goroutine-safe. The current implementation runs all script hooks from the same goroutine state. For high-throughput scenarios this is a bottleneck; a future version should maintain a pool of Lua states.
