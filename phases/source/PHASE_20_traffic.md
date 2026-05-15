# PHASE 20 — Traffic / Tickets FL Wizard
**Status: BUILD. Prerequisite: Phases 15–19 complete.**

## Universal rules

- **uv only.** No `pip`.
- **Backend port 8001.**
- **Florida jurisdiction only.**
- **Brutalist design tokens** from Phase 15 mandatory.
- **All agent prompts** use `cache_control: ephemeral`.
- **Strip markdown fences** from agent JSON output.
- **No `myflcourtaccess.com` automation.**

## Universal DO-NOT-TOUCH

- Existing agents
- Stripe paywall
- `.env`, env vars
- Existing FastAPI routes
- No new npm or python packages

## Goal

3-step wizard for handling FL traffic citations. Three resolution paths: pay, traffic school, contest. Backend endpoint scaffold for contest path. Real packet generation arrives in Phase 23.

## Frontend deliverables

### Create
```
frontend/src/pages/TrafficFL.tsx
frontend/src/components/traffic/CitationTypeStep.tsx
frontend/src/components/traffic/OptionsStep.tsx
frontend/src/components/traffic/GenerateStep.tsx
frontend/src/data/fl_traffic_violations.json
```

### Modify
- Frontend router: route `/traffic` → `TrafficFL`.

## Steps

### Step 1 — Citation type (radio)
- Speeding
- Red light camera
- Stop sign / traffic signal violation
- Reckless driving
- DUI (informational only — display: "Strongly recommend consulting an attorney"; disable Contest path)
- Equipment / paperwork violation
- Other civil infraction

### Step 2 — Options (depends on Step 1)
Show available paths:
- **Pay** the citation (admit guilt, points apply)
- **Traffic school** (only if civil infraction AND points-bearing AND first offense in 12 months)
- **Contest** (request court hearing)

For DUI selection: only "Contest" disabled; show attorney recommendation prominently.

### Step 3 — Generate (path-dependent)
- **Pay path**: display county clerk payment portal link (from `fl_counties.json` from Phase 16)
- **Traffic school path**: link to `https://www.flhsmv.gov/driver-licenses-id-cards/locations/`
- **Contest path**: POST to `/api/traffic/generate` → render returned letter template + filing instructions

## `fl_traffic_violations.json`

Format:
```json
[
  {
    "type": "Speeding",
    "is_civil_infraction": true,
    "is_criminal": false,
    "points": 4,
    "traffic_school_eligible": true
  },
  {
    "type": "Red light camera",
    "is_civil_infraction": true,
    "is_criminal": false,
    "points": 0,
    "traffic_school_eligible": false
  },
  {
    "type": "Stop sign / traffic signal violation",
    "is_civil_infraction": true,
    "is_criminal": false,
    "points": 4,
    "traffic_school_eligible": true
  },
  {
    "type": "Reckless driving",
    "is_civil_infraction": false,
    "is_criminal": true,
    "points": 4,
    "traffic_school_eligible": false
  },
  {
    "type": "DUI",
    "is_civil_infraction": false,
    "is_criminal": true,
    "points": 0,
    "traffic_school_eligible": false
  },
  {
    "type": "Equipment / paperwork violation",
    "is_civil_infraction": true,
    "is_criminal": false,
    "points": 0,
    "traffic_school_eligible": false
  },
  {
    "type": "Other civil infraction",
    "is_civil_infraction": true,
    "is_criminal": false,
    "points": 3,
    "traffic_school_eligible": true
  }
]
```

Must cover all 7 types.

## Backend deliverables

### Create `backend/src/api/routes/traffic.py`

```python
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/traffic")

class TrafficRequest(BaseModel):
    citation_type: str
    citation_number: str
    issue_date: str
    county: str
    chosen_path: str  # "pay" | "school" | "contest"

@router.post("/generate")
async def gen_traffic(req: TrafficRequest):
    # TODO: replace with real Claude-generated output (Phase 23 wires to PacketBuilder)
    return {
        "document_name": "Request for Court Hearing",
        "document_url": None,
        "filing_deadline_days": 30,
        "filing_location": f"{req.county} County Clerk of Courts",
        "hearing_preparation_tips": [
            "Request the officer's notes via discovery",
            "Photograph the location of the alleged violation",
            "Subpoena any witnesses if applicable",
            "Bring a copy of your driving record"
        ]
    }
```

### Register router
```python
from .routes.traffic import router as traffic_router
app.include_router(traffic_router)
```

## Verification — `backend/tests/test_phase_20.py`

```python
import httpx
import json

BACKEND = "http://localhost:8001"

def test_traffic_data_file():
    with open("frontend/src/data/fl_traffic_violations.json") as f:
        data = json.load(f)
    types = {v["type"] for v in data}
    assert len(types) >= 7, f"Need 7 citation types, got {len(types)}"
    expected = {"Speeding", "Red light camera", "Stop sign / traffic signal violation",
                "Reckless driving", "DUI", "Equipment / paperwork violation",
                "Other civil infraction"}
    assert expected.issubset(types)

def test_contest_endpoint():
    r = httpx.post(f"{BACKEND}/api/traffic/generate", json={
        "citation_type": "Speeding",
        "citation_number": "AB1234567",
        "issue_date": "2026-04-15",
        "county": "Miami-Dade",
        "chosen_path": "contest"
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
```

## Pass criteria

- All 7 citation types in `fl_traffic_violations.json`
- 3-step wizard renders correctly
- DUI selection shows attorney recommendation and disables Contest
- Pay path links to clerk URL (from Phase 16 `fl_counties.json`)
- Traffic school path links to FLHSMV
- Contest endpoint returns 30-day deadline + ≥3 prep tips
- Endpoint marked with `# TODO: replace with real Claude-generated output`
- `test_phase_20.py` exits cleanly

## Failure protocol

If a test fails twice: print `PHASE 20 BLOCKED — [error]` and STOP.

## Final report

```
PHASE 20 COMPLETE — all checks passed.
```

Commit + push. Wait for Railway deploys. Proceed to Phase 21.
