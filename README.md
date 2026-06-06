# paxy

A MITM HTTP/HTTPS proxy for inspecting and modifying traffic from browsers and mobile apps. Written in Python.

[![CI](https://github.com/ykus4/paxy/actions/workflows/ci.yml/badge.svg)](https://github.com/ykus4/paxy/actions/workflows/ci.yml)

## Features

- **HTTPS interception** — Dynamically generate per-host certificates signed by a local CA
- **GUI mode** — Browser UI built with NiceGUI; traffic streams in real time
- **CUI mode** — Terminal UI built with rich; works over SSH and in CI environments
- **Rule engine** — Block, modify, or redirect traffic by host, path, method, header, or body (regex supported)
- **Python scripting** — `on_request` / `on_response` hooks in plain Python
- **Replay & fuzzing** — Resend any captured request; increase `count` for parallel fuzzing
- **WebSocket & gRPC** — Frame-level interception and logging
- **YAML config** — Persistent configuration file

## Quick start

```bash
git clone https://github.com/ykus4/paxy
cd paxy
uv sync

# GUI mode (browser UI at http://localhost:8081)
uv run python main.py

# CUI mode (terminal UI)
uv run python main.py --mode cui
```

Install the generated CA certificate (`~/.paxy/ca-cert.pem`) in your browser or device, then point your proxy settings to `localhost:8080`.

See [Getting Started](docs/getting-started.md) for step-by-step setup including iOS, Android, and macOS.

## CLI flags

```
--mode       UI mode: gui (default) or cui
--addr       Proxy listen address (default 0.0.0.0)
--port       Proxy port (default 8080)
--ui-addr    Web UI / API listen address (default 0.0.0.0)
--ui-port    Web UI / API port (default 8081)
--config     Path to YAML config file
--script     Path to Python script file
--ca-dir     Directory to store CA cert/key (default ~/.paxy)
```

## Documentation

| Doc | Description |
|-----|-------------|
| [Getting Started](docs/getting-started.md) | Installation, CA setup, browser/mobile proxy config |
| [Web UI & CUI](docs/web-ui.md) | GUI and terminal UI usage |
| [Rule Engine](docs/rule-engine.md) | Block, modify, redirect rules |
| [Python Scripting](docs/scripting.md) | `on_request` / `on_response` hooks |
| [Replay & Fuzzing](docs/replay.md) | Replaying and fuzzing captured requests |
| [gRPC & WebSocket](docs/protocols.md) | Protocol-specific interception |
| [Configuration](docs/configuration.md) | Full YAML config reference |
| [API Reference](docs/api.md) | REST API and WebSocket endpoints |
| [Architecture](docs/architecture.md) | Package structure and design decisions |

## Development

```bash
uv sync                     # install dependencies
uv run pytest tests/ -v     # run tests
uv run ruff check paxy/     # lint
uv run ruff format paxy/    # format
uv run pre-commit run --all-files  # run all pre-commit hooks
```

## License

MIT
