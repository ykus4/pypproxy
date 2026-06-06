from __future__ import annotations

import gzip
import json
import logging
import struct
import zlib

logger = logging.getLogger(__name__)


# ---- content-encoding decode/encode ----


def decode_body(body: bytes, content_encoding: str) -> tuple[bytes, str]:
    """Decompress body according to Content-Encoding.
    Returns (decoded_bytes, applied_encoding). Falls back to original on error.
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


# ---- binary protocol decode ----


def decode_msgpack(data: bytes) -> str:
    """Decode MessagePack bytes to a pretty-printed JSON string."""
    try:
        import msgpack

        obj = msgpack.unpackb(data, raw=False, strict_map_key=False)
        return json.dumps(obj, indent=2, ensure_ascii=False, default=str)
    except Exception as e:
        return f"<msgpack decode error: {e}>"


def decode_cbor(data: bytes) -> str:
    """Decode CBOR bytes to a pretty-printed JSON string."""
    try:
        import cbor2

        obj = cbor2.loads(data)
        return json.dumps(obj, indent=2, ensure_ascii=False, default=str)
    except Exception as e:
        return f"<cbor decode error: {e}>"


def decode_protobuf_raw(data: bytes) -> str:
    """Decode raw protobuf bytes using wire-type heuristics (no schema needed)."""
    try:
        return _decode_proto_fields(data, indent=0)
    except Exception as e:
        return f"<protobuf decode error: {e}>"


def _decode_proto_fields(data: bytes, indent: int) -> str:
    lines: list[str] = []
    pos = 0
    pad = "  " * indent
    while pos < len(data):
        if pos >= len(data):
            break
        # read varint for tag+wire_type
        tag_wire, pos = _read_varint(data, pos)
        if tag_wire is None:
            break
        field_num = tag_wire >> 3
        wire_type = tag_wire & 0x7
        if wire_type == 0:  # varint
            val, pos = _read_varint(data, pos)
            lines.append(f"{pad}field {field_num} (varint): {val}")
        elif wire_type == 1:  # 64-bit
            if pos + 8 > len(data):
                break
            val = struct.unpack_from("<Q", data, pos)[0]
            pos += 8
            lines.append(f"{pad}field {field_num} (64-bit): {val}")
        elif wire_type == 2:  # length-delimited
            length, pos = _read_varint(data, pos)
            if length is None or pos + length > len(data):
                break
            payload = data[pos : pos + length]
            pos += length
            # try nested message
            try:
                nested = _decode_proto_fields(payload, indent + 1)
                lines.append(f"{pad}field {field_num} (embedded):")
                lines.append(nested)
            except Exception:
                try:
                    lines.append(f"{pad}field {field_num} (string): {payload.decode()!r}")
                except Exception:
                    lines.append(f"{pad}field {field_num} (bytes): {payload.hex()}")
        elif wire_type == 5:  # 32-bit
            if pos + 4 > len(data):
                break
            val = struct.unpack_from("<I", data, pos)[0]
            pos += 4
            lines.append(f"{pad}field {field_num} (32-bit): {val}")
        else:
            lines.append(f"{pad}field {field_num} (unknown wire type {wire_type})")
            break
    return "\n".join(lines)


def _read_varint(data: bytes, pos: int) -> tuple[int | None, int]:
    result, shift = 0, 0
    while pos < len(data):
        b = data[pos]
        pos += 1
        result |= (b & 0x7F) << shift
        shift += 7
        if not (b & 0x80):
            return result, pos
    return None, pos


def sniff_content_type(body: bytes, content_type: str) -> str:
    """Return a hint for how to display the body: json, xml, proto, msgpack, cbor, text, binary."""
    ct = content_type.lower()
    if "json" in ct:
        return "json"
    if "xml" in ct or "html" in ct:
        return "xml"
    if "grpc" in ct or "protobuf" in ct:
        return "proto"
    if "msgpack" in ct:
        return "msgpack"
    if "cbor" in ct:
        return "cbor"
    if not body:
        return "text"
    # heuristic: try JSON
    try:
        json.loads(body.decode("utf-8", errors="strict"))
        return "json"
    except Exception:
        pass
    # check binary
    printable = sum(1 for b in body[:256] if 0x20 <= b < 0x7F or b in (9, 10, 13))
    if len(body) > 0 and printable / min(len(body), 256) < 0.7:
        return "binary"
    return "text"
