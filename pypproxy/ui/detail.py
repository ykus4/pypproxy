from __future__ import annotations

import json

from nicegui import ui

from pypproxy.codec import decode_cbor, decode_msgpack, decode_protobuf_raw, sniff_content_type
from pypproxy.store.models import Entry

from .theme import method_badge, status_badge

_VIEW_MODES = ["Auto", "Text", "JSON", "Hex", "Protobuf", "MessagePack", "CBOR"]


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

            if entry.req_headers:
                ui.label("Headers").classes("text-caption text-weight-bold q-mt-sm")
                _render_headers(entry.req_headers)

            if entry.req_body:
                ui.label("Body").classes("text-caption text-weight-bold q-mt-sm")
                ct = entry.req_headers.get("content-type", [""])[0]
                _render_body_with_selector(entry.req_body, ct)

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
                _render_body_with_selector(entry.resp_body, ct)

        ui.separator()

        # --- replay ---
        with ui.row().classes("q-pa-sm"):
            ui.button("Replay", icon="replay", on_click=lambda: _replay(entry)).props(
                "color=primary size=sm"
            )


def _render_body_with_selector(raw: bytes, content_type: str) -> None:
    sniffed = sniff_content_type(raw, content_type)
    default_mode = {
        "json": "JSON",
        "proto": "Protobuf",
        "msgpack": "MessagePack",
        "cbor": "CBOR",
        "binary": "Hex",
    }.get(sniffed, "Auto")

    body_area = ui.element("div").classes("w-full")

    def _update(mode: str) -> None:
        body_area.clear()
        with body_area:
            text = _decode_as(raw, mode, content_type)
            ui.element("pre").classes("paxy-body-pre").text = text

    with ui.row().classes("items-center gap-2 q-mb-xs"):
        view_select = (
            ui.select(_VIEW_MODES, value=default_mode, label="View")
            .props("dense outlined dark")
            .classes("w-32")
        )
        view_select.on("update:model-value", lambda e: _update(e.args))

    _update(default_mode)


def _decode_as(raw: bytes, mode: str, content_type: str) -> str:
    if mode == "Hex":
        return _to_hex(raw)
    if mode == "Protobuf":
        return decode_protobuf_raw(raw)
    if mode == "MessagePack":
        return decode_msgpack(raw)
    if mode == "CBOR":
        return decode_cbor(raw)
    if mode == "JSON":
        try:
            return json.dumps(
                json.loads(raw.decode("utf-8", errors="replace")), indent=2, ensure_ascii=False
            )
        except Exception:
            return raw.decode("utf-8", errors="replace")
    if mode == "Text":
        return raw.decode("utf-8", errors="replace")
    # Auto
    return _smart_decode(raw, content_type)


def _smart_decode(raw: bytes, content_type: str) -> str:
    sniffed = sniff_content_type(raw, content_type)
    if sniffed == "json":
        try:
            return json.dumps(
                json.loads(raw.decode("utf-8", errors="replace")), indent=2, ensure_ascii=False
            )
        except Exception:
            pass
    if sniffed == "proto":
        return decode_protobuf_raw(raw)
    if sniffed == "msgpack":
        return decode_msgpack(raw)
    if sniffed == "cbor":
        return decode_cbor(raw)
    if sniffed == "binary":
        return _to_hex(raw)
    try:
        return raw.decode("utf-8", errors="replace")
    except Exception:
        return _to_hex(raw)


def _to_hex(raw: bytes) -> str:
    lines: list[str] = []
    for i in range(0, len(raw), 16):
        chunk = raw[i : i + 16]
        hex_part = " ".join(f"{b:02x}" for b in chunk)
        ascii_part = "".join(chr(b) if 0x20 <= b < 0x7F else "." for b in chunk)
        lines.append(f"{i:08x}  {hex_part:<47}  {ascii_part}")
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
