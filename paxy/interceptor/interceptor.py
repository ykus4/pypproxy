from __future__ import annotations

import time

from ..rule.rule import Action, MatchContext, Modification, RuleManager
from ..store.models import Entry
from ..store.store import Store


class Interceptor:
    def __init__(self, rules: RuleManager, store: Store) -> None:
        self._rules = rules
        self._store = store

    def process_request(
        self,
        method: str,
        scheme: str,
        host: str,
        path: str,
        query: str,
        headers: dict[str, list[str]],
        body: bytes,
    ) -> tuple[Entry, bool]:
        entry = Entry(
            method=method,
            scheme=scheme,
            host=host,
            path=path,
            query=query,
            req_headers=dict(headers),
            req_body=body,
            protocol=scheme,
        )

        ctx = MatchContext(
            method=method,
            host=host,
            path=path,
            headers=headers,
            body=body,
        )

        rule = self._rules.match(ctx)
        blocked = False

        if rule:
            if rule.action == Action.BLOCK:
                entry.tags.append("blocked")
                blocked = True
            elif rule.action == Action.MODIFY:
                headers, body = _apply_request_mods(headers, body, rule.modifications)
                entry.req_headers = dict(headers)
                entry.req_body = body
                entry.modified = True
            elif rule.action == Action.REDIRECT:
                entry.tags.append("redirected")

        self._store.add(entry)
        return entry, blocked

    def process_response(
        self,
        entry: Entry,
        status_code: int,
        headers: dict[str, list[str]],
        body: bytes,
        start_time: float,
    ) -> tuple[dict[str, list[str]], bytes]:
        entry.status_code = status_code
        entry.resp_headers = dict(headers)
        entry.resp_body = body
        entry.duration_ms = int((time.monotonic() - start_time) * 1000)

        ctx = MatchContext(
            method=entry.method,
            host=entry.host,
            path=entry.path,
            headers=headers,
            body=body,
        )

        rule = self._rules.match(ctx)
        if rule and rule.action == Action.MODIFY:
            headers, body = _apply_response_mods(headers, body, rule.modifications)
            entry.resp_headers = dict(headers)
            entry.resp_body = body
            entry.modified = True

        self._store.update(entry)
        return headers, body


def _apply_request_mods(
    headers: dict[str, list[str]],
    body: bytes,
    mods: list[Modification],
) -> tuple[dict[str, list[str]], bytes]:
    headers = dict(headers)
    for m in mods:
        if m.target == "req_header":
            headers = _apply_header_mod(headers, m)
        elif m.target == "req_body" and m.operation == "replace":
            body = m.value.encode()
    return headers, body


def _apply_response_mods(
    headers: dict[str, list[str]],
    body: bytes,
    mods: list[Modification],
) -> tuple[dict[str, list[str]], bytes]:
    headers = dict(headers)
    for m in mods:
        if m.target == "resp_header":
            headers = _apply_header_mod(headers, m)
        elif m.target == "resp_body":
            if m.operation == "replace":
                body = m.value.encode()
            elif m.operation == "find_replace":
                body = body.replace(m.find.encode(), m.replace.encode())
    return headers, body


def _apply_header_mod(headers: dict[str, list[str]], m: Modification) -> dict[str, list[str]]:
    h = {k.lower(): v for k, v in headers.items()}
    key = m.key.lower()
    if m.operation == "set":
        h[key] = [m.value]
    elif m.operation == "delete":
        h.pop(key, None)
    elif m.operation == "append":
        h.setdefault(key, []).append(m.value)
    return h
