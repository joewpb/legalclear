---
name: source-part-a
description: SUPERSEDED — Part A source moved from LegalClear_OneShot_Prompt.md to per-phase files at phases/source/PHASE_00..14_*.md
metadata:
  type: reference
---

**Superseded by [[source-canonical]] as of 2026-05-14.**

The earlier "oneshot is canonical" framing was wrong. The per-phase source
files at `phases/source/PHASE_NN_*.md` are now canonical for all 24 phases.

The oneshot files at repo root (`LegalClear_OneShot_Prompt.md`,
`Complete One Shot Build.md`) drift from the per-phase source in
multiple places — most importantly Phase 1 (per-phase source: memory
layer / DB; oneshot: document ingestion) and Phase 2 (per-phase source:
PDF processor; oneshot: classifier in some readings, "core utilities" in
others). Treat the oneshot as historical only.

When reconciling Part A status against the repo, use
`phases/source/PHASE_00..14_*.md` — never the oneshot.
