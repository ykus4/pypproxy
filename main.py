from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path

from paxy.cert.ca import CA
from paxy.cert.client_cert import ClientCertManager
from paxy.config.config import Config
from paxy.intercept.manager import InterceptManager
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
    p.add_argument("--no-db", action="store_true", help="disable SQLite persistence")
    return p.parse_args()


async def run_proxy(proxy: Proxy, host: str, port: int) -> None:
    try:
        server = await asyncio.start_server(proxy.handle, host, port)
    except OSError as e:
        logger.error("Failed to start proxy on %s:%d — %s", host, port, e)
        logger.error("Is another process already using port %d? Run: lsof -i :%d", port, port)
        return
    logger.info("proxy listening on %s:%d", host, port)
    async with server:
        await server.serve_forever()


def _build_core(
    args: argparse.Namespace,
) -> tuple[Config, Proxy, Store, RuleManager, InterceptManager, str, ClientCertManager]:
    cfg = Config.load(str(Path(args.config).resolve())) if args.config else Config.default()

    if args.port:
        cfg.proxy.port = args.port
    if args.addr:
        cfg.proxy.addr = args.addr
    if args.ui_port:
        cfg.ui.port = args.ui_port
    if args.ui_addr:
        cfg.ui.addr = args.ui_addr
    if args.script:
        cfg.script.path = str(Path(args.script).resolve())

    ca_dir = Path(args.ca_dir).resolve() if args.ca_dir else Path(cfg.ca.cert_path).parent
    ca_dir.mkdir(parents=True, exist_ok=True)

    cert_path = cfg.ca.cert_path or str(ca_dir / "ca-cert.pem")
    key_path = cfg.ca.key_path or str(ca_dir / "ca-key.pem")
    ca = CA.load_or_create(cert_path, key_path)

    db_path = str(ca_dir / "paxy.db") if not args.no_db else ""

    store = Store()
    rules = RuleManager()
    interceptor = Interceptor(rules, store)
    intercept_mgr = InterceptManager()
    cert_mgr = ClientCertManager()

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
        intercept_manager=intercept_mgr,
    )

    print("paxy MITM proxy")
    print(f"  proxy : {cfg.proxy.addr}:{cfg.proxy.port}")
    print(f"  UI    : http://{cfg.ui.addr}:{cfg.ui.port}")
    print(f"  CA    : {cert_path}")
    if db_path:
        print(f"  DB    : {db_path}")
    print("Install the CA cert in your browser/device to avoid TLS warnings.")

    return cfg, proxy, store, rules, intercept_mgr, db_path, cert_mgr


async def _init_db(store: Store, db_path: str) -> None:
    if not db_path:
        return
    from paxy.store.db import Database

    db = Database(db_path)
    await db.open()
    store.set_db(db)
    await store.load_from_db()
    logger.info("loaded %d entries from database", len(store._entries))


def run_gui(args: argparse.Namespace) -> None:
    from nicegui import app as nicegui_app
    from nicegui import ui

    from paxy.api.server import init as api_init
    from paxy.api.server import register_routes
    from paxy.ui.app import build_ui

    cfg, proxy, store, rules, intercept_mgr, db_path, cert_mgr = _build_core(args)
    api_init(store, rules)

    register_routes(nicegui_app)
    build_ui(
        store,
        intercept_mgr,
        settings_kwargs={
            "cfg": cfg,
            "rules": rules,
            "cert_mgr": cert_mgr,
        },
    )

    async def startup() -> None:
        loop = asyncio.get_event_loop()
        store.set_loop(loop)
        await _init_db(store, db_path)
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

    cfg, proxy, store, rules, intercept_mgr, db_path, cert_mgr = _build_core(args)
    api_init(store, rules)

    async def _main() -> None:
        loop = asyncio.get_event_loop()
        store.set_loop(loop)
        await _init_db(store, db_path)

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
