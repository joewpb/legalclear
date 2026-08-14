# TASK: Implement one approved decision. Do exactly this and nothing else.

This repo was audited at 0c2e006. AUDIT_FINDINGS.md is the diagnosis; DECISIONS.md holds
Joe's approved decisions. Read only the section for this item — do not read either file
end to end.

## The defect
Decision 1 (DECISIONS.md, verbatim):
"- Set `PAYMENTS_ENABLED` to false/off and confirm the effective value in Railway
  (`zesty-delight`).
- Keep ALL gating code in place. Do not remove payment code paths, tables, or
  dependencies — billing will be re-enabled later.
- Add a test asserting the flag is off and that no route is payment-gated while it is
  off.
- Report exactly what becomes reachable that was previously gated."

## Scope resolution (authoritative for this run)
- The Railway confirmation step is OUT OF SCOPE for this run (Joe verifies the Railway
  dashboard separately; item 0 recon already established the repo cannot read Railway).
  Do not attempt any Railway/network action.
- Code-side work is: (a) verify `PAYMENTS_ENABLED` reads from config and defaults to off
  (`backend/src/core/config.py:37-38`, `.env.example`); if the default or the `.env.example`
  value is anything but false/off, set it to false — do not touch gating logic itself;
  (b) add the test: flag is off by default AND no route is payment-gated while it is off.
- Find every place the flag gates behavior (grep `PAYMENTS_ENABLED`): routes.py webhook,
  subscribe, filing count, packet checkout, chat limit, etc. The test must assert each of
  those gates is effectively open when the flag is off.
- Report (in your final paragraph): exactly what is reachable while the flag is off that
  would be gated/priced when on (e.g., packet checkout free, chat unlimited, etc.) —
  with file:line for each gate.
- Do NOT remove any payment code path, table, or dependency. Do NOT touch Stripe code
  except as needed to assert flag behavior in tests.

## Scope rules
- Read only the named files, their direct callers, and their tests.
- Fix only this defect. Anything else you notice: one line in FOLLOW_UPS.md, then move on.
- No refactoring, renaming, reformatting, or import reordering.
- Do not delete files, tables, columns, or dependencies.
- Do not change public API response shapes.
- If the fix is larger than the finding describes, STOP and report instead of coding.

## Standing doctrines
- No LLM in date arithmetic. No LLM call without explicit user action.
- Missing config raises loudly at startup — never degrades to [], None, {}, or a default.
  Never a default secret.
- uv for Python. No pip, no poetry.

## Done means
1. A test that fails before and passes after. Show both runs.
2. Minimal diff.
3. Full suite green.
4. One paragraph: what was wrong, what changed, what could regress — including the
   reachability report required by Decision 1.
