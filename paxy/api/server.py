from __future__ import annotations

import json
import logging

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from pydantic import BaseModel

from paxy.bulk.sender import BulkPayload, bulk_send, race_send
from paxy.exporter.exporter import export_all, export_har, import_rules
from paxy.replay.replay import ReplayOptions, replay_many
from paxy.rule.rule import Rule, RuleManager
from paxy.store.models import Filter
from paxy.store.store import Store

logger = logging.getLogger(__name__)

app = FastAPI(title="paxy API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_store: Store | None = None
_rules: RuleManager | None = None


def init(store: Store, rules: RuleManager) -> None:
    global _store, _rules
    _store = store
    _rules = rules


def register_routes(target_app: FastAPI) -> None:
    """Include all API routes into another FastAPI/NiceGUI app (for GUI mode)."""
    target_app.include_router(app.router)


# --- traffic ---


@app.get("/api/traffic")
async def list_traffic(
    offset: int = 0,
    limit: int = 100,
    method: str = "",
    host: str = "",
    search: str = "",
    protocol: str = "",
) -> JSONResponse:
    assert _store is not None
    f = Filter(method=method, host=host, search=search, protocol=protocol)
    entries, total = _store.list(f, offset, limit)
    return JSONResponse(
        {
            "entries": [e.to_dict() for e in entries],
            "total": total,
            "offset": offset,
            "limit": limit,
        }
    )


@app.get("/api/traffic/{entry_id}")
async def get_traffic(entry_id: int) -> JSONResponse:
    assert _store is not None
    entry = _store.get(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="not found")
    return JSONResponse(entry.to_dict())


# --- rules ---


@app.get("/api/rules")
async def list_rules() -> JSONResponse:
    assert _rules is not None
    return JSONResponse([r.to_dict() for r in _rules.list()])


@app.post("/api/rules")
async def create_rule(data: dict) -> JSONResponse:
    assert _rules is not None
    rule = Rule.from_dict(data)
    _rules.add(rule)
    return JSONResponse(rule.to_dict())


@app.put("/api/rules/{rule_id}")
async def update_rule(rule_id: int, data: dict) -> JSONResponse:
    assert _rules is not None
    data["id"] = rule_id
    rule = Rule.from_dict(data)
    _rules.update(rule)
    return JSONResponse(rule.to_dict())


@app.delete("/api/rules/{rule_id}")
async def delete_rule(rule_id: int) -> Response:
    assert _rules is not None
    _rules.delete(rule_id)
    return Response(status_code=204)


# --- replay ---


class ReplayRequest(BaseModel):
    entry_id: int
    options: dict = {}


@app.post("/api/replay")
async def replay(req: ReplayRequest) -> JSONResponse:
    assert _store is not None
    entry = _store.get(req.entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="entry not found")
    opts = ReplayOptions(
        override_host=req.options.get("override_host", ""),
        extra_headers=req.options.get("extra_headers", {}),
        timeout_seconds=req.options.get("timeout_seconds", 30),
        count=req.options.get("count", 1),
    )
    results = await replay_many(entry, opts)
    return JSONResponse([r.to_dict() for r in results])


# --- bulk sender ---


class BulkRequest(BaseModel):
    entry_id: int
    payloads: list[dict] = []
    count: int = 10
    concurrency: int = 10
    mode: str = "payloads"  # "payloads" or "race"


@app.post("/api/bulk")
async def bulk(req: BulkRequest) -> JSONResponse:
    assert _store is not None
    entry = _store.get(req.entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="entry not found")
    if req.mode == "race":
        results = await race_send(entry, count=req.count)
    else:
        payloads = [
            BulkPayload(
                label=p.get("label", f"payload-{i}"),
                override_body=p.get("body", "").encode() if p.get("body") else b"",
                override_headers=p.get("headers", {}),
                override_path=p.get("path", ""),
            )
            for i, p in enumerate(req.payloads)
        ]
        results = await bulk_send(entry, payloads, concurrency=req.concurrency)
    return JSONResponse([r.to_dict() for r in results])


# --- export / import ---


@app.get("/api/export/json")
async def export_json() -> PlainTextResponse:
    assert _store is not None and _rules is not None
    entries, _ = _store.list(Filter(), 0, 0)
    return PlainTextResponse(export_all(entries, _rules), media_type="application/json")


@app.get("/api/export/har")
async def export_har_endpoint() -> PlainTextResponse:
    assert _store is not None
    entries, _ = _store.list(Filter(), 0, 0)
    return PlainTextResponse(export_har(entries), media_type="application/json")


@app.post("/api/import/rules")
async def import_rules_endpoint(data: dict) -> JSONResponse:
    assert _rules is not None
    import json as _json

    count = import_rules(_json.dumps(data.get("rules", data)), _rules)
    return JSONResponse({"imported": count})


# --- clear ---


@app.post("/api/clear")
async def clear() -> Response:
    assert _store is not None
    _store.clear()
    return Response(status_code=204)


# --- websocket ---


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket) -> None:
    assert _store is not None
    await websocket.accept()
    q = _store.subscribe()
    try:
        while True:
            entry = await q.get()
            await websocket.send_text(json.dumps(entry.to_dict()))
    except WebSocketDisconnect:
        pass
    finally:
        _store.unsubscribe(q)
