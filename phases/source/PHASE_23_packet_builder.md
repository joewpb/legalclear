# PHASE 23 — Mode A Filing Pipeline (PacketBuilder + EN/ES + Stripe Gates)
**Status: BUILD. Final phase. Prerequisite: Phases 15–22 complete.**

## Universal rules

- **uv only.** No `pip`.
- **Backend port 8001.**
- **Florida jurisdiction only.**
- **Brutalist design tokens** from Phase 15 mandatory.
- **All agent prompts** use `cache_control: ephemeral`.
- **Strip markdown fences** from agent JSON output.

## Critical phase-specific rule

**No automation against `myflcourtaccess.com`.** This phase has a hard test (`test_no_mode_b`) that scans every Python file in `backend/src/` for the string `myflcourtaccess`. Any non-commented match fails the build. The walkthrough TEXT may reference the URL — but no Python code may navigate to it via Playwright or any HTTP client.

## Universal DO-NOT-TOUCH

- Existing agents (classifier, explainer, form_guide, risk_scanner, expungement, scanner from Phase 21)
- Stripe paywall **internals** — this phase ATTACHES a new product via existing patterns
- `.env`, env vars (Stripe keys already exist from Phase 09)
- Existing FastAPI routes (this phase MODIFIES tile-generate routes from Phases 16/17/18/20, but only to swap their response from scaffold JSON to PacketBuilder output)
- Phase 11's `florida_courts.py` — leave it alone; this phase supersedes it but doesn't delete it

## Goal

Replace scaffold responses from tile-generate endpoints (Phases 16, 17, 18, 20) with **real packet generation**:

- Unified `PacketBuilder` service
- PDF/A-1b output via Playwright print-to-PDF + pikepdf metadata post-processing
- Bilingual templates (EN / ES)
- $35 Stripe pay-per-packet, download gated by payment
- Manual upload walkthrough for myflcourtaccess.com (TEXT ONLY — no automation)
- Filing tracker — user enters confirmation number after manual submission

## New dependencies

```bash
cd backend && uv add pikepdf jinja2
```

Playwright is already installed from earlier phases. Verify:
```bash
uv pip list | grep playwright
```

No new npm dependencies.

## Backend file structure (new)

```
backend/src/services/
├── packet_builder.py
├── pdfa_generator.py
├── county_router.py
└── translation_layer.py

backend/src/api/routes/packet.py

backend/src/templates/
├── cover_sheets/
│   ├── small_claims_en.html
│   ├── small_claims_es.html
│   ├── expungement_en.html
│   ├── expungement_es.html
│   ├── landlord_deposit_en.html
│   ├── landlord_deposit_es.html
│   ├── landlord_repairs_en.html
│   ├── landlord_repairs_es.html
│   ├── landlord_eviction_en.html
│   ├── landlord_eviction_es.html
│   ├── traffic_en.html
│   ├── traffic_es.html
│   └── _form_fields_summary.html
└── walkthroughs/
    ├── manual_upload_en.html
    └── manual_upload_es.html

backend/src/data/
├── fl_county_clerk_details.json
├── instructions_en.json
├── instructions_es.json
├── walkthrough_steps_en.json
└── walkthrough_steps_es.json

backend/storage/packets/    # Generated ZIPs land here at runtime
```

## `packet_builder.py`

