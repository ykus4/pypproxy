from __future__ import annotations

from pypproxy.store.filter_parser import FilterExpression
from pypproxy.store.models import Entry


def make_entry(**kwargs) -> Entry:
    defaults = {
        "method": "GET",
        "scheme": "https",
        "host": "api.example.com",
        "path": "/v1/users",
        "protocol": "https",
        "status_code": 200,
    }
    defaults.update(kwargs)
    return Entry(**defaults)


def test_empty_expression_matches_all():
    expr = FilterExpression("")
    assert expr.matches(make_entry())


def test_host_equals():
    expr = FilterExpression("host == api.example.com")
    assert expr.matches(make_entry(host="api.example.com"))
    assert not expr.matches(make_entry(host="other.com"))


def test_host_contains():
    expr = FilterExpression("host contains example")
    assert expr.matches(make_entry(host="api.example.com"))
    assert not expr.matches(make_entry(host="other.com"))


def test_method_equals():
    expr = FilterExpression("method == POST")
    assert expr.matches(make_entry(method="POST"))
    assert not expr.matches(make_entry(method="GET"))


def test_path_contains():
    expr = FilterExpression("path contains users")
    assert expr.matches(make_entry(path="/v1/users"))
    assert not expr.matches(make_entry(path="/v1/items"))


def test_status_equals():
    expr = FilterExpression("status == 200")
    assert expr.matches(make_entry(status_code=200))
    assert not expr.matches(make_entry(status_code=404))


def test_protocol_equals():
    expr = FilterExpression("protocol == https")
    assert expr.matches(make_entry(protocol="https"))
    assert not expr.matches(make_entry(protocol="http"))


def test_and_logic():
    expr = FilterExpression("host == api.example.com && method == GET")
    assert expr.matches(make_entry(host="api.example.com", method="GET"))
    assert not expr.matches(make_entry(host="api.example.com", method="POST"))
    assert not expr.matches(make_entry(host="other.com", method="GET"))


def test_or_logic():
    expr = FilterExpression("method == GET || method == POST")
    assert expr.matches(make_entry(method="GET"))
    assert expr.matches(make_entry(method="POST"))
    assert not expr.matches(make_entry(method="DELETE"))


def test_not_equals():
    expr = FilterExpression("method != GET")
    assert expr.matches(make_entry(method="POST"))
    assert not expr.matches(make_entry(method="GET"))


def test_regex():
    expr = FilterExpression("path ~ ^/v[0-9]+/")
    assert expr.matches(make_entry(path="/v1/users"))
    assert expr.matches(make_entry(path="/v2/items"))
    assert not expr.matches(make_entry(path="/api/users"))


def test_full_text():
    e = make_entry(host="api.example.com", path="/search")
    e.resp_body = b'{"results": []}'
    expr = FilterExpression("full_text contains results")
    assert expr.matches(e)


def test_invalid_expression_matches_all():
    expr = FilterExpression("!@#$%")
    assert expr.matches(make_entry())
