from __future__ import annotations

import asyncio

from nicegui import app as nicegui_app
from nicegui import ui

from ..store.models import Entry, Filter
from ..store.store import Store
from .detail import render_detail
from .theme import apply_dark_theme


def build_ui(store: Store) -> None:
    apply_dark_theme()

    @ui.page("/")
    async def index() -> None:
        ui.dark_mode().enable()

        state = {
            "entries": [],
            "selected": None,
            "filter": Filter(),
        }

        # --- toolbar ---
        with ui.header().classes("items-center q-px-md gap-4").style("background:#1a1a2e"):
            ui.label("paxy").classes("text-h6 text-weight-bold")
            ui.badge("●", color="positive").props("rounded").tooltip("Proxy running")

            search_input = (
                ui.input(placeholder="Search host/path…")
                .props("dense outlined dark")
                .classes("w-64")
            )
            method_select = (
                ui.select(
                    ["", "GET", "POST", "PUT", "PATCH", "DELETE"],
                    value="",
                    label="Method",
                )
                .props("dense outlined dark")
                .classes("w-28")
            )
            protocol_select = (
                ui.select(
                    ["", "http", "https", "ws", "grpc"],
                    value="",
                    label="Protocol",
                )
                .props("dense outlined dark")
                .classes("w-28")
            )

            ui.space()
            ui.button(
                "Clear",
                icon="delete_sweep",
                on_click=lambda: _clear(store, state, table, detail_container),
            ).props("color=negative size=sm flat")

        # --- layout ---
        with (
            ui.splitter(value=60).classes("w-full").style("height: calc(100vh - 56px)") as splitter
        ):
            with splitter.before:
                table = _build_table(state, detail_container_ref=[None])

            with splitter.after:
                detail_container = ui.scroll_area().classes("w-full h-full q-pa-sm")
                render_detail(None, detail_container)

        # wire detail_container into table callbacks
        table._props["detail_container"] = detail_container

        # --- filter reactivity ---
        def apply_filter() -> None:
            state["filter"] = Filter(
                search=search_input.value or "",
                method=method_select.value or "",
                protocol=protocol_select.value or "",
            )
            _refresh_table(store, state, table)

        search_input.on("update:model-value", lambda: apply_filter())
        method_select.on("update:model-value", lambda: apply_filter())
        protocol_select.on("update:model-value", lambda: apply_filter())

        # --- initial load ---
        _refresh_table(store, state, table)

        # --- live updates via store subscription ---
        q = store.subscribe()

        async def _live() -> None:
            try:
                while True:
                    await asyncio.wait_for(
                        asyncio.shield(
                            asyncio.get_event_loop().run_in_executor(None, q.get_nowait)
                        ),
                        timeout=0.1,
                    )
            except Exception:
                pass

        async def _poller() -> None:
            try:
                while True:
                    try:
                        entry = q.get_nowait()
                        if state["filter"].matches(entry):
                            state["entries"].insert(0, entry)
                            _update_table_rows(state, table)
                    except asyncio.QueueEmpty:
                        pass
                    await asyncio.sleep(0.2)
            except asyncio.CancelledError:
                store.unsubscribe(q)

        nicegui_app.on_shutdown(lambda: store.unsubscribe(q))
        asyncio.ensure_future(_poller())


def _build_table(state: dict, detail_container_ref: list) -> ui.table:
    columns = [
        {"name": "id", "label": "ID", "field": "id", "align": "right", "style": "width:50px"},
        {
            "name": "method",
            "label": "Method",
            "field": "method",
            "align": "center",
            "style": "width:80px",
        },
        {"name": "host", "label": "Host", "field": "host", "align": "left"},
        {"name": "path", "label": "Path", "field": "path", "align": "left"},
        {
            "name": "status",
            "label": "Status",
            "field": "status_code",
            "align": "center",
            "style": "width:70px",
        },
        {
            "name": "duration",
            "label": "ms",
            "field": "duration_ms",
            "align": "right",
            "style": "width:60px",
        },
        {
            "name": "protocol",
            "label": "Proto",
            "field": "protocol",
            "align": "center",
            "style": "width:60px",
        },
    ]
    table = (
        ui.table(columns=columns, rows=[], row_key="id")
        .classes("w-full")
        .props("dense flat dark virtual-scroll")
    )
    table.add_slot(
        "body-cell-method",
        """
        <q-td :props="props">
          <q-badge :color="{'GET':'blue','POST':'green','PUT':'orange','PATCH':'purple','DELETE':'red'}[props.value] || 'grey'" :label="props.value" rounded />
        </q-td>
    """,
    )
    table.add_slot(
        "body-cell-status",
        """
        <q-td :props="props">
          <q-badge v-if="props.value"
            :color="props.value < 300 ? 'positive' : props.value < 400 ? 'info' : props.value < 500 ? 'warning' : 'negative'"
            :label="props.value" rounded />
        </q-td>
    """,
    )
    return table


def _refresh_table(store: Store, state: dict, table: ui.table) -> None:
    entries, _ = store.list(state["filter"], 0, 500)
    state["entries"] = list(reversed(entries))
    _update_table_rows(state, table)


def _update_table_rows(state: dict, table: ui.table) -> None:
    table.rows = [_entry_to_row(e) for e in state["entries"]]
    table.update()


def _entry_to_row(e: Entry) -> dict:
    return {
        "id": e.id,
        "method": e.method,
        "host": e.host,
        "path": e.path + (f"?{e.query}" if e.query else ""),
        "status_code": e.status_code,
        "duration_ms": e.duration_ms,
        "protocol": e.protocol,
        "_tags": e.tags,
        "_modified": e.modified,
    }


async def _clear(store: Store, state: dict, table: ui.table, detail_container: ui.element) -> None:
    store.clear()
    state["entries"] = []
    state["selected"] = None
    table.rows = []
    table.update()
    render_detail(None, detail_container)
    ui.notify("Cleared", type="info")
