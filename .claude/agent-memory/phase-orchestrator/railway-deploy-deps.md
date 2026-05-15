---
name: railway-deploy-deps
description: Railway nixpacks installs from backend/requirements.txt, NOT pyproject.toml — every `uv add` must be mirrored to requirements.txt or the prod deploy 500s
metadata:
  type: feedback
---

The Railway deploy reads `backend/requirements.txt` for Python deps, not
`backend/pyproject.toml`. Both `nixpacks.toml` and `railway.json` run
`pip install -r requirements.txt` as their install step. `uv sync` /
`uv.lock` / `pyproject.toml` are local-dev only.

**Why:** Phase 23 nearly shipped a broken prod deploy. `uv add pikepdf
jinja2` updated `pyproject.toml` + `uv.lock` (great for local tests,
which pass) but Railway didn't see the new deps until I synced them
into `requirements.txt`. Without that sync, every `/api/packet/build`
on prod would have 500'd on `ModuleNotFoundError: No module named
'pikepdf'`.

**How to apply:** any time you `uv add <pkg>` in `backend/`:

1. Add the package + a version pin to `backend/requirements.txt` in the
   same commit. The two files must stay in lockstep.
2. If the package is a Python wrapper around a native binary (Playwright
   for Chromium, pyppeteer for Puppeteer, etc.), also:
   - Add the runtime apt deps to `aptPkgs` in `nixpacks.toml`.
   - Add the binary-download step to the install commands (Playwright:
     `python -m playwright install chromium`; analogous for others).
3. Push, then watch the Railway build log for "ModuleNotFoundError" or
   missing-shared-library errors. The build can succeed and the deploy
   still 500 at first request because Playwright launches Chromium
   lazily — verify with a real `/api/packet/build` call against prod.

Related: [[phase-23-shipped]] documents the in-memory packet store +
Supabase mirror pattern. The Supabase mirror is best-effort, so a
missing `packets` table doesn't 500 requests — but a missing pikepdf
import does.
