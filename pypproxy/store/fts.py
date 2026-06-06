from __future__ import annotations

import logging
from dataclasses import dataclass

import aiosqlite

logger = logging.getLogger(__name__)

_CREATE_FTS = """
CREATE VIRTUAL TABLE IF NOT EXISTS entries_fts
USING fts5(
    host,
    path,
    req_body,
    resp_body,
    req_headers,
    resp_headers,
    content='entries',
    content_rowid='id'
)
"""

_TRIGGER_INSERT = """
CREATE TRIGGER IF NOT EXISTS entries_fts_insert
AFTER INSERT ON entries BEGIN
    INSERT INTO entries_fts(rowid, host, path, req_body, resp_body, req_headers, resp_headers)
    VALUES (new.id, new.host, new.path, new.req_body, new.resp_body, new.req_headers, new.resp_headers);
END
"""

_TRIGGER_UPDATE = """
CREATE TRIGGER IF NOT EXISTS entries_fts_update
AFTER UPDATE ON entries BEGIN
    INSERT INTO entries_fts(entries_fts, rowid, host, path, req_body, resp_body, req_headers, resp_headers)
    VALUES ('delete', old.id, old.host, old.path, old.req_body, old.resp_body, old.req_headers, old.resp_headers);
    INSERT INTO entries_fts(rowid, host, path, req_body, resp_body, req_headers, resp_headers)
    VALUES (new.id, new.host, new.path, new.req_body, new.resp_body, new.req_headers, new.resp_headers);
END
"""

_TRIGGER_DELETE = """
CREATE TRIGGER IF NOT EXISTS entries_fts_delete
BEFORE DELETE ON entries BEGIN
    INSERT INTO entries_fts(entries_fts, rowid, host, path, req_body, resp_body, req_headers, resp_headers)
    VALUES ('delete', old.id, old.host, old.path, old.req_body, old.resp_body, old.req_headers, old.resp_headers);
END
"""


@dataclass
class SearchResult:
    entry_id: int
    rank: float
    snippet: str

    def to_dict(self) -> dict:
        return {
            "entry_id": self.entry_id,
            "rank": self.rank,
            "snippet": self.snippet,
        }


async def setup_fts(db: aiosqlite.Connection) -> None:
    """Create FTS5 virtual table and triggers if not already present."""
    await db.execute(_CREATE_FTS)
    await db.execute(_TRIGGER_INSERT)
    await db.execute(_TRIGGER_UPDATE)
    await db.execute(_TRIGGER_DELETE)
    await db.commit()
    logger.info("FTS5 full-text search index ready")


async def search(
    db: aiosqlite.Connection,
    query: str,
    limit: int = 50,
) -> list[SearchResult]:
    """Search entries using FTS5. Returns matching entry IDs sorted by relevance."""
    if not query.strip():
        return []
    try:
        async with db.execute(
            """
            SELECT rowid, rank,
                   snippet(entries_fts, 0, '<b>', '</b>', '…', 10)
            FROM entries_fts
            WHERE entries_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (query, limit),
        ) as cur:
            rows = await cur.fetchall()
        return [SearchResult(entry_id=r[0], rank=r[1], snippet=r[2]) for r in rows]
    except Exception as e:
        logger.debug("FTS search error: %s", e)
        return []


async def rebuild_index(db: aiosqlite.Connection) -> None:
    """Rebuild the FTS index from the entries table."""
    await db.execute("INSERT INTO entries_fts(entries_fts) VALUES ('rebuild')")
    await db.commit()
