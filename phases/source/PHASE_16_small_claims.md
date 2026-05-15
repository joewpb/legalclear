# PHASE 16 — Small Claims FL Wizard
**Status: BUILD. Prerequisite: Phase 15 complete.**

## Universal rules

- **uv only.** No `pip`.
- **Backend port 8001.**
- **Florida jurisdiction only.**
- **Brutalist design tokens** from Phase 15 are mandatory.
- **All agent prompts** use `cache_control: ephemeral`.
- **Strip markdown fences** from agent JSON output.
- **No `myflcourtaccess.com` automation.**

## Universal DO-NOT-TOUCH

- Existing agents and Stripe paywall
- `.env`, env vars
- Existing FastAPI routes
- No new npm or python packages

## Goal

5-step wizard for filing FL small claims (≤$8,000). Backend endpoint returns scaffold form packet (real packet generation arrives in Phase 23). All 67 FL counties supported.

## Frontend deliverables

### Create
```
frontend/src/pages/SmallClaimsFL.tsx
frontend/src/components/smallclaims/WizardContext.tsx
frontend/src/components/smallclaims/ProgressBar.tsx
frontend/src/components/smallclaims/ClaimTypeStep.tsx
frontend/src/components/smallclaims/AmountStep.tsx
frontend/src/components/smallclaims/DefendantStep.tsx
frontend/src/components/smallclaims/CountyStep.tsx
frontend/src/components/smallclaims/ReviewStep.tsx
frontend/src/data/fl_counties.json
```

### Modify
- Frontend router: route `/small-claims` to `SmallClaimsFL`. Sub-routes `/small-claims/1` through `/small-claims/5` optional — single-page state machine works too.

## Wizard steps

| Step | Content | Validation |
|---|---|---|
| 1 | Radio: claim type — Unpaid debt / Property damage / Security deposit / Breach of contract / Minor personal injury / Other | Required |
| 2 | Numeric input: amount claimed (USD) | `0 < amount ≤ 8000`; if over, block with the message below |
| 3 | Defendant: type (Individual/Business/Both), name, address, optional phone/email | Name + address required |
| 4 | County (searchable select, all 67) | Required |
| 5 | Read-only review + "GENERATE MY FORM PACKET" button | POST to `/api/small-claims/generate` |

### Amount over-limit message
> "This exceeds Florida's small claims limit of $8,000. You'll need to file in County Civil Court instead."
Block "Next" until amount is valid.

### Progress bar
Top of each step: "STEP X OF 5" in mono uppercase, with a 5-segment bar showing completion.

## `fl_counties.json` — all 67 FL counties

Format:
```json
[
  {
    "name": "Miami-Dade",
    "clerk_url": "https://www.miamidade.gov/clerk",
    "fee_tier_1": 55,
    "fee_tier_2": 80,
    "fee_tier_3": 175,
    "fee_tier_4": 300
  }
]
```

Fee tier mapping by claim amount:
- Tier 1: ≤ $100 → $55
- Tier 2: $101–500 → $80
- Tier 3: $501–2,500 → $175
- Tier 4: $2,501–8,000 → $300

If a county-specific clerk URL can't be verified, fallback to `https://www.flclerks.com/`. **Do NOT fabricate URLs.**

## Backend deliverables

### Create `backend/src/api/routes/small_claims.py`

```python
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/small-claims")

class SmallClaimsRequest(BaseModel):
    claim_type: str
    amount: float
    defendant_type: str
    defendant_name: str
    defendant_address: str
    defendant_phone: str | None = None
    defendant_email: str | None = None
    county: str

@router.post("/generate")
async def generate_small_claims(req: SmallClaimsRequest):
    # TODO: replace with real Claude-generated output (Phase 23 wires to PacketBuilder)
    return {
        "forms": [
            {"name": "Statement of Claim (Form 7.301)", "url": "https://www.flcourts.gov/content/download/218019/file/7.301.pdf"},
            {"name": "Summons (Form 7.321)", "url": "https://www.flcourts.gov/content/download/218020/file/7.321.pdf"}
        ],
        "filing_instructions": f"File at {req.county} County Clerk of Courts.",
        "filing_fee_usd": 175,
        "clerk_url": "https://www.flclerks.com/",
        "service_of_process_options": ["Sheriff", "Certified Mail", "Private Process Server"]
    }
```

### Register router
In `backend/src/api/main.py`:
```python
from .routes.small_claims import router as small_claims_router
app.include_router(small_claims_router)
```

Backend stays on **port 8001**.

## Verification — `backend/tests/test_phase_16.py`

```python
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
```

## Pass criteria

- Wizard renders 5 steps with working back/next
- Amount > $8,000 blocked with correct message
- All 67 FL counties loadable in selector
- `/api/small-claims/generate` returns scaffold response with all required fields
- `# TODO: replace with real Claude-generated output` comment present in the new endpoint file
- Backend still on port 8001
- `test_phase_16.py` exits cleanly

## Failure protocol

If a test fails twice: print `PHASE 16 BLOCKED — [error]` and STOP.

## Final report

After all checks pass:
```
PHASE 16 COMPLETE — all checks passed.
```

Commit + push. Wait for Railway deploys. Proceed to Phase 17.
