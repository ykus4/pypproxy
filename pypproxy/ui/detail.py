from __future__ import annotations

import json

from nicegui import ui

from pypproxy.codec import (
    decode_base64_body,
    decode_cbor,
    decode_charset,
    decode_chunked,
    decode_jwt,
    decode_msgpack,
    decode_multipart,
    decode_protobuf_raw,
    decode_url_encoded,
    decode_xml,
    detect_charset,
    extract_jwt_from_body,
    is_likely_base64,
    sniff_content_type,
)
from pypproxy.store.models import Entry

from .theme import method_badge, status_badge

_VIEW_MODES = [
    "Auto",
    "Text",
    "JSON",
    "XML/HTML",
    "Hex",
    "URL-encoded",
    "Multipart",
    "Base64",
    "JWT",
    "Protobuf",
    "MessagePack",
    "CBOR",
]


def render_detail(entry: Entry | None, container: ui.element) -> None:
    container.clear()
    if entry is None:
        with container:
            ui.label("Select a request to inspect").classes("text-grey q-pa-md")
        return

    with container:
        # --- request ---
        with ui.expansion("Request", icon="upload", value=True).classes("w-full"):
            with ui.row().classes("items-center q-mb-sm gap-2"):
                method_badge(entry.method)
                url = f"{entry.scheme}://{entry.host}{entry.path}"
                if entry.query:
                    url += "?" + entry.query
                ui.label(url).classes("text-caption text-mono")

            if entry.query:
                ui.label("Query Parameters").classes("text-caption text-weight-bold q-mt-sm")
                _render_query_params(entry.query)

            if entry.req_headers:
                ui.label("Headers").classes("text-caption text-weight-bold q-mt-sm")
                _render_headers(entry.req_headers)

            if entry.req_body:
                ui.label("Body").classes("text-caption text-weight-bold q-mt-sm")
                ct = entry.req_headers.get("content-type", [""])[0]
                te = entry.req_headers.get("transfer-encoding", [""])[0]
                body = decode_chunked(entry.req_body) if "chunked" in te.lower() else entry.req_body
                _render_body_with_selector(body, ct, entry.req_headers)

        ui.separator()

        # --- response ---
        with ui.expansion("Response", icon="download", value=True).classes("w-full"):
            if entry.status_code:
                with ui.row().classes("items-center gap-2 q-mb-sm"):
                    status_badge(entry.status_code)
                    ui.label(f"{entry.duration_ms} ms").classes("text-caption text-grey")

            if entry.resp_headers:
                ui.label("Headers").classes("text-caption text-weight-bold q-mt-sm")
                _render_headers(entry.resp_headers)

            if entry.resp_body:
                ui.label("Body").classes("text-caption text-weight-bold q-mt-sm")
                ct = entry.resp_headers.get("content-type", [""])[0]
                te = entry.resp_headers.get("transfer-encoding", [""])[0]
                body = (
                    decode_chunked(entry.resp_body) if "chunked" in te.lower() else entry.resp_body
                )
                charset = detect_charset(ct)
                _render_body_with_selector(body, ct, entry.resp_headers, charset)

        ui.separator()

        # --- replay ---
        with ui.row().classes("q-pa-sm"):
            ui.button("Replay", icon="replay", on_click=lambda: _replay(entry)).props(
                "color=primary size=sm"
            )


def _render_query_params(query: str) -> None:
    from pypproxy.codec import decode_url_params

    text = decode_url_params(query)
    ui.element("pre").classes("paxy-body-pre").text = text


def _render_body_with_selector(
    raw: bytes,
    content_type: str,
    headers: dict | None = None,
    charset: str = "utf-8",
) -> None:
    sniffed = sniff_content_type(raw, content_type)

    # Check for JWT in headers
    jwt_token = extract_jwt_from_body(b"", headers or {}) if headers else None

    default_mode = {
        "json": "JSON",
        "xml": "XML/HTML",
        "html": "XML/HTML",
        "proto": "Protobuf",
        "msgpack": "MessagePack",
        "cbor": "CBOR",
        "binary": "Hex",
        "form": "URL-encoded",
        "multipart": "Multipart",
    }.get(sniffed, "Auto")

    # Override: if JWT found in auth header, suggest JWT view
    if jwt_token and default_mode == "Auto":
        default_mode = "JWT"

    # Override: if likely base64 and binary
    if sniffed == "binary" and is_likely_base64(raw):
        default_mode = "Base64"

    body_area = ui.element("div").classes("w-full")

    def _update(mode: str) -> None:
        body_area.clear()
        with body_area:
            text = _decode_as(raw, mode, content_type, headers or {}, charset)
            ui.element("pre").classes("paxy-body-pre").text = text

    with ui.row().classes("items-center gap-2 q-mb-xs"):
        view_select = (
            ui.select(_VIEW_MODES, value=default_mode, label="View")
            .props("dense outlined dark")
            .classes("w-36")
        )
        # size badge
        size = len(raw)
        if size > 0:
            ui.label(f"{size:,} bytes").classes("text-caption text-grey")

        view_select.on("update:model-value", lambda e: _update(e.args))

    _update(default_mode)


