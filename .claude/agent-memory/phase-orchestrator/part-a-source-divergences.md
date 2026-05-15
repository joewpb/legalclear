---
name: part-a-source-divergences
description: Six places where the deployed Part A repo diverges from phases/source/ — two block Phase 15 start
metadata:
  type: project
---

After landing the per-phase source files at `phases/source/`, six
points of divergence between the live repo and the source were
identified on 2026-05-14. Two are hard blockers for Phase 15 start.

| # | Phase | Divergence | Blocks Part B? | Status |
|---|-------|------------|----------------|--------|
| 1 | 0 | Source verifies `backend/pyproject.toml` (uv project file). Repo had only `backend/requirements.txt`. | ~~YES~~ | **RESOLVED 2026-05-14.** `backend/pyproject.toml` added mirroring `requirements.txt`. Railway nixpacks still uses `pip install -r requirements.txt` per the root `nixpacks.toml` — keep both files in sync. Run `cd backend && uv sync` to materialize the lockfile before Phase 22/23 `uv add`. |
| 2 | 2 | Source path `backend/src/services/pdf_processor.py`; repo has `backend/src/ingestion/{pdf_parser,ocr,text_cleaner}.py`. | Soft — Phase 21 imports `from ..services.pdf_processor import extract`. | Deferred to Phase 21. Either (a) adjust Phase 21's import to point at the existing `ingestion/` module, or (b) add a `services/pdf_processor.py` shim re-exporting from `ingestion/`. |
| 3 | 10 | Source endpoint paths use `/api/*` prefix (e.g., `/api/upload`, `/api/stripe/webhook`). Repo serves at bare paths (`/upload`, `/webhook`). | No — Part B routers declare their own `prefix="/api/..."`. | Documented permanent difference. Part A endpoints stay at bare paths (frontend already knows them). |
| 4 | 11 | `backend/src/platforms/florida_courts.py` contains 5 unmarked `myflcourtaccess` references. Phase 23 `test_no_mode_b` would fail. | Soft — only at Phase 23 final test time. | Phase 23 source plan: deprecate `florida_courts.py` to a thin wrapper or add `# walkthrough text only` markers. Phase 23 handles it. |
| 5 | 12 | Source uses `.tsx`; repo was 100% `.jsx`, no `tsconfig.json`, no TS deps in `package.json`. | ~~YES~~ | **RESOLVED 2026-05-14.** `frontend/tsconfig.json` + `tsconfig.node.json` added; `typescript` + `@types/{node,react,react-dom}` added to `package.json` devDeps; `allowJs: true` keeps existing `.jsx` working; `type-check` script added. Run `cd frontend && npm install` to materialize TS deps before Phase 15. Vite handles `.tsx` automatically via `@vitejs/plugin-react`. |
| 6 | 13 | Source expects `mobile/{App.tsx,app.json,package.json}` present; repo `mobile/` is empty. | No — source policy is "do not block." | Document in final report as a known gap. No build action. |

## How to apply

Both hard blockers (#1 and #5) are resolved as of 2026-05-14. Before
executing Phase 15:
- `cd backend && uv sync` (materializes lockfile + venv)
- `cd frontend && npm install` (materializes TS deps + types)

Divergences #2 and #4 are deferred to the phases that own them.
Divergences #3 and #6 are documented permanent differences.

The Phase 14 hard stop lifts once `uv sync` + `npm install` complete
successfully.
