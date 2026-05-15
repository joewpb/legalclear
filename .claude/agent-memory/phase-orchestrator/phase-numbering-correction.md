---
name: phase-numbering-correction
description: Original LEDGER.md Part A phase names were misaligned with the oneshot source; corrected 2026-05-14
metadata:
  type: project
---

On 2026-05-14 the ledger's Part A rows were rewritten to match
`LegalClear_OneShot_Prompt.md`. The earlier ledger version had the
phase names shifted starting at Phase 2: it labeled Phase 2 as "Classifier",
Phase 3 as "Explainer", etc., and treated Phases 10-14 as STUBs.

**The actual mapping (canonical):**
  0 Scaffold · 1 Document ingestion · 2 Core utilities · 3 Classifier ·
  4 Explainer · 5 Form guide · 6 Risk scanner · 7 Expungement ·
  8 Memory layer · 9 Payments · 10 API · 11 Florida courts ·
  12 Web frontend · 13 Mobile app · 14 Deploy

**Why this matters:** prior reconciliation reports may exist (in chat
history or commits) that use the WRONG mapping. If a finding refers to
"Phase 9 mobile" or "Phase 2 classifier", it predates the correction —
treat its phase numbers as suspect and re-map against the canonical list
above.

**How to apply:** when reading any older artifact that references Part A
phase numbers, sanity-check against the canonical mapping before
trusting the claim.
