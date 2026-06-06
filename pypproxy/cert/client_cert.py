from __future__ import annotations

import ssl
import threading
from dataclasses import dataclass


@dataclass
class ClientCert:
    name: str
    cert_path: str
    key_path: str
    host_pattern: str = "*"  # glob pattern, "*" means all hosts

    def matches(self, host: str) -> bool:
        import fnmatch

        return fnmatch.fnmatch(host, self.host_pattern)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "cert_path": self.cert_path,
            "key_path": self.key_path,
            "host_pattern": self.host_pattern,
        }


class ClientCertManager:
    def __init__(self) -> None:
        self._certs: list[ClientCert] = []
        self._lock = threading.Lock()

    def add(self, cert: ClientCert) -> None:
        with self._lock:
            self._certs.append(cert)

    def remove(self, name: str) -> None:
        with self._lock:
            self._certs = [c for c in self._certs if c.name != name]

    def list(self) -> list[ClientCert]:
        with self._lock:
            return list(self._certs)

    def get_for_host(self, host: str) -> ClientCert | None:
        with self._lock:
            for cert in self._certs:
                if cert.matches(host):
                    return cert
        return None

    def ssl_context_for(self, host: str) -> ssl.SSLContext | None:
        cert = self.get_for_host(host)
        if cert is None:
            return None
        try:
            ctx = ssl.create_default_context()
            ctx.load_cert_chain(cert.cert_path, cert.key_path)
            return ctx
        except Exception:
            return None

    def to_list(self) -> list[dict]:
        return [c.to_dict() for c in self.list()]
