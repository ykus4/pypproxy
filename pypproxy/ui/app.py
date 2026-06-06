from __future__ import annotations

import asyncio

from nicegui import app as nicegui_app
from nicegui import ui

from pypproxy.intercept.manager import InterceptManager
from pypproxy.store.models import Entry, Filter
from pypproxy.store.store import Store

from .intercept_dialog import build_intercept_panel
from .theme import PALETTE, apply_dark_theme

_ROW_COLORS = ["", "#b91c1c", "#166534", "#1e40af", "#b45309", "#6b21a8"]
_COLOR_LABELS = ["None", "Red", "Green", "Blue", "Yellow", "Purple"]

# Navigation structure
_NAV = [
    ("Traffic", [("Traffic", "list", "traffic")]),
    (
        "Tools",
        [
            ("Resender", "send", "resender"),
            ("Bulk Sender", "dynamic_feed", "bulk"),
            ("Macro", "playlist_play", "macro"),
            ("Diff", "difference", "diff"),
            ("A/B Test", "compare", "ab"),
        ],
    ),
    (
        "Security",
        [
            ("Security", "security", "security"),
            ("Adv Security", "shield", "advsec"),
            ("Scan", "search", "scan"),
            ("CORS/SSRF", "bug_report", "advsec2"),
        ],
    ),
    (
        "Analysis",
        [
            ("GraphQL", "account_tree", "graphql"),
            ("Analytics", "bar_chart", "analytics"),
            ("OpenAPI", "description", "openapi"),
        ],
    ),
    (
        "Dev",
        [
            ("Code Gen", "code", "codegen"),
            ("Frida", "adb", "frida"),
            ("Sessions", "folder", "sessions"),
            ("Report", "summarize", "report"),
        ],
    ),
    (
        "Data",
        [
            ("Import/Search", "upload", "import"),
        ],
    ),
]


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
            "active_page": "traffic",
        }

        # ── Root layout: sidebar + main ──────────────────────────
        with ui.row().classes("w-full").style("height:100vh; overflow:hidden; gap:0"):
            # ── Sidebar ──────────────────────────────────────────
            with ui.element("div").classes("pp-sidebar"):
                with ui.element("div").classes("pp-logo"):
                    ui.element("div").classes("pp-logo-name").text = "pypproxy"
                    with ui.row().classes("items-center gap-2").style("margin-top:4px"):
                        ui.element("div").classes("pp-status-dot").tooltip("Proxy running")
                        ui.element("div").classes("pp-logo-sub").text = "v0.2.0 · :8080"

                nav_items: dict[str, ui.element] = {}

                for group_name, items in _NAV:
                    with ui.element("div").classes("pp-nav-section"):
                        ui.element("div").classes("pp-nav-section-label").text = group_name
                        for label, icon, page_id in items:
                            item_el = ui.element("div").classes("pp-nav-item")
                            with item_el:
                                ui.html(f'<span class="material-icons pp-nav-icon">{icon}</span>')
                                ui.label(label).style("font-size:13.5px")

                            def _nav(pid=page_id, el=item_el) -> None:
                                state["active_page"] = pid
                                for _, v in nav_items.items():
                                    v.classes(remove="active")
                                el.classes("active")
                                page_container.clear()
                                _render_page(
                                    pid, store, state, intercept_mgr, page_container, nav_items
                                )

                            item_el.on("click", _nav)
                            nav_items[page_id] = item_el

                # Settings link at bottom
                ui.element("div").style("flex:1")
                with ui.element("div").style(
                    "padding:12px 18px 16px; border-top:1px solid var(--pp-border)"
                ):
                    settings_item = ui.element("div").classes("pp-nav-item").style("padding:6px 0")
                    with settings_item:
                        ui.html(
                            '<span class="material-icons pp-nav-icon" style="font-size:14px">settings</span>'
                        )
                        ui.label("Settings").style("font-size:12px")
                    settings_item.on("click", lambda: ui.navigate.to("/settings"))

            # ── Main area ─────────────────────────────────────────
            with ui.element("div").classes("pp-main"):
                # Toolbar
                with ui.element("div").classes("pp-toolbar"):
                    filter_input = (
                        ui.input(placeholder="host == example.com && method == POST")
                        .props("dense outlined dark")
                        .classes("pp-filter-wrap")
                        .tooltip(
                            "Fields: host path method status protocol request response full_text  |  Ops: == != contains ~  |  Logic: && ||"
                        )
                    )

                    ui.element("div").style("flex:1")

                    if intercept_mgr is not None:
                        intercept_toggle = (
                            ui.switch("Intercept")
                            .props("dense dark color=warning")
                            .tooltip("Pause requests")
                        )
                        intercept_toggle.on(
                            "update:model-value",
                            lambda e: intercept_mgr.set_enabled(e.args),
                        )

                    ui.button(
                        icon="delete_sweep", on_click=lambda: _clear_traffic(store, state)
                    ).props("flat dense size=sm color=negative").tooltip("Clear traffic")
                    ui.button(
                        icon="light_mode",
                        on_click=lambda: ui.run_javascript(
                            "const t = ppToggleTheme(); "
                            "document.querySelector('.pp-theme-btn .material-icons').textContent = "
                            "t === 'light' ? 'dark_mode' : 'light_mode';"
                        ),
                    ).props("flat dense size=sm").classes("pp-theme-btn").style(
                        f"color:{PALETTE['text_muted']}"
                    ).tooltip("Toggle light/dark mode")
                    ui.button(icon="settings", on_click=lambda: ui.navigate.to("/settings")).props(
                        "flat dense size=sm"
                    ).style(f"color:{PALETTE['text_muted']}").tooltip("Settings")

                # Page container
                page_container = ui.element("div").style(
                    "flex:1; overflow:hidden; display:flex; flex-direction:column"
                )

                # Filter reactivity
                def apply_filter() -> None:
                    state["filter"] = Filter(expression=filter_input.value or "")
                    if state["active_page"] == "traffic":
                        _render_page(
                            "traffic", store, state, intercept_mgr, page_container, nav_items
                        )

                filter_input.on("update:model-value", lambda: apply_filter())

                if intercept_mgr is not None:
                    build_intercept_panel(intercept_mgr, page_container)

        # Activate traffic page by default
        nav_items["traffic"].classes("active")
        _render_page("traffic", store, state, intercept_mgr, page_container, nav_items)

        # Live update poller
        q = store.subscribe()

        async def _poller() -> None:
            try:
                while True:
                    try:
                        entry = q.get_nowait()
                        if state["active_page"] == "traffic" and state["filter"].matches(entry):
                            existing = next(
                                (i for i, e in enumerate(state["entries"]) if e.id == entry.id),
                                None,
                            )
                            if existing is not None:
                                state["entries"][existing] = entry
                            else:
                                state["entries"].insert(0, entry)
                            if "traffic_table" in state:
                                _update_table(state["entries"], state["traffic_table"])
                    except asyncio.QueueEmpty:
                        pass
                    await asyncio.sleep(0.2)
            except asyncio.CancelledError:
                store.unsubscribe(q)

        nicegui_app.on_shutdown(lambda: store.unsubscribe(q))
        asyncio.ensure_future(_poller())


