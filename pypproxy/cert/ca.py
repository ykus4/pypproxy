from __future__ import annotations

import ipaddress
import ssl
import tempfile
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID


class CA:
    def __init__(self, cert: x509.Certificate, key: rsa.RSAPrivateKey) -> None:
        self._cert = cert
        self._key = key
        self._cache: dict[str, ssl.SSLContext] = {}
        self._lock = threading.Lock()

    @classmethod
    def load_or_create(cls, cert_path: str, key_path: str) -> CA:
        cp, kp = Path(cert_path).resolve(), Path(key_path).resolve()
        if cp.exists() and kp.exists():
            return cls._load(cp, kp)
        return cls._generate(cp, kp)

    @classmethod
    def _load(cls, cert_path: Path, key_path: Path) -> CA:
        cert = x509.load_pem_x509_certificate(cert_path.read_bytes())
        key = serialization.load_pem_private_key(key_path.read_bytes(), password=None)
        return cls(cert, key)  # type: ignore[arg-type]

    @classmethod
    def _generate(cls, cert_path: Path, key_path: Path) -> CA:
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        now = datetime.now(UTC)
        cert = (
            x509.CertificateBuilder()
            .subject_name(
                x509.Name(
                    [
                        x509.NameAttribute(NameOID.COMMON_NAME, "paxy CA"),
                        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "paxy"),
                    ]
                )
            )
            .issuer_name(
                x509.Name(
                    [
                        x509.NameAttribute(NameOID.COMMON_NAME, "paxy CA"),
                    ]
                )
            )
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(hours=1))
            .not_valid_after(now + timedelta(days=3650))
            .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
            .add_extension(
                x509.KeyUsage(
                    digital_signature=False,
                    content_commitment=False,
                    key_encipherment=False,
                    data_encipherment=False,
                    key_agreement=False,
                    key_cert_sign=True,
                    crl_sign=True,
                    encipher_only=False,
                    decipher_only=False,
                ),
                critical=True,
            )
            .sign(key, hashes.SHA256())
        )

        cert_path.parent.mkdir(parents=True, exist_ok=True)
        cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        key_path.write_bytes(
            key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.TraditionalOpenSSL,
                serialization.NoEncryption(),
            )
        )
        return cls(cert, key)

    def cert_pem(self) -> bytes:
        return self._cert.public_bytes(serialization.Encoding.PEM)

    def ssl_context_for(self, hostname: str) -> ssl.SSLContext:
        with self._lock:
            if hostname in self._cache:
                return self._cache[hostname]
            ctx = self._make_context(hostname)
            self._cache[hostname] = ctx
            return ctx

    def _make_context(self, hostname: str) -> ssl.SSLContext:
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        now = datetime.now(UTC)

        san: list[x509.GeneralName]
        try:
            san = [x509.IPAddress(ipaddress.ip_address(hostname))]
        except ValueError:
            san = [x509.DNSName(hostname)]

        cert = (
            x509.CertificateBuilder()
            .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, hostname)]))
            .issuer_name(self._cert.subject)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(hours=1))
            .not_valid_after(now + timedelta(days=1))
            .add_extension(x509.SubjectAlternativeName(san), critical=False)
            .add_extension(
                x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.SERVER_AUTH]),
                critical=False,
            )
            .sign(self._key, hashes.SHA256())
        )

        cert_pem = cert.public_bytes(serialization.Encoding.PEM)
        key_pem = key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )

        # Write to temp files because ssl.SSLContext requires file paths.
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pem") as cf:
            cf.write(cert_pem)
            cert_file = cf.name
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pem") as kf:
            kf.write(key_pem)
            key_file = kf.name

        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(cert_file, key_file)
        return ctx
