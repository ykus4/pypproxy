from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path

from paxy.cert.ca import CA
from paxy.config.config import Config
from paxy.interceptor.interceptor import Interceptor
from paxy.proxy.proxy import Proxy
from paxy.rule.rule import RuleManager
from paxy.script.engine import ScriptEngine
from paxy.store.store import Store

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("paxy")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="paxy MITM proxy")
    p.add_argument(
        "--mode",
        choices=["gui", "cui"],
        default="gui",
        help="UI mode: gui (browser, default) or cui (terminal)",
    )
    p.add_argument("--addr", default="", help="proxy listen address")
    p.add_argument("--port", type=int, default=0, help="proxy port (default 8080)")
    p.add_argument("--ui-addr", default="", help="web UI / API listen address")
    p.add_argument("--ui-port", type=int, default=0, help="web UI port (default 8081)")
    p.add_argument("--config", default="", help="path to YAML config file")
    p.add_argument("--script", default="", help="path to Python script file")
    p.add_argument("--ca-dir", default="", help="directory to store CA cert/key")
    return p.parse_args()


async def run_proxy(proxy: Proxy, host: str, port: int) -> None:
    server = await asyncio.start_server(proxy.handle, host, port)
    logger.info("proxy listening on %s:%d", host, port)
    async with server:
        await server.serve_forever()


def _build_core(args: argparse.Namespace) -> tuple[Config, Proxy, Store, RuleManager]:
    cfg = Config.load(args.config) if args.config else Config.default()

    if args.port:
        cfg.proxy.port = args.port
    if args.addr:
        cfg.proxy.addr = args.addr
    if args.ui_port:
        cfg.ui.port = args.ui_port
    if args.ui_addr:
        cfg.ui.addr = args.ui_addr
    if args.script:
        cfg.script.path = args.script

    ca_dir = Path(args.ca_dir) if args.ca_dir else Path(cfg.ca.cert_path).parent
    ca_dir.mkdir(parents=True, exist_ok=True)

    cert_path = cfg.ca.cert_path or str(ca_dir / "ca-cert.pem")
    key_path = cfg.ca.key_path or str(ca_dir / "ca-key.pem")
    ca = CA.load_or_create(cert_path, key_path)

    store = Store()
    rules = RuleManager()
    interceptor = Interceptor(rules, store)

    script: ScriptEngine | None = None
    if cfg.script.path:
        script = ScriptEngine()
        script.load_file(cfg.script.path)
        logger.info("loaded script: %s", cfg.script.path)

    proxy = Proxy(
        ca=ca,
        interceptor=interceptor,
        store=store,
        script=script,
        ignore=set(cfg.proxy.ignore),
    )

    print("paxy MITM proxy")
    print(f"  proxy : {cfg.proxy.addr}:{cfg.proxy.port}")
    print(f"  UI    : http://{cfg.ui.addr}:{cfg.ui.port}")
    print(f"  CA    : {cert_path}")
    print("Install the CA cert in your browser/device to avoid TLS warnings.")

    return cfg, proxy, store, rules


def run_gui(args: argparse.Namespace) -> None:
    from nicegui import app as nicegui_app
    from nicegui import ui

    from paxy.api.server import app as api_app
    from paxy.api.server import init as api_init
    from paxy.ui.app import build_ui

    cfg, proxy, store, rules = _build_core(args)
    api_init(store, rules)

    nicegui_app.mount("/api", api_app)
    build_ui(store)

    async def startup() -> None:
        loop = asyncio.get_event_loop()
        store.set_loop(loop)
        asyncio.ensure_future(run_proxy(proxy, cfg.proxy.addr, cfg.proxy.port))

    nicegui_app.on_startup(startup)

    ui.run(
        host=cfg.ui.addr,
        port=cfg.ui.port,
        title="paxy",
        dark=True,
        reload=False,
        show=False,
    )


def run_cui(args: argparse.Namespace) -> None:
    import uvicorn

    from paxy.api.server import app as api_app
    from paxy.api.server import init as api_init
    from paxy.ui.cui import run_cui as _run_cui

    cfg, proxy, store, rules = _build_core(args)
    api_init(store, rules)

    async def _main() -> None:
        loop = asyncio.get_event_loop()
        store.set_loop(loop)

        uv_config = uvicorn.Config(
            api_app,
            host=cfg.ui.addr,
            port=cfg.ui.port,
            log_level="warning",
        )
        uv_server = uvicorn.Server(uv_config)

        await asyncio.gather(
            run_proxy(proxy, cfg.proxy.addr, cfg.proxy.port),
            uv_server.serve(),
            _run_cui(store, f"{cfg.proxy.addr}:{cfg.proxy.port}", cfg.ui.port),
        )

    asyncio.run(_main())


def main() -> None:
    args = parse_args()
    if args.mode == "cui":
        run_cui(args)
    else:
        run_gui(args)


if __name__ == "__main__":
    main()