```python
"""Unified packet builder. Called by every tile's /generate endpoint."""
import uuid
import zipfile
from pathlib import Path
from typing import Literal
from pydantic import BaseModel

from .pdfa_generator import render_html_to_pdfa
from .county_router import get_county_details, get_filing_fee
from .translation_layer import get_template_path, get_instructions
from ..memory.db import get_db

PacketType = Literal[
    "small_claims", "expungement",
    "landlord_deposit", "landlord_repairs", "landlord_eviction",
    "traffic"
]
Language = Literal["en", "es"]

class PacketRequest(BaseModel):
    packet_type: PacketType
    language: Language
    county: str
    user_id: str
    tile_data: dict

class PacketResult(BaseModel):
    packet_id: str
    fee_usd: float
    file_count: int
    zip_path: str
    paid: bool = False

async def build_packet(req: PacketRequest) -> PacketResult:
    packet_id = str(uuid.uuid4())
    packet_dir = Path(f"backend/storage/packets/{packet_id}")
    packet_dir.mkdir(parents=True, exist_ok=True)

    county_info = get_county_details(req.county)
    fee = get_filing_fee(req.county, req.packet_type, req.tile_data)
    instructions = get_instructions(req.packet_type, req.language, req.county)

    template_path = get_template_path(req.packet_type, req.language)
    ctx = {
        **req.tile_data,
        "county": county_info,
        "instructions": instructions,
        "fee_usd": fee,
        "packet_id": packet_id,
    }

    cover = packet_dir / "01_cover_sheet.pdf"
    await render_html_to_pdfa(template_path, ctx, cover)

    walkthrough_template = f"walkthroughs/manual_upload_{req.language}.html"
    walkthrough = packet_dir / "02_how_to_file.pdf"
    await render_html_to_pdfa(walkthrough_template, ctx, walkthrough)

    summary = packet_dir / "03_form_fields_summary.pdf"
    await render_html_to_pdfa("cover_sheets/_form_fields_summary.html", ctx, summary)

    zip_path = packet_dir / f"legalclear_packet_{packet_id}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in [cover, walkthrough, summary]:
            zf.write(f, arcname=f.name)

    db = get_db()
    await db.execute(
        """INSERT INTO packets (id, user_id, packet_type, language, county,
           fee_usd, zip_path, status, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'pending_payment', datetime('now'))""",
        (packet_id, req.user_id, req.packet_type, req.language,
         req.county, fee, str(zip_path))
    )

    return PacketResult(
        packet_id=packet_id,
        fee_usd=fee,
        file_count=3,
        zip_path=str(zip_path),
        paid=False,
    )
```

## `pdfa_generator.py`

```python
"""HTML → Playwright PDF → pikepdf PDF/A-1b metadata."""
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from playwright.async_api import async_playwright
import pikepdf

env = Environment(loader=FileSystemLoader("backend/src/templates"))

async def render_html_to_pdfa(template_relative_path: str, context: dict, output_path: Path) -> Path:
    template = env.get_template(template_relative_path)
    html = template.render(**context)

    temp_pdf = output_path.with_suffix(".tmp.pdf")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_content(html, wait_until="networkidle")
        await page.pdf(
            path=str(temp_pdf),
            format="Letter",
            margin={"top": "0.75in", "bottom": "0.75in", "left": "0.75in", "right": "0.75in"},
            print_background=True,
        )
        await browser.close()

    with pikepdf.open(temp_pdf) as pdf:
        with pdf.open_metadata() as meta:
            meta["pdf:Producer"] = "LegalClear Filing Packet Generator"
            meta["pdfaid:part"] = "1"
            meta["pdfaid:conformance"] = "B"
            meta["dc:title"] = context.get("packet_id", "LegalClear Filing Packet")
        pdf.save(str(output_path), linearize=True)

    temp_pdf.unlink(missing_ok=True)
    return output_path
```

## `county_router.py`

```python
"""County-specific clerk info, fees, local rules."""
import json
from functools import lru_cache

@lru_cache(maxsize=1)
def _load_counties():
    with open("backend/src/data/fl_county_clerk_details.json") as f:
        return {c["name"]: c for c in json.load(f)}

def get_county_details(county_name: str) -> dict:
    counties = _load_counties()
    if county_name not in counties:
        return {
            "name": county_name,
            "clerk_url": "https://www.flclerks.com/",
            "clerk_address": "",
            "clerk_phone": "",
            "fee_tier_1": 55, "fee_tier_2": 80,
            "fee_tier_3": 175, "fee_tier_4": 300,
        }
    return counties[county_name]

def get_filing_fee(county: str, packet_type: str, tile_data: dict) -> float:
    c = get_county_details(county)
    if packet_type == "small_claims":
        a = float(tile_data.get("amount", 0))
        if a <= 100: return c["fee_tier_1"]
        if a <= 500: return c["fee_tier_2"]
        if a <= 2500: return c["fee_tier_3"]
        return c["fee_tier_4"]
    if packet_type == "expungement": return 75.0
    if packet_type.startswith("landlord_"): return 401.0
    if packet_type == "traffic": return 90.0
    return 100.0
```

## `translation_layer.py`

