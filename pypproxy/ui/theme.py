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

PALETTE = {
    "bg": "#0a0e1a",
    "surface": "#111827",
    "surface2": "#1a2236",
    "border": "#1e2d45",
    "accent": "#3b82f6",
    "text": "#e2e8f0",
    "text_muted": "#64748b",
}


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
    ui.add_head_html(f"""
    <style>
      :root {{
        --pp-bg: {PALETTE["bg"]};
        --pp-surface: {PALETTE["surface"]};
        --pp-surface2: {PALETTE["surface2"]};
        --pp-border: {PALETTE["border"]};
        --pp-accent: {PALETTE["accent"]};
        --pp-text: {PALETTE["text"]};
        --pp-muted: {PALETTE["text_muted"]};
      }}

      * {{ box-sizing: border-box; }}

      body, .q-page, #q-app {{
        background: var(--pp-bg) !important;
        color: var(--pp-text) !important;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
      }}

      /* ---- Sidebar ---- */
      .pp-sidebar {{
        width: 200px; min-width: 200px;
        background: var(--pp-surface);
        border-right: 1px solid var(--pp-border);
        display: flex; flex-direction: column;
        height: 100vh; overflow-y: auto;
      }}
      .pp-logo {{
        padding: 16px 18px 14px;
        border-bottom: 1px solid var(--pp-border);
      }}
      .pp-logo-name {{
        font-size: 17px; font-weight: 700;
        color: var(--pp-accent); letter-spacing: -0.3px;
      }}
      .pp-logo-sub {{
        font-size: 10px; color: var(--pp-muted);
        margin-top: 1px;
      }}
      .pp-nav-section {{
        padding: 14px 0 4px;
      }}
      .pp-nav-section-label {{
        font-size: 9.5px; font-weight: 700;
        color: var(--pp-muted); text-transform: uppercase;
        letter-spacing: 0.1em; padding: 0 18px 5px;
      }}
      .pp-nav-item {{
        display: flex; align-items: center; gap: 9px;
        padding: 7px 18px; cursor: pointer;
        color: var(--pp-muted); font-size: 13px;
        border-left: 2px solid transparent;
        transition: all 0.12s;
        user-select: none;
      }}
      .pp-nav-item:hover {{
        background: var(--pp-surface2); color: var(--pp-text);
      }}
      .pp-nav-item.active {{
        background: rgba(59,130,246,0.1);
        color: var(--pp-accent);
        border-left-color: var(--pp-accent);
      }}
      .pp-nav-icon {{
        font-size: 15px; width: 16px; text-align: center; flex-shrink: 0;
      }}

      /* ---- Toolbar ---- */
      .pp-toolbar {{
        background: var(--pp-surface);
        border-bottom: 1px solid var(--pp-border);
        padding: 7px 14px;
        display: flex; align-items: center; gap: 8px;
        min-height: 48px; flex-shrink: 0;
      }}
      .pp-toolbar-title {{
        font-size: 13px; font-weight: 600; color: var(--pp-text);
        white-space: nowrap;
      }}
      .pp-status-dot {{
        width: 7px; height: 7px; border-radius: 50%;
        background: #22c55e; box-shadow: 0 0 5px #22c55e88;
        flex-shrink: 0;
      }}

      /* ---- Filter ---- */
      .pp-filter-wrap {{ flex: 1; max-width: 420px; }}
      .pp-filter-wrap .q-field__control {{
        background: var(--pp-surface2) !important;
        border-color: var(--pp-border) !important;
        border-radius: 6px; height: 32px; min-height: 32px;
      }}
      .pp-filter-wrap .q-field__native {{
        font-size: 12px; padding: 0 8px;
        font-family: 'SF Mono', Consolas, monospace;
        color: var(--pp-text) !important;
      }}
      .pp-filter-wrap .q-field__label {{
        font-size: 12px; color: var(--pp-muted);
        top: 6px !important;
      }}
      .pp-filter-wrap .q-field--focused .q-field__control {{
        border-color: var(--pp-accent) !important;
      }}

      /* ---- Traffic table ---- */
      .pp-traffic .q-table__top, .pp-traffic .q-table__bottom {{ display: none; }}
      .pp-traffic thead tr th {{
        background: var(--pp-surface) !important;
        color: var(--pp-muted) !important;
        font-size: 10.5px !important; font-weight: 700 !important;
        text-transform: uppercase; letter-spacing: 0.07em;
        border-bottom: 1px solid var(--pp-border) !important;
        padding: 7px 10px; white-space: nowrap;
      }}
      .pp-traffic tbody tr td {{
        font-size: 12px; padding: 5px 10px;
        border-bottom: 1px solid rgba(30,45,69,0.6);
        color: var(--pp-text);
      }}
      .pp-traffic tbody tr:hover td {{ background: var(--pp-surface2) !important; }}
      .pp-traffic tbody tr.pp-row-selected td {{
        background: rgba(59,130,246,0.06) !important;
        border-left: 2px solid var(--pp-accent);
      }}

      /* ---- Method pill ---- */
      .m-get    {{ background: rgba(59,130,246,0.14); color: #93c5fd; border-radius: 3px; }}
      .m-post   {{ background: rgba(34,197,94,0.14);  color: #86efac; border-radius: 3px; }}
      .m-put    {{ background: rgba(245,158,11,0.14); color: #fcd34d; border-radius: 3px; }}
      .m-patch  {{ background: rgba(168,85,247,0.14); color: #d8b4fe; border-radius: 3px; }}
      .m-delete {{ background: rgba(239,68,68,0.14);  color: #fca5a5; border-radius: 3px; }}
      .m-pill {{
        font-size: 10px; font-weight: 700;
        padding: 1px 5px;
        font-family: 'SF Mono', Consolas, monospace;
        letter-spacing: 0.04em;
        display: inline-block;
      }}

      /* ---- Status pill ---- */
      .s-2 {{ background: rgba(34,197,94,0.12);  color: #86efac; border-radius: 3px; }}
      .s-3 {{ background: rgba(56,189,248,0.12); color: #7dd3fc; border-radius: 3px; }}
      .s-4 {{ background: rgba(245,158,11,0.12); color: #fcd34d; border-radius: 3px; }}
      .s-5 {{ background: rgba(239,68,68,0.12);  color: #fca5a5; border-radius: 3px; }}
      .s-pill {{
        font-size: 11px; font-weight: 600;
        padding: 1px 6px;
        font-family: 'SF Mono', Consolas, monospace;
        display: inline-block;
      }}

      /* ---- Detail panel ---- */
      .pp-detail {{
        background: var(--pp-surface);
        border-left: 1px solid var(--pp-border);
        overflow-y: auto; height: 100%;
      }}
      .pp-detail-section {{ padding: 12px 14px; border-bottom: 1px solid var(--pp-border); }}
      .pp-section-title {{
        font-size: 10px; font-weight: 700;
        text-transform: uppercase; letter-spacing: 0.09em;
        color: var(--pp-muted); margin-bottom: 8px;
        display: flex; align-items: center; gap: 6px;
      }}
      .pp-url-bar {{
        font-family: 'SF Mono', Consolas, monospace; font-size: 11px;
        color: var(--pp-text); background: var(--pp-bg);
        padding: 5px 8px; border-radius: 4px;
        border: 1px solid var(--pp-border); word-break: break-all;
        line-height: 1.5;
      }}
      .pp-headers {{ width: 100%; }}
      .pp-hrow {{ display: flex; gap: 0; font-size: 11.5px; border-bottom: 1px solid rgba(30,45,69,0.5); padding: 3px 0; }}
      .pp-hkey {{
        color: var(--pp-muted); min-width: 148px; max-width: 148px;
        font-family: 'SF Mono', Consolas, monospace; font-size: 11px;
        padding-right: 8px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
      }}
      .pp-hval {{
        color: var(--pp-text); font-size: 11px;
        font-family: 'SF Mono', Consolas, monospace; word-break: break-all;
      }}
      .paxy-body-pre {{
        font-family: 'SF Mono', Consolas, 'Fira Code', monospace;
        font-size: 11.5px; color: var(--pp-text);
        white-space: pre-wrap; word-break: break-all;
        max-height: 340px; overflow-y: auto;
        background: var(--pp-bg); padding: 10px 12px;
        border-radius: 6px; border: 1px solid var(--pp-border);
        line-height: 1.55;
      }}

      /* ---- View selector ---- */
      .pp-view-select .q-field__control {{
        height: 28px; min-height: 28px;
        background: var(--pp-surface2) !important;
        border-color: var(--pp-border) !important;
        border-radius: 5px;
      }}
      .pp-view-select .q-field__native span {{ font-size: 11px; color: var(--pp-text); }}
      .pp-view-select .q-field__label {{ font-size: 11px; top: 4px !important; }}

      /* ---- Size chip ---- */
      .pp-size-chip {{
        font-size: 10px; color: var(--pp-muted);
        background: var(--pp-surface2);
        padding: 1px 6px; border-radius: 3px;
        font-family: 'SF Mono', Consolas, monospace;
      }}

      /* ---- Quasar overrides ---- */
      .q-splitter__separator {{ background: var(--pp-border) !important; width: 1px !important; }}
      .q-expansion-item__header {{ padding: 8px 14px !important; background: transparent !important; }}
      .q-expansion-item .q-item__label {{ font-size: 11px !important; font-weight: 700 !important; color: var(--pp-muted) !important; text-transform: uppercase; letter-spacing: 0.07em; }}
      .q-menu {{ background: var(--pp-surface2) !important; border: 1px solid var(--pp-border) !important; border-radius: 7px !important; box-shadow: 0 8px 32px rgba(0,0,0,0.5) !important; }}
      .q-item {{ color: var(--pp-text) !important; font-size: 13px !important; min-height: 34px !important; padding: 0 12px !important; }}
      .q-item:hover {{ background: rgba(59,130,246,0.08) !important; }}
      .q-separator {{ background: var(--pp-border) !important; opacity: 1 !important; }}
      .q-dialog .q-card {{ background: var(--pp-surface) !important; border: 1px solid var(--pp-border) !important; border-radius: 10px !important; box-shadow: 0 20px 60px rgba(0,0,0,0.7) !important; }}
      .q-field--outlined .q-field__control {{ border-color: var(--pp-border) !important; background: var(--pp-surface2) !important; border-radius: 6px !important; }}
      .q-field--outlined.q-field--focused .q-field__control {{ border-color: var(--pp-accent) !important; }}
      .q-field__native, .q-field__input {{ color: var(--pp-text) !important; }}
      .q-field__label {{ color: var(--pp-muted) !important; }}
      .q-textarea .q-field__native {{ font-family: 'SF Mono', Consolas, monospace !important; font-size: 12px !important; color: var(--pp-text) !important; }}
      .q-badge {{ font-size: 10px !important; font-weight: 600 !important; padding: 2px 5px !important; border-radius: 4px !important; }}
      .q-table__container {{ background: transparent !important; }}
      .q-notification {{ border-radius: 7px !important; font-size: 13px !important; }}
      .q-tooltip {{ font-size: 11px !important; background: #1e2d45 !important; border-radius: 4px !important; }}
      .q-select__dropdown-icon {{ color: var(--pp-muted) !important; }}
      .q-btn {{ border-radius: 5px !important; font-size: 12px !important; font-weight: 500 !important; }}
      .q-btn--flat {{ background: transparent !important; }}
      .q-btn--flat:hover {{ background: var(--pp-surface2) !important; }}
      .q-linear-progress {{ height: 3px !important; border-radius: 2px !important; }}
      .q-card {{ background: var(--pp-surface) !important; border: 1px solid var(--pp-border) !important; border-radius: 8px !important; }}
      .q-switch__thumb {{ background: var(--pp-muted) !important; }}
      .q-switch--checked .q-switch__track {{ background: var(--pp-accent) !important; opacity: 0.5 !important; }}
      .q-switch--checked .q-switch__thumb {{ background: var(--pp-accent) !important; }}
      .q-header {{ border-bottom: 1px solid var(--pp-border) !important; box-shadow: none !important; }}
      .q-tabs {{ background: transparent !important; }}
      .q-tab {{ font-size: 12px !important; font-weight: 500 !important; color: var(--pp-muted) !important; min-height: 38px !important; padding: 0 12px !important; }}
      .q-tab--active {{ color: var(--pp-accent) !important; }}
      .q-tab-panels {{ background: transparent !important; }}
      .q-tab-panel {{ padding: 0 !important; }}
      .q-tabs__content {{ }}
      .q-tabs__arrow {{ color: var(--pp-muted) !important; }}

      /* Scrollbar */
      ::-webkit-scrollbar {{ width: 4px; height: 4px; }}
      ::-webkit-scrollbar-track {{ background: transparent; }}
      ::-webkit-scrollbar-thumb {{ background: var(--pp-border); border-radius: 2px; }}
      ::-webkit-scrollbar-thumb:hover {{ background: #2d4060; }}
    </style>
    """)
