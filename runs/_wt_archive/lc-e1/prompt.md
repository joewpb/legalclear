# Dispatch E1 — checker correction + expungement prompt fix (Jobs 1+2)

Repo: joewpb/legalclear. Worktree: ~/code/lc-e1 (branch fix/e1-checker-correction, cut from origin/main).

## Job 1 — Remove check #4 from scripts/verify_educational.py

Advice-phrasing detection is the wrong mechanism: two of its three hits were
CaseLawLookupFL's "you should double-check/verify" lines — verification
instructions that the educational standard explicitly REQUIRES. Phrase-policing
flags safety language as advice and inverts the goal.

1. Delete check #4 entirely from scripts/verify_educational.py:
   - Remove ADVICE_PATTERNS and ADVICE_ALLOWLIST.
   - Remove the check-4 scanning loop.
   - Renumber: old check 5 ("single canonical disclaimer") becomes check 4.
     The violation dict keys, the report loop `range(1, 6)`, and the final
     summary line must all become 1..4. Update the module docstring's check
     list (drop the advice-phrasing entry, renumber).
2. Do NOT touch frontend/src/pages/CaseLawLookupFL.tsx.
3. backend/src/core/reminders.py line ~88: the reminder email body
   `"Your deadline is in 3 days. This requires urgent attention."` —
   keep the deadline statement (that is what a reminder is for), replace the
   imperative tail with declarative educational phrasing, e.g.
   `"Your deadline is in 3 days. The court docket is the official source for
   this deadline."` — your call on exact wording: declarative, no "requires",
   no command. Check for sibling templates in the same file with similar
   phrasing and align them.
4. Record in DECISIONS.md (new entry or note under Decision 11): phrase-policing
   (verify_educational check #4, advice-phrasing regex) was built, tested
   against the codebase, and removed on evidence — it flagged required
   verification language as advice. Substantive legal explanation, including
   second-person guidance, is the product's purpose.

## Job 2 — expungement.py:97, highest priority

backend/src/agents/expungement.py line ~97 currently instructs the model:
"Always include expungement.com and lawhelp.org". expungement.com is an
unsanctioned commercial third party. Fix:

1. Remove both domains from the prompt. Replace with an instruction pointing
   users to the on-site /find-legal-help directory instead of any external
   link ("direct users to the in-app Find Legal Help page — no external
   domains").
2. Verify at the OUTPUT level (B4b-1a lesson — prompt changes do not guarantee
   the model stops emitting the domains; the URL filter is the backstop):
   - Run the expungement agent once with a representative input (you have
     backend/.env with ANTHROPIC_API_KEY; mimic how the router invokes the
     agent — read backend/src/agents/expungement.py for its interface and a
     plausible input shape; it is fine to use a minimal stub context).
   - Grep the raw agent output for expungement.com / lawhelp.org / any bare
     domain.
   - Then run the same output through the URL filter (find the function in
     backend/src/core/url_filter.py — import and call it directly) and confirm
     domains are stripped.
   - Report both results verbatim-ish (quote the relevant lines, redact
     nothing else needed).
3. Do not add new tests unless trivial; the checker re-run is the regression
   net.

## Verify

- python3 scripts/verify_educational.py — must now show checks 1–4 only (no
  advice check); the expungement.py:97 domain hits must be GONE; total
  violation count must drop from 35 to ~29 (advice 3 + expungement 2 + the
  removed check numbering).
- Suite with CI-scope ignores (baseline 369 passed, 1 skipped) — zero new
  failures.

## Hard rules

No git push/merge/checkout/reset/clean/stash/add/commit/branch. No network
(no curl, WebFetch) — the agent LLM call is the only allowed outbound, exactly
as described. No railway/supabase. Final answer: per-job summary with file:line
of every edit, the agent-output verification quotes, checker re-run summary,
suite result, turn count.
