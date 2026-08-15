# TASK: Fix a single audited defect. Do exactly this and nothing else.

This repo was audited at 0c2e006 (main has since gained docs commits; source is
unchanged). AUDIT_FINDINGS.md is the diagnosis; DECISIONS.md holds Joe's approved
decisions. Read only the section for this item — do not read either file end to end.

## The defect
Triage S2-2 (AUDIT_FINDINGS.md §6):
"Find Legal Help unreachable — no inbound link to `/find-legal-help`. Built, routed,
invisible. Proposed fix: HomeHub tile or footer link. Blast radius: trivial. Indep: yes."

## Pre-check (do this FIRST and state the finding in your report)
The audit also says `/attorney-referral` has no main-nav tile (Q6). Confirm the current
inbound-link state of BOTH routes before touching anything:
- grep `frontend/src` for `/find-legal-help` and `/attorney-referral` as href/route
  targets (App.tsx route definitions vs. actual clickable links are different things).
- HomeHub tile config (frontend/src/pages/HomeHub.tsx) and any footer component.
- Report exactly what inbound links exist today for each route, with file:line.
This item covers ONLY `/find-legal-help`. If you find `/attorney-referral` also has no
nav entry, note it in your report and FOLLOW_UPS.md as belonging to S2-1 — do NOT code
a referral link in this run.

## Scope resolution (authoritative for this run)
- Add ONE inbound entry point for `/find-legal-help`: a HomeHub tile (preferred — it is
  a first-class user-facing page) or a footer link, matching the existing tile/link
  style of the repo. Do not restyle anything else.
- Frontend only. Do not touch backend, do not change routing.
- If the fix is larger than the finding describes, STOP and report instead of coding.

## Done means
1. Evidence the link was absent before (grep with file:line) and present after.
2. Minimal diff.
3. `npm run build` inside frontend/ completes with no errors (this is the verification
   for a frontend-only change; there is no pytest for the React app).
4. One paragraph: what was wrong, what changed, what could regress.
