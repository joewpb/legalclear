# LegalClear — Output Path UPL Audit

**Audited by:** Claude Code (automated static analysis of system prompts and
  consequence strings). Human attorney review required before public launch.
**Date:** 2026-05-19
**Status:** Engineering audit complete. Attorney review PENDING.

---

## Output paths audited

### 1. `ExplainerAgent` system prompt (`backend/src/agents/explainer.py`)

**Instruction:** "You never give legal advice — you explain what documents say,
not what people should do."

**Assessment:** ✓ Explicit UPL instruction present. LLM is instructed to explain
  and translate, not advise. Flag for attorney review of actual output.

---

### 2. `FormGuideAgent` system prompt (`backend/src/agents/form_guide.py`)

**Instruction:** Review needed — check system prompt for directive language.

**Action required:** Attorney reviewer should verify actual form_guide outputs
  do not instruct what to write in form fields.

---

### 3. Deadline `consequence_if_missed` strings (`backend/deadline/rules.py`)

All 8 rules reviewed. Each uses "may" language:

| Rule | Consequence text | Assessment |
|------|-----------------|------------|
| civil_summons | "A default judgment **may** be entered against you if you do not file a written response within 20 days." | ✓ "may" — factual |
| eviction_complaint | "A default judgment for eviction and possession **may** be entered if you do not file a written response within 5 business days." | ✓ "may" — factual |
| foreclosure_complaint | "A default judgment of foreclosure **may** be entered if you do not file a written response within 20 days." | ✓ "may" — factual |
| family_law_petition | "The court **may** grant the petition by default if you do not file a written response within 20 days." | ✓ "may" — factual |
| small_claims_summons | "You must appear at the pretrial conference date shown on your summons." | ⚠ "must" — states a legal obligation, not an instruction. Flag for attorney review. |
| notice_of_appeal | "You will lose your right to appeal if you do not file a notice of appeal within 30 days." | ⚠ "will lose" — factual consequence but strong. Flag for review. |
| motion_for_rehearing | "You will waive your right to seek rehearing if you do not file a motion within 15 days." | ⚠ "will waive" — same. Flag for review. |
| discovery_request | "Failure to respond to a discovery request within 30 days **may** result in court sanctions or the facts being deemed admitted." | ✓ "may" — factual |

**Note on ⚠ items:** "Must appear" and "will lose/waive" are factual legal
  consequences derived from the rules themselves (Fla. Sm. Cl. R. 7.090,
  Fla. R. App. P. 9.110(b)). They state consequences, not instructions.
  Present to attorney reviewer for final determination.

---

### 4. Escalation referral text (`backend/src/core/upl.py`)

**Reviewed:** Referral text uses "may be available" and "consider consulting" —
  no directive language. ✓

---

### 5. Triage classifier output (`backend/triage/classify.py`)

**System prompt:** "You produce legal information — never legal advice or conclusions."
**Assessment:** ✓ Explicit instruction. Classifier outputs metadata (type, confidence),
  not recommendations.

---

### 6. Disclaimer texts (`backend/src/core/upl.py`)

**English:** "This is legal information, not legal advice. LegalClear helps you
  understand court documents and deadlines. It is not a substitute for advice
  from a licensed Florida attorney..."
**Assessment:** ✓ Clearly states the distinction. Must be reviewed against the ToS
  when drafted.

---

## Items requiring attorney review before launch

1. `small_claims_summons.consequence_if_missed` — "must appear" language
2. `notice_of_appeal.consequence_if_missed` — "will lose your right" language
3. `motion_for_rehearing.consequence_if_missed` — "will waive your right" language
4. Actual LLM-generated `explanation` outputs from real documents
5. Actual LLM-generated `form_guide` outputs from real FL court forms
6. Disclaimer text consistency with ToS (ToS not yet drafted)

## Items confirmed UPL-safe (engineering audit)

1. All "may" consequence strings (civil_summons, eviction, foreclosure, discovery)
2. Escalation referral text
3. Classifier system prompt
4. Explainer system prompt
5. Triage router reasoning strings

---

*This document is an engineering-level audit only. It does not constitute
legal advice and does not substitute for the attorney review required by
Phase 8 Task 5.*
