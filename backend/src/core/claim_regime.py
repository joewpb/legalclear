"""I-2c — policy_inception_date -> claims regime. Pure function, no IO.

Cutoff is 2022-12-16 (SB 2-A). Per the playbook §0, the reform applies to
policies issued ON OR AFTER 2022-12-16 — so the boundary date itself
resolves to "post". A ``None`` inception date is "unknown": this module
never defaults an unknown date to either regime. Unknown must escalate,
never guess (see dispatch I-2c).
"""

from __future__ import annotations

from datetime import date
from typing import Literal

CLAIM_REGIME_CUTOFF = date(2022, 12, 16)

ClaimRegime = Literal["pre", "post", "unknown"]


def resolve_regime(policy_inception_date: date | None) -> ClaimRegime:
    """Return "pre", "post", or "unknown" for a policy inception date.

    "unknown" is returned only for ``None`` — never inferred or defaulted.
    """
    if policy_inception_date is None:
        return "unknown"
    if policy_inception_date >= CLAIM_REGIME_CUTOFF:
        return "post"
    return "pre"
