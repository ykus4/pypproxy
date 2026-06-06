from __future__ import annotations

import asyncio

from nicegui import app as nicegui_app
from nicegui import ui

from pypproxy.intercept.manager import InterceptManager
from pypproxy.store.models import Entry, Filter
from pypproxy.store.store import Store

from .detail import render_detail
from .intercept_dialog import build_intercept_panel
from .theme import apply_dark_theme

_ROW_COLORS = ["", "#b71c1c", "#1b5e20", "#0d47a1", "#f57f17", "#4a148c"]
_COLOR_LABELS = ["None", "Red", "Green", "Blue", "Yellow", "Purple"]


def build_ui(
    store: Store,
    intercept_mgr: InterceptManager | None = None,
    settings_kwargs: dict | None = None,
) -> None:
    if settings_kwargs:
        from .settings import build_settings_page

        build_settings_page(**settings_kwargs)

    @ui.page("/")
    async def index() -> None:
        apply_dark_theme()
        ui.dark_mode().enable()

        state: dict = {
            "entries": [],
            "selected": None,
            "filter": Filter(),
            "compare_left": None,
        }

        # toolbar
        with ui.header().classes("items-center q-px-md gap-4").style("background:#1a1a2e"):
            ui.label("paxy").classes("text-h6 text-weight-bold")
            ui.badge("●", color="positive").props("rounded").tooltip("Proxy running")

            filter_input = (
                ui.input(placeholder="Filter: host == example.com && method == POST")
                .props("dense outlined dark")
                .classes("w-96")
                .tooltip(
                    "Fields: host path method status protocol request response full_text  "
                    "Ops: == != contains ~  Logic: && ||"
                )
            )
            ui.space()

            if intercept_mgr is not None:
                intercept_toggle = (
                    ui.switch("Intercept")
                    .props("dense dark color=warning")
                    .tooltip("Pause requests for manual review")
                )
                intercept_toggle.on(
                    "update:model-value",
                    lambda e: intercept_mgr.set_enabled(e.args),
                )

            clear_btn = ui.button("Clear", icon="delete_sweep").props("color=negative size=sm flat")
            ui.button(icon="settings", on_click=lambda: ui.navigate.to("/settings")).props(
                "flat dark size=sm"
            ).tooltip("Settings")

        # main tabs
        with ui.tabs().props("dense dark").classes("bg-dark") as tabs:
            traffic_tab = ui.tab("Traffic", icon="list")
            resender_tab = ui.tab("Resender", icon="send")
            bulk_tab = ui.tab("Bulk Sender", icon="dynamic_feed")
            diff_tab = ui.tab("Diff", icon="difference")
            security_tab = ui.tab("Security", icon="security")
            scan_tab = ui.tab("Scan", icon="search")
            graphql_tab = ui.tab("GraphQL", icon="account_tree")
            import_tab_btn = ui.tab("Import/Search", icon="upload")

        with (
            ui.tab_panels(tabs, value=traffic_tab)
            .classes("w-full flex-1")
            .style("height:calc(100vh - 96px)")
        ):
            with (
                ui.tab_panel(traffic_tab).classes("p-0 h-full"),
                ui.splitter(value=60).classes("w-full h-full") as splitter,
            ):
                with splitter.before, ui.column().classes("w-full h-full overflow-auto"):
                    table = _build_table()
                with (
                    splitter.after,
                    ui.column().classes("w-full h-full overflow-auto q-pa-sm") as detail_col,
                ):
                    render_detail(None, detail_col)

            with ui.tab_panel(resender_tab).classes("p-0 h-full"):
                from .resender import build_resender_tab

                resender_container = ui.column().classes("w-full h-full")
                with resender_container:
                    build_resender_tab(store)

            with ui.tab_panel(bulk_tab).classes("p-0 h-full"):
                from .bulk_sender_ui import build_bulk_sender

                bulk_container = ui.column().classes("w-full h-full overflow-auto q-pa-md")
                bulk_state = build_bulk_sender(bulk_container)

            with ui.tab_panel(diff_tab).classes("p-0 h-full"):
                from .diff_view import build_diff_view

                diff_container = ui.column().classes("w-full h-full overflow-auto q-pa-md")
                diff_state = build_diff_view(diff_container)

            with ui.tab_panel(security_tab).classes("p-0 h-full"):
                from .security_tab import build_security_tab

                sec_state = build_security_tab(store)

            with ui.tab_panel(scan_tab).classes("p-0 h-full"):
                from .scan_tab import build_scan_tab

                scan_state = build_scan_tab(store)

            with ui.tab_panel(graphql_tab).classes("p-0 h-full"):
                from .graphql_tab import build_graphql_tab

                gql_state = build_graphql_tab(store)

            with ui.tab_panel(import_tab_btn).classes("p-0 h-full"):
                from .import_tab import build_import_tab

                build_import_tab(store)

        clear_btn.on("click", lambda: _clear(store, state, table, detail_col))

        def apply_filter() -> None:
            state["filter"] = Filter(expression=filter_input.value or "")
            _refresh_table(store, state, table)

        filter_input.on("update:model-value", lambda: apply_filter())

        async def on_row_click(e) -> None:  # noqa: ANN001
            try:
                row = e.args[1] if isinstance(e.args, list) else e.args
                entry_id = int(row["id"])
            except (IndexError, KeyError, TypeError, ValueError):
                return
            entry = store.get(entry_id)
            if entry:
                state["selected"] = entry
                render_detail(entry, detail_col)

        table.on("row-click", on_row_click)

        async def on_row_contextmenu(e) -> None:  # noqa: ANN001
            try:
                row = e.args[1] if isinstance(e.args, list) else e.args
                entry_id = int(row["id"])
            except (IndexError, KeyError, TypeError, ValueError):
                return
            entry = store.get(entry_id)
            if not entry:
                return

            with ui.menu() as menu:
                ui.menu_item(
                    "Send to Resender",
                    on_click=lambda: (
                        tabs.set_value(resender_tab),
                        ui.notify(f"Opened #{entry.id} in Resender", type="info"),
                    ),
                )
                ui.menu_item(
                    "Send to Bulk Sender",
                    on_click=lambda: (bulk_state["open_entry"](entry), tabs.set_value(bulk_tab)),
                )
                ui.menu_item(
                    "Security check",
                    on_click=lambda: (sec_state["open_entry"](entry), tabs.set_value(security_tab)),
                )
                ui.menu_item(
                    "Active Scan",
                    on_click=lambda: (scan_state["open_entry"](entry), tabs.set_value(scan_tab)),
                )
                if "graphql" in (entry.tags or []):
                    ui.menu_item(
                        "Open in GraphQL tab",
                        on_click=lambda: (
                            gql_state["open_entry"](entry),
                            tabs.set_value(graphql_tab),
                        ),
                    )
                ui.menu_item(
                    "Set as Diff left",
                    on_click=lambda: _set_diff_left(entry, state),
                )
                if state.get("compare_left"):
                    ui.menu_item(
                        "Diff with left",
                        on_click=lambda eid=entry_id: _compare(
                            eid, state, diff_state, tabs, diff_tab, store
                        ),
                    )
                ui.separator()
                ui.label("Set color").classes("q-px-sm text-caption text-grey")
                for color, label in zip(_ROW_COLORS, _COLOR_LABELS, strict=False):

                    def _set_color(c=color, eid=entry_id) -> None:
                        store.set_color(eid, c)
                        _refresh_table(store, state, table)
                        menu.close()

                    with ui.menu_item(on_click=_set_color), ui.row().classes("items-center gap-2"):
                        if color:
                            ui.element("div").style(
                                f"width:12px;height:12px;border-radius:2px;background:{color}"
                            )
                        ui.label(label)
            menu.open()

        table.on("row-contextmenu", on_row_contextmenu)

        if intercept_mgr is not None:
            build_intercept_panel(intercept_mgr, detail_col)

        _refresh_table(store, state, table)
        q = store.subscribe()

        async def _poller() -> None:
            try:
                while True:
                    try:
                        entry = q.get_nowait()
                        if state["filter"].matches(entry):
                            existing = next(
                                (i for i, e in enumerate(state["entries"]) if e.id == entry.id),
                                None,
                            )
                            if existing is not None:
                                state["entries"][existing] = entry
                            else:
                                state["entries"].insert(0, entry)
                            _update_table_rows(state, table)
                    except asyncio.QueueEmpty:
                        pass
                    await asyncio.sleep(0.2)
            except asyncio.CancelledError:
                store.unsubscribe(q)

        nicegui_app.on_shutdown(lambda: store.unsubscribe(q))
        asyncio.ensure_future(_poller())


