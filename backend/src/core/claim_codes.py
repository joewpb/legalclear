"""I-2d — anonymous resumable claim codes.

The claim code is a CREDENTIAL, not an identifier: 128-bit urlsafe random
(secrets.token_urlsafe), never sequential, never derivable from claim state.
Only sha256(code) is stored — a database leak reveals nothing usable, and
the code itself is never persisted or logged.
"""

import hashlib
import secrets


def hash_code(code: str) -> str:
    """Return the sha256 hex digest of a claim code."""
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def issue_claim_code() -> tuple[str, str]:
    """Issue a new claim code and its hash.

    Returns (code, code_hash). The caller stores code_hash and returns code
    to the client exactly once — it cannot be recovered from the hash.
    """
    code = secrets.token_urlsafe(16)
    return code, hash_code(code)
