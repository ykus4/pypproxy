from __future__ import annotations

import asyncio
import logging
import ssl
import time
from urllib.parse import urlparse

from pypproxy.cert.ca import CA
from pypproxy.intercept.manager import InterceptManager
from pypproxy.interceptor.interceptor import Interceptor
from pypproxy.proto import grpc as grpc_proto
from pypproxy.proto import ws as ws_proto
from pypproxy.script.engine import ScriptEngine
from pypproxy.store.store import Store

logger = logging.getLogger(__name__)

HTTP_200_CONNECT = b"HTTP/1.1 200 Connection Established\r\n\r\n"


class Proxy:
    def __init__(
        self,
        ca: CA,
        interceptor: Interceptor,
        store: Store,
        script: ScriptEngine | None = None,
        ignore: set[str] | None = None,
        intercept_manager: InterceptManager | None = None,
    ) -> None:
        self._ca = ca
        self._interceptor = interceptor
        self._store = store
        self._script = script
        self._ignore = ignore or set()
        self._intercept = intercept_manager

    async def handle(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        try:
            request_line = await reader.readline()
            if not request_line:
                return
            headers_raw = await _read_headers(reader)
            headers = _parse_headers(headers_raw)

            parts = request_line.decode(errors="replace").split()
            if len(parts) < 3:
                return
            method, target, _ = parts[0], parts[1], parts[2]

            if method == "CONNECT":
                await self._handle_connect(reader, writer, target, headers)
            else:
                await self._handle_http(reader, writer, method, target, headers, scheme="http")
        except (ConnectionResetError, BrokenPipeError, asyncio.IncompleteReadError):
            pass
        finally:
            writer.close()

    async def _handle_connect(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        target: str,
        headers: dict,
    ) -> None:
        host = target.split(":")[0]
        port = int(target.split(":")[1]) if ":" in target else 443

        if host in self._ignore:
            await self._tunnel(reader, writer, host, port)
            return

        writer.write(HTTP_200_CONNECT)
        await writer.drain()

        ssl_ctx = self._ca.ssl_context_for(host)
        try:
            tls_reader, tls_writer = await asyncio.wait_for(
                self._upgrade_server_tls(reader, writer, ssl_ctx), timeout=10
            )
        except (TimeoutError, ssl.SSLError, OSError) as e:
            logger.debug("TLS handshake failed for %s: %s", host, e)
            return

        try:
            await self._serve_decrypted(tls_reader, tls_writer, host, port)
        finally:
            tls_writer.close()

    async def _upgrade_server_tls(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        ssl_ctx: ssl.SSLContext,
    ) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        transport = writer.transport
        loop = asyncio.get_event_loop()
        tls_transport = await loop.start_tls(
            transport, transport.get_protocol(), ssl_ctx, server_side=True
        )
        tls_reader = asyncio.StreamReader()
        tls_protocol = asyncio.StreamReaderProtocol(tls_reader)
        tls_transport.set_protocol(tls_protocol)
        tls_writer = asyncio.StreamWriter(tls_transport, tls_protocol, tls_reader, loop)
        return tls_reader, tls_writer

    async def _serve_decrypted(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        host: str,
        port: int,
    ) -> None:
        while True:
            request_line = await reader.readline()
            if not request_line:
                return
            headers_raw = await _read_headers(reader)
            headers = _parse_headers(headers_raw)

            if ws_proto.is_upgrade(headers):
                await self._handle_websocket(reader, writer, host, port, request_line, headers_raw)
                return

            parts = request_line.decode(errors="replace").split()
            if len(parts) < 2:
                return
            method, path = parts[0], parts[1]

            content_length = int(headers.get("content-length", ["0"])[0] or 0)
            body = await reader.read(content_length) if content_length > 0 else b""

            await self._handle_https(writer, method, host, port, path, headers, body)

            if headers.get("connection", [""])[0].lower() == "close":
                return

    async def _handle_http(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        method: str,
        target: str,
        headers: dict,
        scheme: str,
    ) -> None:
        parsed = urlparse(target if target.startswith("http") else f"http://{target}")
        host = parsed.netloc or parsed.hostname or target
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query
        query = parsed.query or ""

        content_length = int(headers.get("content-length", ["0"])[0] or 0)
        body = await reader.read(content_length) if content_length > 0 else b""

        response = await self._forward(method, scheme, host, path, query, headers, body)
        writer.write(response)
        await writer.drain()

    async def _handle_https(
        self,
        writer: asyncio.StreamWriter,
        method: str,
        host: str,
        port: int,
        path: str,
        headers: dict,
        body: bytes,
    ) -> None:
        full_host = f"{host}:{port}" if port != 443 else host
        query = ""
        if "?" in path:
            path, query = path.split("?", 1)

        response = await self._forward(method, "https", full_host, path, query, headers, body)
        writer.write(response)
        await writer.drain()

    async def _forward(
        self,
        method: str,
        scheme: str,
        host: str,
        path: str,
        query: str,
        headers: dict,
        body: bytes,
    ) -> bytes:
        import httpx

        from pypproxy.codec import decode_body

        if self._script:
            body = self._script.on_request(method, host, path, body)

        # Manual intercept — pause until user forwards or drops
        if self._intercept:
            headers, body, drop = await self._intercept.intercept(
                method, scheme, host, path, headers, body
            )
            if drop:
                return b"HTTP/1.1 403 Forbidden\r\nContent-Length: 7\r\n\r\ndropped"

        entry, blocked = self._interceptor.process_request(
            method, scheme, host, path, query, headers, body
        )

        if blocked:
            return b"HTTP/1.1 403 Forbidden\r\nContent-Length: 7\r\n\r\nblocked"

        url = f"{scheme}://{host}{path}"
        if query:
            url += "?" + query

        req_headers = {
            k: ", ".join(v)
            for k, v in headers.items()
            if k.lower() not in ("proxy-connection", "proxy-authorization")
        }

        start = time.monotonic()
        try:
            async with httpx.AsyncClient(
                verify=False,
                timeout=30,
                http2=True,
            ) as client:
                resp = await client.request(
                    method=method,
                    url=url,
                    headers=req_headers,
                    content=entry.req_body,
                    follow_redirects=False,
                )
            raw_body = resp.content
            content_encoding = resp.headers.get("content-encoding", "")
            decoded_body, applied_encoding = decode_body(raw_body, content_encoding)

            if self._script:
                decoded_body = self._script.on_response(resp.status_code, decoded_body)

            if grpc_proto.is_grpc({k: [v] for k, v in resp.headers.items()}):
                grpc_proto.log_frames(entry.id, "response", decoded_body)

            resp_headers_dict = {}
            for k, v in resp.headers.multi_items():
                resp_headers_dict.setdefault(k.lower(), []).append(v)

            # Store decoded body so UI can display plain text
            self._interceptor.process_response(
                entry, resp.status_code, resp_headers_dict, decoded_body, start
            )

            # Forward original (encoded) body to client unless script modified it
            forward_body = decoded_body if self._script else raw_body
            # Strip content-encoding header if we decoded the body to forward as-is
            forward_headers = list(resp.headers.multi_items())
            if applied_encoding and not self._script:
                pass  # keep original encoding; body is untouched
            elif applied_encoding and self._script:
                forward_headers = [
                    (k, v) for k, v in forward_headers if k.lower() != "content-encoding"
                ]
            return _build_http_response(resp.status_code, forward_headers, forward_body)

        except Exception as e:
            logger.warning("upstream error %s %s: %s", method, url, e)
            msg = str(e).encode()
            return _build_http_response(502, [], msg)

    async def _handle_websocket(
        self,
        client_reader: asyncio.StreamReader,
        client_writer: asyncio.StreamWriter,
        host: str,
        port: int,
        request_line: bytes,
        headers_raw: bytes,
    ) -> None:
        from pypproxy.store.models import Entry

        try:
            server_reader, server_writer = await asyncio.open_connection(
                host, port, ssl=ssl.create_default_context()
            )
        except Exception as e:
            logger.warning("ws: cannot connect to %s:%d: %s", host, port, e)
            return

        server_writer.write(request_line + headers_raw + b"\r\n")
        await server_writer.drain()

        resp_line = await server_reader.readline()
        resp_headers_raw = await _read_headers(server_reader)
        client_writer.write(resp_line + resp_headers_raw + b"\r\n")
        await client_writer.drain()

        entry = self._store.add(
            Entry(
                method="GET",
                scheme="wss",
                host=host,
                path="/",
                protocol="ws",
                tags=["websocket"],
            )
        )

        await ws_proto.relay_frames(
            client_reader,
            client_writer,
            server_reader,
            server_writer,
            entry,
            self._store,
        )

    async def _tunnel(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        host: str,
        port: int,
    ) -> None:
        writer.write(HTTP_200_CONNECT)
        await writer.drain()
        try:
            server_reader, server_writer = await asyncio.open_connection(host, port)
        except OSError:
            return

        async def pipe(r: asyncio.StreamReader, w: asyncio.StreamWriter) -> None:
            try:
                while True:
                    data = await r.read(65536)
                    if not data:
                        break
                    w.write(data)
                    await w.drain()
            except (ConnectionResetError, BrokenPipeError):
                pass

        await asyncio.gather(
            pipe(reader, server_writer),
            pipe(server_reader, writer),
        )


def _build_http_response(status: int, headers: list[tuple[str, str]], body: bytes) -> bytes:
    reason = _STATUS.get(status, "Unknown")
    lines = [f"HTTP/1.1 {status} {reason}"]
    skip = {"transfer-encoding"}
    for k, v in headers:
        if k.lower() not in skip:
            lines.append(f"{k}: {v}")
    lines.append(f"Content-Length: {len(body)}")
    lines.append("")
    lines.append("")
    return "\r\n".join(lines).encode() + body


async def _read_headers(reader: asyncio.StreamReader) -> bytes:
    buf = b""
    while True:
        line = await reader.readline()
        buf += line
        if line in (b"\r\n", b"\n", b""):
            break
    return buf


def _parse_headers(raw: bytes) -> dict:
    headers: dict[str, list[str]] = {}
    for line in raw.split(b"\r\n"):
        if b":" not in line:
            continue
        k, _, v = line.partition(b":")
        key = k.strip().decode(errors="replace").lower()
        val = v.strip().decode(errors="replace")
        headers.setdefault(key, []).append(val)
    return headers


_STATUS = {
    200: "OK",
    201: "Created",
    204: "No Content",
    301: "Moved Permanently",
    302: "Found",
    304: "Not Modified",
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    429: "Too Many Requests",
    500: "Internal Server Error",
    502: "Bad Gateway",
    503: "Service Unavailable",
}
