# Phase G, group 3 — INTEGRATION_PLAN dead-code deletions (P2.1.c + related)

Repo: joewpb/legalclear. Worktree: ~/code/lc-g3 (branch fix/g3-dead-code, cut from origin/main 849c4a5).

## Context (from INTEGRATION_PLAN.md, lines 52-57, 141, 149, 161)

The plan's P2.1.c ordered deletion of dead frontend components; audit finding 7 says
it was never performed. Named candidates (all still exist on disk):
- frontend/src/pages/AnalysisDashboard.jsx
- frontend/src/pages/LandingPage.jsx
- frontend/src/pages/ExpungementPage.jsx
- frontend/src/pages/PhaseStub.tsx
- frontend/src/components/layout/Navbar.jsx
Plan line 161: top-level POST /eligibility (backend/src/api/routes.py:170-173) is
DARK — superseded by /api/expungement/eligibility, 0 consumers claimed.
Plan lines 159-160 list triage router and analysis router as AMBIGUOUS — the
analysis router was already deleted in group g1; the TRIAGE router is OUT OF SCOPE
here (needs a Joe decision — do not touch it).

## Part 1 — enumerate + verify (report-first; this list goes in the phase report)

For EACH candidate component, prove dead or not:
1. grep -rn "<ComponentName" frontend/src/ — who imports/renders it? App.tsx /
   SiteHeader / routes? A component with zero importers is dead.
2. Also grep for its route registration (e.g. "/analysis-dashboard", "/landing",
   "/expungement-old", "/phase-stub") in App.tsx/router config.
3. For POST /eligibility: grep frontend/src for fetch/axios calls to "/eligibility"
   (exact path, not /api/expungement/eligibility). Report which page calls what
   with file:line. If ExpungementFL.tsx calls /api/expungement/eligibility and
   nothing calls /eligibility — the route is provably unreferenced.
4. Sweep for OTHER obviously-dead files the plan's audit table flags (DARK rows,
   lines 49-57): report any additional candidates with import evidence.
5. Output a table: file | importers found | verdict (DEAD / LIVE / UNCERTAIN).
   If ANY candidate shows a live importer — do NOT delete it; mark UNCERTAIN.

## Part 2 — delete only provably-unreferenced items

1. Delete each DEAD-verdict file from Part 1.
2. If /eligibility is provably unreferenced: remove the route in
   backend/src/api/routes.py (~170-173) AND its now-unused import + the
   EligibilityRequest model if it becomes unused (verify with grep first).
3. Do NOT touch: triage router, anything UNCERTAIN, anything not in your table.
4. Verify: cd frontend && npm run build (exit 0, "✓ built in" — the chunks>500kB
   note is advisory) AND the backend suite with the CI-scope ignores from
   .github/workflows/pytest.yml (baseline 352 passed, 1 skipped).
5. Report: the enumeration table, files deleted, build + suite results.

## Hard rules

No git push/merge/checkout/reset/clean/stash/add/commit/branch. No network. No
railway/supabase. Edit in place — orchestrator commits. Do not touch backend routes
other than the /eligibility removal. Do not touch triage.py, any page that is LIVE.
