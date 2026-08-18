"""Unit tests for the XFF/X-Real-IP-aware rate-limit key function — RL-1.

Pure Python — no live server, no LLM, no DB calls.

Run: cd backend && uv run python -m pytest tests/test_limiter_xff.py -v
"""

import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.api.limiter import _client_ip, limiter  # noqa: E402


class _Headers(dict):
    """Case-insensitive .get() shim mimicking starlette's Headers."""

    def get(self, key, default=None):
        return super().get(key.lower(), default)


def _req(headers=None, client_host="10.0.0.5"):
    return SimpleNamespace(
        headers=_Headers({k.lower(): v for k, v in (headers or {}).items()}),
        client=SimpleNamespace(host=client_host),
    )


def test_different_real_ips_behind_same_proxy_get_different_keys():
    req_a = _req({"X-Real-IP": "203.0.113.10"}, client_host="10.0.0.5")
    req_b = _req({"X-Real-IP": "203.0.113.20"}, client_host="10.0.0.5")

    assert _client_ip(req_a) == "203.0.113.10"
    assert _client_ip(req_b) == "203.0.113.20"
    assert _client_ip(req_a) != _client_ip(req_b)


def test_spoofed_xff_ignored_when_real_ip_present():
    req = _req(
        {
            "X-Real-IP": "203.0.113.10",
            "X-Forwarded-For": "6.6.6.6, 1.1.1.1",
        }
    )
    assert _client_ip(req) == "203.0.113.10"


def test_no_real_ip_falls_back_to_leftmost_xff():
    req = _req({"X-Forwarded-For": "198.51.100.7, 10.0.0.1"})
    assert _client_ip(req) == "198.51.100.7"


def test_malformed_xff_falls_through_to_client_host():
    req = _req({"X-Forwarded-For": "not-an-ip, 10.0.0.1"}, client_host="10.0.0.5")
    assert _client_ip(req) == "10.0.0.5"


def test_no_headers_uses_client_host():
    req = _req({}, client_host="192.0.2.9")
    assert _client_ip(req) == "192.0.2.9"


def test_malformed_real_ip_falls_back_to_xff():
    req = _req(
        {"X-Real-IP": "garbage", "X-Forwarded-For": "198.51.100.7, 10.0.0.1"}
    )
    assert _client_ip(req) == "198.51.100.7"


def test_empty_real_ip_header_falls_back():
    req = _req({"X-Real-IP": "", "X-Forwarded-For": "198.51.100.7"})
    assert _client_ip(req) == "198.51.100.7"


def test_whitespace_around_xff_entries():
    req = _req({"X-Forwarded-For": "  198.51.100.7  , 10.0.0.1"})
    assert _client_ip(req) == "198.51.100.7"


def test_ipv6_real_ip_literal():
    req = _req({"X-Real-IP": "2001:db8::1"})
    assert _client_ip(req) == "2001:db8::1"


def test_ipv6_bracketed_with_port_in_xff():
    req = _req({"X-Forwarded-For": "[2001:db8::1]:443"})
    assert _client_ip(req) == "2001:db8::1"


def test_ipv4_with_port_in_xff():
    req = _req({"X-Forwarded-For": "198.51.100.7:8080"})
    assert _client_ip(req) == "198.51.100.7"


def test_limiter_key_func_is_client_ip():
    assert limiter._key_func is _client_ip


def test_existing_decorated_routers_import_cleanly():
    import src.api.routers.property_casualty  # noqa: F401
    import src.api.routers.small_claims  # noqa: F401
    import src.api.routers.wills_trusts  # noqa: F401
