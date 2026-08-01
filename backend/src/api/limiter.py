"""Shared rate limiter for the LegalClear API.

Extracted from routes.py so routers can import the limiter
without depending on the top-level app module.
"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter: Limiter = Limiter(key_func=get_remote_address)
