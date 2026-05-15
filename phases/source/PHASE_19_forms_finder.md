# PHASE 19 — Court Forms Finder FL (Frontend Only)
**Status: BUILD. Prerequisite: Phases 15–18 complete.**

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
- Backend untouched in this phase
- No new npm or python packages

## Goal

Data-driven lookup of FL court forms by case type. No backend call — pure static data. Lightweight tile; ships fast.

## Frontend deliverables

### Create
```
frontend/src/pages/FormsFinderFL.tsx
frontend/src/data/fl_courts_forms_index.json
```

### Modify
- Frontend router: route `/forms` → `FormsFinderFL`.

## Flow

1. User selects case type (Family / Civil / Probate / Small Claims / Traffic / Criminal)
2. User selects sub-category for that case type
3. Page renders list of relevant forms with download links

## `fl_courts_forms_index.json` — minimum 18 entries across all 6 case types

Format:
```json
[
  {
    "case_type": "Family",
    "sub_category": "Divorce (no children, no property)",
    "forms": [
      {
        "name": "Petition for Simplified Dissolution of Marriage",
        "form_number": "12.901(a)",
        "url": "https://www.flcourts.gov/Resources-Services/Court-Improvement/Family-Courts/Family-Law-Forms"
      }
    ]
  }
]
```

### Coverage requirement
- Family: ≥5 entries (divorce, child support, paternity, custody, name change)
- Civil: ≥3 entries (complaint, summons, motion)
- Probate: ≥3 entries (formal admin, summary admin, disposition without admin)
- Small Claims: ≥3 entries (statement of claim, summons, attachment)
- Traffic: ≥2 entries (request for hearing, election of school)
- Criminal: ≥2 entries (motion to seal/expunge, motion for return of property)

### URL constraint
URLs MUST resolve under one of these government domains:
- `flcourts.gov`
- `fdle.state.fl.us`
- `flhsmv.gov`
- `flclerks.com`

**Do NOT fabricate form numbers or URLs.** If a specific form's URL can't be verified, use the FL Courts forms landing page as a fallback (`https://www.flcourts.gov/Resources-Services/Court-Improvement/Family-Courts/Family-Law-Forms` or equivalent).

## Backend deliverables

None this phase.

## Verification — `backend/tests/test_phase_19.py`

```python
import json

def test_forms_index_exists():
    with open("frontend/src/data/fl_courts_forms_index.json") as f:
        data = json.load(f)
    assert len(data) >= 18, f"Need ≥18 entries, got {len(data)}"

def test_all_case_types_covered():
    with open("frontend/src/data/fl_courts_forms_index.json") as f:
        data = json.load(f)
    case_types = {entry["case_type"] for entry in data}
    required = {"Family", "Civil", "Probate", "Small Claims", "Traffic", "Criminal"}
    assert required.issubset(case_types), f"Missing case types: {required - case_types}"

def test_coverage_per_case_type():
    with open("frontend/src/data/fl_courts_forms_index.json") as f:
        data = json.load(f)
    counts = {"Family": 0, "Civil": 0, "Probate": 0, "Small Claims": 0, "Traffic": 0, "Criminal": 0}
    for entry in data:
        counts[entry["case_type"]] += 1
    assert counts["Family"] >= 5
    assert counts["Civil"] >= 3
    assert counts["Probate"] >= 3
    assert counts["Small Claims"] >= 3
    assert counts["Traffic"] >= 2
    assert counts["Criminal"] >= 2

def test_urls_not_fabricated():
    with open("frontend/src/data/fl_courts_forms_index.json") as f:
        data = json.load(f)
    allowed_domains = ["flcourts.gov", "fdle.state.fl.us", "flhsmv.gov", "flclerks.com"]
    for entry in data:
        for form in entry["forms"]:
            assert any(d in form["url"] for d in allowed_domains), \
                f"Suspect URL (not on approved govt domain): {form['url']}"

if __name__ == "__main__":
    test_forms_index_exists()
    test_all_case_types_covered()
    test_coverage_per_case_type()
    test_urls_not_fabricated()
    print("PHASE 19 COMPLETE — all checks passed.")
```

## Pass criteria

- Forms index has ≥ 18 entries
- All 6 case types represented with minimum coverage counts
- Every form URL resolves to an approved government domain
- UI navigates case type → sub-category → form list cleanly
- `test_phase_19.py` exits cleanly

## Failure protocol

If a test fails twice: print `PHASE 19 BLOCKED — [error]` and STOP.

## Final report

```
PHASE 19 COMPLETE — all checks passed.
```

Commit + push. Wait for Railway deploys. Proceed to Phase 20.