def _render_page(
    page_id: str,
    store: Store,
    state: dict,
    intercept_mgr,
    container: ui.element,
    nav_items: dict,
) -> None:
    container.clear()
    with container:
        if page_id == "traffic":
            _build_traffic_page(store, state, intercept_mgr)
        elif page_id == "resender":
            from .resender import build_resender_tab

            build_resender_tab(store)
        elif page_id == "bulk":
            from .bulk_sender_ui import build_bulk_sender

            bulk_state = build_bulk_sender(
                ui.column().classes("w-full h-full overflow-auto q-pa-md")
            )
            state["bulk_state"] = bulk_state
        elif page_id == "macro":
            from .macro_tab import build_macro_tab

            macro_state = build_macro_tab(store)
            state["macro_state"] = macro_state
        elif page_id == "diff":
            from .diff_view import build_diff_view

            diff_state = build_diff_view(ui.column().classes("w-full h-full overflow-auto q-pa-md"))
            state["diff_state"] = diff_state
        elif page_id == "ab":
            from .ab_tab import build_ab_tab

            ab_state = build_ab_tab(store)
            state["ab_state"] = ab_state
        elif page_id == "security":
            from .security_tab import build_security_tab

            sec_state = build_security_tab(store)
            state["sec_state"] = sec_state
        elif page_id == "advsec":
            from .advanced_security_tab import build_advanced_security_tab

            advsec_state = build_advanced_security_tab(store)
            state["advsec_state"] = advsec_state
        elif page_id == "scan":
            from .scan_tab import build_scan_tab

            scan_state = build_scan_tab(store)
            state["scan_state"] = scan_state
        elif page_id == "graphql":
            from .graphql_tab import build_graphql_tab

            gql_state = build_graphql_tab(store)
            state["gql_state"] = gql_state
        elif page_id == "analytics":
            from .analytics_tab import build_analytics_tab

            build_analytics_tab(store)
        elif page_id == "openapi":
            from .openapi_tab import build_openapi_tab

            build_openapi_tab(store)
        elif page_id == "codegen":
            from .codegen_tab import build_codegen_tab

            codegen_state = build_codegen_tab(store)
            state["codegen_state"] = codegen_state
        elif page_id == "frida":
            from .frida_tab import build_frida_tab

            frida_state = build_frida_tab(store)
            state["frida_state"] = frida_state
        elif page_id == "sessions":
            from .session_tab import build_session_tab

            session_state = build_session_tab(store)
            state["session_state"] = session_state
        elif page_id == "report":
            from .report_tab import build_report_tab

            build_report_tab(store)
        elif page_id == "import":
            from .import_tab import build_import_tab

            build_import_tab(store)


