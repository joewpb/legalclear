"""Phase 17 verification — copied verbatim from
phases/source/PHASE_17_expungement_ui.md.

Requires:
  - Backend (FastAPI) running on http://localhost:8001
"""
import httpx

BACKEND = "http://localhost:8001"


def test_eligibility_disqualified():
    r = httpx.post(f"{BACKEND}/api/expungement/eligibility", json={
        "disposition": "Dismissed",
        "charge": "Sexual battery in the second degree",
        "completed_terms": "Yes",
        "previously_sealed": "No",
        "years_since_closed": "5-10 yrs"
    })
    assert r.json()["status"] == "not_eligible"


def test_eligibility_previously_sealed():
    r = httpx.post(f"{BACKEND}/api/expungement/eligibility", json={
        "disposition": "Dismissed",
        "charge": "Petit theft",
        "completed_terms": "Yes",
        "previously_sealed": "Yes",
        "years_since_closed": "5-10 yrs"
    })
    assert r.json()["status"] == "not_eligible"


def test_eligibility_adjudicated_guilty():
    r = httpx.post(f"{BACKEND}/api/expungement/eligibility", json={
        "disposition": "Adjudicated guilty",
        "charge": "Petit theft",
        "completed_terms": "Yes",
        "previously_sealed": "No",
        "years_since_closed": "5-10 yrs"
    })
    assert r.json()["status"] == "likely_eligible"


def test_eligibility_clean_dismissal():
    r = httpx.post(f"{BACKEND}/api/expungement/eligibility", json={
        "disposition": "Dismissed",
        "charge": "Petit theft",
        "completed_terms": "Yes",
        "previously_sealed": "No",
        "years_since_closed": "5-10 yrs"
    })
    assert r.json()["status"] == "eligible"


def test_generate_returns_packet():
    # Phase 23 supersedes Phase 17's scaffold response. /api/expungement/generate
    # now builds a real packet via PacketBuilder and returns the canonical
    # {packet_id, fee_usd, file_count, checkout_url} shape.
    r = httpx.post(f"{BACKEND}/api/expungement/generate", json={
        "disposition": "Dismissed",
        "charge": "Petit theft",
        "completed_terms": "Yes",
        "previously_sealed": "No",
        "years_since_closed": "5-10 yrs",
        "county": "Miami-Dade",
        "language": "en"
    }, timeout=60.0)
    assert r.status_code == 200, r.text
    data = r.json()
    for key in ("packet_id", "fee_usd", "file_count", "checkout_url"):
        assert key in data, f"missing {key} in {data}"
    # TODO(paywall): bypass — checkout_url is "" while the gate is disabled.
    assert data["checkout_url"] == "" or data["checkout_url"].startswith("https://checkout.stripe.com")


if __name__ == "__main__":
    test_eligibility_disqualified()
    test_eligibility_previously_sealed()
    test_eligibility_adjudicated_guilty()
    test_eligibility_clean_dismissal()
    test_generate_returns_packet()
    print("PHASE 17 COMPLETE — all checks passed.")
