"""Phase 20 verification — copied verbatim from
phases/source/PHASE_20_traffic.md.

Requires:
  - Backend (FastAPI) running on http://localhost:8001
"""
import httpx
import json
import os


def _data_path():
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(
        os.path.join(
            here, "..", "..", "frontend", "src", "data", "fl_traffic_violations.json"
        )
    )


BACKEND = "http://localhost:8001"


def test_traffic_data_file():
    with open(_data_path()) as f:
        data = json.load(f)
    types = {v["type"] for v in data}
    assert len(types) >= 7, f"Need 7 citation types, got {len(types)}"
    expected = {
        "Speeding",
        "Red light camera",
        "Stop sign / traffic signal violation",
        "Reckless driving",
        "DUI",
        "Equipment / paperwork violation",
        "Other civil infraction",
    }
    assert expected.issubset(types)


def test_contest_endpoint():
    r = httpx.post(f"{BACKEND}/api/traffic/generate", json={
        "citation_type": "Speeding",
        "citation_number": "AB1234567",
        "issue_date": "2026-04-15",
        "county": "Miami-Dade",
        "chosen_path": "contest",
    })
    assert r.status_code == 200
    data = r.json()
    assert data["filing_deadline_days"] == 30
    assert "hearing_preparation_tips" in data
    assert len(data["hearing_preparation_tips"]) >= 3


if __name__ == "__main__":
    test_traffic_data_file()
    test_contest_endpoint()
    print("PHASE 20 COMPLETE — all checks passed.")
