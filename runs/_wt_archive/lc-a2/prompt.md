# TASK: A-2 (B5-e) — I-don't-know path + recompute-on-edit UI.

Repo: frontend/ is this repo. Run shape: sonnet, capped 40 turns / $3.
Worktree: /home/joe/code/lc-a2, branch fix/b5-e-idk-recompute (checked out).
NOTE: A-1 (service-date form) is NOT merged yet — it lives on branch
fix/b5-d-service-date-ui (commit 59ca7c9). Your branch is cut from main, so
you will NOT see A-1's form. Build your work in the SAME component area
(frontend/src/pages/ResultsPage.jsx Deadlines tab) and structure it so the
merge is mechanical: you may re-implement the form's EXTENSIONS on top of
the same file regions A-1 used (the form component in ResultsPage.jsx), but
do not duplicate the base form. At merge time the orchestrator reconciles —
keep your diff minimal and clearly separable (new handlers + small form
additions, not a rewrite of the page).

## Job — two behaviors on the service-date form
1. I-don't-know path: an explicit "I don't know" option for the HOW question
   (method = unknown) with helper text explaining what to do (check the case
   docket or the clerk's file for the return of service). Submitting
   unknown shows the escalation guidance returned by the backend
   ({recompute: "escalated", guidance}) — matching A-1's escalation render.
2. Recompute-on-edit: when the user edits the date/method and re-submits,
   the deadline display must REFRESH from the new response (supersede
   happens backend-side; the UI must replace the displayed deadline list
   with the response's deadlines — no stale rows shown, no page reload
   required).

## Response contract (verified live)
- complete: {recompute, deadlines:[{label, due_date, ...}]}
- escalated: {recompute: "escalated", escalation_reasons, guidance,
  deadlines: []} → render guidance clearly, no deadline
- 422 {detail} → inline detail text

## CONSTRAINT — collision map
Deadline components only. Do not edit the api client or any other lane's
files. Use the existing axios api client as-is.

## Verification
cd frontend && npm run build — must pass. Report file:line changes and the
build result.
