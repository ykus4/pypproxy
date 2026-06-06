from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC
from pathlib import Path

import aiosqlite

from .models import Entry, Filter

logger = logging.getLogger(__name__)

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS entries (
    id          INTEGER PRIMARY KEY,
    created_at  TEXT NOT NULL,
    method      TEXT NOT NULL DEFAULT '',
    scheme      TEXT NOT NULL DEFAULT '',
    host        TEXT NOT NULL DEFAULT '',
    path        TEXT NOT NULL DEFAULT '/',
    query       TEXT NOT NULL DEFAULT '',
    req_headers TEXT NOT NULL DEFAULT '{}',
    req_body    BLOB NOT NULL DEFAULT '',
    status_code INTEGER NOT NULL DEFAULT 0,
    resp_headers TEXT NOT NULL DEFAULT '{}',
    resp_body   BLOB NOT NULL DEFAULT '',
    duration_ms INTEGER NOT NULL DEFAULT 0,
    protocol    TEXT NOT NULL DEFAULT 'http',
    tags        TEXT NOT NULL DEFAULT '[]',
    modified    INTEGER NOT NULL DEFAULT 0,
    color       TEXT NOT NULL DEFAULT ''
)
"""

_CREATE_INDEX = """
CREATE INDEX IF NOT EXISTS idx_entries_host ON entries (host);
CREATE INDEX IF NOT EXISTS idx_entries_method ON entries (method);
CREATE INDEX IF NOT EXISTS idx_entries_protocol ON entries (protocol);
"""


class Database:
    def __init__(self, path: str) -> None:
        self._path = path
        self._db: aiosqlite.Connection | None = None
        self._lock = asyncio.Lock()

    async def open(self) -> None:
        Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(self._path)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute(_CREATE_TABLE)
        for stmt in _CREATE_INDEX.strip().split("\n"):
            if stmt.strip():
                await self._db.execute(stmt)
        await self._db.commit()
        # Initialize FTS index
        from pypproxy.store.fts import setup_fts

        await setup_fts(self._db)
        logger.info("database opened: %s", self._path)

    async def search(self, query: str, limit: int = 50) -> list:
        from pypproxy.store.fts import search

        if not self._db:
            return []
        return await search(self._db, query, limit)

    async def close(self) -> None:
        if self._db:
            await self._db.close()

    async def insert(self, entry: Entry) -> None:
        if not self._db:
            return
        async with self._lock:
            await self._db.execute(
                """INSERT OR REPLACE INTO entries
                   (id, created_at, method, scheme, host, path, query,
                    req_headers, req_body, status_code, resp_headers, resp_body,
                    duration_ms, protocol, tags, modified, color)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                _entry_to_row(entry),
            )
            await self._db.commit()

    async def update(self, entry: Entry) -> None:
        await self.insert(entry)

    async def get(self, entry_id: int) -> Entry | None:
        if not self._db:
            return None
        async with self._db.execute("SELECT * FROM entries WHERE id = ?", (entry_id,)) as cur:
            row = await cur.fetchone()
        return _row_to_entry(row) if row else None

    async def list(self, f: Filter, offset: int = 0, limit: int = 100) -> tuple[list[Entry], int]:
        if not self._db:
            return [], 0
        where, params = _build_where(f)
        async with self._db.execute(f"SELECT COUNT(*) FROM entries {where}", params) as cur:
            total = (await cur.fetchone())[0]

        order = "ORDER BY id DESC"
        q = f"SELECT * FROM entries {where} {order} LIMIT ? OFFSET ?"
        async with self._db.execute(q, [*params, limit, offset]) as cur:
            rows = await cur.fetchall()
        return [_row_to_entry(r) for r in rows], total

    async def clear(self) -> None:
        if not self._db:
            return
        async with self._lock:
            await self._db.execute("DELETE FROM entries")
            await self._db.commit()

    async def max_id(self) -> int:
        if not self._db:
            return 0
        async with self._db.execute("SELECT MAX(id) FROM entries") as cur:
            row = await cur.fetchone()
        return row[0] or 0


def _build_where(f: Filter) -> tuple[str, list]:
    clauses, params = [], []
    if f.method:
        clauses.append("method = ?")
        params.append(f.method)
    if f.host:
        clauses.append("host = ?")
        params.append(f.host)
    if f.protocol:
        clauses.append("protocol = ?")
        params.append(f.protocol)
    if f.search:
        clauses.append("(host || path) LIKE ?")
        params.append(f"%{f.search}%")
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    return where, params


def _entry_to_row(e: Entry) -> tuple:
    return (
        e.id,
        e.created_at.isoformat(),
        e.method,
        e.scheme,
        e.host,
        e.path,
        e.query,
        json.dumps(e.req_headers),
        e.req_body,
        e.status_code,
        json.dumps(e.resp_headers),
        e.resp_body,
        e.duration_ms,
        e.protocol,
        json.dumps(e.tags),
        int(e.modified),
        getattr(e, "color", ""),
    )


def _row_to_entry(row: aiosqlite.Row) -> Entry:
    from datetime import datetime

    e = Entry()
    e.id = row["id"]
    e.created_at = datetime.fromisoformat(row["created_at"]).replace(tzinfo=UTC)
    e.method = row["method"]
    e.scheme = row["scheme"]
    e.host = row["host"]
    e.path = row["path"]
    e.query = row["query"]
    e.req_headers = json.loads(row["req_headers"])
    e.req_body = bytes(row["req_body"]) if row["req_body"] else b""
    e.status_code = row["status_code"]
    e.resp_headers = json.loads(row["resp_headers"])
    e.resp_body = bytes(row["resp_body"]) if row["resp_body"] else b""
    e.duration_ms = row["duration_ms"]
    e.protocol = row["protocol"]
    e.tags = json.loads(row["tags"])
    e.modified = bool(row["modified"])
    e.color = row["color"]
    return e
