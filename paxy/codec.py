from __future__ import annotations

import gzip
import logging
import zlib

logger = logging.getLogger(__name__)


def decode_body(body: bytes, content_encoding: str) -> tuple[bytes, str]:
    """Decompress body according to Content-Encoding.

    Returns (decoded_bytes, effective_encoding_applied).
    Falls back to original bytes on error.
    """
    if not body or not content_encoding:
        return body, ""

    encoding = content_encoding.lower().strip()

    try:
        if encoding == "gzip":
            return gzip.decompress(body), "gzip"
        if encoding == "br":
            import brotli  # type: ignore[import-untyped]

            return brotli.decompress(body), "br"
        if encoding in ("deflate", "zlib"):
            try:
                return zlib.decompress(body), encoding
            except zlib.error:
                return zlib.decompress(body, -zlib.MAX_WBITS), encoding
    except Exception as e:
        logger.debug("decode_body failed (encoding=%s): %s", encoding, e)

    return body, ""


def encode_body(body: bytes, encoding: str) -> bytes:
    """Re-compress body (for modified responses that need recompression)."""
    if not encoding:
        return body
    try:
        if encoding == "gzip":
            return gzip.compress(body)
        if encoding == "br":
            import brotli  # type: ignore[import-untyped]

            return brotli.compress(body)
        if encoding in ("deflate", "zlib"):
            return zlib.compress(body)
    except Exception as e:
        logger.debug("encode_body failed (encoding=%s): %s", encoding, e)
    return body
