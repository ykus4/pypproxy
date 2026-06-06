# Replay & Fuzzing

paxy can resend any captured request — once for manual re-testing, or hundreds of times in parallel for load testing and fuzzing.

## Replay from the Web UI

1. Click any entry in the traffic list to open the detail panel.
2. Click the **Replay** button.
3. The result (status code, body, duration) appears inline.

## Replay via API

```bash
curl -X POST http://localhost:8081/api/replay \
  -H 'Content-Type: application/json' \
  -d '{
    "entry_id": 42,
    "options": {}
  }'
```

Response:

```json
[
  {
    "entry_id": 42,
    "status_code": 200,
    "body": "...(base64)...",
    "duration_ms": 134
  }
]
```

## Options

| Field | Type | Description |
|-------|------|-------------|
| `override_host` | string | Send to a different host (e.g. staging) |
| `extra_headers` | object | Headers to add/override |
| `timeout_seconds` | int | Per-request timeout (default 30) |
| `count` | int | Number of parallel replays (default 1) |

## Parallel replay (load test / fuzz)

```bash
curl -X POST http://localhost:8081/api/replay \
  -H 'Content-Type: application/json' \
  -d '{
    "entry_id": 42,
    "options": {
      "count": 100,
      "timeout_seconds": 10
    }
  }'
```

Returns an array of 100 results. Requests are fired concurrently.

## Replay to a different host

Useful for replaying production traffic against a staging environment:

```bash
curl -X POST http://localhost:8081/api/replay \
  -H 'Content-Type: application/json' \
  -d '{
    "entry_id": 42,
    "options": {
      "override_host": "staging.example.com"
    }
  }'
```

## Adding headers

```bash
curl -X POST http://localhost:8081/api/replay \
  -H 'Content-Type: application/json' \
  -d '{
    "entry_id": 42,
    "options": {
      "extra_headers": {
        "Authorization": "Bearer new-token",
        "X-Test": "replay"
      }
    }
  }'
```
