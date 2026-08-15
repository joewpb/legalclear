# S2-5 Smoke Test Plan — deadline pipeline first execution

Status: PREPARED, NOT RUN. Runs only on Joe's explicit go. Supersedes nothing;
complements runs/13_s2_5_diagnose/REPORT.md (diagnosis of why the pipeline never ran).

## Goal

Prove whether break #1 ("/api/deadline/analyze has never successfully executed") is
merely an unexercised path or a live failure. This test exercises the UPSTREAM half
only (trigger_events + deadlines writes). The downstream reminder half is diagnosed as
structurally broken (absent table, unscheduled cron) and is NOT tested here.

## Baseline counts (read-only, capture immediately before the test)

Tables: documents, sessions, trigger_events, deadlines — via PostgREST count header:
  curl -s -H "apikey: $KEY" -H "Authorization: Bearer $KEY" -H "Prefer: count=exact" \
       -H "Range: 0-0" "https://miedifclpqewnixxkahs.supabase.co/rest/v1/<table>?select=*" \
       -o /dev/null -D - | grep -i content-range
Known today: documents=45, sessions=45, trigger_events=0, deadlines=0.

## Procedure (API path, orchestrator-run under Joe's supervision)

1. Obtain the backend API key into an env var WITHOUT printing it (proven technique:
   railway variables → in-memory classification only; or app_config read via service
   key piped into a variable). Never echo it. Use it only as an HTTP header.
2. Pick a test document: a PUBLIC Florida court document (court opinion PDF or sample
   summons). Explicitly NOT anything containing personal data. ~1-3 pages.
3. POST /upload (multipart file) to https://zesty-delight-production-b533.up.railway.app/api/upload
   with X-API-Key header. Record the returned document_id and session_id.
4. POST /process/{session_id} with X-API-Key. Confirm 200.
5. Verify documents.document_text is non-empty for the new document_id (read-only
   PostgREST select of length(document_text) — capture length ONLY, never the text).
6. POST /api/deadline/analyze/{document_id} with X-API-Key. Capture the FULL JSON
   response (contains counts and escalation flags only — no secrets).
7. Re-check counts: trigger_events, deadlines (+ per-document_id filtered reads).

Optional UI-path observation (Joe in his own browser): upload through the live site,
click the Deadlines tab on ResultsPage, watch the network tab for the analyze POST and
its JSON. Same interpretation table below.

## Interpretation

- PASS (unexercised path): analyze JSON reports trigger_events_written >= 1 and
  deadlines_written >= 1; Supabase counts increase by those amounts; new deadlines
  rows show reminder_state='pending'. Break #1 is a never-clicked tab, not a code
  failure. The only remaining blocker for the full loop is the already-diagnosed
  reminder half (migration + cron config).
- FAIL-A (live insert failure → proves S3-5d): analyze returns HTTP 200 with
  written=0, or rows never appear. Capture Railway service logs (zesty-delight) for
  the window — look for the swallowed errors logged at pipeline.py:209,245.
- FAIL-B (auth): 401 from analyze. Means the deployed frontend bundle's VITE_API_KEY
  differs from the backend API_KEY (rotation window: stale bundle). A hard refresh
  re-fetches the new bundle; if it persists, the frontend redeploy didn't pick up the
  new variable.
- FAIL-C: 404 (document not found) or 422 (empty text) → upload/process produced no
  extractable text. Capture /process response and the retention-job hypothesis
  (fresh upload should rule that out).

## Writes to prod and reversibility

- Writes: 1 documents row, 1 sessions row, N trigger_events rows, N deadlines rows.
- All writes are additive inserts; no existing rows are updated or deleted. Nothing
  consumes trigger_events/deadlines today (cron unscheduled), so the rows are inert.
- Reversibility: leaving the rows is harmless; deleting them is NOT part of this plan.

## Capture discipline

- CAPTURE on failure: analyze/process endpoint JSON responses, Railway zesty-delight
  logs for the window, the count deltas, the error text from pipeline.py log lines.
- NEVER capture or print: any API key value, document_text contents, any
  user_profiles/attorney_inquiries row contents, any PII from the test document (use a
  public document so there is none).

## Go / stop

This plan runs ONLY after Joe says go. On completion, report the interpretation
(PASS / FAIL-A / FAIL-B / FAIL-C) with the count deltas and the analyze JSON summary —
never the key.
