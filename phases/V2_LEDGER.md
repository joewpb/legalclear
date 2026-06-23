# LegalClear — v2 Phase Ledger

**Single source of truth for v2 build state.**
v1 state lives in `phases/LEDGER.md`. This file tracks phases defined in
`phases/BUILD_PLAN.md` (Phases 0–N). If this ledger disagrees with the repo,
the repo wins — re-verify and correct.

Status values: `COMPLETE` · `IN PROGRESS` · `PENDING` · `BLOCKED`

---

| # | Title | Status | Date | Notes |
|---|-------|--------|------|-------|
| 0 | Stabilize the Foundation | COMPLETE | 2026-06-23 | Re-verified: 2 new PRs merged (#10 migration rename, #13 forms integration); forms/ harvest debris cleaned (167MB → 1.3MB); .gitignore hardened (forms/*.txt, forms/*/, forms/crawled/, .whale/, supabase-schema-*.svg); AGENTS.md phase count fixed (0–8 → 0–9); CLAUDE.md verified accurate; README baseline confirmed |
| 1 | Database Schema, Security & PII | COMPLETE | 2026-05-19 | 6 migrations: court_forms / trigger_events / deadlines tables; packets uuid migration (31 rows survived); cost cols on usage_stats; pg_cron; 9 RLS policies; 2 retention jobs. Manual gaps: anon sign-in, Presidio PII redaction |
| 2 | Form Catalog & Version-Aware Permanent Cache | COMPLETE | 2026-05-19 | court-forms bucket; court_forms table seeded from CSV; GET /api/forms/{num} endpoint; POST /api/forms/check-updates; harvest script. Manual gaps: browser harvest of all PDFs; OSCA contact; pg_cron app.backend_url setting |
| 3 | Statutes, Court Rules & Local AOs Corpus | COMPLETE | 2026-05-19 | statutes / court_rules / local_administrative_orders / court_closures tables; law_sources.json; /api/law/* router; ingest_statutes.py. Manual gap: run ingest_statutes.py --all-priority; 19th Circuit AOs |
| 4 | The Deadline Engine | COMPLETE | 2026-05-19 | backend/deadline/rules.py (8 rules, 2.514, FL holidays); compute.py (deterministic, full trace); extract.py (LLM stage 1); pipeline.py; 16 tests pass |
| 5 | The Document Triage Classifier | COMPLETE | 2026-05-19 | backend/triage/classify.py (13 types); router.py (ALWAYS_ESCALATE_TYPES); /api/triage/* router; 16 tests pass |
| 6 | The Reminder & Notification Scheduler | COMPLETE | 2026-05-19 | reminders.py (severity-scaled schedule); notifications.py (Expo push + email stub); hourly cron endpoint; EN/ES copy; 14 tests pass. Manual gap: set app.backend_url + app.api_key in Supabase |
| 7 | The Evaluation Harness | COMPLETE | 2026-05-19 | 50-doc eval set; locked ground_truth.json; run_all.py (fast mode CI / --full manual); eval-deadline.yml CI; 45/45 pass, 34/34 fatal = 100% |
| 8 | UPL Wall & Escalation Enforcement | COMPLETE | 2026-05-19 | upl.py (5 triggers, FATAL_CONFIDENCE_THRESHOLD=0.90, URGENT_HOURS=72); EN/ES disclaimers 3 levels; /api/analysis/* router; REVIEW_TEMPLATE.md + OUTPUT_AUDIT.md; 25 tests pass. Manual gap: FL attorney review |
| 9 | Police Report Scanner: CaseContext Activation | COMPLETE | 2026-05-19 | case_context.py (empty_case_context mirrors types.ts); scanner.py extended (CASE_CONTEXT_PROMPT + extract_case_context, findings flow unchanged); police_report.py router returns case_context alongside findings; CaseContextBanner.tsx above findings; AnalyzeResponse extended; V2_LEDGER.md created |
| 10 | Form Library Ingest (167-form corpus) | COMPLETE | 2026-06-15 | migration `20260615120000_phase_10_form_library.sql` (form_text, plain_language_summary, situation_tags, review_reason, bucket_path cols; status default 'review'; FTS gin index). `scripts/ingest_forms.py` = deterministic clean→dedupe→gate→upload→load→emit (dropped 11 test-junk; 2 superseded dupes; gate by metadata quality). 154 forms in court-forms bucket + court_forms: **25 published** (clean statewide-numbered, real titles, servable) + **129 review** (gated: suspect_metadata/circuit_local/no_form_number/failed_extraction/superseded). forms.py serves status in (published, active). LLM enrichment OFFLOADED: `forms/run_enrichment.py` (DeepSeek, not run) → `enrichment_output.jsonl` → `scripts/writeback_form_enrichment.py` (not run) writes summary+tags+title back. Leftover: 32 unverified seed stubs (no file), 1 legacy active row |

---

## Open manual gaps (non-engineering, gate public launch)

1. **Railway SUPABASE_SERVICE_KEY** — wrong value in `zesty-delight`; service-role JWT required (not anon key). Verify payload `"role": "service_role"` at jwt.io before pasting.
2. **Supabase anonymous sign-in** — enable in Auth dashboard (Phase 1).
3. **Presidio PII redaction** — post-extraction pass over `document_text` (Phase 1).
4. **Form harvest** — DONE (Phase 10): 154 forms ingested via `scripts/ingest_forms.py`. Remaining: run LLM enrichment + writeback (see item 14).
5. **OSCA contact** — initiate access arrangement (Phase 2).
6. **Supabase pg_cron app settings** — set `app.backend_url` + `app.api_key` in DB Configuration (Phases 2, 6).
7. **Statute ingest** — `cd backend && uv run python ../scripts/ingest_statutes.py --all-priority` (Phase 3).
8. **19th Circuit AOs** — review `19thcircuit.org/administrative-orders`, seed `local_administrative_orders` (Phase 3).
9. **Full LLM eval** — run `python -m evals.run_all --full` before launch (Phase 7).
10. **FL attorney review** — complete `attorney_review/REVIEW_TEMPLATE.md` with FL attorney; retain signed copy (Phase 8).
11. **Terms of Service** — draft + review (parallel workstream, gates launch).
12. **Tech E&O insurance** — obtain before public launch.
13. **Operating entity** — LLC/corp formation.
14. **Form enrichment + writeback** — DONE 2026-06-15. DeepSeek enrichment (cheap agent, off-box) → `forms/enrichment_output.json` (109 records); `scripts/writeback_form_enrichment.py --execute` updated 106 rows (plain_language_summary + situation_tags + corrected titles). `situation_tags` normalized to snake_case in DB. `12.980(g)` re-enriched as a single record (Claude, DeepSeek key not on this box). Model QA flagged 2 `published` forms as not-single-form → demoted to `review` (`12.931(a)`, `12.980(j)`). State (2026-06-15): **58 published** (all enriched), 96 review. Promoted 35 Group-A `suspect_metadata` forms (clean statewide numbers + corrected titles) after title eyeball; 4 bad titles fixed first (`12.980(n)` + 3 circuit5 packets). **Follow-ups:** (a) still on `review` by design — 9 `12.980` DV/injunction forms (HOLD for attorney review), Group B eviction/probate (synthetic keys — assign real form numbers?), Group C circuit_local, Group D `12.980(o)` scanned (empty text); (b) 3 enrichment records had no catalog row (`12.930(a)`, `12.980(k)`×2) — skipped; (c) 32 `unverified` seed stubs + 1 legacy `active` row still unreconciled; (d) **`12.980` series file→number scramble** — `12.980_g_.txt` header reads `12.980(k)`, `12.980(j)`'s text was `(g)`'s; likely legacy FL renumbering, verify file→number mapping against official FL forms before trusting the numbers.
