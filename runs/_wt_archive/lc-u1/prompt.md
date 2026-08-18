# Dispatch U1 — inject canonical disclaimer into criminal + discovery streams

Repo: joewpb/legalclear. Worktree: ~/code/lc-u1 (branch fix/u1-criminal-discovery-disclaimer, cut from origin/main).

## Task (U1 closure — B4b-6 applied to the two surfaces B4 missed)

The audit (AUDIT_FINDINGS.md) found: "Criminal Procedure and Discovery Motion
streaming success paths emit no server-injected disclaimer." Both modules
stream prose to the user with zero disclaimer.

1. Read backend/src/agents/criminal_procedure.py and
   backend/src/agents/discovery_motion.py — find where their stream chunks
   are produced, and how the established pattern works in
   backend/src/agents/property_casualty.py (imports `apply_disclaimer` from
   src.core.upl and emits a typed `event: disclaimer` SSE event — the B4b-1
   canonical, versioned source. core/upl.py is THE source; never inline
   disclaimer text).
2. Inject the canonical disclaimer into BOTH streams, mirroring the
   property_casualty pattern: `apply_disclaimer` called with the response
   language (en/es if the module is bilingual — check), emitted as a typed
   `event: disclaimer` chunk. Match the exact SSE event format the respective
   frontend pages parse (frontend/src/pages/CriminalProcedureExplainer.tsx
   parses `event === "disclaimer"` via lib/sse.ts readSSE — keep it
   compatible).
3. Do NOT change the disclaimer text — it comes from the canonical source.
4. Tests: extend or add pure-Python tests (backend/tests/) proving each stream
   emits the disclaimer event — follow how existing stream tests are shaped
   (look at backend/tests/test_deadline_disclaimer.py for the canonical-match
   pattern: the emitted disclaimer must equal `apply_disclaimer({}, lang=...)["disclaimer"]`).

## Verify

Suite with CI-scope ignores (baseline 374 passed, 1 skipped). Zero new failures.
Re-run scripts/verify_educational.py at the end — the two modules must drop
OUT of the check-1 "no disclaimer field" findings (if the checker's remaining
complaints about these files are router-level, note it in your report — the
checker is being refined separately; do not edit the checker).

## Hard rules

No git push/merge/checkout/reset/clean/stash/add/commit/branch. No network
(curl/WebFetch forbidden). No railway/supabase. Final answer: file:line of
each edit, test results, checker delta, turn count.
