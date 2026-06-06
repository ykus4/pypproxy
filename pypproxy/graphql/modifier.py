from __future__ import annotations

import json
import re
from typing import Any


def set_variable(body: bytes, var_name: str, new_value: Any) -> bytes:
    """Replace a variable value in a GraphQL request body."""
    try:
        data = json.loads(body)
        if isinstance(data, dict) and "variables" in data and isinstance(data["variables"], dict):
            data["variables"][var_name] = new_value
            return json.dumps(data).encode()
    except Exception:
        pass
    return body


def replace_field_alias(body: bytes, field: str, alias: str) -> bytes:
    """Add an alias to a field in the query string."""
    try:
        data = json.loads(body)
        if "query" in data:
            data["query"] = re.sub(
                rf"\b{re.escape(field)}\b",
                f"{alias}: {field}",
                data["query"],
                count=1,
            )
            return json.dumps(data).encode()
    except Exception:
        pass
    return body


def inject_field(body: bytes, type_name: str, extra_fields: list[str]) -> bytes:
    """
    Inject extra fields into the selection set of a named type in the query.
    E.g. inject_field(body, "User", ["__typename", "id"]) adds those fields
    after the opening brace of User { ...
    """
    try:
        data = json.loads(body)
        if "query" in data:
            extra = " ".join(extra_fields)
            # insert after the type name's opening brace
            data["query"] = re.sub(
                rf"\b{re.escape(type_name)}\s*{{",
                f"{type_name} {{ {extra} ",
                data["query"],
                count=1,
            )
            return json.dumps(data).encode()
    except Exception:
        pass
    return body


def strip_operation_name(body: bytes) -> bytes:
    """Remove operationName to test anonymous query handling."""
    try:
        data = json.loads(body)
        if isinstance(data, dict):
            data.pop("operationName", None)
            return json.dumps(data).encode()
    except Exception:
        pass
    return body


def add_introspection_field(body: bytes) -> bytes:
    """Inject __typename into every selection set as a probe."""
    try:
        data = json.loads(body)
        if "query" in data:
            data["query"] = re.sub(r"{\s*", "{ __typename ", data["query"])
            return json.dumps(data).encode()
    except Exception:
        pass
    return body


def build_query(fields: list[str], type_name: str = "") -> bytes:
    """Build a simple GraphQL query for the given field list."""
    selection = "\n  ".join(fields)
    query = f"{{ {selection} }}"
    return json.dumps({"query": query}).encode()


def build_mutation(mutation_name: str, args: dict, return_fields: list[str]) -> bytes:
    """Build a GraphQL mutation."""
    arg_str = ", ".join(
        f'{k}: "{v}"' if isinstance(v, str) else f"{k}: {v}" for k, v in args.items()
    )
    return_str = " ".join(return_fields)
    query = f"mutation {{ {mutation_name}({arg_str}) {{ {return_str} }} }}"
    return json.dumps({"query": query}).encode()
