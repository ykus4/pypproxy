from __future__ import annotations

import json

from nicegui import ui

from ..store.models import Entry
from .theme import method_badge, status_badge


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
                _render_body(entry.req_body)

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
                _render_body(entry.resp_body)

        ui.separator()

        # --- replay ---
        with ui.row().classes("q-pa-sm"):
            ui.button("Replay", icon="replay", on_click=lambda: _replay(entry)).props(
                "color=primary size=sm"
            )


def _render_headers(headers: dict[str, list[str]]) -> None:
    with ui.element("table").classes("paxy-header-table w-full"):
        for k, vs in sorted(headers.items()):
            with ui.element("tr"):
                ui.element("td").bind_text_from({"t": k}, "t")
                ui.element("td").bind_text_from({"t": ", ".join(vs)}, "t")


def _render_body(raw: bytes) -> None:
    text = _decode_body(raw)
    ui.element("pre").classes("paxy-body-pre").bind_text_from({"t": text}, "t")


def _decode_body(raw: bytes) -> str:
    if not raw:
        return ""
    try:
        text = raw.decode("utf-8", errors="replace")
    except Exception:
        return f"<binary {len(raw)} bytes>"
    try:
        parsed = json.loads(text)
        return json.dumps(parsed, indent=2, ensure_ascii=False)
    except Exception:
        return text


async def _replay(entry: Entry) -> None:
    import httpx

    url = f"{entry.scheme}://{entry.host}{entry.path}"
    if entry.query:
        url += "?" + entry.query
    headers = {k: ", ".join(v) for k, v in entry.req_headers.items()}
    try:
        async with httpx.AsyncClient(verify=False, timeout=30) as client:
            resp = await client.request(
                method=entry.method,
                url=url,
                headers=headers,
                content=entry.req_body,
            )
        ui.notify(f"Replay: {resp.status_code} ({len(resp.content)} bytes)", type="positive")
    except Exception as e:
        ui.notify(f"Replay failed: {e}", type="negative")
