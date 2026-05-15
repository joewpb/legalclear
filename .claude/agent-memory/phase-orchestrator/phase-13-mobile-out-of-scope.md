---
name: phase-13-mobile-out-of-scope
description: Phase 13 mobile app is intentionally out of v1 scope; mobile/ is empty by design
metadata:
  type: project
---

Phase 13 (Mobile app — Expo / React Native) is **OUT-OF-SCOPE for v1**.

**Why:** Joe explicitly dropped it from v1 scope on 2026-05-14 after the
Part A verification sweep found `mobile/` empty. The oneshot specifies
an Expo build there; the decision is to ship v1 web-only and revisit
mobile later.

**How to apply:**
- Do NOT build anything in `mobile/`.
- Do NOT mark Phase 13 as BLOCKED or FAIL — its status is `OUT-OF-SCOPE`.
- An empty `mobile/` directory is the expected, correct state.
- If a future verification step trips on Phase 13 emptiness, that step is
  wrong — fix the step, not the directory.
- If Joe later un-drops it, this memory should be revised, not deleted.

Related: [[phase-14-railway-supersedes-systemd]] —
Phase 14 also diverges from the oneshot under the same precedent
(documented policy override).
