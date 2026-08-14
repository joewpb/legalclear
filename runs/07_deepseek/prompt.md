# TASK: Map the PII→DeepSeek data flow. Investigation only — change NO code.

This repo was audited at 0c2e006. AUDIT_FINDINGS.md is the diagnosis; DECISIONS.md holds
Joe's approved decisions. Read only the sections for this item — do not read either file
end to end.

## The defect
Triage S1-5 (AUDIT_FINDINGS.md §6):
"User legal data sent to DeepSeek (3 call-sites) undisclosed — `opinion_retrieval.py:246+`,
`attorney_referral.py:224`, `orin_opinions.py:178`. Third-party, non-US processing of
legal PII; ToS/privacy alignment unknown. Product decision: drop, or gate + disclose in
ToS; document in ledger either way. Needs Joe's call."

DECISIONS.md Group A item 5: "S1-5 PII to DeepSeek in the three production paths — do not
change behavior yet. Produce a written data-flow map: which fields, which endpoint, which
provider, what is retained. Joe decides on disclosure/consent after seeing it."

This run is INVESTIGATION ONLY. No behavior changes.

## What to map (with file:line evidence for every claim)
For EACH of the three call-sites, produce:
1. Trigger path: which HTTP endpoint(s) reach this call-site, and which frontend page
   invokes them.
2. Fields: exactly which user data is in the prompt at the moment of the DeepSeek call —
   distinguish direct PII (name, phone, email) from legal-content data (case narrative
   excerpts, document text, attorney-question context) from synthesized/derived text.
   Quote the prompt-construction code.
3. Provider & model: the exact API endpoint and model string used (deepseek-chat?),
   config read from `config.py` (DEEPSEEK_API_KEY default ""), and what happens at
   runtime when the key is missing (exception? silent skip? fallback to Anthropic?).
4. Retention: what the response is used for, what gets stored (Supabase tables? logs?),
   and whether any of the input/output is persisted server-side or client-side.
5. Liveness: is each path live in production today? The repo-side recon (item 0) found
   `DEEPSEEK_API_KEY` UNVERIFIED in Railway — mark each path LIVE / LATENT /
   UNVERIFIABLE-FROM-REPO with the reason.
6. Disclosure: search docs/TERMS_OF_SERVICE.md, README.md, CLAUDE.md, and the frontend
   for any user-facing statement about third-party LLM processing. State verbatim what
   exists or confirm absence.
7. `services/orin_opinions.py:178` — also note the surrounding SSH-to-Orin context (this
   path runs on a personal box, not Railway).

## Scope rules
- Investigation only. You may write ONLY the named report file. No source edits.
- No LLM calls, no network, read-only git.

## Done means
Investigation only. Change no code. Report where the boundary sits, with file:line
evidence, what you verified versus inferred, and what remains UNVERIFIED. Write your
findings to runs/07_deepseek/REPORT.md (create it — that is the ONLY file you may write).
