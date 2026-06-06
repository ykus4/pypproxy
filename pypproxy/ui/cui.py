from __future__ import annotations

import asyncio

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from pypproxy.store.models import Entry
from pypproxy.store.store import Store

console = Console()

METHOD_STYLES: dict[str, str] = {
    "GET": "bold blue",
    "POST": "bold green",
    "PUT": "bold yellow",
    "PATCH": "bold magenta",
    "DELETE": "bold red",
    "HEAD": "dim",
    "OPTIONS": "dim",
}


def _method_text(method: str) -> Text:
    style = METHOD_STYLES.get(method.upper(), "white")
    return Text(method, style=style)


def _status_text(code: int) -> Text:
    if code == 0:
        return Text("—", style="dim")
    if 200 <= code < 300:
        return Text(str(code), style="bold green")
    if 300 <= code < 400:
        return Text(str(code), style="bold cyan")
    if 400 <= code < 500:
        return Text(str(code), style="bold yellow")
    return Text(str(code), style="bold red")


def _build_table(entries: list[Entry]) -> Table:
    table = Table(
        show_header=True,
        header_style="bold bright_white",
        box=None,
        padding=(0, 1),
        expand=True,
    )
    table.add_column("ID", style="dim", width=6, justify="right")
    table.add_column("Method", width=8, justify="center")
    table.add_column("Host", min_width=20)
    table.add_column("Path", min_width=30, no_wrap=False)
    table.add_column("Status", width=7, justify="center")
    table.add_column("ms", style="dim", width=6, justify="right")
    table.add_column("Tags", style="dim", width=14)

    for e in entries[:200]:
        tags = ",".join(e.tags) if e.tags else ""
        row_style = ""
        if "blocked" in e.tags:
            row_style = "on dark_red"
        elif e.modified:
            row_style = "on dark_orange3"

        table.add_row(
            str(e.id),
            _method_text(e.method),
            e.host,
            e.path + (f"?{e.query}" if e.query else ""),
            _status_text(e.status_code),
            str(e.duration_ms) if e.duration_ms else "—",
            tags,
            style=row_style,
        )
    return table


def _build_layout(entries: list[Entry], status: str) -> Layout:
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="footer", size=1),
    )

    layout["header"].update(
        Panel(
            Text("paxy", style="bold white")
            + Text("  MITM Proxy  ", style="dim")
            + Text(f"[{len(entries)} requests]", style="cyan"),
            style="on #1a1a2e",
            border_style="bright_blue",
        )
    )

    layout["body"].update(
        Panel(
            _build_table(entries),
            title="[bold]Traffic[/bold]",
            border_style="bright_blue",
            padding=(0, 1),
        )
    )

    layout["footer"].update(
        Text(f"  {status}  q: quit  c: clear  /: filter", style="dim on #16213e")
    )

    return layout


async def run_cui(store: Store, proxy_addr: str, ui_port: int) -> None:
    entries: list[Entry] = []
    status = f"proxy :{proxy_addr}  API :http://localhost:{ui_port}/api"
    running = True

    q = store.subscribe()

    with Live(console=console, refresh_per_second=4, screen=True) as live:

        async def _updater() -> None:
            while running:
                try:
                    entry = q.get_nowait()
                    entries.insert(0, entry)
                except asyncio.QueueEmpty:
                    pass
                live.update(_build_layout(entries, status))
                await asyncio.sleep(0.25)

        async def _input_loop() -> None:
            nonlocal running
            loop = asyncio.get_event_loop()
            import sys
            import termios
            import tty

            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                while running:
                    ch = await loop.run_in_executor(None, sys.stdin.read, 1)
                    if ch in ("q", "Q", "\x03"):
                        running = False
                        break
                    elif ch in ("c", "C"):
                        store.clear()
                        entries.clear()
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)

        try:
            await asyncio.gather(_updater(), _input_loop())
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass
        finally:
            store.unsubscribe(q)
