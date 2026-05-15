---
name: part-a-source-divergences
description: Six places where the deployed Part A repo diverges from phases/source/ — two block Phase 15 start
metadata:
  type: project
---

After landing the per-phase source files at `phases/source/`, six
points of divergence between the live repo and the source were
identified on 2026-05-14. Two are hard blockers for Phase 15 start.

| # | Phase | Divergence | Blocks Part B? | Resolution |
|---|-------|------------|----------------|------------|
| 1 | 0 | Source verifies `backend/pyproject.toml` (uv project file). Repo has only `backend/requirements.txt`. | **YES** — Phase 22 (`uv add httpx`) and Phase 23 (`uv add pikepdf jinja2`) require pyproject.toml. | One-time scaffold patch before Phase 15: add `backend/pyproject.toml` capturing current `requirements.txt` content. Not a Part A rebuild — a scaffold completion. |
| 2 | 2 | Source path `backend/src/services/pdf_processor.py`; repo has `backend/src/ingestion/{pdf_parser,ocr,text_cleaner}.py`. | Soft — Phase 21 imports `from ..services.pdf_processor import extract`. | At Phase 21 time, either (a) adjust Phase 21's import to point at the existing `ingestion/` module, or (b) add a `services/pdf_processor.py` shim re-exporting from `ingestion/`. |
| 3 | 10 | Source endpoint paths use `/api/*` prefix (e.g., `/api/upload`, `/api/stripe/webhook`). Repo serves at bare paths (`/upload`, `/webhook`). | No — Part B routers declare their own `prefix="/api/..."`, so Part B endpoints will be at `/api/*` regardless of where Part A endpoints are. | None for Part B. Documented divergence. Part A endpoints stay at bare paths (frontend already knows them). |
| 4 | 11 | `backend/src/platforms/florida_courts.py` contains 5 unmarked `myflcourtaccess` references. Phase 23 `test_no_mode_b` would fail. | Soft — only at Phase 23 final test time. | Phase 23 source plan: deprecate `florida_courts.py` to a thin wrapper or add `# walkthrough text only` markers. Phase 23 handles it. |
| 5 | 12 | Source uses `.tsx`; repo is 100% `.jsx`, no `tsconfig.json`, no TS deps in `package.json`. | **YES** — Phase 15 source creates new files as `.tsx`. | At Phase 15 setup: add `tsconfig.json`, install `typescript` + `@types/react` + `@types/react-dom`, configure Vite to accept `.tsx`. Then Phase 15 deliverables build cleanly. |
| 6 | 13 | Source expects `mobile/{App.tsx,app.json,package.json}` present; repo `mobile/` is empty. | No — source policy is "do not block." | Document in final report as a known gap. No build action. |

## How to apply

Before executing Phase 15:
- Resolve divergence #1 (add `backend/pyproject.toml`)
- Resolve divergence #5 (add TS config + deps to `frontend/`)

These are one-time scaffold completions, not Part A rebuilds, and they
unblock the entire Part B chain. Divergences #2 and #4 are deferred to
the phases that own them. Divergence #3 is a documented permanent
difference. Divergence #6 is a no-block gap.

Once #1 and #5 are resolved, the orchestrator can move past the
Phase 14 hard stop and execute Phase 15.
