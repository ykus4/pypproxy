from __future__ import annotations

import json
import logging

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from ..replay.replay import ReplayOptions, replay_many
from ..rule.rule import Rule, RuleManager
from ..store.models import Filter
from ..store.store import Store

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
