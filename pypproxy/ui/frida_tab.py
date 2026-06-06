from __future__ import annotations

from nicegui import ui

from pypproxy.store.models import Entry, Filter
from pypproxy.store.store import Store


def build_frida_tab(store: Store) -> dict:
    state: dict = {"entry": None}

    with ui.column().classes("w-full h-full overflow-auto q-pa-md"):
        with ui.tabs().props("dense dark") as tabs:
            bypass_tab = ui.tab("SSL Bypass", icon="lock_open")
            hooks_tab = ui.tab("Request Hooks", icon="code")
            traffic_tab_btn = ui.tab("Traffic Hooks", icon="wifi")

        with ui.tab_panels(tabs, value=bypass_tab).classes("w-full"):
            # --- SSL Bypass ---
            with ui.tab_panel(bypass_tab):
                ui.label("Certificate Pinning Bypass Scripts").classes("text-subtitle2 q-mb-xs")
                ui.label(
                    "Generated Frida scripts to bypass SSL/TLS certificate pinning on iOS and Android."
                ).classes("text-caption text-grey q-mb-md")

                with ui.row().classes("gap-2 items-center q-mb-sm"):
                    from pypproxy.frida.pinning_bypass import list_templates

                    template_select = (
                        ui.select(list_templates(), value=list_templates()[0], label="Template")
                        .props("dense outlined dark")
                        .classes("w-72")
                    )
                    load_btn = ui.button("Load", icon="download").props("color=primary size=sm")

                bypass_area = (
                    ui.textarea()
                    .props("outlined dense rows=28 readonly")
                    .classes("w-full font-mono text-xs")
                )

                def _load_template() -> None:
                    from pypproxy.frida.pinning_bypass import get_template

                    bypass_area.value = get_template(template_select.value)

                load_btn.on("click", _load_template)
                _load_template()

                with ui.row().classes("gap-2 q-mt-sm"):
                    ui.button(
                        "Copy",
                        icon="content_copy",
                        on_click=lambda: (
                            ui.run_javascript(
                                f"navigator.clipboard.writeText({bypass_area.value!r})"
                            ),
                            ui.notify("Copied!", type="positive"),
                        ),
                    ).props("flat size=sm")
                    ui.label(
                        "Usage: frida -U -f <bundle_id/package> -l script.js --no-pause"
                    ).classes("text-caption text-grey self-center")

            # --- Request Hooks ---
            with ui.tab_panel(hooks_tab):
                ui.label("Request Hook Generator").classes("text-subtitle2 q-mb-xs")
                ui.label("Generate a Frida hook for a specific captured request.").classes(
                    "text-caption text-grey q-mb-sm"
                )

                entry_label = ui.label("No entry selected").classes(
                    "text-grey text-caption q-mb-sm"
                )

                with ui.row().classes("gap-2 items-center q-mb-sm"):
                    target_select = (
                        ui.select(
                            ["okhttp3", "nsurlsession", "fetch"], value="okhttp3", label="Target"
                        )
                        .props("dense outlined dark")
                        .classes("w-36")
                    )
                    gen_hook_btn = ui.button("Generate Hook", icon="code").props(
                        "color=primary size=sm"
                    )

                hook_area = (
                    ui.textarea()
                    .props("outlined dense rows=24 readonly")
                    .classes("w-full font-mono text-xs")
                )

                def _gen_hook() -> None:
                    entry = state.get("entry")
                    if not entry:
                        ui.notify("Select an entry from Traffic first", type="warning")
                        return
                    from pypproxy.frida.hook_generator import generate_parameter_hook

                    hook_area.value = generate_parameter_hook(entry, target_select.value)

                gen_hook_btn.on("click", _gen_hook)

                with ui.row().classes("gap-2 q-mt-sm"):
                    ui.button(
                        "Copy",
                        icon="content_copy",
                        on_click=lambda: (
                            ui.run_javascript(
                                f"navigator.clipboard.writeText({hook_area.value!r})"
                            ),
                            ui.notify("Copied!", type="positive"),
                        ),
                    ).props("flat size=sm")

            # --- Traffic-based hooks ---
            with ui.tab_panel(traffic_tab_btn):
                ui.label("Traffic-based Hook Generator").classes("text-subtitle2 q-mb-xs")
                ui.label(
                    "Generate a Frida script based on all captured traffic — logs every observed endpoint."
                ).classes("text-caption text-grey q-mb-sm")

                with ui.row().classes("gap-2 items-center q-mb-sm"):
                    host_input = (
                        ui.input(label="Filter host (optional)")
                        .props("dense outlined dark")
                        .classes("w-48")
                    )
                    traffic_target = (
                        ui.select(
                            ["okhttp3", "nsurlsession", "fetch"], value="okhttp3", label="Target"
                        )
                        .props("dense outlined dark")
                        .classes("w-36")
                    )
                    gen_traffic_btn = ui.button("Generate", icon="wifi").props(
                        "color=primary size=sm"
                    )

                traffic_hook_area = (
                    ui.textarea()
                    .props("outlined dense rows=24 readonly")
                    .classes("w-full font-mono text-xs")
                )
                traffic_summary = ui.label("").classes("text-caption text-grey q-mt-xs")

                def _gen_traffic_hooks() -> None:
                    from pypproxy.frida.hook_generator import generate_request_logger

                    f = (
                        Filter(host=host_input.value.strip())
                        if host_input.value.strip()
                        else Filter()
                    )
                    entries, total = store.list(f, 0, 0)
                    hosts = list({e.host for e in entries if e.host})
                    endpoints = list({(e.method, e.path) for e in entries if e.method and e.path})
                    traffic_hook_area.value = generate_request_logger(entries, traffic_target.value)
                    traffic_summary.text = f"Based on {total} entries — {len(hosts)} hosts, {len(endpoints)} unique endpoints"
                    ui.notify(f"Generated from {total} entries", type="positive")

                gen_traffic_btn.on("click", _gen_traffic_hooks)

                with ui.row().classes("gap-2 q-mt-sm"):
                    ui.button(
                        "Copy",
                        icon="content_copy",
                        on_click=lambda: (
                            ui.run_javascript(
                                f"navigator.clipboard.writeText({traffic_hook_area.value!r})"
                            ),
                            ui.notify("Copied!", type="positive"),
                        ),
                    ).props("flat size=sm")

    def open_entry(entry: Entry) -> None:
        state["entry"] = entry
        entry_label.text = f"#{entry.id} {entry.method} {entry.scheme}://{entry.host}{entry.path}"

    return {"open_entry": open_entry}