```python
"""EN/ES template lookup. Pre-translated, no live LLM translation."""
import json
from functools import lru_cache

@lru_cache(maxsize=2)
def _load_instructions(language: str):
    with open(f"backend/src/data/instructions_{language}.json") as f:
        return json.load(f)

def get_template_path(packet_type: str, language: str) -> str:
    return f"cover_sheets/{packet_type}_{language}.html"

def get_instructions(packet_type: str, language: str, county: str) -> dict:
    inst = _load_instructions(language)
    base = inst.get(packet_type, {})
    overrides = base.get("county_overrides", {}).get(county, {})
    return {**base, **overrides}
```

## `/api/packet/*` routes

```python
"""Packet endpoints — build, fetch, gated download, tracking."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
import stripe
import os

from ..services.packet_builder import build_packet, PacketRequest
from ...memory.db import get_db

router = APIRouter(prefix="/api/packet")
stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
PACKET_PRICE_CENTS = 3500  # $35.00

@router.post("/build")
async def build(req: PacketRequest):
    result = await build_packet(req)
    checkout = stripe.checkout.Session.create(
        mode="payment",
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {"name": f"LegalClear Filing Packet ({req.packet_type})"},
                "unit_amount": PACKET_PRICE_CENTS,
            },
            "quantity": 1,
        }],
        metadata={"packet_id": result.packet_id, "user_id": req.user_id},
        success_url=f"https://legalclear.app/filing-packet/{result.packet_id}?paid=1",
        cancel_url=f"https://legalclear.app/filing-packet/{result.packet_id}?paid=0",
    )
    return {
        "packet_id": result.packet_id,
        "fee_usd": result.fee_usd,
        "file_count": result.file_count,
        "checkout_url": checkout.url,
    }

@router.get("/{packet_id}")
async def get_packet_metadata(packet_id: str):
    db = get_db()
    row = await db.fetch_one("SELECT * FROM packets WHERE id = ?", (packet_id,))
    if not row:
        raise HTTPException(404, "Packet not found")
    return dict(row)

@router.get("/{packet_id}/download")
async def download_packet(packet_id: str):
    db = get_db()
    row = await db.fetch_one("SELECT * FROM packets WHERE id = ?", (packet_id,))
    if not row:
        raise HTTPException(404, "Packet not found")
    if row["status"] != "paid":
        raise HTTPException(402, "Payment required")
    zip_path = Path(row["zip_path"])
    if not zip_path.exists():
        raise HTTPException(500, "Packet file missing")
    return FileResponse(zip_path, filename=f"legalclear_packet_{packet_id}.zip")

@router.post("/{packet_id}/track")
async def track_filing(packet_id: str, confirmation_number: str):
    db = get_db()
    await db.execute(
        """UPDATE packets SET confirmation_number = ?, filed_at = datetime('now')
           WHERE id = ?""",
        (confirmation_number, packet_id)
    )
    return {
        "status": "tracked",
        "packet_id": packet_id,
        "confirmation_number": confirmation_number
    }
```

### Register router
```python
from .routes.packet import router as packet_router
app.include_router(packet_router)
```

## DB schema addition

Add to existing migration system (Phase 08 Supabase):

```sql
CREATE TABLE IF NOT EXISTS packets (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    packet_type TEXT NOT NULL,
    language TEXT NOT NULL,
    county TEXT NOT NULL,
    fee_usd REAL NOT NULL,
    zip_path TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending_payment',
    confirmation_number TEXT,
    filed_at TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_packets_user ON packets(user_id);
CREATE INDEX IF NOT EXISTS idx_packets_status ON packets(status);
```

## Stripe webhook addition

Extend existing Phase 09 webhook handler — DO NOT replace it, ADD a new branch:

```python
# Inside existing webhook handler in backend/src/services/payments.py
if event["type"] == "checkout.session.completed":
    session = event["data"]["object"]
    metadata = session.get("metadata", {})
    packet_id = metadata.get("packet_id")
    if packet_id:
        await db.execute(
            "UPDATE packets SET status = 'paid' WHERE id = ?",
            (packet_id,)
        )
```

## Wire existing tile endpoints

Modify these endpoints from prior phases to call `build_packet()` instead of returning scaffold JSON:

- `/api/small-claims/generate` (Phase 16)
- `/api/expungement/generate` (Phase 17)
- `/api/landlord/deposit/generate` (Phase 18)
- `/api/landlord/repairs/generate` (Phase 18)
- `/api/landlord/eviction/generate` (Phase 18)
- `/api/traffic/generate` (Phase 20)