def _set_diff_left(entry: Entry, state: dict) -> None:
    state["compare_left"] = entry
    ui.notify(f"#{entry.id} set as left side", type="info")


def _compare(
    right_id: int,
    state: dict,
    diff_state: dict,
    tabs: ui.tabs,
    tab: ui.tab,
    store: Store,
) -> None:
    left = state.get("compare_left")
    right = store.get(right_id)
    if left and right:
        diff_state["set_entries"](left, right)
        tabs.set_value(tab)


def _build_table() -> ui.table:
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
        {"name": "size", "label": "Size", "field": "size", "align": "right", "style": "width:70px"},
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
        "body",
        r"""
        <q-tr :props="props"
              :style="props.row.color ? 'background:' + props.row.color + '33' : ''"
              @click="$emit('row-click', $event, props.row)"
              @contextmenu.prevent="$emit('row-contextmenu', $event, props.row)"
              style="cursor:pointer">
          <q-td key="id" :props="props" class="text-right text-grey">{{ props.row.id }}</q-td>
          <q-td key="method" :props="props">
            <q-badge
              :color="{'GET':'blue','POST':'green','PUT':'orange','PATCH':'purple','DELETE':'red'}[props.row.method] || 'grey'"
              :label="props.row.method" rounded />
          </q-td>
          <q-td key="host" :props="props">{{ props.row.host }}</q-td>
          <q-td key="path" :props="props">{{ props.row.path }}</q-td>
          <q-td key="status" :props="props">
            <q-badge v-if="props.row.status_code"
              :color="props.row.status_code < 300 ? 'positive' : props.row.status_code < 400 ? 'info' : props.row.status_code < 500 ? 'warning' : 'negative'"
              :label="props.row.status_code" rounded />
          </q-td>
          <q-td key="size" :props="props" class="text-right text-grey">{{ props.row.size }}</q-td>
          <q-td key="duration" :props="props" class="text-right text-grey">{{ props.row.duration_ms }}</q-td>
          <q-td key="protocol" :props="props">
            <q-badge color="grey-7" :label="props.row.protocol" rounded />
          </q-td>
        </q-tr>
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
    size = len(e.resp_body) if e.resp_body else 0
    return {
        "id": e.id,
        "method": e.method,
        "host": e.host,
        "path": e.path + (f"?{e.query}" if e.query else ""),
        "status_code": e.status_code,
        "size": f"{size:,}" if size else "",
        "duration_ms": e.duration_ms or "",
        "protocol": e.protocol,
        "color": getattr(e, "color", ""),
    }


async def _clear(store: Store, state: dict, table: ui.table, detail_col: ui.element) -> None:
    store.clear()
    state["entries"] = []
    state["selected"] = None
    table.rows = []
    table.update()
    render_detail(None, detail_col)
    ui.notify("Cleared", type="info")
