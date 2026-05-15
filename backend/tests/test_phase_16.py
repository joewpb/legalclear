"""Phase 16 verification — copied verbatim from
phases/source/PHASE_16_small_claims.md.

Requires:
  - Backend (FastAPI) running on http://localhost:8001
  - Run from repo root so frontend/src/data/fl_counties.json resolves
"""
import httpx
import json

BACKEND = "http://localhost:8001"


def test_endpoint_exists():
    r = httpx.post(f"{BACKEND}/api/small-claims/generate", json={
        "claim_type": "Unpaid debt",
        "amount": 1500,
        "defendant_type": "Individual",
        "defendant_name": "John Doe",
        "defendant_address": "123 Main St, Miami FL",
        "county": "Miami-Dade"
    })
    assert r.status_code == 200
    data = r.json()
    assert "forms" in data
    assert len(data["forms"]) >= 2
    assert "filing_fee_usd" in data
    assert "clerk_url" in data


def test_counties_json_complete():
    with open("frontend/src/data/fl_counties.json") as f:
        counties = json.load(f)
    assert len(counties) == 67, f"Expected 67 counties, got {len(counties)}"
    required = {"name", "clerk_url", "fee_tier_1", "fee_tier_2", "fee_tier_3", "fee_tier_4"}
    for c in counties:
        assert required.issubset(c.keys()), f"County missing fields: {c}"


def test_backend_still_on_8001():
    r = httpx.get(f"{BACKEND}/health")
    assert r.status_code == 200


if __name__ == "__main__":
    test_endpoint_exists()
    test_counties_json_complete()
    test_backend_still_on_8001()
    print("PHASE 16 COMPLETE — all checks passed.")
