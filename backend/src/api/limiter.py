"""Shared rate limiter for the LegalClear API.

Extracted from routes.py so routers can import the limiter
without depending on the top-level app module.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
