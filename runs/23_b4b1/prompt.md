# TASK: B4b-1 — canonicalize apply_disclaimer. No call-site changes.

Repo: backend/ is this repo. Run shape: sonnet, capped 40 turns / $3.
Branch: fix/b4b-1-canonicalize (already checked out).

## Goal (Decision 3, recorded in DECISIONS.md)
`apply_disclaimer` (backend/src/core/upl.py) becomes the single versioned disclaimer
source. `get_disclaimer` (backend/src/core/disclaimer.py) becomes a thin delegator to it.

## Scope — exactly this, nothing more
1. backend/src/core/upl.py: strip the external links from every language variant
   (floridalawhelp.org, floridabar.org — en and es). Replace with the on-site
   reference per the Aug 12 pattern: "Free help: LegalClear /find-legal-help" — match
   the phrasing already used elsewhere in the codebase (search for find-legal-help to
   copy the established wording). Do NOT change the disclaimer's overall structure,
   tone (nudge, not wall), or the UPL boundaries.
2. Add/verify a DISCLAIMER_VERSION constant (string or int) that bumps on any text
   change, so consumers can log which text they shipped.
3. backend/src/core/disclaimer.py: get_disclaimer(lang, level="standard") becomes a
   thin delegator to apply_disclaimer — keep its EXACT signature and return type
   (string). Construct the minimal data dict it needs. Call-site files must not be
   touched.
4. NO agent-prompt changes (explainer.py, form_guide.py are B4b-1a). NO call-site
   changes anywhere. Tests: update any test asserting the OLD link text; add tests
   asserting (a) no external link strings remain in either module's output for en+es,
   (b) get_disclaimer and apply_disclaimer return identical text for the same
   lang/level, (c) version constant exists and changes with text edits (just assert
   presence/type — do not overengineer).

## Verification
Full CI-scope suite (exact):
  cd backend && uv run pytest tests/ -q --ignore=tests/test_full_v1.py
  --ignore=tests/test_phase_2.py --ignore=tests/test_phase_16.py
  --ignore=tests/test_phase_17.py --ignore=tests/test_phase_18.py
  --ignore=tests/test_phase_20.py --ignore=tests/test_phase_21.py
  --ignore=tests/test_phase_22.py --ignore=tests/test_phase_23.py
  --ignore=tests/test_pc_integration.py
Baseline is 249/1 on main — must not drop.

## Rules
- uv only. No migrations, no prod writes, no secrets.
- Report: file:line of every edit, the exact replacement wording, test evidence, suite
  count, and confirm zero call-site files were touched.
