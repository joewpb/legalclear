---
name: source-part-a
description: Canonical verbatim source for Part A phases 0-14 lives in two identical files at repo root
metadata:
  type: reference
---

Canonical Part A build prompt:
- `LegalClear_OneShot_Prompt.md` (3079 lines)
- `Complete One Shot Build.md` (same content, identical bytes)

Both files at repo root. Phases 0-14 only — Part B (15-23) is not in this
document. The oneshot defines:
  0 Scaffold · 1 Document ingestion · 2 Core utilities · 3 Classifier ·
  4 Explainer · 5 Form guide · 6 Risk scanner · 7 Expungement ·
  8 Memory layer · 9 Payments · 10 API · 11 Florida courts ·
  12 Web frontend · 13 Mobile app · 14 Deploy

Each phase ends with a `test_phaseN.py` (where N=1..9, 11) plus an inline
verify block for Phase 0 and a route-enum check for Phase 10 and a
final deploy checklist for Phase 14. Test files live at `backend/test_phaseN.py`.

Two policies were hardened AFTER the oneshot and supersede parts of it:
1. Railway deploy supersedes the oneshot's systemd + nginx plan
   (see [[phase-14-railway-supersedes-systemd]]).
2. Mode B automation is now banned in `backend/src/`
   (see [[mode-b-hardened]]).

When reconciling, the oneshot is canonical for names/structure, but
`AGENTS.md` is canonical for policy.
