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


def test_generate_returns_forms():
    r = httpx.post(f"{BACKEND}/api/expungement/generate", json={
        "disposition": "Dismissed",
        "charge": "Petit theft",
        "completed_terms": "Yes",
        "previously_sealed": "No",
        "years_since_closed": "5-10 yrs"
    })
    assert "forms" in r.json()
    assert len(r.json()["forms"]) >= 2


if __name__ == "__main__":
    test_eligibility_disqualified()
    test_eligibility_previously_sealed()
    test_eligibility_adjudicated_guilty()
    test_eligibility_clean_dismissal()
    test_generate_returns_forms()
    print("PHASE 17 COMPLETE — all checks passed.")
