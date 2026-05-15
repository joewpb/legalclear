# PHASE 18 — Landlord / Tenant FL (3 Sub-Flows)
**Status: BUILD. Prerequisite: Phases 15, 16, 17 complete.**

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

Three landlord/tenant sub-flows for FL renters:
- **Deposit recovery** (FL §83.49)
- **Repair issues** (FL §83.56)
- **Eviction defense** (FL §83.60)

Each sub-flow is a 3-step wizard. Backend returns the right document name + statute reference per flow. Real packet generation arrives in Phase 23.

## Frontend deliverables

### Create
```
frontend/src/pages/LandlordTenantFL.tsx              # Landing — picks sub-flow
frontend/src/components/landlord/DepositFlow.tsx
frontend/src/components/landlord/RepairsFlow.tsx
frontend/src/components/landlord/EvictionFlow.tsx
```

### Modify
- Frontend router: route `/landlord` → `LandlordTenantFL`; sub-routes `/landlord/deposit`, `/landlord/repairs`, `/landlord/eviction`.

## Landing page

3 large tiles (Brutalist style, same component as HubTile):
- DEPOSIT NOT RETURNED → `/landlord/deposit`
- REPAIRS NOT MADE → `/landlord/repairs`
- EVICTION DEFENSE → `/landlord/eviction`

## Sub-flow A — Deposit (`/landlord/deposit`)

3 steps:

| Step | Content |
|---|---|
| 1 | Move-out date · Deposit amount · Current forwarding address |
| 2 | Landlord name · Landlord address |
| 3 | Reason landlord gave (if any) · Tenant response · Generate button |

Generates: §83.49 demand letter. Statute reference shown in result: "FL §83.49 (15-day landlord-response window if claim was made; 30-day landlord-notice window applies)."

## Sub-flow B — Repairs (`/landlord/repairs`)

3 steps:

| Step | Content |
|---|---|
| 1 | Property address · Issue type (Heat/AC/Water/Mold/Electrical/Structural/Other) · Issue description |
| 2 | Prior communication with landlord (dates + methods) |
| 3 | Tenant intent (Withhold rent / Terminate lease / Repair-and-deduct) · Generate button |

Generates: 7-day notice per §83.56(1). Result statute: "FL §83.56(1) — landlord has 7 days to cure; after 7 days, tenant may withhold rent or terminate."

## Sub-flow C — Eviction defense (`/landlord/eviction`)

3 steps:

| Step | Content |
|---|---|
| 1 | Eviction type (Nonpayment / Nonrenewal / Cause) |
| 2 | Notice received type (3-day / 7-day / 15-day) · Notice date |
| 3 | Defenses checklist (Paid rent / Retaliation / Withholding for repairs / Improper notice / Other) · Generate button |

Generates: Answer to Eviction Complaint. Result statute: "FL §83.60 — 5 business days to file answer; disputed rent must be deposited with the court registry."

## Backend deliverables

### Create `backend/src/api/routes/landlord.py`

```python
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/landlord")

class DepositRequest(BaseModel):
    move_out_date: str
    deposit_amount: float
    current_address: str
    landlord_name: str
    landlord_address: str
    reason_given: str | None = None
    tenant_response: str | None = None

class RepairsRequest(BaseModel):
    property_address: str
    issue_type: str
    issue_description: str
    prior_communication: str
    tenant_intent: str

class EvictionRequest(BaseModel):
    eviction_type: str
    notice_type: str
    notice_date: str
    defenses: list[str]

@router.post("/deposit/generate")
async def gen_deposit(req: DepositRequest):
    # TODO: replace with real Claude-generated output (Phase 23 wires to PacketBuilder)
    return {
        "document_name": "Demand for Return of Security Deposit",
        "document_url": None,
        "delivery_instructions": "Send via certified mail with return receipt. Keep a copy.",
        "applicable_statute": "FL §83.49",
        "deadlines": [
            "Landlord has 15 days from receipt to respond if claim was made",
            "30-day landlord-notice window may have already elapsed"
        ]
    }

@router.post("/repairs/generate")
async def gen_repairs(req: RepairsRequest):
    # TODO: replace with real Claude-generated output (Phase 23 wires to PacketBuilder)
    return {
        "document_name": "7-Day Notice of Noncompliance with Opportunity to Cure",
        "document_url": None,
        "delivery_instructions": "Send via certified mail. Wait 7 days before further action.",
        "applicable_statute": "FL §83.56(1)",
        "deadlines": [
            "Landlord has 7 days to cure",
            "After 7 days, tenant may withhold rent or terminate"
        ]
    }

@router.post("/eviction/generate")
async def gen_eviction(req: EvictionRequest):
    # TODO: replace with real Claude-generated output (Phase 23 wires to PacketBuilder)
    return {
        "document_name": "Answer to Eviction Complaint",
        "document_url": None,
        "delivery_instructions": "File with the court within 5 business days of being served. Pay any disputed rent into the court registry.",
        "applicable_statute": "FL §83.60",
        "deadlines": [
            "5 business days from service to file answer",
            "Disputed rent must be deposited with court registry"
        ]
    }
```

### Register router
```python
from .routes.landlord import router as landlord_router
app.include_router(landlord_router)
```

## Verification — `backend/tests/test_phase_18.py`

```python
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
```

## Pass criteria

- 3 sub-flow landing tiles render and route correctly
- Each sub-flow has 3 steps with working back/next
- Each generate endpoint returns the correct statute reference
- All 3 endpoints marked with `# TODO: replace with real Claude-generated output`
- `test_phase_18.py` exits cleanly

## Failure protocol

If a test fails twice: print `PHASE 18 BLOCKED — [error]` and STOP.

## Final report

```
PHASE 18 COMPLETE — all checks passed.
```

Commit + push. Wait for Railway deploys. Proceed to Phase 19.