Each now accepts a `language: "en"|"es"` field (default `"en"`). Response shape becomes:
```json
{
  "packet_id": "uuid-string",
  "fee_usd": 175.0,
  "file_count": 3,
  "checkout_url": "https://checkout.stripe.com/..."
}
```

Each tile's frontend review step now navigates to `/filing-packet/:packetId` after receiving `packet_id`.

## Data files — specs

### `fl_county_clerk_details.json`
All 67 counties:
```json
{
  "name": "Miami-Dade",
  "clerk_url": "https://www.miamidade.gov/clerk",
  "clerk_address": "73 W Flagler St, Miami, FL 33130",
  "clerk_phone": "(305) 275-1155",
  "fee_tier_1": 55, "fee_tier_2": 80, "fee_tier_3": 175, "fee_tier_4": 300
}
```
Unverified phone → `(555) 000-0000` placeholder. **Never fabricate.**

### `instructions_en.json` and `instructions_es.json`
Per packet type. Example structure:
```json
{
  "small_claims": {
    "title": "Filing Your Small Claims Case",
    "summary": "This packet contains the documents you need to file...",
    "steps": [
      "Print all three documents in this packet.",
      "Sign the Statement of Claim in front of a notary.",
      "Go to myflcourtaccess.com and log in (or register).",
      "Select your county and upload each PDF.",
      "Pay the filing fee online with a card.",
      "Save your confirmation number — you'll need it to track your case."
    ],
    "what_happens_next": "The clerk will review your filing within 5–7 business days...",
    "county_overrides": {}
  },
  "expungement": { ... },
  "landlord_deposit": { ... },
  "landlord_repairs": { ... },
  "landlord_eviction": { ... },
  "traffic": { ... }
}
```
Spanish must use U.S. court interpreter register — NOT machine translation tone. All 6 packet types covered in both files.

### `walkthrough_steps_en.json` and `walkthrough_steps_es.json`
Step-by-step manual upload guide for myflcourtaccess.com (≥8 steps each):
```json
{
  "title": "How to file your packet on MyFLCourtAccess",
  "steps": [
    {
      "number": 1,
      "title": "Go to MyFLCourtAccess.com",
      "instruction": "Open a browser and navigate to https://www.myflcourtaccess.com",
      "what_to_expect": "You'll see a login screen. First time? Click 'Register' top-right."
    }
    // ... at least 7 more
  ]
}
```
Cover: login, file new case, select county, select case type, upload documents in order, review, pay filing fee, get confirmation number.

## Frontend deliverables

### Create
```
frontend/src/pages/FilingPacket.tsx
frontend/src/components/packet/PacketSummary.tsx
frontend/src/components/packet/LanguageToggle.tsx
frontend/src/components/packet/PaymentGate.tsx
frontend/src/components/packet/UploadWalkthrough.tsx
frontend/src/components/packet/FilingTracker.tsx
```

### Modify
- Frontend router: route `/filing-packet/:packetId` → `FilingPacket`
- Tile wizard review steps (Phases 16/17/18/20): after Generate returns `packet_id`, navigate to `/filing-packet/${packet_id}`

### `FilingPacket.tsx` states
Route: `/filing-packet/:packetId?paid=0|1`

| URL state | UI |
|---|---|
| No `paid` param or `paid=0` | PacketSummary + fee + "Pay $35 to download" button → opens Stripe checkout in new tab |
| `paid=1` | Download button (calls `/api/packet/{id}/download`) → UploadWalkthrough → FilingTracker |
| After confirmation entered | Tracking dashboard with filed_at timestamp |

### Language toggle
Top-right of FilingPacket page. EN / ES buttons. Selection persists in `localStorage` AND sent in the packet build request. Each tile wizard's review step includes the toggle BEFORE generation, so the user picks language up front.

## Verification — `backend/tests/test_phase_23.py`

