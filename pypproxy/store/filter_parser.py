from __future__ import annotations

import re
from dataclasses import dataclass

from .models import Entry


@dataclass
class Condition:
    field: str
    op: str  # ==, !=, contains, ~  (regex)
    value: str

    def matches(self, entry: Entry) -> bool:
        val = _extract(entry, self.field)
        if self.op == "==":
            result = val == self.value
        elif self.op == "!=":
            result = val != self.value
        elif self.op == "contains":
            result = self.value.lower() in val.lower()
        elif self.op == "~":
            try:
                result = bool(re.search(self.value, val))
            except re.error:
                result = False
        else:
            result = self.value.lower() in val.lower()
        return result


def _extract(entry: Entry, field: str) -> str:
    field = field.lower()
    if field in ("host", "server"):
        return entry.host
    if field in ("path", "url"):
        return entry.path
    if field in ("method",):
        return entry.method
    if field in ("status", "status_code"):
        return str(entry.status_code)
    if field in ("protocol", "type"):
        return entry.protocol
    if field == "request":
        hdrs = " ".join(f"{k}: {','.join(v)}" for k, v in entry.req_headers.items())
        return f"{entry.method} {entry.path} {hdrs} {entry.req_body.decode(errors='replace')}"
    if field == "response":
        hdrs = " ".join(f"{k}: {','.join(v)}" for k, v in entry.resp_headers.items())
        return f"{entry.status_code} {hdrs} {entry.resp_body.decode(errors='replace')}"
    if field in ("full_text", "all"):
        req = _extract(entry, "request")
        resp = _extract(entry, "response")
        return req + " " + resp
    return ""


class FilterExpression:
    """
    Parses PacketProxy-style filter expressions.

    Syntax:
        field == value
        field != value
        field contains value
        field ~ regex
        expr && expr
        expr || expr

    Example:
        host == example.com && method == POST
        request contains token || response contains error
    """

    def __init__(self, expr: str) -> None:
        self._expr = expr.strip()
        self._compiled: list | None = None
        if self._expr:
            try:
                self._compiled = _parse(self._expr)
            except Exception:
                self._compiled = None

    @property
    def is_empty(self) -> bool:
        return not self._expr

    def matches(self, entry: Entry) -> bool:
        if not self._compiled:
            return True  # empty or invalid expression → match all
        return _eval(self._compiled, entry)


# --- parser ---

_TOKEN_RE = re.compile(
    r"(\|\||&&|\(|\)|"
    r"(?:host|path|url|method|status|status_code|protocol|type|request|response|full_text|all)"
    r"\s*(?:==|!=|contains|~)\s*[^\s()]+)",
    re.IGNORECASE,
)

_COND_RE = re.compile(
    r"^([\w_]+)\s*(==|!=|contains|~)\s*(.+)$",
    re.IGNORECASE,
)


def _parse(expr: str) -> list:
    """Tokenize into an AST-like list: ['cond', Condition], ['and'/'or'], ['('], [')']"""
    tokens = []
    i = 0
    expr = expr.strip()

    while i < len(expr):
        if expr[i : i + 2] == "&&":
            tokens.append(("and",))
            i += 2
        elif expr[i : i + 2] == "||":
            tokens.append(("or",))
            i += 2
        elif expr[i] == "(":
            tokens.append(("lparen",))
            i += 1
        elif expr[i] == ")":
            tokens.append(("rparen",))
            i += 1
        elif expr[i] == " ":
            i += 1
        else:
            # find end of condition token (up to next operator or paren)
            end = len(expr)
            for marker in ["&&", "||", ")", "("]:
                pos = expr.find(marker, i)
                if pos != -1 and pos < end:
                    end = pos
            token = expr[i:end].strip()
            if token:
                m = _COND_RE.match(token)
                if m:
                    tokens.append(
                        (
                            "cond",
                            Condition(
                                field=m.group(1),
                                op=m.group(2).lower(),
                                value=m.group(3).strip(),
                            ),
                        )
                    )
            i = end

    return tokens


def _eval(tokens: list, entry: Entry) -> bool:
    """Evaluate token list with short-circuit && / ||."""
    if not tokens:
        return True

    results = []
    ops = []

    for tok in tokens:
        kind = tok[0]
        if kind == "cond":
            results.append(tok[1].matches(entry))
        elif kind == "and":
            ops.append("and")
        elif kind == "or":
            ops.append("or")

    if not results:
        return True

    result = results[0]
    for i, op in enumerate(ops):
        if i + 1 >= len(results):
            break
        result = result and results[i + 1] if op == "and" else result or results[i + 1]
    return result
