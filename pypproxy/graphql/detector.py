from __future__ import annotations

import json
import re

from pypproxy.store.models import Entry


def is_graphql(entry: Entry) -> bool:
    """Return True if the entry looks like a GraphQL request."""
    ct = entry.req_headers.get("content-type", [""])[0].lower()
    if "graphql" in ct:
        return True

    # POST with JSON body containing 'query' key
    if entry.method == "POST" and entry.req_body:
        try:
            body = json.loads(entry.req_body)
            if isinstance(body, dict) and "query" in body:
                q = body["query"].strip()
                if q.startswith(("{", "query", "mutation", "subscription", "fragment")):
                    return True
        except Exception:
            pass

    # GET with 'query' parameter
    if entry.method == "GET" and entry.query and "query=" in entry.query:
        return True

    # common GraphQL paths
    return bool(re.search(r"/graphql", entry.path, re.IGNORECASE))


def parse_operation(body: bytes) -> dict:
    """Parse a GraphQL request body. Returns dict with query/variables/operationName."""
    try:
        data = json.loads(body)
        if isinstance(data, dict):
            return {
                "query": data.get("query", ""),
                "variables": data.get("variables", {}),
                "operationName": data.get("operationName", ""),
            }
    except Exception:
        pass
    return {"query": body.decode("utf-8", errors="replace"), "variables": {}, "operationName": ""}


def extract_operation_type(query: str) -> str:
    """Return 'query', 'mutation', 'subscription', or 'unknown'."""
    q = query.strip().lower()
    if q.startswith("mutation"):
        return "mutation"
    if q.startswith("subscription"):
        return "subscription"
    if q.startswith("query") or q.startswith("{"):
        return "query"
    return "unknown"


def extract_operation_name(query: str) -> str:
    """Extract the operation name from a GraphQL query string."""
    m = re.search(r"(?:query|mutation|subscription)\s+(\w+)", query)
    if m:
        return m.group(1)
    return ""


def extract_field_names(query: str) -> list[str]:
    """Extract top-level field names from a GraphQL query (heuristic)."""
    # Remove strings, comments, and directives to avoid false positives
    clean = re.sub(r'"[^"]*"', '""', query)
    clean = re.sub(r"#[^\n]*", "", clean)
    # Find word tokens after '{' that look like field names
    fields = re.findall(r"[{,]\s*(\w+)\s*[({:\s]", clean)
    return list(dict.fromkeys(fields))  # dedupe preserving order
