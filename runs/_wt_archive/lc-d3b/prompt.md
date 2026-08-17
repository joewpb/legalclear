# TASK: D-3b (S1-3b frontend) — AttorneyReferralFL.tsx → the shared api client.

Repo: frontend/ is this repo. Run shape: sonnet, capped 40 turns / $3.
Worktree: /home/joe/code/lc-d3b, branch fix/d3b-referral-api-client (checked
out).

## Background
The backend now REQUIRES the API key on /attorney-referral/intake and
/submit (D-3a, unmerged). The frontend page currently uses raw fetch and
does not send X-API-Key — after D-3a lands, the intake flow will 401.

## Job
1. Switch frontend/src/pages/AttorneyReferralFL.tsx from raw fetch to the
   existing shared axios api client (the one other pages import — find its
   path, e.g. src/api.js), so the API key header rides along as the client
   already configures it.
2. Verify the client actually attaches X-API-Key (read it). If it does not,
   add the header the way the client handles it for other keyed endpoints —
   this file IS in your lane's footprint (the api client is Lane D), so
   editing it is allowed.
3. Keep the page's UX identical — only the transport changes.
4. ChatDrawer (if it also calls intake/submit) — check it; if it uses raw
   fetch for the same endpoints, switch it too (ChatDrawer.tsx is in Lane D
   footprint).

## Verification
cd frontend && npm run build — must pass. Report file:line changes and
confirm the client attaches the key (cite the line).
