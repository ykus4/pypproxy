from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class ProxyConfig:
    addr: str = "0.0.0.0"
    port: int = 8080
    ignore: list[str] = field(default_factory=list)
    max_body: int = 1024 * 1024  # 1MB


@dataclass
class CAConfig:
    cert_path: str = ""
    key_path: str = ""


@dataclass
class UIConfig:
    addr: str = "0.0.0.0"
    port: int = 8081


@dataclass
class ScriptConfig:
    path: str = ""


@dataclass
class Config:
    proxy: ProxyConfig = field(default_factory=ProxyConfig)
    ca: CAConfig = field(default_factory=CAConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    script: ScriptConfig = field(default_factory=ScriptConfig)

    @classmethod
    def default(cls) -> Config:
        cfg = cls()
        home = Path.home()
        cfg.ca.cert_path = str(home / ".paxy" / "ca-cert.pem")
        cfg.ca.key_path = str(home / ".paxy" / "ca-key.pem")
        return cfg

    @classmethod
    def load(cls, path: str) -> Config:
        cfg = cls.default()
        p = Path(path)
        if not p.exists():
            return cfg
        with p.open() as f:
            data = yaml.safe_load(f) or {}

        if proxy := data.get("proxy"):
            if "addr" in proxy:
                cfg.proxy.addr = proxy["addr"]
            if "port" in proxy:
                cfg.proxy.port = int(proxy["port"])
            if "ignore" in proxy:
                cfg.proxy.ignore = proxy["ignore"]
            if "max_body" in proxy:
                cfg.proxy.max_body = int(proxy["max_body"])

        if ca := data.get("ca"):
            if "cert_path" in ca:
                cfg.ca.cert_path = str(Path(ca["cert_path"]).resolve())
            if "key_path" in ca:
                cfg.ca.key_path = str(Path(ca["key_path"]).resolve())

        if ui := data.get("ui"):
            if "addr" in ui:
                cfg.ui.addr = ui["addr"]
            if "port" in ui:
                cfg.ui.port = int(ui["port"])

        if (script := data.get("script")) and "path" in script:
            cfg.script.path = str(Path(script["path"]).resolve())

        return cfg

    def save(self, path: str) -> None:
        data = {
            "proxy": {
                "addr": self.proxy.addr,
                "port": self.proxy.port,
                "ignore": self.proxy.ignore,
                "max_body": self.proxy.max_body,
            },
            "ca": {
                "cert_path": self.ca.cert_path,
                "key_path": self.ca.key_path,
            },
            "ui": {
                "addr": self.ui.addr,
                "port": self.ui.port,
            },
            "script": {
                "path": self.script.path,
            },
        }
        with open(path, "w") as f:
            yaml.dump(data, f, default_flow_style=False)