def _build_traffic_page(store: Store, state: dict, intercept_mgr) -> None:
    with ui.splitter(value=58).classes("w-full").style("height:calc(100vh - 48px)") as sp:
        with sp.before:
            table = _build_traffic_table(store, state)
            state["traffic_table"] = table

        with sp.after, ui.element("div").classes("pp-detail"):
            detail_col = ui.column().classes("w-full h-full")
            state["detail_col"] = detail_col
            _render_empty_detail(detail_col)


def _build_traffic_table(store: Store, state: dict) -> ui.table:
    columns = [
        {
            "name": "id",
            "label": "#",
            "field": "id",
            "align": "right",
            "style": "width:42px; color:var(--pp-muted)",
        },
        {
            "name": "method",
            "label": "Method",
            "field": "method",
            "align": "center",
            "style": "width:72px",
        },
        {"name": "host", "label": "Host", "field": "host", "align": "left"},
        {"name": "path", "label": "Path", "field": "path", "align": "left"},
        {
            "name": "status",
            "label": "Status",
            "field": "status_code",
            "align": "center",
            "style": "width:64px",
        },
        {
            "name": "size",
            "label": "Size",
            "field": "size",
            "align": "right",
            "style": "width:64px; color:var(--pp-muted)",
        },
        {
            "name": "ms",
            "label": "ms",
            "field": "duration_ms",
            "align": "right",
            "style": "width:52px; color:var(--pp-muted)",
        },
    ]

    table = (
        ui.table(columns=columns, rows=[], row_key="id")
        .classes("w-full pp-traffic")
        .props("dense flat dark virtual-scroll")
        .style("height:calc(100vh - 48px); overflow-y:auto")
    )
    table.add_slot(
        "body",
        r"""
        <q-tr :props="props"
              :class="{'pp-row-selected': props.row._selected}"
              :style="props.row.color ? 'border-left:2px solid ' + props.row.color : ''"
              @click="$emit('row-click', $event, props.row)"
              @contextmenu.prevent="$emit('row-contextmenu', $event, props.row)"
              style="cursor:pointer">
          <q-td key="id"     :props="props" style="color:var(--pp-muted); font-size:11px; font-family:monospace">{{ props.row.id }}</q-td>
          <q-td key="method" :props="props">
            <span :class="'m-pill m-' + props.row.method.toLowerCase()">{{ props.row.method }}</span>
          </q-td>
          <q-td key="host"   :props="props" style="font-size:12px; max-width:200px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap">{{ props.row.host }}</q-td>
          <q-td key="path"   :props="props" style="font-size:12px; font-family:monospace; max-width:300px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap">{{ props.row.path }}</q-td>
          <q-td key="status" :props="props">
            <span v-if="props.row.status_code" :class="'s-pill s-' + Math.floor(props.row.status_code/100)">{{ props.row.status_code }}</span>
          </q-td>
          <q-td key="size"   :props="props" style="font-size:11px; font-family:monospace">{{ props.row.size }}</q-td>
          <q-td key="ms"     :props="props" style="font-size:11px; font-family:monospace">{{ props.row.duration_ms }}</q-td>
        </q-tr>
        """,
    )

    # Load entries
    entries, _ = store.list(state["filter"], 0, 500)
    state["entries"] = list(reversed(entries))
    _update_table(state["entries"], table)

    # Row click → detail
    async def on_row_click(e) -> None:  # noqa: ANN001
        try:
            row = e.args[1] if isinstance(e.args, list) else e.args
            entry_id = int(row["id"])
        except (IndexError, KeyError, TypeError, ValueError):
            return
        entry = store.get(entry_id)
        if entry:
            state["selected"] = entry
            # Mark selected
            for r in table.rows:
                r["_selected"] = r["id"] == entry_id
            table.update()
            if "detail_col" in state:
                from .detail import render_detail

                render_detail(entry, state["detail_col"])

    table.on("row-click", on_row_click)

    # Row right-click → context menu
    async def on_row_contextmenu(e) -> None:  # noqa: ANN001
        try:
            row = e.args[1] if isinstance(e.args, list) else e.args
            entry_id = int(row["id"])
        except (IndexError, KeyError, TypeError, ValueError):
            return
        entry = store.get(entry_id)
        if not entry:
            return
        _show_context_menu(entry, state, store)

    table.on("row-contextmenu", on_row_contextmenu)
    return table


