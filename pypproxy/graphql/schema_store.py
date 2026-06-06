from __future__ import annotations

import threading

from .introspection import GraphQLSchema


class SchemaStore:
    """Per-host schema cache."""

    def __init__(self) -> None:
        self._schemas: dict[str, GraphQLSchema] = {}
        self._lock = threading.Lock()

    def set(self, host: str, schema: GraphQLSchema) -> None:
        with self._lock:
            self._schemas[host] = schema

    def get(self, host: str) -> GraphQLSchema | None:
        with self._lock:
            return self._schemas.get(host)

    def list_hosts(self) -> list[str]:
        with self._lock:
            return list(self._schemas.keys())

    def delete(self, host: str) -> None:
        with self._lock:
            self._schemas.pop(host, None)

    def all(self) -> dict[str, GraphQLSchema]:
        with self._lock:
            return dict(self._schemas)
