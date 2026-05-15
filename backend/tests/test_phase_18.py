"""Phase 18 verification — adapted for the Phase 23 PacketBuilder contract.

Phase 18 originally asserted the FL statute reference (§83.49 / §83.56(1) /
§83.60) in the scaffold JSON. Phase 23 replaces those scaffold responses
with the canonical {packet_id, fee_usd, file_count, checkout_url} shape;
the statute references now live in the rendered PDF cover sheets (via
instructions_*.json), where they remain the single source of truth.

Requires:
  - Backend (FastAPI) running on http://localhost:8001
  - STRIPE_SECRET_KEY env var set (Stripe test mode is fine)
"""
import json
from pathlib import Path

import httpx

BACKEND = "http://localhost:8001"


def _assert_packet_shape(r: httpx.Response) -> dict:
    assert r.status_code == 200, r.text
    d = r.json()
    for key in ("packet_id", "fee_usd", "file_count", "checkout_url"):
        assert key in d, f"missing {key} in {d}"
    assert d["checkout_url"].startswith("https://checkout.stripe.com")
    return d


def test_deposit_endpoint():
    r = httpx.post(
        f"{BACKEND}/api/landlord/deposit/generate",
        json={
            "move_out_date": "2026-03-01",
            "deposit_amount": 1500,
            "current_address": "123 New St",
            "landlord_name": "Acme LLC",
            "landlord_address": "456 Old Ave",
            "county": "Miami-Dade",
            "language": "en",
        },
        timeout=60.0,
    )
    _assert_packet_shape(r)


def test_repairs_endpoint():
    r = httpx.post(
        f"{BACKEND}/api/landlord/repairs/generate",
        json={
            "property_address": "789 Rent Rd",
            "issue_type": "AC",
            "issue_description": "AC out 2 weeks",
            "prior_communication": "Email March 1",
            "tenant_intent": "withhold rent",
            "county": "Miami-Dade",
            "language": "en",
        },
        timeout=60.0,
    )
    _assert_packet_shape(r)


def test_eviction_endpoint():
    r = httpx.post(
        f"{BACKEND}/api/landlord/eviction/generate",
        json={
            "eviction_type": "nonpayment",
            "notice_type": "3-day",
            "notice_date": "2026-04-01",
            "defenses": ["paid rent", "retaliation"],
            "county": "Miami-Dade",
            "language": "en",
        },
        timeout=60.0,
    )
    _assert_packet_shape(r)


def test_statute_references_in_instructions():
    """Phase 18 invariant: the FL statute citations live in the rendered
    PDFs via instructions_en.json. Verify the three required statutes are
    present in the instruction copy that drives the packets."""
    inst = json.load(
        open(Path("backend/src/data/instructions_en.json"))
    )
    deposit_text = json.dumps(inst["landlord_deposit"])
    repairs_text = json.dumps(inst["landlord_repairs"])
    eviction_text = json.dumps(inst["landlord_eviction"])
    assert "83.49" in deposit_text
    assert "83.56" in repairs_text
    assert "83.60" in eviction_text


if __name__ == "__main__":
    test_deposit_endpoint()
    test_repairs_endpoint()
    test_eviction_endpoint()
    test_statute_references_in_instructions()
    print("PHASE 18 COMPLETE — all checks passed.")
