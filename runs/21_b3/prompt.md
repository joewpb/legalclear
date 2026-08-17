# TASK: B3 — S3-5e. Verifier silence: log every rejected date. Single surface.

Repo: backend/ is this repo. Run shape: sonnet, capped 40 turns / $3.
Branch: fix/b3-s3-5e-verifier-logging (already checked out).

## Defect
backend/deadline/extract.py: `_date_appears_in_text` is the deterministic
anti-hallucination guard (from the extract-hallucinated-date lineage, plus S2-5c's
ordinal support — both merged). When it rejects an extracted date, `_sanitize_events`
nulls it silently (well, it logs a warning at the `_sanitize_events` level with the
rejected value — RE-CHECK: the pre-existing warning includes the value but NOT the
surrounding text context; and any rejection that happens WITHOUT the warning path is
invisible). The legal date phrasing space is unbounded ("DATED this 14th day of
August", "the 3rd day of June", Spanish dates, etc.) — you cannot enumerate your way
out; the misses must be VISIBLE so each new phrasing failure is diagnosable from logs.

## Fix
1. Every rejection must log, with: the rejected ISO date string, the document
   identifier or a stable doc hash if available in scope (otherwise a truncated text
   head), the surrounding text span (e.g. ±80 chars around the best-miss location —
   find the nearest numeric occurrence in the text if the date is not found verbatim),
   and which variant family failed (iso/numeric-us/textual/ordinal).
2. Keep a rejection counter/tally in the returned data (e.g.
   `data["rejected_dates"] = [...]` capped at a small number, say 10) so tests and
   downstream can assert visibility — do NOT change the nullification behavior itself
   (dates still get nulled + escalation set; S2-5c semantics stay intact).
3. Do NOT weaken `_date_appears_in_text`. Adding variants is allowed ONLY if they are
   unambiguous (e.g. clearly-safe textual forms) and covered by tests — but the task's
   core is logging, not matcher expansion.

## Tests (red→green)
- A rejected date appears in the logged/tally structure with a text span.
- The matcher still rejects a fabricated date (regression guard).
- Existing sanitize/ordinal tests keep passing.
Full CI-scope suite command (exact):
  cd backend && uv run pytest tests/ -q --ignore=tests/test_full_v1.py
  --ignore=tests/test_phase_2.py --ignore=tests/test_phase_16.py
  --ignore=tests/test_phase_17.py --ignore=tests/test_phase_18.py
  --ignore=tests/test_phase_20.py --ignore=tests/test_phase_21.py
  --ignore=tests/test_phase_22.py --ignore=tests/test_phase_23.py
  --ignore=tests/test_pc_integration.py
NOTE: this branch was cut from main WITHOUT B1's changes (B1 is on
fix/b1-s2-7-date-anchors and also edits extract.py). Overlap is expected and fine —
note it in your report, do not reconcile.

## Rules
- uv only. No migrations, no DDL, no prod writes, no secrets.
- Report: file:line of the change, the log shape, test evidence (red→green),
  suite count, overlap note.
