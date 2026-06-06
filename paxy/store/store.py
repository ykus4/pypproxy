from __future__ import annotations

import asyncio
import contextlib
import threading

from .models import Entry, Filter


class Store:
    def __init__(self) -> None:
        self._entries: list[Entry] = []
        self._by_id: dict[int, Entry] = {}
        self._counter = 0
        self._lock = threading.Lock()
        self._subscribers: list[asyncio.Queue] = []
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def add(self, entry: Entry) -> Entry:
        with self._lock:
            self._counter += 1
            entry.id = self._counter
            self._entries.append(entry)
            self._by_id[entry.id] = entry
        self._publish(entry)
        return entry

    def update(self, entry: Entry) -> None:
        with self._lock:
            self._by_id[entry.id] = entry
        self._publish(entry)

    def get(self, entry_id: int) -> Entry | None:
        return self._by_id.get(entry_id)

    def list(self, f: Filter, offset: int = 0, limit: int = 100) -> tuple[list[Entry], int]:
        with self._lock:
            filtered = [e for e in self._entries if f.matches(e)]
        total = len(filtered)
        if limit == 0:
            return filtered[offset:], total
        return filtered[offset : offset + limit], total

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
            self._by_id.clear()

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=512)
        with self._lock:
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        with self._lock, contextlib.suppress(ValueError):
            self._subscribers.remove(q)

    def _publish(self, entry: Entry) -> None:
        if self._loop is None:
            return
        with self._lock:
            subs = list(self._subscribers)
        for q in subs:
            with contextlib.suppress(asyncio.QueueFull):
                self._loop.call_soon_threadsafe(q.put_nowait, entry)
