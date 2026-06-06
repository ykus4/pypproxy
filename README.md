# paxy

A MITM HTTP/HTTPS proxy for inspecting and modifying traffic from browsers and mobile apps.

## Features

- **HTTP/HTTPS interception** — TLS termination with dynamically generated certificates
- **Web UI** — Real-time traffic viewer in the browser
- **Rule engine** — Block, modify, or redirect requests/responses by host, path, method, header, or body
- **WebSocket interception** — Capture and inspect WebSocket frames
- **gRPC interception** — Decode length-prefixed gRPC messages
- **Lua scripting** — Transform requests and responses with custom scripts
- **Replay & fuzzing** — Resend captured requests, optionally in parallel
- **YAML config** — Persistent configuration file

## Quick start

```bash
# Build
make build

# Run (proxy on :8080, UI on :8081)
./bin/paxy

# Or run without building
make run
```

Then install the CA certificate and configure your browser or device to use the proxy.

See [docs/getting-started.md](docs/getting-started.md) for step-by-step setup.

## Documentation

| Doc | Description |
|-----|-------------|
| [Getting Started](docs/getting-started.md) | Installation, CA setup, browser/mobile config |
| [Web UI](docs/web-ui.md) | Traffic list, detail view, filtering |
| [Rule Engine](docs/rule-engine.md) | Writing intercept/modify/block rules |
| [Lua Scripting](docs/lua-scripting.md) | `on_request` / `on_response` hooks |
| [Replay & Fuzzing](docs/replay.md) | Replaying and fuzzing captured requests |
| [gRPC & WebSocket](docs/protocols.md) | Protocol-specific interception |
| [Configuration](docs/configuration.md) | YAML config reference |
| [API Reference](docs/api.md) | REST API and WebSocket endpoints |
| [Architecture](docs/architecture.md) | Codebase overview and design decisions |

## CLI flags

```
--addr       Proxy listen address (default :8080)
--ui-addr    Web UI listen address (default :8081)
--config     Path to YAML config file
--script     Path to Lua script file
--ca-dir     Directory to store CA cert/key (default ~/.paxy)
```

## License

MIT
