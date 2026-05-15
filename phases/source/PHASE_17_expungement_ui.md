# PHASE 17 — Expungement FL UI + Endpoint
**Status: BUILD. Prerequisite: Phases 15, 16 complete.**

## Universal rules

- **uv only.** No `pip`.
- **Backend port 8001.**
- **Florida jurisdiction only.**
- **Brutalist design tokens** from Phase 15 mandatory.
- **All agent prompts** use `cache_control: ephemeral`.
- **Strip markdown fences** from agent JSON output.
- **No `myflcourtaccess.com` automation.**

## Universal DO-NOT-TOUCH

- Existing agents (especially `expungement.py` from Phase 07 — this phase WRAPS it, does not modify it)
- Stripe paywall
- `.env`, env vars
- Existing FastAPI routes
- No new npm or python packages

## Goal

Structured 5-question eligibility quiz UI wrapping the existing Phase 07 expungement agent. New backend endpoint that takes quiz answers and returns eligibility verdict. Separate form-packet endpoint (scaffold for Phase 23).

References: FL §943.0585 (expungement), §943.059 (sealing), §943.0584 (disqualifying offenses).

## Frontend deliverables

### Create
```
frontend/src/pages/ExpungementFL.tsx
frontend/src/components/expungement/EligibilityQuiz.tsx
frontend/src/components/expungement/ResultDisplay.tsx
frontend/src/data/fl_disqualifying_offenses.json
```

### Modify
- Frontend router: route `/expungement` to `ExpungementFL`.

## Quiz — 5 linear questions

| # | Question | Field type | Options / validation |
|---|---|---|---|
| 1 | What was the case disposition? | Radio | Dismissed / Nolle prossed / Adjudication withheld / Adjudicated guilty / Never charged |
| 2 | What was the charge? | Text + autocomplete | Autocomplete suggestions from `fl_disqualifying_offenses.json` |
| 3 | Have you completed all terms (probation, fees, restitution)? | Radio | Yes / No / N/A |
| 4 | Have you previously sealed or expunged any FL record? | Radio | Yes / No |
| 5 | How long since case closed? | Radio | <1 yr / 1–5 yrs / 5–10 yrs / 10+ yrs |

## `fl_disqualifying_offenses.json`

Minimum entries (per FL §943.0584):
```json
[
  "sexual battery",
  "lewd or lascivious",
  "sexual misconduct",
  "aggravated assault",
  "aggravated battery",
  "aggravated stalking",
  "murder",
  "manslaughter",
  "attempted murder",
  "robbery",
  "carjacking",
  "home invasion",
  "burglary of a dwelling",
  "kidnapping",
  "false imprisonment",
  "arson",
  "terroristic threats",
  "drug trafficking",
  "human trafficking",
  "dui manslaughter"
]
```

## Result page logic

After quiz submission, POST to `/api/expungement/eligibility` and render result card.

| Result status | UI treatment |
|---|---|
| `eligible` | Green border (`var(--success)`), "YOU APPEAR ELIGIBLE", next-steps list, button "Generate my expungement packet" → POST `/api/expungement/generate` |
| `likely_eligible` | Accent border (`var(--accent)`), "YOU MAY BE ELIGIBLE FOR SEALING", explanation, same generate button |
| `not_eligible` | Danger border (`var(--danger)`), "YOU DO NOT APPEAR ELIGIBLE", reason, "Consult a licensed FL attorney" |

## Backend deliverables

### Create `backend/src/api/routes/expungement.py`

```python
from fastapi import APIRouter
from pydantic import BaseModel
import json

router = APIRouter(prefix="/api/expungement")

class EligibilityRequest(BaseModel):
    disposition: str
    charge: str
    completed_terms: str
    previously_sealed: str
    years_since_closed: str

# Load disqualifiers once at module load
with open("frontend/src/data/fl_disqualifying_offenses.json") as f:
    DISQUALIFIERS = [d.lower() for d in json.load(f)]

@router.post("/eligibility")
async def check_eligibility(req: EligibilityRequest):
    # TODO: replace with real Claude-generated output (call Phase 07 expungement agent in v1.1)
    charge_lower = req.charge.lower()

    # Hard disqualifiers per §943.0584
    if any(d in charge_lower for d in DISQUALIFIERS):
        return {
            "status": "not_eligible",
            "reason": f"Charges involving '{req.charge}' are disqualifying under FL §943.0584.",
            "applicable_statute": "FL §943.0584",
            "next_steps": ["Consult a licensed Florida attorney about case-specific options."]
        }

    if req.previously_sealed == "Yes":
        return {
            "status": "not_eligible",
            "reason": "Florida allows only one expungement or sealing per lifetime.",
            "applicable_statute": "FL §943.0585(2)(b)",
            "next_steps": ["No further administrative action is available under FL law.",
                           "Consult an attorney about restoration-of-rights alternatives."]
        }

    if req.disposition == "Adjudicated guilty":
        return {
            "status": "likely_eligible",
            "reason": "Adjudication of guilt generally bars expunction. Sealing may be possible.",
            "applicable_statute": "FL §943.059",
            "next_steps": ["Apply for Certificate of Eligibility (FDLE)",
                           "Confirm sealing-vs-expunction with a licensed FL attorney"]
        }

    return {
        "status": "eligible",
        "reason": "Based on your answers, you appear eligible to apply for expungement.",
        "applicable_statute": "FL §943.0585",
        "next_steps": [
            "Apply for Certificate of Eligibility from FDLE",
            "File petition in court of original jurisdiction",
            "Pay applicable filing fees"
        ]
    }

@router.post("/generate")
async def generate_expungement_packet(req: EligibilityRequest):
    # TODO: replace with real Claude-generated output (Phase 23 wires to PacketBuilder)
    return {
        "forms": [
            {"name": "Application for Certification of Eligibility (FDLE)",
             "url": "https://www.fdle.state.fl.us/Seal-and-Expunge-Process/"},
            {"name": "Petition to Expunge",
             "url": "https://www.flcourts.gov/"}
        ],
        "filing_instructions": "Submit FDLE application first. Once Certificate received, file petition in court of original jurisdiction.",
        "estimated_timeline_months": 6
    }
```

### Register router
```python
from .routes.expungement import router as expungement_router
app.include_router(expungement_router)
```

## Verification — `backend/tests/test_phase_17.py`

```python
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
```

## Pass criteria

- Quiz renders all 5 questions in order
- Disqualifying charge → `not_eligible` with correct statute
- Previously sealed = Yes → `not_eligible` with §943.0585(2)(b)
- Adjudicated guilty → `likely_eligible` with §943.059
- Clean dismissal of non-disqualifying charge → `eligible` with §943.0585
- Generate endpoint returns ≥ 2 forms with FDLE URL
- `# TODO: replace with real Claude-generated output` comments present in new endpoint file
- `test_phase_17.py` exits cleanly

## Failure protocol

If a test fails twice: print `PHASE 17 BLOCKED — [error]` and STOP.

## Final report

```
PHASE 17 COMPLETE — all checks passed.
```

Commit + push. Wait for Railway deploys. Proceed to Phase 18.
