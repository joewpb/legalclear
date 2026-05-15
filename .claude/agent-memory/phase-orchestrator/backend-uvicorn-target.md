---
name: backend-uvicorn-target
description: Backend FastAPI app object is at src.api.routes:app, not main:app — uvicorn invocation gotcha when running verification tests by hand
metadata:
  type: project
---

When running the backend by hand on port 8001 (e.g. to execute a Phase
verification test that hits live HTTP endpoints), the correct uvicorn
target is `src.api.routes:app`, not `main:app`.

`backend/main.py` is just a thin entrypoint that does
`uvicorn.run("src.api.routes:app", ...)` — the app object itself lives in
`src/api/routes.py`. `main:app` does not exist and will fail with
`Error loading ASGI app. Attribute "app" not found in module "main"`.

**Why:** Part A Phase 10 split the source-spec single `backend/src/api/main.py`
into a `backend/main.py` entrypoint + `backend/src/api/routes.py` app
module (see [[part-a-source-divergences]]). Phases 18+ verification tests
expect a live 8001 backend; getting uvicorn pointed at the right module
is the difference between a 1-second test and a 60-second debug.

**How to apply:** From `backend/`, run
`uv run uvicorn src.api.routes:app --host 127.0.0.1 --port 8001 --log-level warning`
to spin up a verification backend. Phase 16/17/18+ tests then run as
`uv run python tests/test_phase_NN.py`.
