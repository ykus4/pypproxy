from __future__ import annotations

import fnmatch
import re
import threading
from dataclasses import dataclass


@dataclass
class ScopeRule:
    pattern: str
    mode: str = "glob"  # glob or regex
    enabled: bool = True

    def matches(self, host: str) -> bool:
        if not self.enabled:
            return False
        if self.mode == "regex":
            try:
                return bool(re.search(self.pattern, host))
            except re.error:
                return False
        return fnmatch.fnmatch(host, self.pattern)

    def to_dict(self) -> dict:
        return {"pattern": self.pattern, "mode": self.mode, "enabled": self.enabled}


class ScopeManager:
    """Controls which hosts are in-scope for capture."""

    def __init__(self) -> None:
        self._rules: list[ScopeRule] = []
        self._lock = threading.Lock()
        self._enabled = False  # when False, all hosts are in-scope

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, value: bool) -> None:
        self._enabled = value

    def add(self, rule: ScopeRule) -> None:
        with self._lock:
            self._rules.append(rule)

    def remove(self, pattern: str) -> None:
        with self._lock:
            self._rules = [r for r in self._rules if r.pattern != pattern]

    def list(self) -> list[ScopeRule]:
        with self._lock:
            return list(self._rules)

    def is_in_scope(self, host: str) -> bool:
        if not self._enabled:
            return True
        with self._lock:
            rules = list(self._rules)
        if not rules:
            return True
        return any(r.matches(host) for r in rules)
