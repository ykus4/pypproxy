from __future__ import annotations

import contextlib
import json
import logging

import httpx
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from pydantic import BaseModel

from paxy.bulk.sender import BulkPayload, bulk_send, race_send
from paxy.exporter.exporter import export_all, export_har, import_rules
from paxy.exporter.importer import import_har, import_json
from paxy.replay.replay import ReplayOptions, replay_many
from paxy.rule.rule import Rule, RuleManager
from paxy.store.models import Filter
from paxy.store.scope import ScopeManager, ScopeRule
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
_scope: ScopeManager | None = None


def init(store: Store, rules: RuleManager, scope: ScopeManager | None = None) -> None:
    global _store, _rules, _scope
    _store = store
    _rules = rules
    _scope = scope


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


@app.post("/api/import/har")
async def import_har_endpoint(data: dict) -> JSONResponse:
    assert _store is not None
    import json as _json

    count = import_har(_json.dumps(data), _store)
    return JSONResponse({"imported": count})


@app.post("/api/import/json")
async def import_json_endpoint(data: dict) -> JSONResponse:
    assert _store is not None
    import json as _json

    count = import_json(_json.dumps(data.get("entries", data)), _store)
    return JSONResponse({"imported": count})


# --- full-text search ---


@app.get("/api/search")
async def fts_search(q: str = "", limit: int = 50) -> JSONResponse:
    assert _store is not None
    if not q:
        return JSONResponse([])
    db = getattr(_store, "_db", None)
    if db is None:
        # fallback: in-memory filter
        f = Filter(search=q)
        entries, _ = _store.list(f, 0, limit)
        return JSONResponse(
            [{"entry_id": e.id, "rank": 0.0, "snippet": e.host + e.path} for e in entries]
        )
    results = await db.search(q, limit)
    return JSONResponse([r.to_dict() for r in results])


# --- scope ---


@app.get("/api/scope")
async def list_scope() -> JSONResponse:
    if _scope is None:
        return JSONResponse({"enabled": False, "rules": []})
    return JSONResponse(
        {
            "enabled": _scope.enabled,
            "rules": [r.to_dict() for r in _scope.list()],
        }
    )


@app.post("/api/scope")
async def update_scope(data: dict) -> JSONResponse:
    if _scope is None:
        return JSONResponse({"error": "scope not initialized"}, status_code=503)
    if "enabled" in data:
        _scope.set_enabled(bool(data["enabled"]))
    if "add" in data:
        _scope.add(
            ScopeRule(
                pattern=data["add"].get("pattern", ""),
                mode=data["add"].get("mode", "glob"),
            )
        )
    if "remove" in data:
        _scope.remove(data["remove"])
    return JSONResponse({"enabled": _scope.enabled, "rules": [r.to_dict() for r in _scope.list()]})


# --- active scan ---


class ScanRequest(BaseModel):
    entry_id: int
    categories: list[str] = []
    concurrency: int = 5


@app.post("/api/scan")
async def active_scan(req: ScanRequest) -> JSONResponse:
    assert _store is not None
    from paxy.scan.scanner import run_scan

    entry = _store.get(req.entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="entry not found")
    cats = req.categories or None
    results = await run_scan(entry, categories=cats, concurrency=req.concurrency)
    return JSONResponse([r.to_dict() for r in results])


# --- GraphQL ---

_gql_schema_store = None


def init_graphql() -> None:
    global _gql_schema_store
    from paxy.graphql.schema_store import SchemaStore

    _gql_schema_store = SchemaStore()


class IntrospectRequest(BaseModel):
    url: str
    headers: dict[str, str] = {}


@app.post("/api/graphql/introspect")
async def graphql_introspect(req: IntrospectRequest) -> JSONResponse:
    from paxy.graphql.introspection import fetch_schema

    schema = await fetch_schema(req.url, req.headers)
    if schema is None:
        raise HTTPException(status_code=502, detail="Introspection failed or not supported")
    if _gql_schema_store is not None:
        from urllib.parse import urlparse

        host = urlparse(req.url).netloc
        _gql_schema_store.set(host, schema)
    return JSONResponse(schema.to_dict())


@app.get("/api/graphql/schemas")
async def graphql_list_schemas() -> JSONResponse:
    if _gql_schema_store is None:
        return JSONResponse([])
    return JSONResponse(
        [
            {"host": host, "query_type": s.query_type, "mutation_type": s.mutation_type}
            for host, s in _gql_schema_store.all().items()
        ]
    )


@app.get("/api/graphql/schema/{host}")
async def graphql_get_schema(host: str) -> JSONResponse:
    if _gql_schema_store is None:
        raise HTTPException(status_code=404, detail="no schema store")
    schema = _gql_schema_store.get(host)
    if schema is None:
        raise HTTPException(status_code=404, detail=f"no schema for {host}")
    return JSONResponse(schema.to_dict())


@app.delete("/api/graphql/schema/{host}")
async def graphql_delete_schema(host: str) -> Response:
    if _gql_schema_store is not None:
        _gql_schema_store.delete(host)
    return Response(status_code=204)


class GQLReplayRequest(BaseModel):
    entry_id: int
    query: str = ""
    variables: dict = {}
    operation_name: str = ""


@app.post("/api/graphql/replay")
async def graphql_replay(req: GQLReplayRequest) -> JSONResponse:
    assert _store is not None
    import json as _json
    import time

    entry = _store.get(req.entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="entry not found")

    url = f"{entry.scheme}://{entry.host}{entry.path}"
    body_dict: dict = {}
    if entry.req_body:
        with contextlib.suppress(Exception):
            body_dict = _json.loads(entry.req_body)

    if req.query:
        body_dict["query"] = req.query
    if req.variables:
        body_dict["variables"] = req.variables
    if req.operation_name:
        body_dict["operationName"] = req.operation_name

    req_headers = {k: ", ".join(v) for k, v in entry.req_headers.items()}
    start = time.monotonic()
    try:
        async with httpx.AsyncClient(verify=False, timeout=30, http2=True) as client:
            resp = await client.post(url, json=body_dict, headers=req_headers)
        dur = int((time.monotonic() - start) * 1000)
        return JSONResponse(
            {
                "status_code": resp.status_code,
                "duration_ms": dur,
                "body": resp.json()
                if "json" in resp.headers.get("content-type", "")
                else resp.text,
            }
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=502)


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
