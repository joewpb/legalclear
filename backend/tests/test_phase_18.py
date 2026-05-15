"""Phase 18 verification — copied verbatim from
phases/source/PHASE_18_landlord_tenant.md.

Requires:
  - Backend (FastAPI) running on http://localhost:8001
"""
import httpx

BACKEND = "http://localhost:8001"


def test_deposit_endpoint():
    r = httpx.post(f"{BACKEND}/api/landlord/deposit/generate", json={
        "move_out_date": "2026-03-01",
        "deposit_amount": 1500,
        "current_address": "123 New St",
        "landlord_name": "Acme LLC",
        "landlord_address": "456 Old Ave"
    })
    assert r.status_code == 200
    assert "§83.49" in r.json()["applicable_statute"]


def test_repairs_endpoint():
    r = httpx.post(f"{BACKEND}/api/landlord/repairs/generate", json={
        "property_address": "789 Rent Rd",
        "issue_type": "AC",
        "issue_description": "AC out 2 weeks",
        "prior_communication": "Email March 1",
        "tenant_intent": "withhold rent"
    })
    assert r.status_code == 200
    assert "§83.56" in r.json()["applicable_statute"]


def test_eviction_endpoint():
    r = httpx.post(f"{BACKEND}/api/landlord/eviction/generate", json={
        "eviction_type": "nonpayment",
        "notice_type": "3-day",
        "notice_date": "2026-04-01",
        "defenses": ["paid rent", "retaliation"]
    })
    assert r.status_code == 200
    assert "§83.60" in r.json()["applicable_statute"]


if __name__ == "__main__":
    test_deposit_endpoint()
    test_repairs_endpoint()
    test_eviction_endpoint()
    print("PHASE 18 COMPLETE — all checks passed.")
