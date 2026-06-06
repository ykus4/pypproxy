# Architecture

## Overview

```
┌──────────────────────────────────────────────────────────────┐
│  Client (browser / mobile app)                               │
└────────────────────────┬─────────────────────────────────────┘
                         │ HTTP / CONNECT
┌────────────────────────▼─────────────────────────────────────┐
│  paxy/proxy/proxy.py  (port :8080)                           │
│  asyncio TCP server                                          │
│  ├─ HTTP  → intercept → forward upstream (httpx, HTTP/2)     │
│  ├─ CONNECT → TLS termination (MITM)                         │
│  │    ├─ HTTP/HTTPS → intercept → forward upstream           │
│  │    ├─ WebSocket  → paxy/proto/ws.py                       │
│  │    ├─ gRPC       → paxy/proto/grpc.py                     │
│  │    └─ MQTT       → paxy/proto/mqtt.py                     │
│  └─ ignored hosts → raw TCP tunnel (passthrough)             │
└─────────────┬────────────────────────┬───────────────────────┘
              │                        │
┌─────────────▼──────┐    ┌────────────▼──────────────────────┐
│  paxy/cert/ca.py   │    │  paxy/interceptor/                 │
│  CA + per-host TLS │    │  apply rules, record entries       │
│  SSL Context cache │    └────────────┬───────────────────────┘
│                    │                 │
│  paxy/cert/        │    ┌────────────▼───────────────────────┐
│  client_cert.py    │    │  paxy/store/store.py               │
│  Mutual TLS certs  │    │  in-memory store + SQLite persist  │
└────────────────────┘    │  asyncio pub/sub                   │
                          └────────────┬───────────────────────┘
                                       │
          ┌────────────────────────────┼──────────────────────┐
          │                            │                      │
┌─────────▼──────────┐   ┌─────────────▼─────────┐  ┌────────▼──────────┐
│  paxy/api/         │   │  paxy/ui/app.py        │  │  paxy/ui/cui.py   │
│  FastAPI REST API  │   │  NiceGUI 4-tab UI      │  │  rich terminal UI │
│  + WebSocket /ws   │   │  Traffic/Resender/     │  │  (CUI mode)       │
│  Bulk/Export APIs  │   │  Bulk/Diff             │  └───────────────────┘
└────────────────────┘   └─────────────────────────┘
```

## Package overview

| Package | Responsibility |
|---------|----------------|
| `paxy/proxy` | asyncio TCP server; HTTP forwarding; TLS MITM for CONNECT; raw tunnel for ignored hosts |
| `paxy/cert/ca` | CA certificate generation; per-host SSL Context cache |
| `paxy/cert/client_cert` | Client certificate management for mutual TLS |
| `paxy/interceptor` | Apply rules to requests and responses; record entries in the store |
| `paxy/intercept` | Manual intercept manager; pause requests for user review |
| `paxy/rule` | Rule evaluation engine; condition matching; priority ordering |
| `paxy/store/store` | Thread-safe in-memory traffic store; asyncio pub/sub |
| `paxy/store/db` | SQLite persistence via aiosqlite; load/save entries |
| `paxy/store/filter_parser` | Filter expression parser (`host == x && method == POST`) |
| `paxy/api` | FastAPI REST endpoints, WebSocket streaming, bulk/export APIs |
| `paxy/ui/app` | NiceGUI 4-tab browser UI (Traffic, Resender, Bulk Sender, Diff) |
| `paxy/ui/settings` | Settings page (rules, SSL passthrough, DNS, ports, client certs) |
| `paxy/ui/detail` | Request/response detail panel with body view selector |
| `paxy/ui/resender` | Resender tab — edit and re-send requests |
| `paxy/ui/bulk_sender_ui` | Bulk Sender tab — parallel payload sending and race testing |
| `paxy/ui/diff_view` | Diff tab — unified diff between two captured entries |
| `paxy/ui/intercept_dialog` | Intercept dialog — pause, edit, forward or drop requests |
| `paxy/ui/cui` | rich terminal UI (CUI mode) |
| `paxy/proto/ws` | WebSocket frame relay and logging |
| `paxy/proto/grpc` | gRPC length-prefix frame decoding |
| `paxy/proto/mqtt` | MQTT frame decoding and detection |
| `paxy/script` | Python script engine; `on_request` / `on_response` hooks |
| `paxy/replay` | Async HTTP replay and parallel fuzzing via httpx |
| `paxy/bulk` | Bulk sender and race condition test runner |
| `paxy/dns` | Built-in DNS server with domain spoofing |
| `paxy/exporter` | JSON/HAR export and rule import/export |
| `paxy/codec` | Content-encoding decode (gzip/br/deflate); binary format decode (Protobuf/MessagePack/CBOR) |
| `paxy/config` | YAML config loading |

## Key design decisions

### asyncio TCP server

The proxy is a raw `asyncio.start_server` TCP server that parses HTTP manually.
This lets a single connection handle HTTP/1.1 keep-alive, CONNECT tunnels, WebSocket upgrades, and MQTT detection without switching servers mid-connection.

### TLS termination with `loop.start_tls()`

After responding `200 Connection Established` to a CONNECT request, paxy calls `loop.start_tls()` to upgrade the existing asyncio transport to TLS server-side. Per-host certificates are cached as `ssl.SSLContext` objects.

### SQLite persistence via aiosqlite

All captured traffic is stored in memory for fast access. Writes to SQLite are fire-and-forget via `asyncio.run_coroutine_threadsafe`. On startup, `store.load_from_db()` restores prior sessions. The DB path defaults to `~/.paxy/paxy.db`.

### Store pub/sub

The `Store` maintains a list of `asyncio.Queue` subscribers. The proxy calls `loop.call_soon_threadsafe` to push entries into queues from the proxy coroutine. The UI polls each queue to receive live updates without blocking.

### HTTP/2

All upstream requests use `httpx` with `http2=True`. httpx negotiates HTTP/2 via ALPN where the server supports it and falls back to HTTP/1.1 transparently.

### Filter expression engine

The filter bar in the UI accepts a structured expression parsed by `paxy/store/filter_parser.py`. The parser tokenizes `field op value` conditions and evaluates them with AND/OR short-circuit logic against `Entry` objects in memory.

### Binary format detection

`paxy/codec.py` implements `sniff_content_type()` which combines Content-Type inspection with a JSON parse attempt and a binary entropy heuristic to guess the best display mode. Protobuf decoding uses wire-type heuristics without requiring a `.proto` schema.

### GUI / CUI startup

In **GUI mode**, `ui.run()` owns the event loop and the proxy is launched via `nicegui_app.on_startup`. In **CUI mode**, `asyncio.run()` owns the loop and `asyncio.gather` runs the proxy, uvicorn API server, and rich TUI concurrently.
