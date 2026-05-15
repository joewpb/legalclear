---
name: phase-14-railway-supersedes-systemd
description: Phase 14 deploy uses Railway not systemd; oneshot's systemd+nginx plan is superseded
metadata:
  type: project
---

Phase 14 (Deploy) ships via **Railway**, not the oneshot's systemd +
nginx plan.

**Why:** The oneshot prescribed local systemd services
(`legalclear-backend.service`, `legalclear-frontend.service`) and an
nginx reverse proxy. The project moved to Railway hosting instead.
Joe confirmed Railway is canonical on 2026-05-14, same precedent as the
Mode B policy hardening (see [[mode-b-hardened]]).

**How it actually deploys:**
- Backend: `backend/nixpacks.toml` + `backend/railway.json` →
  Railway service `zesty-delight`.
- Frontend: `frontend/nixpacks.toml` + `frontend/railway.json` →
  Railway service `appealing-victory`.
- Repo root also has top-level `nixpacks.toml` and `railway.json`.

**How to apply:**
- Phase 14 verification checks for nixpacks/railway config files, not
  systemd unit files or nginx.conf.
- The oneshot's final deploy block (systemctl, /etc/systemd/system,
  sed YOUR_USERNAME) is dead. Do not run it. Do not transcribe it
  into PHASE_SPECS.md.
- The repo's `deploy/` directory may still contain `supabase_schema.sql`
  (legitimate, Phase 8) plus possibly orphaned systemd unit files
  (ignore for Phase 14 purposes).
