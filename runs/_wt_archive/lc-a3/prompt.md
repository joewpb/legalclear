# TASK: A-3 (D2) — legacy 422 empty-state on the deadline surface.

Repo: frontend/ is this repo. Run shape: sonnet, capped 40 turns / $3.
Worktree: /home/joe/code/lc-a3, branch fix/a3-legacy-empty-state (checked
out).

## Job
Some older documents predate text storage; the backend returns 422 with a
legacy empty-state detail for them on the deadline surface. The UI currently
shows whatever falls out — give it a real empty state:
1. In frontend/src/pages/ResultsPage.jsx (Deadlines area), when the
   deadlines GET returns 422 with the legacy detail (find the exact shape:
   grep the backend deadline router for the 422 responses with detail),
   render a plain-language panel: "This document was uploaded before we
   stored the full text. Upload the document again to get deadlines."
   (word it plainly; the exact copy is yours to refine, plain English,
   no jargon).
2. Include a re-upload prompt/button that routes to the existing upload
   flow (use the existing upload route/link pattern — find how the app
   links to upload elsewhere and reuse it; do not create a new upload
   mechanism).
3. Isolate your change as new handlers/small additions (do not rewrite the
   page) — two sibling lanes also edit this file and the orchestrator
   reconciles the three diffs at merge time. Keep your diff minimal and
   clearly separable.
4. Do not touch the api client.

## Verification
cd frontend && npm run build — must pass. Report file:line changes and the
build result.
