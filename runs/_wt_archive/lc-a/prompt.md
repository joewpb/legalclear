# TASK: A-1 (B5-d) — service-date prompt UI + conditional presentation.

Repo: frontend/ is in this repo. Run shape: sonnet, capped 40 turns / $3.
Worktree: /home/joe/code/lc-a, branch fix/b5-d-service-date-ui (checked out).

## Job
On the deadline results surface (frontend/src/pages/ResultsPage.jsx and its
Deadlines tab — find the component structure), add the service-date capture
UI:

1. Prompt: "When and how were you served?" with a date input and a method
   select (personal / substitute / posted / unknown).
2. When method = posted, a second date input appears: "date the clerk mailed
   the papers" (clerk_mailing_date).
3. On submit, PUT to the existing backend endpoint
   /api/deadline/{document_id}/service-date?session_id=... with JSON
   {service_method, service_date, clerk_mailing_date?} and the X-API-Key
   header via the EXISTING api client — see CONSTRAINT below.
4. On success, conditional presentation: "If you were served on X, your
   response is due Y" using the response's deadlines[0].due_date, rendered
   where the deadline results appear.
5. Input remains visible and EDITABLE after submit (values shown, can be
   changed and re-submitted).
6. Method select defaults to unknown if the user hasn't answered.

## CONSTRAINT — collision map
Your footprint is the deadline components ONLY. Use the existing api client
as-is (import it; do not edit it). If the service-date PUT cannot be made
with the existing client's helpers, STOP and report instead of editing the
client — another lane owns that file.

## Response contract you are building against (verified live)
- {recompute: "complete", deadlines: [{label, due_date, ...}], ...}
- {recompute: "escalated", escalation_reasons: [...], guidance: "...",
  deadlines: []} — render the guidance text in the same place, clearly, no
  deadline shown.
- 422 with {detail} — show the detail text (e.g. posted requires the mailing
  date).

Not in scope: the I-don't-know path and recompute-on-edit refresh flows —
those are A-2. Basic display + editability only.

## Verification
cd frontend && npm run build — must pass. Report file:line changes and
build result.
