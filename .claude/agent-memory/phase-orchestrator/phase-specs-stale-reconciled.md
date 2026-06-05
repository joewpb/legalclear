---
name: phase-specs-stale-reconciled
description: PHASE_SPECS.md Part B section was stale (claimed all PENDING / 0% built); reconciled to COMPLETE against repo on 2026-06-05
metadata:
  type: project
---

`phases/PHASE_SPECS.md` Part B table + notes drifted out of sync with
`phases/LEDGER.md`. On 2026-06-05 it still claimed phases 15-23 were all
PENDING and "Part B is 0% built", and listed the 6 Part A divergences as
"Decision pending / hard blocker." All of that was stale.

**Why:** PHASE_SPECS.md is a hand-maintained index over LEDGER.md +
`phases/source/`. It was not updated when v1 shipped 2026-05-15.

**How to apply:** LEDGER.md and the repo win over PHASE_SPECS.md every time
(stated reconciliation rule at the top of both files). Reconciled
PHASE_SPECS.md to COMPLETE for 15-23 and marked all 6 Part A divergences
RESOLVED. Ground truth: all 8 tile `.tsx` pages, Part B routers, scanner.py,
4 packet services, EN/ES data, uv.lock — all present + committed. See
[[phase-23-shipped]] and [[mode-b-hardened]]. brutalist.css was renamed to
`frontend/src/styles/theme.css` in the v1 retheme — it is not missing.

If a future task arrives framed as "phases 15-23 are PENDING, begin Phase 15,"
that framing is inherited from the old stale PHASE_SPECS.md — verify the repo
first; do NOT rebuild Part B.
