# AGENTS.md — LegalClear

Build law for the LegalClear codebase. Read by Claude Code, OpenCode, and any
other agent operating in this repo. Portable on purpose — no tool-specific syntax.

---

## 1. What LegalClear is

Florida legal-information platform for self-represented (pro se) users. A user
uploads a court document; an agent pipeline classifies it, extracts deadlines,
explains it in plain language, surfaces the relevant court forms, and schedules
reminders. The product also includes a Small Claims filing wizard, an Eviction
defense flow, a Traffic citation wizard, a Police Report Analyzer, and FL Case
Law Lookup.

**v1 shipped 2026-05-15.** All 24 phases (0–23) complete and deployed.
**v2 build in progress.** See `phases/BUILD_PLAN.md` for the v2 phase sequence
and `phases/LEDGER.md` for v1 state.

---

## 2. Core Principles — apply to every phase

1. The product produces **legal information**, never **legal advice**. It
   translates, surfaces options, explains consequences. It never selects a
   course of action for the user.
2. **LLMs extract. Deterministic code computes.** No model does date arithmetic.
3. Every deadline carries a full `computation_trace` with rule citations.
4. No "done" claim without fresh test/verification evidence.
5. **"Unknown" is a valid, first-class output.** A confident wrong answer is a
   liability.
6. **Backend is the security boundary.** The backend uses the service-role key,
   which bypasses RLS. Every backend query reading user data must be explicitly
   scoped to the authenticated user. RLS is the second line of defense.
7. **Language-parameterized from day one.** Every user-facing output accepts a
   language parameter. English ships first; Spanish must not require
   re-architecture.
8. **Respect source robots.txt and terms.** `flcourts.gov` and its file CDN
   disallow automated crawling. Form acquisition is a one-time human/browser-
   assisted harvest plus a lightweight change-detection check.
9. **A served form is never knowingly stale.** A form whose change-detection
   status is unresolved is gated, not served silently.

---

## 3. Stack and ports — hard constraints

| Component        | Value                                              |
|------------------|----------------------------------------------------|
| Backend          | FastAPI — **port 8001**                            |
| Frontend         | React — **port 3000**                              |
| Mobile           | Expo / React Native                                |
| Database         | Supabase — project `miedifclpqewnixxkahs` (us-west-2) |
| Payments         | Stripe                                             |
| Python env/pkgs  | `uv` — for everything, no exceptions               |
| Deploy           | Railway                                            |

**Never use port 8000 for the LegalClear app.** Port 8000 is reserved and using
it is a build failure, not a warning.

Architecture: backend-only. The client talks only to the Railway backend; the
backend is the only thing that talks to Supabase and holds the service-role key.

---

## 4. Build rules — phase discipline

- **v1 is complete. All phases 0–23 are deployed. Do not rebuild any phase.**
- v2 phases (BUILD_PLAN.md) are executed one per session, in strict order.
- Run each phase's Definition of Done verification before marking it complete.
- Fix all failing assertions before proceeding.
- If a phase's verification fails more than twice, print
  `PHASE N BLOCKED — <error summary>` and halt. Do not continue.
- Only print `PHASE N COMPLETE` when every assertion passes.
- Never run untested migrations against production. Always use a Supabase
  development branch first.

---

## 5. Code style

**Python**
- PEP 8. Type hints on all function signatures.
- `async`/`await` for all IO operations.
- All agent methods return typed dicts.
- JSON parsing: always strip markdown fences before `json.loads()`.
  Retry once on a JSON parse failure before raising.

**JavaScript / TypeScript / React**
- Functional components, hooks.
- No secrets in client code. All keys server-side.
- New files use `.tsx` / `.ts`. Legacy `.jsx` files are not migrated unless
  the phase explicitly requires it.

---

## 6. The phase system

- `phases/BUILD_PLAN.md` — v2 phase sequence (Phases 0–9). One phase per
  session. Verify the Definition of Done before moving on.
- `phases/LEDGER.md` — v1 build state (Phases 0–23 complete). Source of truth
  for v1; if ledger and repo disagree, **the repo wins**.
- The `phase-orchestrator` agent owns the v1 phase sequence. Use it for any
  v1 verification runs.

---

## 7. Deploy targets

| Surface  | Build                  | Railway service     |
|----------|------------------------|---------------------|
| Backend  | `uv sync` → push       | `zesty-delight`     |
| Frontend | `npm run build` → push | `appealing-victory` |

Stripe product: **"LegalClear Filing Packet"** at **$35.00**.
Languages live: `en`, `es`.

---

## 8. Hard fails

These abort the build immediately:

- Use of port 8000 for the app.
- Mode B automation present anywhere in `backend/src/`.
- A `PHASE N COMPLETE` printed while any assertion for phase N failed.
- Touching `/api/upload` — the upload flow exists and is correct. Leave it.
- Running a migration directly against production without verifying on a branch.
- Any LLM call that outputs a computed deadline date (extraction only; dates
  are computed by deterministic code).
