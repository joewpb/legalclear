# LegalClear — v2 Phase Ledger

**Single source of truth for v2 build state.**
v1 state lives in `phases/LEDGER.md`. This file tracks phases defined in
`phases/BUILD_PLAN.md` (Phases 0–N). If this ledger disagrees with the repo,
the repo wins — re-verify and correct.

Status values: `COMPLETE` · `IN PROGRESS` · `PENDING` · `BLOCKED`

---

| # | Title | Status | Date | Notes |
|---|-------|--------|------|-------|
| 0 | Stabilize the Foundation | COMPLETE | 2026-05-19 | Repo cleanup; AGENTS.md Core Principles; BUILD_PLAN.md + seed CSV placed; 3 PRs closed; secrets rotated; gitleaks + eval-deadline CI workflows added; Node 24 opt-in |
| 1 | Database Schema, Security & PII | COMPLETE | 2026-05-19 | 6 migrations: court_forms / trigger_events / deadlines tables; packets uuid migration (31 rows survived); cost cols on usage_stats; pg_cron; 9 RLS policies; 2 retention jobs. Manual gaps: anon sign-in, Presidio PII redaction |
| 2 | Form Catalog & Version-Aware Permanent Cache | COMPLETE | 2026-05-19 | court-forms bucket; court_forms table seeded from CSV; GET /api/forms/{num} endpoint; POST /api/forms/check-updates; harvest script. Manual gaps: browser harvest of all PDFs; OSCA contact; pg_cron app.backend_url setting |
| 3 | Statutes, Court Rules & Local AOs Corpus | COMPLETE | 2026-05-19 | statutes / court_rules / local_administrative_orders / court_closures tables; law_sources.json; /api/law/* router; ingest_statutes.py. Manual gap: run ingest_statutes.py --all-priority; 19th Circuit AOs |
| 4 | The Deadline Engine | COMPLETE | 2026-05-19 | backend/deadline/rules.py (8 rules, 2.514, FL holidays); compute.py (deterministic, full trace); extract.py (LLM stage 1); pipeline.py; 16 tests pass |
| 5 | The Document Triage Classifier | COMPLETE | 2026-05-19 | backend/triage/classify.py (13 types); router.py (ALWAYS_ESCALATE_TYPES); /api/triage/* router; 16 tests pass |
| 6 | The Reminder & Notification Scheduler | COMPLETE | 2026-05-19 | reminders.py (severity-scaled schedule); notifications.py (Expo push + email stub); hourly cron endpoint; EN/ES copy; 14 tests pass. Manual gap: set app.backend_url + app.api_key in Supabase |
| 7 | The Evaluation Harness | COMPLETE | 2026-05-19 | 50-doc eval set; locked ground_truth.json; run_all.py (fast mode CI / --full manual); eval-deadline.yml CI; 45/45 pass, 34/34 fatal = 100% |
| 8 | UPL Wall & Escalation Enforcement | COMPLETE | 2026-05-19 | upl.py (5 triggers, FATAL_CONFIDENCE_THRESHOLD=0.90, URGENT_HOURS=72); EN/ES disclaimers 3 levels; /api/analysis/* router; REVIEW_TEMPLATE.md + OUTPUT_AUDIT.md; 25 tests pass. Manual gap: FL attorney review |
| 9 | Police Report Scanner: CaseContext Activation | COMPLETE | 2026-05-19 | case_context.py (empty_case_context mirrors types.ts); scanner.py extended (CASE_CONTEXT_PROMPT + extract_case_context, findings flow unchanged); police_report.py router returns case_context alongside findings; CaseContextBanner.tsx above findings; AnalyzeResponse extended; V2_LEDGER.md created |

---

## Open manual gaps (non-engineering, gate public launch)

1. **Railway SUPABASE_SERVICE_KEY** — wrong value in `zesty-delight`; service-role JWT required (not anon key). Verify payload `"role": "service_role"` at jwt.io before pasting.
2. **Supabase anonymous sign-in** — enable in Auth dashboard (Phase 1).
3. **Presidio PII redaction** — post-extraction pass over `document_text` (Phase 1).
4. **Form harvest** — download all PDFs via browser; run `scripts/harvest_form.py` per form (Phase 2).
5. **OSCA contact** — initiate access arrangement (Phase 2).
6. **Supabase pg_cron app settings** — set `app.backend_url` + `app.api_key` in DB Configuration (Phases 2, 6).
7. **Statute ingest** — `cd backend && uv run python ../scripts/ingest_statutes.py --all-priority` (Phase 3).
8. **19th Circuit AOs** — review `19thcircuit.org/administrative-orders`, seed `local_administrative_orders` (Phase 3).
9. **Full LLM eval** — run `python -m evals.run_all --full` before launch (Phase 7).
10. **FL attorney review** — complete `attorney_review/REVIEW_TEMPLATE.md` with FL attorney; retain signed copy (Phase 8).
11. **Terms of Service** — draft + review (parallel workstream, gates launch).
12. **Tech E&O insurance** — obtain before public launch.
13. **Operating entity** — LLC/corp formation.
