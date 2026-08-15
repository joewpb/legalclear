# TASK: Diagnose why the deadline→reminder pipeline has never executed end to end. Investigation only. Change no code.

Repo: backend/ is this repo. AUDIT_FINDINGS.md is the diagnosis; DECISIONS.md holds Joe's
approved decisions. Read only the sections for S2-5 and §4.8 — do not read either file
end to end.

## Known prod facts (provided by the orchestrator — do not verify with network; you
have no network access in this run)

Prod Supabase (project miedifclpqewnixxkahs), read-only counts taken today:
- documents: 45 rows; sessions: 45 rows
- trigger_events: TABLE EXISTS, 0 rows
- deadlines: TABLE EXISTS, 0 rows
- push_tokens: TABLE EXISTS, 0 rows
- reminders: TABLE ABSENT (PostgREST 404) — its migration never reached prod
- court_closures: 9 rows (seed applied)
- citation_treatment: 4770 rows (applied + populated)
- user_profiles / attorney_inquiries: absent (20260813 migration unapplied)
- app_config: exactly two keys: backend_url (= https://zesty-delight-production-b533.up.railway.app)
  and api_key. NO cron/schedule/interval keys.
- Railway deploy: Nixpacks build + uvicorn start only. No cron service, no deploy
  hooks, nothing runs SQL at deploy.

## Your job

Trace the INTENDED end-to-end chain from document upload to deadline computation to
reminder delivery, and find every place it breaks. Answer with file:line evidence:

1. The intended writers. For each of: trigger_events, deadlines, reminders, push_tokens
   — find the code that is supposed to write rows (backend/src/...). For each writer:
   file:line, what triggers it (endpoint? scheduled job? post-processing step?), and
   whether that trigger is reachable in prod today.
2. The cron/scheduler mechanism. Search supabase/migrations/ for pg_cron installation
   and cron.job definitions (the audit cites a pg_cron caller configured via app_config).
   What does the cron SQL do, what backend endpoint does it hit (app_config backend_url),
   and which migration file carries it? Cross-reference with the "reminders table
   absent" fact: which migration creates reminders, and is it among the unapplied set?
3. The client chain. In frontend/src, trace the user flow that SHOULD produce a
   deadline (upload → process → packet/payment gate → deadline analyze?). With
   PAYMENTS_ENABLED unset (effective false), does the user reach the deadline analyze
   call at all, or does the flow dead-end at the packet/payment screen? Find the
   frontend calls that would create trigger_events or invoke the pipeline.
4. The verdict: list each break in the chain, ranked by "which break is first" — the
   first break is the one that must be fixed before anything downstream can ever run.
   For each: is it (a) an unapplied migration, (b) missing app_config/cron keys,
   (c) a code path with no caller, (d) a paywall/flow dead-end, or (e) something else.
5. What a fix would require, described (not implemented): migration apply order,
   app_config keys to add, endpoint wiring, and what a supervised prod smoke test would
   look like (upload → process → analyze → verify trigger_events/deadlines rows appear).

## Rules
- No code changes, no file writes except the report. Write findings to
  runs/13_s2_5_diagnose/REPORT.md (create the file; that is the ONLY file you may write).
- No network calls of any kind (no curl, no pip, no fetch). Everything from repo files.
- Separate VERIFIED (read the code at cited lines) from INFERRED (reasoned, not
  executed) from UNVERIFIED (needs a network/dashboard check) in the report.
- If the answer is "the chain was never wired at all", say so plainly with the
  evidence — do not invent a chain.
