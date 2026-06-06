# Lua Scripting

Lua scripts let you transform requests and responses with arbitrary logic. The script is loaded once at startup and reused for every request.

## Loading a script

```bash
./bin/paxy --script /path/to/script.lua
```

Or via config:

```yaml
script:
  path: /path/to/script.lua
```

## Hooks

Define any of these global functions in your script:

### `on_request(method, host, path, body)`

Called before a request is forwarded upstream. Return the (possibly modified) body as a string.

```lua
function on_request(method, host, path, body)
  -- Add a custom header via body modification (header mods use the rule engine)
  if host:find("api.example.com") then
    print("intercepted: " .. method .. " " .. path)
  end
  return body  -- return unchanged
end
```

### `on_response(status, body)`

Called after a response is received. Return the (possibly modified) body.

```lua
function on_response(status, body)
  if status == 200 then
    -- Pretty-print JSON responses to the log
    print("response body length: " .. #body)
  end
  return body
end
```

## Examples

### Inject a token into all requests

```lua
function on_request(method, host, path, body)
  -- Body modification only; use the rule engine for header injection
  return body
end
```

### Replace a string in all responses

```lua
function on_response(status, body)
  return body:gsub("https://prod.example.com", "https://staging.example.com")
end
```

### Log slow responses

```lua
local start_times = {}

function on_request(method, host, path, body)
  -- Lua scripts share one state; use path as a rough key
  start_times[path] = os.time()
  return body
end

function on_response(status, body)
  return body
end
```

## Notes

- The script runs in a single Lua state (not per-goroutine). Avoid shared mutable state in concurrent scenarios.
- `print()` writes to the paxy stdout log.
- The Lua standard library is available (`string`, `table`, `math`, `io`, `os`).
- To reload the script, restart paxy.
