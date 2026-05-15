# PHASE 15 — Hub Restructure + Brutalist Design System
**Status: BUILD. Execute in order. Prerequisite: Phases 00–14 verified.**

## Universal rules

- **uv only.** No `pip`.
- **Backend port 8001.** Never 8000.
- **Florida jurisdiction only.**
- **Brutalist design tokens** (defined in this phase) mandatory for all later phases.
- **All agent prompts** use `cache_control: ephemeral`.
- **Strip markdown fences** from agent JSON output before `json.loads()`.
- **No automation against `myflcourtaccess.com`.** Mode A only.
- Use Antigravity Planning mode → review → Fast mode to execute.

## Universal DO-NOT-TOUCH

- Existing agents (classifier, explainer, form_guide, risk_scanner, expungement)
- Existing Stripe paywall internals (Phase 09)
- `.env`, `.env.example`, env vars
- Railway config, Dockerfile, build scripts
- Existing FastAPI routes
- `package.json` unless explicitly noted below

## Goal

Replace upload-first landing with an 8-tile navigation hub. Move existing uploader to `/upload`. Establish Brutalist CSS system used by every later phase.

## Frontend deliverables

### Create
```
frontend/src/pages/HomeHub.tsx
frontend/src/components/HubTile.tsx
frontend/src/styles/brutalist.css
```

### Modify minimally
- `frontend/src/App.tsx` — change `/` to `HomeHub`, add `/upload` pointing to existing uploader, declare stub routes for: `/small-claims`, `/expungement`, `/landlord`, `/forms`, `/traffic`, `/police-report`, `/case-law`
- Global CSS entry — import `brutalist.css`

If `react-router-dom` is missing, install with `npm install react-router-dom`. That is the ONLY allowed npm install in this phase.

## Brutalist design tokens — `frontend/src/styles/brutalist.css`

```css
:root {
  --bg: #0A0A0A;
  --fg: #F5F5F5;
  --accent: #FFFFFF;
  --muted: #666666;
  --border: #1F1F1F;
  --border-strong: #333333;
  --danger: #FF3B30;
  --success: #34C759;
  --font-mono: "JetBrains Mono", "IBM Plex Mono", ui-monospace, monospace;
  --font-sans: "Inter", system-ui, sans-serif;
}
* { border-radius: 0 !important; }
body { background: var(--bg); color: var(--fg); font-family: var(--font-sans); }
h1, h2, h3, .mono { font-family: var(--font-mono); text-transform: uppercase; letter-spacing: -0.02em; }
.btn { border: 1px solid var(--border); padding: 12px 24px; text-transform: uppercase; letter-spacing: 0.08em; background: transparent; color: var(--fg); cursor: pointer; transition: opacity 150ms ease; }
.btn:hover { background: var(--fg); color: var(--bg); }
.input { border: 1px solid var(--border); background: transparent; color: var(--fg); padding: 12px; }
.input:focus { border-color: var(--accent); outline: none; }
```

## 8 Tiles (exact order)

| # | Title | Subtitle | Route |
|---|---|---|---|
| 1 | I HAVE A DOCUMENT | Upload and get a plain-English breakdown | `/upload` |
| 2 | SMALL CLAIMS (FL) | File a claim for up to $8,000 in Florida | `/small-claims` |
| 3 | EXPUNGEMENT (FL) | Seal or expunge a Florida record | `/expungement` |
| 4 | LANDLORD / TENANT (FL) | Rent, deposits, eviction defense | `/landlord` |
| 5 | COURT FORMS FINDER (FL) | Locate the correct FL forms for your case | `/forms` |
| 6 | TRAFFIC / TICKETS (FL) | Contest or handle a Florida ticket | `/traffic` |
| 7 | POLICE REPORT ANALYZER | Upload a report — find inconsistencies | `/police-report` |
| 8 | FL CASE LAW LOOKUP | Search Florida case law via CourtListener | `/case-law` |

### Layout
- 1 column mobile (<640px)
- 2 columns tablet (640–1024px)
- 4 columns desktop (>1024px)
- Grid gap: 1px (tile borders form a single lattice)
- Tile padding: 32px

### Tile behavior
- All 8 tiles ACTIVE and clickable
- Hover: border color shifts from `var(--border)` to `var(--accent)`
- Keyboard focusable, proper `aria-label`
- Each tile is a `<Link>` (react-router) wrapping the HubTile component

## HomeHub structure

```tsx
<header>
  <h1>LEGALCLEAR</h1>
  <p>Florida legal help, explained in plain English.</p>
</header>
<main>
  <section className="hub-grid">
    {/* 8 HubTile components */}
  </section>
</main>
<footer>
  <p>
    LegalClear provides informational tools only. Nothing here is legal advice.
    Using this site does not create an attorney-client relationship.
    For your specific situation, consult a licensed Florida attorney.
  </p>
</footer>
```

Footer style: `color: var(--muted); font-size: 12px;` — applies to EVERY page from this phase onward.

## Backend deliverables

None this phase.

## Verification — `frontend/tests/test_phase_15.py`

```python
import httpx
BASE = "http://localhost:5173"  # Vite dev port

def test_home_loads():
    r = httpx.get(f"{BASE}/")
    assert r.status_code == 200
    html = r.text.lower()
    for title in ["i have a document", "small claims", "expungement",
                  "landlord", "court forms", "traffic", "police report", "case law"]:
        assert title in html, f"Missing tile: {title}"

def test_upload_route_exists():
    r = httpx.get(f"{BASE}/upload")
    assert r.status_code == 200

def test_brutalist_loaded():
    """Check brutalist tokens reach the page."""
    r = httpx.get(f"{BASE}/")
    text = r.text.lower()
    # At least one Brutalist token should appear in the served HTML/CSS bundle reference
    assert "brutalist" in text or "0a0a0a" in text or "var(--bg)" in text

def test_existing_upload_endpoint_unchanged():
    """Backend /api/upload still responds."""
    r = httpx.get("http://localhost:8001/health")
    assert r.status_code == 200

if __name__ == "__main__":
    test_home_loads()
    test_upload_route_exists()
    test_brutalist_loaded()
    test_existing_upload_endpoint_unchanged()
    print("PHASE 15 COMPLETE — all checks passed.")
```

## Pass criteria

- `/` renders all 8 tiles in the correct order
- All 8 tile routes resolve (stubs OK for tiles 2–8; tile 1 reaches the existing uploader)
- Footer disclaimer visible on every page
- `npm run build` succeeds with zero errors
- `test_phase_15.py` all assertions pass
- Backend untouched: `/health` still 200

## Failure protocol

If any test fails twice: print `PHASE 15 BLOCKED — [error]` and STOP. Do not proceed to Phase 16.

## Final report

After all checks pass:
```
PHASE 15 COMPLETE — all checks passed.
```

Commit + push to GitHub `main`. Wait for Railway `appealing-victory` deploy to show Success. Then proceed to Phase 16.
