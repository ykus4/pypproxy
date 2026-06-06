# gRPC & WebSocket

## WebSocket

WebSocket connections are automatically detected and intercepted when a CONNECT tunnel is upgraded.

### How it works

1. Client sends a CONNECT request to the proxy.
2. paxy establishes a TLS tunnel (same as HTTPS MITM).
3. When paxy sees an `Upgrade: websocket` header in the decrypted stream, it switches to WebSocket frame relay mode.
4. Each frame is logged with direction (`client` / `server`), opcode, and payload.

### In the Web UI

WebSocket entries appear in the traffic list with the `websocket` tag and protocol `ws`.

The entry captures the upgrade request. Individual frames are logged to the paxy console.

### Limitations

- Frame-level interception is read-only in this version. Modifying individual frames requires a Lua script.
- Compressed WebSocket frames (permessage-deflate) are relayed as-is.

## gRPC

gRPC uses HTTP/2 over TLS with a length-prefixed binary framing. paxy detects gRPC by the `Content-Type: application/grpc` header.

### How it works

1. The HTTPS MITM terminates TLS normally.
2. paxy detects the `application/grpc` content type on the request or response.
3. The 5-byte length-prefix header is decoded: 1 byte compressed flag + 4 bytes message length.
4. Frame metadata (compressed, length) is logged per request.

### In the Web UI

gRPC entries appear with the `grpc` tag. The raw binary body is stored in the entry for inspection.

### Protobuf decoding

paxy stores the raw protobuf bytes. To decode them into readable fields you need the `.proto` schema. A future version will support schema registration and automatic decoding.

For now, use a tool like `protoc` or `grpcurl` with the captured bytes:

```bash
# Decode a captured body (base64-encoded in the API response)
echo "<base64-body>" | base64 -d | protoc --decode_raw
```

## Plain TCP / binary protocols

For other binary protocols, paxy's tunnel mode passes through the raw TCP stream without modification. Use the `ignore` list in the config to skip MITM for specific hosts if needed.