def _decode_as(
    raw: bytes,
    mode: str,
    content_type: str,
    headers: dict,
    charset: str = "utf-8",
) -> str:
    if mode == "Hex":
        return _to_hex(raw)
    if mode == "Protobuf":
        return decode_protobuf_raw(raw)
    if mode == "MessagePack":
        return decode_msgpack(raw)
    if mode == "CBOR":
        return decode_cbor(raw)
    if mode == "URL-encoded":
        return decode_url_encoded(raw)
    if mode == "Multipart":
        return decode_multipart(raw, content_type)
    if mode == "Base64":
        return decode_base64_body(raw)
    if mode == "JWT":
        # Try to find JWT in Authorization header or body
        token = extract_jwt_from_body(raw, headers)
        if token:
            return decode_jwt(token)
        # fallback: try raw body as JWT
        return decode_jwt(raw.decode("utf-8", errors="replace"))
    if mode == "XML/HTML":
        return decode_xml(raw)
    if mode == "JSON":
        try:
            text = decode_charset(raw, charset)
            return json.dumps(json.loads(text), indent=2, ensure_ascii=False)
        except Exception:
            return decode_charset(raw, charset)
    if mode == "Text":
        return decode_charset(raw, charset)
    # Auto
    return _smart_decode(raw, content_type, headers, charset)


def _smart_decode(
    raw: bytes,
    content_type: str,
    headers: dict | None = None,
    charset: str = "utf-8",
) -> str:
    sniffed = sniff_content_type(raw, content_type)
    if sniffed == "json":
        try:
            text = decode_charset(raw, charset)
            return json.dumps(json.loads(text), indent=2, ensure_ascii=False)
        except Exception:
            pass
    if sniffed in ("xml", "html"):
        return decode_xml(raw)
    if sniffed == "proto":
        return decode_protobuf_raw(raw)
    if sniffed == "msgpack":
        return decode_msgpack(raw)
    if sniffed == "cbor":
        return decode_cbor(raw)
    if sniffed == "form":
        return decode_url_encoded(raw)
    if sniffed == "multipart":
        return decode_multipart(raw, content_type)
    if sniffed == "binary":
        if is_likely_base64(raw):
            return decode_base64_body(raw)
        return _to_hex(raw)
    return decode_charset(raw, charset)


def _to_hex(raw: bytes, width: int = 16) -> str:
    lines: list[str] = []
    for i in range(0, len(raw), width):
        chunk = raw[i : i + width]
        hex_part = " ".join(f"{b:02x}" for b in chunk)
        ascii_part = "".join(chr(b) if 0x20 <= b < 0x7F else "." for b in chunk)
        lines.append(f"{i:08x}  {hex_part:<{width * 3}}  {ascii_part}")
    return "\n".join(lines)


def _render_headers(headers: dict[str, list[str]]) -> None:
    with ui.element("table").classes("paxy-header-table w-full"):
        for k, vs in sorted(headers.items()):
            with ui.element("tr"):
                ui.element("td").style(
                    "color:#aaa; min-width:160px; padding:2px 8px; font-size:12px"
                ).text = k
                ui.element("td").style("padding:2px 8px; font-size:12px").text = ", ".join(vs)


async def _replay(entry: Entry) -> None:
    import httpx

    url = f"{entry.scheme}://{entry.host}{entry.path}"
    if entry.query:
        url += "?" + entry.query
    headers = {k: ", ".join(v) for k, v in entry.req_headers.items()}
    try:
        async with httpx.AsyncClient(verify=False, timeout=30, http2=True) as client:
            resp = await client.request(
                method=entry.method,
                url=url,
                headers=headers,
                content=entry.req_body,
            )
        ui.notify(f"Replay: {resp.status_code} ({len(resp.content)} bytes)", type="positive")
    except Exception as e:
        ui.notify(f"Replay failed: {e}", type="negative")
