# Dispatch J2 — small-claims citation pilot (ch. 34 ONLY, curated-set pattern)

Repo: joewpb/legalclear. Worktree: ~/code/lc-j2 (branch fix/j2-small-claims-citations, cut from origin/main).

## Doctrine (already merged on main — read these first)

- `backend/src/core/citation_resolver.py` — the resolution guard: citations
  must resolve against owned statute/rule rows; unresolvable = stripped, never
  displayed. `load_owned_citations(db)` builds the owned map from Supabase
  `statutes` + `court_rules`.
- `scripts/verify_educational.py` check 5 asserts the guard's presence.

## Task — pilot the curated-set pattern on small_claims ONLY

1. **Curated set.** Create `backend/src/agents/small_claims_citations.py`
   (or a data dict inside agents/small_claims.py — your call, but keep it a
   SEPARATE, greppable constant) holding the ch. 34 sections below. These are
   the ONLY citations the small-claims explainer may emit. The set was
   verified by the orchestrator against prod: each citation resolves to a row
   (citation → row lookup → text present → source_url on leg.state.fl.us).
   Include per entry: canonical citation, title (from the row), and the
   source_url. The 17 sections:
   Fla. Stat. § 34.01 (Jurisdiction of county court), § 34.011 (Jurisdiction
   in landlord and tenant cases), § 34.017 (Certification of questions),
   § 34.021 (Qualifications of county court judges), § 34.022 (Number of
   judges), § 34.031 (Clerk), § 34.032 (Power of clerk to appoint deputies),
   § 34.041 (Filing fees), § 34.045 (Cost recovery), § 34.07 (Sheriff),
   § 34.08 (Compensation of sheriff), § 34.13 (Method of prosecution),
   § 34.131 (Voluntary pleas of guilty), § 34.161 (48 hours to pay fines),
   § 34.171 (Salaries of bailiffs), § 34.181 (Branch courts), § 34.191 (Fines
   and forfeitures). All source_urls are the leg.state.fl.us Display_Statute
   links — use the same pattern as the DB rows.
2. **Agent wiring** (`backend/src/agents/small_claims.py`): the prompt must
   state the model may cite ONLY citations from the curated set, verbatim, and
   never invent one; the response schema gains a `citation` string field per
   section (or a `citations` list mapped to sections — match the existing
   schema shape; read the file first).
3. **Resolution guard on output**: after the agent returns, run every emitted
   citation through `resolve_citation` (or `resolve_citations`) against the
   CURATED map — strip any citation not present in the curated set before the
   router yields it. The curated set is a strict subset of the owned rows, so
   this enforces both verifiability and coverage safety. Unresolvable →
   stripped (section keeps its text, loses only the cite — never fail the
   whole response).
4. **Frontend** (`frontend/src/pages/SmallClaimsExplainer.tsx`): render the
   citation with each section that carries one — small mono text, non-link
   styling consistent with the page; do NOT render source_url as a clickable
   external link (no-external-links rule); render the citation text only.
5. **Tests** (`backend/tests/test_small_claims_citations.py`, pure Python):
   - every entry in the curated set resolves via `resolve_citation`;
   - a fabricated cite in an agent-style payload is stripped by the output
     filter;
   - a Rules 7.x cite is stripped (not in curated set);
   - the prompt contains the only-cite-from-the-set instruction.

## Verify

Suite with CI-scope ignores (baseline 383 passed, 1 skipped). Zero new
failures. `python3 scripts/verify_educational.py` — check 5 stays 0
violations. No network calls (the curated set is provided here; do NOT query
Supabase).

## Hard rules

No git push/merge/checkout/reset/clean/stash/add/commit/branch. No network
(curl/WebFetch forbidden). No railway/supabase. Final answer: file:line of the
curated set, the schema change, the output-filter call, the frontend render,
test results, checker delta, turn count, and — explicitly — any citation from
the 17 you could NOT wire or verify against the given data (name it rather
than shipping it silently).
