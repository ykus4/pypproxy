# Configuration

paxy can be configured via CLI flags or a YAML file. CLI flags override config file values.

## YAML config file

```bash
./bin/paxy --config paxy.yaml
```

### Full example

```yaml
proxy:
  addr: ":8080"
  # Hosts to skip MITM and tunnel directly (no TLS termination)
  ignore:
    - pinned.example.com
    - internal.corp
  # Maximum body size to capture (bytes). Larger bodies are truncated.
  max_body: 1048576  # 1MB

ca:
  cert_path: /custom/path/ca-cert.pem
  key_path:  /custom/path/ca-key.pem

ui:
  addr: ":8081"

script:
  path: /path/to/script.lua
```

## Reference

### `proxy`

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `addr` | string | `:8080` | Proxy listen address |
| `ignore` | []string | `[]` | Hosts to tunnel without MITM |
| `max_body` | int | `1048576` | Max body bytes to capture |

### `ca`

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `cert_path` | string | `~/.paxy/ca-cert.pem` | CA certificate path |
| `key_path` | string | `~/.paxy/ca-key.pem` | CA private key path |

### `ui`

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `addr` | string | `:8081` | Web UI / API listen address |

### `script`

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `path` | string | — | Path to Lua script file |

## CLI flags

CLI flags take precedence over the config file.

| Flag | Default | Description |
|------|---------|-------------|
| `--addr` | `:8080` | Proxy listen address |
| `--ui-addr` | `:8081` | Web UI listen address |
| `--config` | — | Config file path |
| `--script` | — | Lua script path |
| `--ca-dir` | `~/.paxy` | Directory for CA cert/key |

## Ignoring hosts

Some apps use certificate pinning and will fail if paxy terminates their TLS connections. Add those hosts to the `ignore` list:

```yaml
proxy:
  ignore:
    - pinned-api.example.com
```

paxy will create a raw TCP tunnel for those hosts instead of intercepting.
