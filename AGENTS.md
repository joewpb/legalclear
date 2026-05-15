# AGENTS.md — LegalClear

Build law for the LegalClear codebase. Read by Claude Code, OpenCode, and any
other agent operating in this repo. Portable on purpose — no tool-specific syntax.

---

## 1. What LegalClear is

Pay-per-use legal document analysis. A user uploads a contract, lease, or court
form; an agent pipeline classifies it, explains it in plain language, walks the
user through form fields, scans for risky clauses, and exports a structured
report. Part B adds a Small Claims filing wizard with a paid Filing Packet,
Florida courts integration, a filing walkthrough, and a tracking page.

This is a phased build. The phase system is the project. See
`phases/LEDGER.md` for current state and `phases/PHASE_SPECS.md` for specs.

---

## 2. Stack and ports — hard constraints

| Component        | Value                                    |
|------------------|------------------------------------------|
| Backend          | FastAPI — **port 8001**                  |
| Frontend         | React — **port 3000**                    |
| Mobile           | React Native                             |
| Database         | Supabase (production DB — not SQLite)    |
| Payments         | Stripe                                   |
| Python env/pkgs  | `uv` — for everything, no exceptions     |
| Deploy           | Railway                                  |

**Never use port 8000 for the LegalClear app.** Port 8000 is reserved and using
it is a build failure, not a warning.

---

## 3. Build rules — phase discipline

- Execute phases in strict numeric order. **Never skip. Never reorder.**
- Complete each phase fully before starting the next.
- Run the phase's verification command at the end of every phase.
- Fix all failing assertions before proceeding.
- If a phase's verification fails more than twice, print
  `PHASE N BLOCKED — <error summary>` and halt. Do not continue.
- Only print `PHASE N COMPLETE` when every assertion passes.
- Part A (phases 0–14) is already built and deployed. **Verify only — never
  rebuild Part A.** Part B (phases 15–23) is the build target.

---

## 4. Code style

**Python**
- PEP 8. Type hints on all function signatures.
- `async`/`await` for all IO operations.
- All agent methods return typed dicts.
- JSON parsing: always strip markdown fences before `json.loads()`.
  Retry once on a JSON parse failure before raising.

**JavaScript / React**
- Functional components, hooks.
- No secrets in client code. All keys server-side.

---

## 5. The phase system

- `phases/LEDGER.md` — the single source of truth for phase status. If the
  ledger, agent memory, and the actual repo disagree, **the repo wins.**
  Re-verify and correct the ledger.
- `phases/PHASE_SPECS.md` — goal, verification command, and pass criteria per
  phase. Part A entries are verify-only. Part B entries are full build specs.
- The `phase-orchestrator` agent drives this. Launch a build session with
  `claude --agent phase-orchestrator`.

---

## 6. Deploy targets

| Surface  | Build               | Railway service     |
|----------|---------------------|---------------------|
| Backend  | `uv sync` → push    | `zesty-delight`     |
| Frontend | `npm run build` → push | `appealing-victory` |

Stripe must show the **"LegalClear Filing Packet"** product at **$35.00**.
Languages live: `en`, `es`.

---

## 7. Hard fails

These abort the build immediately:

- Use of port 8000 for the app.
- Mode B automation present anywhere in `backend/src/`.
- A `PHASE N COMPLETE` printed while any assertion for phase N failed.
- Touching `/api/upload` — the upload flow exists and is correct. Leave it.
