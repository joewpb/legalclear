# TASK: B1 — S2-7 date anchors. DIAGNOSE FIRST, then fix. Two parts, strict order.

Repo: backend/ is this repo. Run shape: fable, capped 50 turns / $6.
Branch: fix/b1-s2-7-date-anchors (already checked out for you).

## Background (verified facts, do not re-verify)
- The deadline pipeline computes the tenant answer deadline for a residential eviction
  summons from Fla. Stat. § 83.60(2): "5 business days after service of process."
- Smoke test evidence (2026-08-14): a summons with the line "DATED this 14th day of
  August, 2026" produced one trigger event (type "issued", event_date 2026-08-14) and a
  deadline due 2026-08-21, computed from the ISSUANCE date.
- Fla. Stat. § 83.60(2) runs the 5-day period from SERVICE OF PROCESS, not issuance.
  Service commonly occurs days after issuance. Computing from the wrong anchor can
  produce a default judgment. This is S2-7, a CORRECTNESS BLOCKER (see FOLLOW_UPS.md).

## PART 1 — DIAGNOSE. No code changes until this is reported with file:line evidence.
Answer exactly these three questions, separating VERIFIED from INFERRED:
(a) Does the extractor distinguish issuance date, service date, and hearing date —
    i.e. does the extraction schema/prompt have separate fields or date-type labels —
    or does it treat every extracted date as an interchangeable "event_date"?
(b) Does each deadline rule declare which anchor (event type / date kind) it requires?
    Inspect the rule base: deadline rules table/JSON/py — does a rule know it needs a
    SERVICE date rather than any date?
(c) What happens today when the required anchor is absent (e.g. only an issuance date
    exists)? Trace pipeline.py end to end and state the exact behavior.
(d) BONUS (decides a product question, report only): can a service date realistically
    be extracted from a summons at all? A summons typically bears issuance/signature
    dates; proof of service is a separate return-of-service document. State what the
    extraction path CAN and CANNOT see, with file:line.
Report Part 1 in your final message BEFORE any edits. If you cannot determine (a)-(c)
from code, say so plainly and stop.

## PART 2 — FIX (only after Part 1 is reported)
1. Rules declare their required anchor: each deadline rule must specify which event
   kind(s) it can consume (e.g. service_date). A rule must never be applied to a date
   it did not ask for.
2. Extractor labels date types: where the schema supports it, emit event dates with a
   kind/type label (issued / served / hearing / filed / other) instead of one
   undifferentiated event_date. Keep the existing event_date field for compatibility
   if callers depend on it — do not break the schema other tests assert.
3. Absent required anchor → SKIP the rule and ESCALATE. Never substitute a different
   date (issuance must never stand in for service). Follow the existing escalation
   pattern (S3-5c / pipeline escalation_reason).

## PART 3 — THE PRODUCT QUESTION — REPORT, DO NOT DECIDE
If Part 1(d) shows service dates are generally NOT extractable from summons documents,
report that clearly as a product decision owed to Joe: "ask the user when they were
served" vs "refuse to compute". Do NOT implement either. This is a legal-correctness
decision; the plan forbids you from making it.

## Rules
- uv for Python. No pip. No migration files, no DDL, no prod writes.
- Tests: every change covered. Show red→green evidence for at least: (1) a rule whose
  anchor is absent is skipped and escalated (no substitution), (2) the extractor labels
  date kinds when the model returns them. Do not weaken existing tests — the CI-scope
  suite (below) must pass.
- Full CI-scope suite command (exact):
  cd backend && uv run pytest tests/ -q --ignore=tests/test_full_v1.py
  --ignore=tests/test_phase_2.py --ignore=tests/test_phase_16.py
  --ignore=tests/test_phase_17.py --ignore=tests/test_phase_18.py
  --ignore=tests/test_phase_20.py --ignore=tests/test_phase_21.py
  --ignore=tests/test_phase_22.py --ignore=tests/test_phase_23.py
  --ignore=tests/test_pc_integration.py
- Do not commit secrets; do not print API keys.
- Report: Part 1 answers (VERIFIED vs INFERRED), the Part 2 changes with file:line,
  test evidence, and the Part 3 product question if it applies.
