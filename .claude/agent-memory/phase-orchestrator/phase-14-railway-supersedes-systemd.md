---
name: phase-14-railway-supersedes-systemd
description: Phase 14 deploy is Railway-only in practice; source mentions systemd+nginx but Railway nixpacks/railway.json are the active config
metadata:
  type: project
---

Phase 14 (Deploy) ships via **Railway** in the actual repo.

**Per `phases/source/PHASE_14_deploy.md`:** source lists Railway services
(`zesty-delight`, `appealing-victory`) AND mentions "nginx reverse proxy
(where applicable)" and "systemd services for any local-host deployments."
The source is permissive — Railway-only is consistent with source.

**How it actually deploys:**
- Backend: `backend/nixpacks.toml` + `backend/railway.json` →
  Railway service `zesty-delight`.
- Frontend: `frontend/nixpacks.toml` + `frontend/railway.json` →
  Railway service `appealing-victory`.
- Repo root also has top-level `nixpacks.toml` + `railway.json` (Railway
  detects whichever it needs).

**How to apply:**
- Phase 14 verification: check for nixpacks/railway config files and
  confirm Railway services are healthy. systemd unit files and nginx.conf
  are NOT required.
- Part B per-phase final reports say "Commit + push. Wait for Railway
  deploys" — that's the deployment loop after every Part B phase.
- The `deploy/` directory may still contain `supabase_schema.sql`
  (legitimate, Phase 8). Any orphaned systemd unit files there are
  ignorable.
