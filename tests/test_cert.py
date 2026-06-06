from __future__ import annotations

from pathlib import Path

from paxy.cert.ca import CA
from paxy.cert.client_cert import ClientCert, ClientCertManager


def test_ca_generate_and_reload(tmp_path):
    cert_path = str(tmp_path / "ca-cert.pem")
    key_path = str(tmp_path / "ca-key.pem")

    ca = CA.load_or_create(cert_path, key_path)
    assert Path(cert_path).exists()
    assert Path(key_path).exists()

    pem = ca.cert_pem()
    assert pem.startswith(b"-----BEGIN CERTIFICATE-----")

    # reload from disk
    ca2 = CA.load_or_create(cert_path, key_path)
    assert ca2.cert_pem() == pem


def test_ca_ssl_context_for_host(tmp_path):
    ca = CA.load_or_create(str(tmp_path / "ca.pem"), str(tmp_path / "ca.key"))
    ctx = ca.ssl_context_for("example.com")
    assert ctx is not None
    # second call returns cached
    ctx2 = ca.ssl_context_for("example.com")
    assert ctx is ctx2


def test_ca_ssl_context_different_hosts(tmp_path):
    ca = CA.load_or_create(str(tmp_path / "ca.pem"), str(tmp_path / "ca.key"))
    ctx_a = ca.ssl_context_for("a.example.com")
    ctx_b = ca.ssl_context_for("b.example.com")
    assert ctx_a is not ctx_b


def test_client_cert_manager_add_remove():
    mgr = ClientCertManager()
    cert = ClientCert(name="test", cert_path="/tmp/c.pem", key_path="/tmp/k.pem")
    mgr.add(cert)
    assert len(mgr.list()) == 1
    mgr.remove("test")
    assert len(mgr.list()) == 0


def test_client_cert_host_pattern_wildcard():
    cert = ClientCert(name="all", cert_path="c.pem", key_path="k.pem", host_pattern="*.example.com")
    assert cert.matches("api.example.com")
    assert cert.matches("auth.example.com")
    assert not cert.matches("other.com")


def test_client_cert_manager_get_for_host():
    mgr = ClientCertManager()
    cert = ClientCert(
        name="api", cert_path="c.pem", key_path="k.pem", host_pattern="api.example.com"
    )
    mgr.add(cert)
    assert mgr.get_for_host("api.example.com") is cert
    assert mgr.get_for_host("other.com") is None


def test_client_cert_to_dict():
    cert = ClientCert(name="n", cert_path="/c.pem", key_path="/k.pem", host_pattern="*")
    d = cert.to_dict()
    assert d["name"] == "n"
    assert d["host_pattern"] == "*"
