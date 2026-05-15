# PHASE 21 — Police Report Analyzer
**Status: BUILD. Prerequisite: Phases 15–20 complete.**

## Universal rules

- **uv only.** No `pip`.
- **Backend port 8001.**
- **Florida jurisdiction only.**
- **Brutalist design tokens** from Phase 15 mandatory.
- **All agent prompts** use `cache_control: ephemeral`.
- **Strip markdown fences** from agent JSON output.
- **No `myflcourtaccess.com` automation.**

## Universal DO-NOT-TOUCH

- Existing agents (classifier, explainer, risk_scanner — this phase adds a NEW scanner agent, doesn't modify the old ones)
- Stripe paywall
- `.env`, env vars
- Existing FastAPI routes
- No new npm packages
- For Python: only allowed install is if the upload/PDF dependencies are somehow missing (extremely unlikely — verified in Phase 02)

## Goal

Multi-document upload → new Scanner Agent flags procedural and factual discrepancies → structured findings rendered with severity badges. Uses existing PDF processor from Phase 02. Reuses upload infrastructure pattern from Phase 10.

This is NOT legal advice. It is **document analysis** that flags things a defense attorney would want to investigate.

## Frontend deliverables

### Create
```
frontend/src/pages/PoliceReportAnalyzer.tsx
frontend/src/components/policereport/UploadInterface.tsx
frontend/src/components/policereport/FindingsList.tsx
frontend/src/components/policereport/FindingCard.tsx
frontend/src/components/SeverityBadge.tsx
```

### Modify
- Frontend router: route `/police-report` → `PoliceReportAnalyzer`.

## UI spec

- **Primary upload:** police report PDF (required)
- **Optional secondary uploads:** up to 4 additional files (witness statements, body cam transcript, dispatch log)
- **ANALYZE button** → POST multipart to `/api/police-report/analyze`
- **Loading state:** 15–45 second analysis indicator
- **Findings:** vertical list of cards
  - Severity badge (top-left)
    - HIGH = `var(--danger)` background, white text
    - MEDIUM = `var(--accent)` background, black text
    - LOW = `var(--muted)` background, white text
  - Category (mono, uppercase, top of card)
  - Page reference (small, muted, top-right)
  - Finding text (sans, main body)
  - "ASK YOUR ATTORNEY ABOUT" callout in a bordered sub-box at bottom of card

## Backend deliverables

### Create `backend/src/agents/scanner.py`

```python
"""New Scanner Agent — flags police-report discrepancies."""
from anthropic import Anthropic
import json

client = Anthropic()

SCANNER_PROMPT = """You are a document analyzer reviewing a police report and any supplementary documents the user uploaded. Your job is to flag inconsistencies and procedural issues a defense attorney would want to know about.

You are NOT giving legal advice. You are NOT recommending a defense strategy. You are pointing out things to ask an attorney about.

Categories to scan:
1. Temporal inconsistencies — timestamps that don't align across documents
2. Spatial inconsistencies — locations described differently
3. Procedural issues — missing Miranda reference in custodial situations, no articulated probable cause for searches, no consent documentation
4. Officer account variance — if multiple officers describe the same event, where do they diverge?
5. Missing required elements — witness names withheld, evidence chain gaps, no badge numbers
6. Internal contradictions within a single document

Output ONLY a JSON array. Each finding:
{
  "category": "Temporal",
  "severity": "high|medium|low",
  "page_reference": "p.3, paragraph 4",
  "finding": "Plain-English description of the inconsistency",
  "ask_your_attorney_about": "What to raise with your lawyer"
}

Do not invent findings. If a category has no issues, omit it. If the documents are too short or lack context to analyze, return an empty array with a note in the meta field.
"""

async def scan_documents(extracted_texts: list[dict]) -> dict:
    """
    extracted_texts: list of {filename, text} dicts from pdf_processor (Phase 02)
    Returns: {findings: [...], meta: {}}
    """
    combined = "\n\n---\n\n".join(
        f"[FILE: {d['filename']}]\n{d['text']}" for d in extracted_texts
    )

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        system=[{
            "type": "text",
            "text": SCANNER_PROMPT,
            "cache_control": {"type": "ephemeral"}
        }],
        messages=[{"role": "user", "content": combined}]
    )

    raw = msg.content[0].text.strip()
    # Strip markdown fences (universal rule)
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        findings = json.loads(raw)
        if not isinstance(findings, list):
            findings = []
    except json.JSONDecodeError:
        findings = []

    return {"findings": findings, "meta": {"documents_analyzed": len(extracted_texts)}}
```

### Create `backend/src/api/routes/police_report.py`

```python
from fastapi import APIRouter, UploadFile, File
from typing import List
from ..services.pdf_processor import extract  # existing Phase 02 function
from ...agents.scanner import scan_documents

router = APIRouter(prefix="/api/police-report")

@router.post("/analyze")
async def analyze_report(files: List[UploadFile] = File(...)):
    # TODO: replace with real Claude-generated output already wired — confirm scanner agent stable in production
    extracted = []
    for f in files:
        content = await f.read()
        # Use existing PDF processor from Phase 02
        text_result = extract(content)  # adjust call signature to actual Phase 02 API
        extracted.append({"filename": f.filename, "text": text_result.get("text", "")})

    result = await scan_documents(extracted)
    return {
        "findings": result["findings"],
        "documents_analyzed": result["meta"]["documents_analyzed"]
    }
```

### Register router
```python
from .routes.police_report import router as police_router
app.include_router(police_router)
```

**Note on `extract()` call signature:** Phase 02's `pdf_processor.py` has its own API — adjust the import and call accordingly. If the actual function name differs (e.g., `extract_text` or `process_pdf`), use the existing one. Do NOT rebuild PDF extraction.

## Verification — `backend/tests/test_phase_21.py`

```python
import httpx
import io

BACKEND = "http://localhost:8001"

def test_analyze_endpoint_accepts_upload():
    fake_pdf = io.BytesIO(b"%PDF-1.4 fake police report content for testing")
    r = httpx.post(
        f"{BACKEND}/api/police-report/analyze",
        files={"files": ("report.pdf", fake_pdf, "application/pdf")},
        timeout=60.0
    )
    assert r.status_code == 200
    data = r.json()
    assert "findings" in data
    assert isinstance(data["findings"], list)

def test_multi_file_upload():
    f1 = io.BytesIO(b"%PDF-1.4 primary report")
    f2 = io.BytesIO(b"%PDF-1.4 supplementary witness statement")
    r = httpx.post(
        f"{BACKEND}/api/police-report/analyze",
        files=[
            ("files", ("primary.pdf", f1, "application/pdf")),
            ("files", ("witness.pdf", f2, "application/pdf")),
        ],
        timeout=60.0
    )
    assert r.status_code == 200
    assert r.json()["documents_analyzed"] == 2

def test_finding_structure():
    """If findings are returned, they must have the required shape."""
    fake = io.BytesIO(b"%PDF-1.4 test")
    r = httpx.post(
        f"{BACKEND}/api/police-report/analyze",
        files={"files": ("report.pdf", fake, "application/pdf")},
        timeout=60.0
    )
    findings = r.json()["findings"]
    if len(findings) > 0:
        required = {"category", "severity", "page_reference", "finding", "ask_your_attorney_about"}
        assert required.issubset(findings[0].keys())
        assert findings[0]["severity"] in {"high", "medium", "low"}

if __name__ == "__main__":
    test_analyze_endpoint_accepts_upload()
    test_multi_file_upload()
    test_finding_structure()
    print("PHASE 21 COMPLETE — all checks passed.")
```

## Pass criteria

- Multi-file upload UI works (primary required, up to 4 supplementary)
- `/api/police-report/analyze` accepts multipart and returns findings array
- Scanner agent prompt uses `cache_control: ephemeral`
- JSON output parsed after stripping markdown fences
- Each finding (when returned) has all 5 required fields with valid severity
- Severity badges render in correct Brutalist colors
- New Scanner agent does NOT modify Phase 03 classifier or Phase 06 risk_scanner
- `test_phase_21.py` exits cleanly

## Failure protocol

If a test fails twice: print `PHASE 21 BLOCKED — [error]` and STOP.

## Final report

```
PHASE 21 COMPLETE — all checks passed.
```

Commit + push. Wait for Railway deploys. Proceed to Phase 22.
