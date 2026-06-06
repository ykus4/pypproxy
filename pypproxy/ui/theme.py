from nicegui import ui

METHOD_COLORS: dict[str, str] = {
    "GET": "blue",
    "POST": "green",
    "PUT": "orange",
    "PATCH": "purple",
    "DELETE": "red",
    "HEAD": "grey",
    "OPTIONS": "grey",
}

STATUS_COLORS: dict[int, str] = {}


def status_color(code: int) -> str:
    if 200 <= code < 300:
        return "positive"
    if 300 <= code < 400:
        return "info"
    if 400 <= code < 500:
        return "warning"
    if code >= 500:
        return "negative"
    return "grey"


def method_badge(method: str) -> None:
    color = METHOD_COLORS.get(method.upper(), "grey")
    ui.badge(method, color=color).props("rounded")


def status_badge(code: int) -> None:
    if code == 0:
        return
    ui.badge(str(code), color=status_color(code)).props("rounded")


def apply_dark_theme() -> None:
    ui.add_head_html("""
    <style>
      .paxy-row-modified { background: rgba(255, 200, 0, 0.08) !important; }
      .paxy-row-blocked  { background: rgba(255, 50,  50, 0.08) !important; }
      .paxy-row-selected { background: rgba(100, 150, 255, 0.15) !important; }
      .paxy-body-pre {
        font-family: monospace;
        font-size: 12px;
        white-space: pre-wrap;
        word-break: break-all;
        max-height: 400px;
        overflow-y: auto;
        background: rgba(0,0,0,0.2);
        padding: 8px;
        border-radius: 4px;
      }
      .paxy-header-table td { padding: 2px 8px; font-size: 12px; }
      .paxy-header-table td:first-child { color: #aaa; min-width: 160px; }
    </style>
    """)
