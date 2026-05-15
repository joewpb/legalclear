# phase-orchestrator — MEMORY.md

Index of durable, cross-session facts. `phases/LEDGER.md` is canonical
for build state; this file is for context not derivable from the ledger
or the repo alone.

- [Canonical Part A source](source-part-a.md) — `LegalClear_OneShot_Prompt.md` (== `Complete One Shot Build.md`) is the verbatim Part A build prompt
- [Part B source missing](source-part-b-missing.md) — `LegalClear_Complete_Phases_0-23.md` not yet supplied; hard stop at Phase 14
- [Phase numbering corrected 2026-05-14](phase-numbering-correction.md) — original ledger had Part A phase names shifted starting at Phase 2; now matches oneshot
- [Phase 13 mobile is out of scope](phase-13-mobile-out-of-scope.md) — `mobile/` is intentionally empty; do not build, do not flag as fail
- [Phase 14 deploy uses Railway not systemd](phase-14-railway-supersedes-systemd.md) — oneshot's systemd+nginx plan superseded by Railway nixpacks config
- [Mode B policy hardened vs oneshot](mode-b-hardened.md) — oneshot allowed optional FL portal automation; AGENTS.md §7 now bans it in `backend/src/`
- [Repo layout cheatsheet](repo-layout.md) — backend/src/ tree and where each Phase 0-14 deliverable lives
- [Playwright is a landmine](playwright-landmine.md) — listed in requirements.txt but unused; not a violation today, recommend removal in Phase 22
- [Phase 12 i18n wiring deferred](phase-12-i18n-deferred.md) — `i18next` installed but not wired; en/es runtime is Part B Phase 17, do not regression-flag
