---
name: phase-12-i18n-deferred
description: i18next is installed in frontend/package.json but no useTranslation calls in frontend/src/; en/es wiring is deferred to Part B Phase 17
metadata:
  type: project
---

The frontend has `i18next` and `react-i18next` listed in
`frontend/package.json`, but `grep -rIl "i18next\|useTranslation" frontend/src/`
returns zero hits. There is **no runtime i18n wiring** in the web app today.

**Why this is correct, not broken:**
- The oneshot's Phase 12 prescribes installing the i18next dependency.
- The actual en/es runtime layer (provider, translations dir, language toggle on
  the review screen) is **Part B Phase 17** — that's what wires the dep up.
- So `i18next` installed-but-unused is the expected state between Phase 12
  completing and Phase 17 starting.

**How to apply:**
- Do NOT regression-flag the absence of `useTranslation` calls as a Phase 12 failure.
- When Phase 17 source lands (see [[source-part-b-missing]]), it will define
  the actual wiring: provider, `en.json`/`es.json` resource files,
  language toggle, and the review screen language switch.
- Stripe product description and `Languages live: en, es` in the final report
  depend on Phase 17 actually wiring this — until then, do NOT claim en/es is live.
