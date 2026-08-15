# TASK: S2-5c — diagnose the missing date extraction, then fix the epoch placeholder.
Two parts. Part 1 MUST be reported before any code changes.

Repo: backend/ is this repo. Run shape: sonnet, capped.

## Context (smoke-test facts, live prod, 2026-08-14)
A Lee County residential eviction summons was uploaded through the live pipeline:
- document_text stored correctly (S2-5a fixed); /process classified it as
  eviction_summons_residential (Lee County, FL).
- POST /api/deadline/analyze returned 200: trigger_events_written=1, deadlines_written=0.
- The one written trigger_event has event_date "1970-01-01" (epoch placeholder) and
  event_type "issued".
- `backend/deadline/pipeline.py:232` writes `event.get("event_date") or "1970-01-01"`.

The test document's full text (as uploaded — a synthetic summons used for the smoke
test):
---
IN THE COUNTY COURT OF THE TWENTIETH JUDICIAL CIRCUIT
IN AND FOR LEE COUNTY, FLORIDA
EVICTION SUMMONS - RESIDENTIAL
TO: John Doe
You are being sued by the landlord. You must respond to this complaint
in writing within 5 business days after the date this summons is served
on you. Your written response must be filed with the Clerk of Court.
A hearing in this matter is scheduled for August 28, 2026 at 9:00 a.m.
in Courtroom 4A of the Lee County Courthouse.
If you do not respond within the required time, a default judgment
may be entered against you without further notice.
DATED this 14th day of August, 2026.
---

An eviction summons is composed almost entirely of dates. Extraction returning NO usable
date is the actual failure. The epoch placeholder is only a symptom.

## Part 1 — DIAGNOSE FIRST (no code changes until this is reported)
Trace document_text → extractor → `event.get("event_date")` and determine why the value
was absent for this document. Check at minimum, each with file:line evidence:
1. What the extractor is supposed to return (read backend/deadline/extract.py fully):
   the LLM prompt, the response schema it requests, and the parse code. Quote the
   relevant prompt lines.
2. Whether the KEY the extractor emits matches the key pipeline.py reads at :232.
   A key-name mismatch produces exactly this symptom — check this carefully.
3. Whether the extraction prompt asks for dates in a format the parser accepts, and
   what the parser accepts vs rejects.
4. Whether the date was extracted but rejected downstream by a parse or validation
   step (search for date parsing in backend/deadline/*).
5. Whether ANY deadline rule would have matched even with a correct date — read the
   rule definitions; is rule-matching a second, independent gap for eviction events?
Also, if it can be done WITHOUT network access beyond the existing local keys and
without writing anything outside the repo, RUN the real extractor against the sample
text above (a uv run python one-liner using backend/.env keys, following however
existing tests invoke it) and report the ACTUAL output shape/keys it returned — the
verbatim dict minus any secret. This is the highest-value evidence. Do NOT log any key.
Separate VERIFIED from INFERRED. If the cause cannot be determined from code + a local
extractor run, say so and stop.

## Part 2 — Fix (only after Part 1 is reported)
1. Remove the epoch placeholder: an event with no usable date must be skipped and
   escalated, never written as 1970-01-01. Mirror the escalation shape from S3-5c
   (backend/src/core/upl.py: except branch appends a reason, sets urgency=immediate,
   disclaimer_level=urgent — read it).
2. Fix the Part 1 root cause IF it is a mechanical defect (key mismatch, format
   mismatch, parse rejection). If it is prompt-quality or rule-coverage, do NOT attempt
   it — report it as a separate item and stop after change 1.
Tests: one asserting no epoch row is ever written (pipeline test, mocking the extractor
to return no date), one covering the root-cause fix (fails before, passes after).
Both shown red→green.

## Also in scope — log only, one entry in FOLLOW_UPS.md
backend/src/api/routers/deadline.py's disclaimer carries EXTERNAL links
(floridalawhelp.org, floridabar.org) — contradicts the no-external-links rule. Do NOT
fix. Add a FOLLOW_UPS.md entry: this is a THIRD parallel disclaimer text — direct
evidence for consolidating on a single apply_disclaimer source rather than patching
each site. Note it in the UPL fix footprint.

## Rules
- uv for Python. No pip, no poetry.
- Do not touch upload/process/analyze handlers except the named lines.
- Full suite green (CI-scope command, exact):
  cd backend && uv run pytest tests/ -q --ignore=tests/test_full_v1.py
  --ignore=tests/test_phase_2.py --ignore=tests/test_phase_16.py
  --ignore=tests/test_phase_17.py --ignore=tests/test_phase_18.py
  --ignore=tests/test_phase_20.py --ignore=tests/test_phase_21.py
  --ignore=tests/test_phase_22.py --ignore=tests/test_phase_23.py
  --ignore=tests/test_pc_integration.py
- Report: Part 1 diagnosis (VERIFIED vs INFERRED), Part 2 changes, test evidence,
  what could regress.
