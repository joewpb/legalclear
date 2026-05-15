---
name: phase-13-mobile-out-of-scope
description: Phase 13 mobile/ is empty in the repo; source spec verifies it but explicitly says "do not block" — out of scope for Part B
metadata:
  type: project
---

Phase 13 (Mobile App — Expo / React Native) is **NOT BUILT** in the repo:
`mobile/` is empty.

**Per `phases/source/PHASE_13_mobile_app.md`:**
- The phase IS spec'd: source verifies `mobile/App.tsx`, `mobile/app.json`,
  `mobile/package.json` exist.
- Source policy on verify failure: "Note it in the final report but do
  NOT block. Mobile is deferred."
- Source explicitly states: **"Mobile work is OUT OF SCOPE for
  Phases 15-23. Web first, then mobile catches up."**
- Phase 23 source confirms: "Phase 23's filing packet flow does NOT
  require mobile parity in v1."

**Why this matters:** the source treats Phase 13's empty `mobile/` as a
documented gap, not a build failure. The orchestrator ledger marks it
`NOT BUILT — no-block`, which is the source's intended status. Earlier
ledger versions used `OUT-OF-SCOPE` — functionally compatible but the
source's phrasing is "deferred / do not block."

**How to apply:**
- Do NOT build anything in `mobile/` during Phases 15-23.
- Do NOT mark Phase 13 BLOCKED or FAIL — its ledger status is
  `NOT BUILT — no-block`.
- In the final deployment report, note Phase 13's status under
  "TODOs remaining" or equivalent — never as a "Blocking issue."
- If Joe later un-defers mobile (post-v1), this memory should be
  revised, not deleted.

Related: [[part-a-source-divergences]] — Phase 13's empty `mobile/` is one
of six documented Part A reality-vs-source divergences.