```python
import httpx, json, time, os
from pathlib import Path

BACKEND = "http://localhost:8001"

def test_packet_build():
    r = httpx.post(f"{BACKEND}/api/packet/build", json={
        "packet_type": "small_claims",
        "language": "en",
        "county": "Miami-Dade",
        "user_id": "test_001",
        "tile_data": {
            "claim_type": "Unpaid debt", "amount": 1500,
            "defendant_type": "Individual", "defendant_name": "X",
            "defendant_address": "Y"
        }
    }, timeout=60.0)
    assert r.status_code == 200
    d = r.json()
    assert all(k in d for k in ["packet_id", "fee_usd", "checkout_url"])
    assert d["checkout_url"].startswith("https://checkout.stripe.com")
    return d["packet_id"]

def test_download_gated():
    pid = test_packet_build()
    r = httpx.get(f"{BACKEND}/api/packet/{pid}/download")
    assert r.status_code == 402

def test_zip_exists():
    pid = test_packet_build()
    time.sleep(2)
    d = Path(f"backend/storage/packets/{pid}")
    assert d.exists()
    for f in ["01_cover_sheet.pdf", "02_how_to_file.pdf", "03_form_fields_summary.pdf"]:
        assert (d / f).exists()
    assert len(list(d.glob("*.zip"))) == 1

def test_pdfa_metadata():
    import pikepdf
    pid = test_packet_build()
    time.sleep(2)
    with pikepdf.open(Path(f"backend/storage/packets/{pid}/01_cover_sheet.pdf")) as pdf:
        with pdf.open_metadata() as meta:
            assert meta.get("pdfaid:part") == "1"
            assert meta.get("pdfaid:conformance") == "B"

def test_spanish():
    r = httpx.post(f"{BACKEND}/api/packet/build", json={
        "packet_type": "small_claims",
        "language": "es",
        "county": "Miami-Dade",
        "user_id": "test_002",
        "tile_data": {
            "claim_type": "Unpaid debt", "amount": 500,
            "defendant_type": "Individual", "defendant_name": "Juan",
            "defendant_address": "Calle"
        }
    }, timeout=60.0)
    assert r.status_code == 200

def test_all_packet_types():
    types = [
        ("small_claims", {"claim_type": "Other", "amount": 100, "defendant_type": "Individual",
                          "defendant_name": "X", "defendant_address": "Y"}),
        ("expungement", {"disposition": "Dismissed", "charge": "Petit theft",
                         "completed_terms": "Yes", "previously_sealed": "No",
                         "years_since_closed": "5-10"}),
        ("landlord_deposit", {"move_out_date": "2026-01-01", "deposit_amount": 1000,
                              "current_address": "A", "landlord_name": "B",
                              "landlord_address": "C"}),
        ("landlord_repairs", {"property_address": "X", "issue_type": "AC",
                              "issue_description": "B", "prior_communication": "E",
                              "tenant_intent": "w"}),
        ("landlord_eviction", {"eviction_type": "nonpayment", "notice_type": "3-day",
                               "notice_date": "2026-04-01", "defenses": ["paid"]}),
        ("traffic", {"citation_type": "Speeding", "citation_number": "X",
                     "issue_date": "2026-04-15", "county": "Miami-Dade",
                     "chosen_path": "contest"}),
    ]
    for ptype, td in types:
        r = httpx.post(f"{BACKEND}/api/packet/build", json={
            "packet_type": ptype, "language": "en", "county": "Miami-Dade",
            "user_id": "test_003", "tile_data": td
        }, timeout=60.0)
        assert r.status_code == 200, f"Failed: {ptype}"

def test_tracking():
    pid = test_packet_build()
    r = httpx.post(f"{BACKEND}/api/packet/{pid}/track",
                   params={"confirmation_number": "MFC-2026-1234567"})
    assert r.status_code == 200

def test_counties():
    with open("backend/src/data/fl_county_clerk_details.json") as f:
        c = json.load(f)
    assert len(c) == 67

def test_bilingual_instructions():
    en = json.load(open("backend/src/data/instructions_en.json"))
    es = json.load(open("backend/src/data/instructions_es.json"))
    needed = {"small_claims", "expungement", "landlord_deposit",
              "landlord_repairs", "landlord_eviction", "traffic"}
    assert needed.issubset(en.keys())
    assert needed.issubset(es.keys())

def test_no_mode_b():
    """CRITICAL: Confirm no Python file in backend/src navigates to myflcourtaccess."""
    for root, _, files in os.walk("backend/src"):
        for f in files:
            if f.endswith(".py"):
                content = Path(root, f).read_text().lower()
                if "myflcourtaccess" in content:
                    # Only allowed in clearly-marked walkthrough text comments
                    assert "# walkthrough text only" in content, \
                        f"Mode B leak detected in {root}/{f}"

if __name__ == "__main__":
    test_packet_build()
    test_download_gated()
    test_zip_exists()
    test_pdfa_metadata()
    test_spanish()
    test_all_packet_types()
    test_tracking()
    test_counties()
    test_bilingual_instructions()
    test_no_mode_b()
    print("PHASE 23 COMPLETE — all checks passed.")
```

