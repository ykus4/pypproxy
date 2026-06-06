# Protocol Support

## WebSocket

WebSocket connections are detected automatically and intercepted as part of the HTTPS MITM flow.

### How it works

1. The client sends a CONNECT request to the proxy.
2. paxy terminates TLS (same as HTTPS MITM).
3. When paxy sees `Upgrade: websocket` in the decrypted stream, it switches to WebSocket relay mode.
4. Frames are relayed between client and server while being logged.

### Frame logging

```
ws frame entry=12 dir=client text={"type":"ping"}
ws frame entry=12 dir=server text={"type":"pong"}
```

### Limitations

- Frame-level modification is not yet supported in the rule engine. Use a Python script hook instead.
- `permessage-deflate` compressed frames are relayed as-is without decompression.

---

## gRPC

gRPC uses HTTP/2 over TLS with a 5-byte length-prefix framing.
paxy detects it via the `Content-Type: application/grpc` header.

### How it works

1. TLS is terminated normally as part of HTTPS MITM.
2. The `application/grpc` content type triggers frame decoding.
3. Each frame's metadata (compressed flag, length) is logged.

### Decoding Protobuf

paxy stores raw bytes and can decode them without a `.proto` schema using wire-type heuristics.
In the detail panel, select **Protobuf** from the body view dropdown.

```
field 1 (varint): 42
field 2 (string): 'hello'
field 3 (embedded):
  field 1 (varint): 100
```

---

## MQTT

MQTT connections over TLS are detected by inspecting the first packet for the MQTT protocol name (`MQTT` or `MQIsdp`).

### Frame logging

```
mqtt frame entry=5 dir=client type=PUBLISH topic='sensors/temp' qos=1 len=12
mqtt frame entry=5 dir=server type=PUBACK topic='' qos=0 len=2
```

### Packet types

`CONNECT`, `CONNACK`, `PUBLISH`, `PUBACK`, `PUBREC`, `PUBREL`, `PUBCOMP`,
`SUBSCRIBE`, `SUBACK`, `UNSUBSCRIBE`, `UNSUBACK`, `PINGREQ`, `PINGRESP`, `DISCONNECT`

---

## MessagePack

When the `Content-Type` contains `msgpack`, or when auto-detection identifies MessagePack encoding, the body is decoded to JSON for display.

Select **MessagePack** in the body view dropdown to force MessagePack decoding.

---

## CBOR

CBOR (Concise Binary Object Representation) is decoded to JSON for display.
Select **CBOR** in the body view dropdown.

---

## Certificate pinning

Apps that use certificate pinning will reject paxy's dynamically generated certificate.
Add those hosts to the `ignore` list in the config, or use the SSL Passthrough panel in Settings:

```yaml
proxy:
  ignore:
    - pinned-api.example.com
```

paxy will create a raw TCP tunnel for ignored hosts instead of intercepting them.

---

## HTTP/2

paxy uses `httpx` with HTTP/2 support enabled. Connections to servers that support HTTP/2 will automatically use it via ALPN negotiation. The Resender and Bulk Sender also use HTTP/2 automatically.

There is no HTTP/2 framing interception at the proxy level — HTTP/2 traffic is decoded to HTTP/1.1 semantics before recording.
