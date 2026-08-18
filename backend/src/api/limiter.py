"""Shared rate limiter for the LegalClear API.

Extracted from routes.py so routers can import the limiter
without depending on the top-level app module.
"""

from __future__ import annotations

import ipaddress

from slowapi import Limiter
from slowapi.util import get_remote_address


def _valid_ip(value: str) -> str | None:
    """Return a normalized IP string if `value` parses as a valid IP, else None."""
    candidate = value.strip()
    if not candidate:
        return None
    # Bracketed IPv6, optionally with a trailing :port -- "[::1]" or "[::1]:8080".
    if candidate.startswith("["):
        closing = candidate.find("]")
        if closing == -1:
            return None
        candidate = candidate[1:closing]
    # Bare IPv4 with a trailing :port -- "1.2.3.4:8080".
    elif candidate.count(":") == 1 and "." in candidate:
        candidate = candidate.rpartition(":")[0] or candidate
    try:
        ipaddress.ip_address(candidate)
    except ValueError:
        return None
    return candidate


def _client_ip(request) -> str:
    """Resolve the client IP for rate-limit bucketing.

    Priority:
    1. X-Real-IP — set by Railway's edge proxy from the actual client
       connection. When present, it is trusted and XFF is ignored entirely,
       since XFF is caller-suppliable and would let a client spoof its way
       into a fresh bucket.
    2. Leftmost entry of X-Forwarded-For — only consulted when X-Real-IP is
       absent (e.g. other proxies, local dev). Never the prod path.
    3. request.client.host — direct connections, unit tests.
    """
    real_ip = request.headers.get("x-real-ip")
    if real_ip is not None:
        parsed = _valid_ip(real_ip)
        if parsed is not None:
            return parsed

    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        leftmost = forwarded_for.split(",")[0]
        parsed = _valid_ip(leftmost)
        if parsed is not None:
            return parsed

    return get_remote_address(request)


limiter: Limiter = Limiter(key_func=_client_ip)
