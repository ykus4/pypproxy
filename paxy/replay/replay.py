from __future__ import annotations

import asyncio
import base64
import time
from dataclasses import dataclass, field

import httpx

from ..store.models import Entry


@dataclass
class ReplayOptions:
    override_host: str = ""
    extra_headers: dict[str, str] = field(default_factory=dict)
    timeout_seconds: int = 30
    count: int = 1


@dataclass
class ReplayResult:
    entry_id: int
    status_code: int = 0
    body: bytes = b""
    duration_ms: int = 0
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "entry_id": self.entry_id,
            "status_code": self.status_code,
            "body": base64.b64encode(self.body).decode() if self.body else "",
            "duration_ms": self.duration_ms,
            "error": self.error,
        }


async def replay_one(entry: Entry, opts: ReplayOptions) -> ReplayResult:
    host = opts.override_host or entry.host
    url = f"{entry.scheme}://{host}{entry.path}"
    if entry.query:
        url += f"?{entry.query}"

    headers = {}
    for k, vs in entry.req_headers.items():
        headers[k] = ", ".join(vs)
    headers.update(opts.extra_headers)

    start = time.monotonic()
    try:
        async with httpx.AsyncClient(
            timeout=opts.timeout_seconds,
            verify=False,
        ) as client:
            resp = await client.request(
                method=entry.method,
                url=url,
                headers=headers,
                content=entry.req_body,
            )
        dur = int((time.monotonic() - start) * 1000)
        return ReplayResult(
            entry_id=entry.id,
            status_code=resp.status_code,
            body=resp.content,
            duration_ms=dur,
        )
    except Exception as e:
        dur = int((time.monotonic() - start) * 1000)
        return ReplayResult(entry_id=entry.id, duration_ms=dur, error=str(e))


async def replay_many(entry: Entry, opts: ReplayOptions) -> list[ReplayResult]:
    count = max(1, opts.count)
    tasks = [replay_one(entry, opts) for _ in range(count)]
    return await asyncio.gather(*tasks)
