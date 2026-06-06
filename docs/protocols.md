# Protocol Support

## GraphQL

pypproxy automatically detects GraphQL requests and provides dedicated tooling.

### Detection

A request is identified as GraphQL when any of these conditions are met:

- `Content-Type: application/graphql`
- POST body is JSON with a `query` key whose value starts with `query`, `mutation`, `subscription`, or `{`
- GET request with a `query=` parameter
- Path matches `/graphql` (case-insensitive)

Detected entries are tagged `graphql` and shown with `protocol = graphql` in the traffic list.

### GraphQL tab

Open the **GraphQL** tab or right-click a GraphQL entry → **Open in GraphQL tab**.

**Schema Introspection**

Enter the endpoint URL and click **Introspect**. pypproxy sends a full `__schema` introspection query and displays the type tree. The schema is cached per-host and available for query completion.

**Query Editor**

When an entry is opened, the query and variables are auto-filled from the captured request. Edit and re-run with the **Run Query** button.

**Operation Analysis**

Shows the operation type (query/mutation/subscription), operation name, and top-level fields of the selected entry.

### API

| Endpoint | Description |
|----------|-------------|
| `POST /api/graphql/introspect` | Fetch schema from `{"url": "...", "headers": {...}}` |
| `GET /api/graphql/schemas` | List cached schemas by host |
| `GET /api/graphql/schema/{host}` | Get full schema for a host |
| `DELETE /api/graphql/schema/{host}` | Remove cached schema |
| `POST /api/graphql/replay` | Re-send with modified query/variables |

### Modifier utilities (pypproxy.graphql.modifier)

```python
from pypproxy.graphql.modifier import set_variable, build_query, build_mutation

# Replace a variable in a captured request body
new_body = set_variable(entry.req_body, "userId", "456")

# Build a query programmatically
body = build_query(["user { id name }", "posts { title }"])

# Build a mutation
body = build_mutation("createUser", {"name": "alice"}, ["id", "name"])
```

---

## WebSocket

WebSocket connections are detected automatically and intercepted as part of the HTTPS MITM flow.

### How it works

1. The client sends a CONNECT request to the proxy.
2. pypproxy terminates TLS (same as HTTPS MITM).
3. When pypproxy sees `Upgrade: websocket` in the decrypted stream, it switches to WebSocket relay mode.
4. Frames are relayed between client and server while being logged.

### Frame intercept

Enable `WSInterceptManager` to pause individual frames for manual review, similar to HTTP intercept. Forward with or without payload edits, or drop entirely.

---

## gRPC

gRPC uses HTTP/2 over TLS with a 5-byte length-prefix framing.
pypproxy detects it via the `Content-Type: application/grpc` header.

The body view selector in the detail panel offers **Protobuf** mode for wire-type heuristic decoding (no schema needed).

---

## MQTT

MQTT connections over TLS are detected by inspecting the first packet for the MQTT protocol name (`MQTT` or `MQIsdp`).

All 14 packet types are decoded: `CONNECT`, `CONNACK`, `PUBLISH`, `PUBACK`, `PUBREC`, `PUBREL`, `PUBCOMP`, `SUBSCRIBE`, `SUBACK`, `UNSUBSCRIBE`, `UNSUBACK`, `PINGREQ`, `PINGRESP`, `DISCONNECT`.

---

## MessagePack / CBOR

When the `Content-Type` contains `msgpack` or `cbor`, or when auto-detection identifies the encoding, the body is decoded to JSON for display. Select the mode explicitly in the body view dropdown.

---

## HTTP/2

All upstream requests use `httpx` with HTTP/2 support enabled. Connections negotiate HTTP/2 via ALPN automatically.

---

## Certificate pinning

Add pinned hosts to the `ignore` list in config or the **SSL Passthrough** settings tab. pypproxy tunnels those hosts without TLS interception.

```yaml
proxy:
  ignore:
    - pinned-api.example.com
```
