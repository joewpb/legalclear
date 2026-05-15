---
name: source-part-b-missing
description: Part B deliverables + code (Phases 15-23) come from the May 12 doc; phases/PHASE_SPECS.md (v2) carries goal/verify/pass but each phase still has a [POINTER] awaiting splice
metadata:
  type: project
---

Part B (Phases 15-23) source: `LegalClear_Complete_Phases_0-23.md` /
"AI legal app clarification" chat, 2026-05-12. Joe holds the original.

**Status as of 2026-05-14:** `phases/PHASE_SPECS.md` is v2 — it already
carries goal / verify / pass for every Part B phase (cross-confirmed from
retrievals on the May 12 doc). What's still missing per phase is the
deliverables + code splice. Each Part B phase carries a line like:

```
<<< VERBATIM SOURCE: Phase N deliverables + code — splice from May 12 doc >>>
```

Treat each of these as a [POINTER] = "not yet sourced." Until the splice
lands for a phase, that phase is unexecutable.

**Why:** v2's goal/verify/pass is solid (cross-confirmed). The deliverables
+ code body is not retrievable through search and only Joe's copy of the
May 12 doc has it. Inventing it is a worse failure than halting.

**How to apply:**
- Orchestrator hard-stops at Phase 14.
- Do NOT execute any Phase 15-23 work — including reconstructing specs
  from the v1 smoke test — until the relevant `<<< VERBATIM SOURCE >>>`
  marker is resolved.
- On session start, scan `phases/PHASE_SPECS.md` for remaining
  `<<< VERBATIM SOURCE >>>` markers. Each one is a hard stop for its phase.
- When Joe pastes a splice for Phase N, the marker for that phase is
  replaced with the verbatim deliverables + code from the May 12 doc.
  Verify the splice is in place, then execute Phase N per its spec.

**Two structural items to confirm at splice-time** (cannot be resolved
from repo today — see [[repo-layout]]):
- 6-tile vs 8-tile drift on the hub (v2 says only "a Small Claims tile";
  no Hub UI exists yet).
- Phase 23 is one phase, not a 9-way split — v2 final-report block lists
  Phases 15…23 (9 phases) and Phase 23 aggregates 10 test files
  (test_phase_15.py … test_phase_23.py + test_full_v1.py).
