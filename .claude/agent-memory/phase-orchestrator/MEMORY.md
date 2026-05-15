# phase-orchestrator — MEMORY.md

Index of durable, cross-session facts. `phases/LEDGER.md` is canonical for
build state; `phases/source/PHASE_NN_*.md` is canonical for phase spec;
this file is for context not derivable from those.

- [Canonical source location](source-canonical.md) — `phases/source/PHASE_NN_*.md` is the verbatim spec for every phase; PHASE_SPECS.md + LEDGER.md are thin indexes over it
- [Part A source — superseded](source-part-a.md) — `LegalClear_OneShot_Prompt.md` is historical; per-phase files at `phases/source/` are now canonical
- [Phase numbering — canonical mapping](phase-numbering-correction.md) — real Part A names per source; two prior wrong mappings flagged
- [Part A source divergences](part-a-source-divergences.md) — 6 documented drift points; #1 (pyproject.toml) and #5 (TS config) block Phase 15 start
- [Repo layout cheatsheet](repo-layout.md) — source path vs repo path for every Phase 0-14 deliverable; Part B is 0% built
- [Hub has 8 tiles](hub-8-tiles.md) — Phase 15 spec, fixed order, resolves prior 6-vs-8 question
- [Phase 23 scope](phase-23-scope.md) — Phase 23 is one phase but the heaviest; PacketBuilder + PDF/A + EN/ES + $35 Stripe + tracker + full-v1 smoke
- [Phase 13 mobile not built](phase-13-mobile-out-of-scope.md) — `mobile/` empty; source policy is "do not block"; OOS for Phases 15-23
- [Phase 14 Railway deploy](phase-14-railway-supersedes-systemd.md) — Railway via nixpacks/railway.json; systemd+nginx referenced in source but not required
- [Mode B hardened](mode-b-hardened.md) — no `myflcourtaccess` automation in `backend/src/`; Phase 23 `test_no_mode_b` enforces with string scan; Playwright IS permitted (used for PDF generation)
- [Backend uvicorn target](backend-uvicorn-target.md) — verification tests need `uvicorn src.api.routes:app`, NOT `main:app` (Phase 10 split entrypoint from app module)
- [Phase 23 shipped](phase-23-shipped.md) — tile-generate response shape changed by design (now `{packet_id, fee_usd, file_count, checkout_url}`); packet store is in-memory with Supabase mirror best-effort