## Pass criteria

- All 6 packet types generate without error
- EN and ES both render
- ZIP contains exactly 3 PDFs (cover sheet, walkthrough, form fields summary)
- PDFs carry PDF/A-1b metadata (pikepdf-applied)
- Download endpoint returns 402 until payment confirmed
- Stripe checkout URL valid with `packet_id` in metadata
- All 67 FL counties present
- All 6 packet types in both EN and ES instructions
- Tracking endpoint stores confirmation number
- **NO file in `backend/src/` automates against myflcourtaccess.com** (hard test)
- All 10 assertions in `test_phase_23.py` pass

## Full system verification — `backend/tests/test_full_v1.py`

After Phase 23 passes its own tests, run:

```python
import httpx

BACKEND = "http://localhost:8001"
FRONTEND = "http://localhost:5173"

def test_all_tiles_reachable():
    for route in ["/", "/upload", "/small-claims", "/expungement",
                  "/landlord", "/forms", "/traffic", "/police-report", "/case-law"]:
        assert httpx.get(f"{FRONTEND}{route}").status_code == 200

def test_packet_endpoint_works():
    r = httpx.post(f"{BACKEND}/api/packet/build", json={
        "packet_type": "small_claims", "language": "en", "county": "Miami-Dade",
        "user_id": "smoke",
        "tile_data": {"claim_type": "Other", "amount": 100, "defendant_type": "Individual",
                      "defendant_name": "X", "defendant_address": "Y"}
    }, timeout=60.0)
    assert r.status_code == 200

def test_backend_port():
    assert httpx.get(f"{BACKEND}/health").status_code == 200

def test_no_port_8000_collision():
    try:
        r = httpx.get("http://localhost:8000/health", timeout=2.0)
        if r.status_code == 200:
            assert "legalclear" not in r.text.lower()
    except httpx.RequestError:
        pass

if __name__ == "__main__":
    test_all_tiles_reachable()
    test_packet_endpoint_works()
    test_backend_port()
    test_no_port_8000_collision()
    print("FULL V1 VERIFICATION COMPLETE — all checks passed.")
```

## Failure protocol

If any Phase 23 test fails twice: print `PHASE 23 BLOCKED — [error]` and STOP.

**If `test_no_mode_b` ever fails: STOP IMMEDIATELY.** That's the one boundary that cannot be crossed under any circumstance.

## Deployment

1. **Backend:** `uv sync` → commit → push to GitHub `main` → Railway auto-deploys `zesty-delight`
2. **Frontend:** `npm run build` → commit → push → Railway auto-deploys `appealing-victory`
3. **Stripe dashboard:** confirm "LegalClear Filing Packet" product at $35.00 visible
4. **Smoke test:**
   - Hub loads → Small Claims tile → 5-step wizard → review with EN selected → Generate
   - Land on FilingPacket → Pay $35 with Stripe test card `4242 4242 4242 4242`
   - Redirect to `?paid=1` → Download ZIP → confirm 3 PDFs inside
   - View Walkthrough → see ≥8 steps for myflcourtaccess.com
   - Enter test confirmation number → tracking page updates

## Final report format

```
=== LEGALCLEAR V1 FULL DEPLOYMENT REPORT ===
Phase 23 status: COMPLETE
Frontend bundle hash: [hash]
Backend deploy: success
Frontend deploy: success
Live URLs:
  Frontend: [url]
  Backend: [url]
Stripe product configured: yes ($35 Filing Packet)
Languages live: en, es
Verification:
  Phase 23 test: passed (10/10 assertions)
  test_full_v1.py: passed
TODOs remaining: [count of `# TODO:` markers in tile-generate routes]
Mode B automation present: no
Blocking issues: none
=== END REPORT ===
```

Do NOT add commentary outside the report. Do NOT claim success if any assertion failed. If Mode B automation is detected anywhere in `backend/src/`, the build is failed regardless of other test results.

LegalClear v1 ships when this report comes back clean. The field is a perfect ledger.