def _show_context_menu(entry: Entry, state: dict, store: Store) -> None:
    with ui.menu() as menu:
        # Tool shortcuts
        _menu_item(menu, "send", "Resender", lambda: _send_to("resender", entry, state))
        _menu_item(menu, "dynamic_feed", "Bulk Sender", lambda: _send_to("bulk", entry, state))
        _menu_item(menu, "playlist_play", "Macro", lambda: _send_to("macro", entry, state))
        _menu_item(menu, "compare", "A/B Test", lambda: _send_to("ab", entry, state))
        _menu_item(menu, "code", "Generate Code", lambda: _send_to("codegen", entry, state))
        _menu_item(menu, "security", "Security Check", lambda: _send_to("security", entry, state))
        _menu_item(menu, "shield", "Adv Security", lambda: _send_to("advsec", entry, state))
        _menu_item(menu, "search", "Active Scan", lambda: _send_to("scan", entry, state))
        _menu_item(menu, "adb", "Frida Hook", lambda: _send_to("frida", entry, state))
        if "graphql" in (entry.tags or []):
            _menu_item(menu, "account_tree", "GraphQL", lambda: _send_to("graphql", entry, state))
        _menu_item(menu, "folder", "Add to Session", lambda: _add_to_session(entry, state))

        ui.separator()
        _menu_item(menu, "difference", "Set Diff left", lambda: _set_diff_left(entry, state))
        if state.get("compare_left"):
            _menu_item(
                menu, "difference", "Diff with left", lambda: _compare_diff(entry, state, store)
            )

        ui.separator()
        ui.element("div").style(
            "font-size:10px; color:var(--pp-muted); padding:4px 12px 2px; font-weight:700; text-transform:uppercase; letter-spacing:0.07em"
        ).text = "Color"
        with ui.row().classes("q-px-sm q-pb-xs gap-1"):
            for color, label in zip(_ROW_COLORS, _COLOR_LABELS, strict=False):

                def _set(c=color, eid=entry.id) -> None:
                    store.set_color(eid, c)
                    _refresh_table_rows(store, state)
                    menu.close()

                dot = (
                    ui.element("div")
                    .style(
                        f"width:16px; height:16px; border-radius:3px; cursor:pointer; "
                        f"background:{color if color else 'var(--pp-surface2)'}; "
                        f"border:1px solid var(--pp-border)"
                    )
                    .tooltip(label)
                )
                dot.on("click", _set)
    menu.open()


def _menu_item(menu: ui.menu, icon: str, label: str, handler) -> None:
    with ui.menu_item(on_click=handler), ui.row().classes("items-center gap-2"):
        ui.html(
            f'<span class="material-icons" style="font-size:14px; color:var(--pp-muted)">{icon}</span>'
        )
        ui.element("span").style("font-size:13px").text = label


def _send_to(page_id: str, entry: Entry, state: dict) -> None:
    state["pending_entry"] = entry
    ui.notify(f"Opening {page_id}…", type="info", timeout=1000)
    # Navigation handled by sidebar click


def _add_to_session(entry: Entry, state: dict) -> None:
    from .session_tab import get_session_manager

    mgr = get_session_manager()
    active = mgr.get_active()
    if active:
        mgr.add_entry(active.id, entry.id)
        ui.notify(f"Added to '{active.name}'", type="positive")
    else:
        ui.notify("No active session", type="warning")


def _set_diff_left(entry: Entry, state: dict) -> None:
    state["compare_left"] = entry
    ui.notify(f"#{entry.id} set as diff left", type="info")


def _compare_diff(entry: Entry, state: dict, store: Store) -> None:
    left = state.get("compare_left")
    if left and "diff_state" in state:
        state["diff_state"]["set_entries"](left, entry)


def _render_empty_detail(container: ui.element) -> None:
    container.clear()
    with (
        container,
        ui.element("div").classes("pp-empty").style("height:100%; justify-content:center"),
    ):
        ui.html(
            '<span class="material-icons" style="font-size:40px; color:var(--pp-muted); opacity:0.3">preview</span>'
        )
        ui.element("div").style(
            "font-size:13px; color:var(--pp-muted)"
        ).text = "Click a request to inspect"


def _update_table(entries: list[Entry], table: ui.table) -> None:
    table.rows = [_entry_to_row(e) for e in entries]
    table.update()


def _refresh_table_rows(store: Store, state: dict) -> None:
    entries, _ = store.list(state["filter"], 0, 500)
    state["entries"] = list(reversed(entries))
    if "traffic_table" in state:
        _update_table(state["entries"], state["traffic_table"])


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
        "_selected": False,
    }


async def _clear_traffic(store: Store, state: dict) -> None:
    store.clear()
    state["entries"] = []
    state["selected"] = None
    if "traffic_table" in state:
        state["traffic_table"].rows = []
        state["traffic_table"].update()
    if "detail_col" in state:
        _render_empty_detail(state["detail_col"])
    ui.notify("Cleared", type="info")
