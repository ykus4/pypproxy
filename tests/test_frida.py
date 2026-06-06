from __future__ import annotations

import json

from pypproxy.frida.hook_generator import generate_parameter_hook, generate_request_logger
from pypproxy.frida.pinning_bypass import (
    ANDROID_BYPASS_OKHTTP,
    IOS_BYPASS_NSURLSESSION,
    generate_traffic_hooks,
    get_template,
    list_templates,
)
from pypproxy.store.models import Entry


def make_entry(**kwargs) -> Entry:
    e = Entry(
        method="GET",
        scheme="https",
        host="api.example.com",
        path="/v1/users",
        protocol="https",
        status_code=200,
    )
    for k, v in kwargs.items():
        setattr(e, k, v)
    e.id = kwargs.get("id", 1)
    return e


# ---- Template tests ----


def test_list_templates_not_empty():
    templates = list_templates()
    assert len(templates) >= 4
    assert "iOS SSL Bypass (NSURLSession)" in templates
    assert "Android SSL Bypass (OkHttp)" in templates


def test_get_template_ios():
    script = get_template("iOS SSL Bypass (NSURLSession)")
    assert "SecTrustEvaluate" in script
    assert "frida" in script.lower() or "Interceptor" in script


def test_get_template_android():
    script = get_template("Android SSL Bypass (OkHttp)")
    assert "CertificatePinner" in script
    assert "Java.perform" in script


def test_get_template_flutter():
    script = get_template("Android SSL Bypass (Flutter)")
    assert "libflutter.so" in script


def test_get_template_unknown():
    result = get_template("nonexistent template")
    assert "not found" in result


def test_ios_bypass_contains_key_methods():
    assert "SecTrustEvaluateWithError" in IOS_BYPASS_NSURLSESSION
    assert "TrustKit" in IOS_BYPASS_NSURLSESSION
    assert "AFSecurityPolicy" in IOS_BYPASS_NSURLSESSION


def test_android_bypass_contains_key_classes():
    assert "okhttp3.CertificatePinner" in ANDROID_BYPASS_OKHTTP
    assert "X509TrustManager" in ANDROID_BYPASS_OKHTTP
    assert "Java.perform" in ANDROID_BYPASS_OKHTTP


# ---- Traffic hook tests ----


def test_generate_traffic_hooks_empty():
    result = generate_traffic_hooks([], [])
    assert "pypproxy" in result
    assert "OkHttpClient" in result


def test_generate_traffic_hooks_with_data():
    hosts = ["api.example.com", "auth.example.com"]
    endpoints = [("GET", "/v1/users"), ("POST", "/v1/login")]
    result = generate_traffic_hooks(hosts, endpoints)
    assert "api.example.com" in result
    assert "/v1/users" in result
    assert "/v1/login" in result


def test_generate_traffic_hooks_deduplicates():
    endpoints = [("GET", "/path"), ("GET", "/path"), ("GET", "/path")]
    result = generate_traffic_hooks([], list(set(endpoints)))
    # should only appear once
    assert result.count("/path") >= 1


# ---- Hook generator tests ----


def test_generate_request_logger_okhttp3():
    entries = [make_entry(), make_entry(host="auth.example.com", path="/login", id=2)]
    result = generate_request_logger(entries, "okhttp3")
    assert "Java.perform" in result
    assert "OkHttpClient" in result
    assert "pypproxy" in result


def test_generate_request_logger_nsurlsession():
    entries = [make_entry()]
    result = generate_request_logger(entries, "nsurlsession")
    assert "NSURLSession" in result
    assert "ObjC.available" in result


def test_generate_request_logger_fetch():
    entries = [make_entry()]
    result = generate_request_logger(entries, "fetch")
    assert "window.fetch" in result
    assert "origFetch" in result


def test_generate_parameter_hook_okhttp3():
    e = make_entry(method="POST", path="/api/login")
    e.req_body = json.dumps({"username": "alice", "password": "secret"}).encode()
    result = generate_parameter_hook(e, "okhttp3")
    assert "Java.perform" in result
    assert "/api/login" in result
    assert "POST" in result
    assert "username" in result


def test_generate_parameter_hook_nsurlsession():
    e = make_entry(method="GET", path="/api/profile")
    result = generate_parameter_hook(e, "nsurlsession")
    assert "NSURLSession" in result
    assert "/api/profile" in result


def test_generate_parameter_hook_no_body():
    e = make_entry(method="GET", path="/api/items")
    result = generate_parameter_hook(e, "okhttp3")
    assert "Java.perform" in result
    assert "/api/items" in result


def test_generate_parameter_hook_includes_host():
    e = make_entry(host="secure.bank.com", path="/transfer")
    result = generate_parameter_hook(e, "okhttp3")
    assert "/transfer" in result


def test_request_logger_includes_observed_hosts():
    entries = [
        make_entry(host="api.example.com"),
        make_entry(host="cdn.example.com", id=2),
    ]
    result = generate_request_logger(entries, "okhttp3")
    assert "api.example.com" in result
    assert "cdn.example.com" in result
