# TASK: Diagnose the UPL wall gaps. Investigation only — change NO code.

This repo was audited at 0c2e006. AUDIT_FINDINGS.md is the diagnosis; DECISIONS.md holds
Joe's approved decisions. Read only the sections for this item — do not read either file
end to end.

## The defect
Triage S3-2 (AUDIT_FINDINGS.md §6):
"U1: no canonical disclaimer on criminal/discovery streaming success; attorney_referral
outside UPL wall — `criminal_procedure.py:150-206`, `discovery_motion.py:175-210`,
`attorney_referral.py` (whole). Core legal-safety invariant silently unenforced. Proposed
fix: emit server-side disclaimer terminal event (copy wills_trusts `:183` or PC `:379`
pattern); wrap referral responses in `apply_disclaimer`."

DECISIONS.md Group A item 6: "S1-6 / S3-2 (UPL) UPL wall gaps — Criminal and Discovery
streaming success paths, and the attorney-referral router."

This run is DIAGNOSIS ONLY. No code changes will be made in this run.

## What to map (with file:line evidence for every claim)
1. `core/upl.py` — what the wall actually is: `apply_disclaimer` signature and behavior,
   the escalation path, how/when it's invoked per-router.
2. For EACH of the four surfaces, state exactly where the disclaimer sits today:
   a. `agents/criminal_procedure.py:150-206` — what is yielded on the SUCCESS path, what
      is yielded on the ERROR path, and where (if anywhere) the LLM is expected to emit a
      `disclaimer` field inside its own JSON.
   b. `agents/discovery_motion.py:175-210` — same questions.
   c. `routers/attorney_referral.py` — confirm the router has no `apply_disclaimer` /
      upl import at all; which of its responses carry legal-ish guidance.
   d. Canonical controls: `agents/wills_trusts.py:183` and
      `agents/property_casualty.py:379-380` — how the reference implementations do it.
3. The streaming contract on the client side: `CriminalProcedureExplainer.tsx:385-410`
   and the discovery twin — how chunks are parsed, how an extra server event would (or
   would not) break parsing, and how the police-report path (`sseMerge.ts`, the tested
   pure reducer) already tolerates typed server events.
4. What a MINIMAL fix would touch, precisely: for each module, the exact file:line(s) a
   server-side disclaimer terminal event or `apply_disclaimer` wrap would land on, and
   which client parser lines would need to tolerate it. Do not write the code — describe
   it.

## Scope rules
- Investigation only. You may write ONLY the named report file. No source edits.
- No LLM calls, no network, read-only git.

## Done means
Investigation only. Change no code. Report where the boundary sits, with file:line
evidence, what you verified versus inferred, and what remains UNVERIFIED. Write your
findings to runs/06_upl/REPORT.md (create it — that is the ONLY file you may write).
