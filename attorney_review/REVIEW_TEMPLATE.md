# LegalClear — Attorney Review Template

**Purpose:** Documented UPL review of actual generated outputs before public launch.
Required by Phase 8. Must be completed and retained on file before any deadline
or analysis feature is shown to real users.

**Reviewer:** _________________________________ Bar No. _____________
**Date of review:** _________________________________
**Florida Bar licensed:** ☐ Yes  ☐ No

---

## What the reviewer receives

The engineering team provides:
1. Actual `explanation` output generated from a real FL court document
2. Actual `form_guide` output for a real FL court form
3. Actual `escalation` output (reasons, referral text) for a document that triggered escalation
4. Actual `deadline` output (label, consequence_if_missed, computation_trace)
5. The current disclaimer text in both English and Spanish

The reviewer marks against the UPL line defined by Fla. Stat. § 454.23 and the
Florida Bar's interpretation of "legal advice."

---

## Review checklist

### A. Disclaimer adequacy
- [ ] The disclaimer clearly states this is legal information, not legal advice
- [ ] The disclaimer is present on every output shown (not buried at the bottom)
- [ ] The disclaimer directs the user toward a licensed Florida attorney
- [ ] The disclaimer is accurate — it does not overstate LegalClear's capabilities
- [ ] Spanish disclaimer is accurate and conveys the same meaning

**Reviewer notes on disclaimer:**
_________________________________________________________________
_________________________________________________________________

---

### B. Explanation output
_(Reviewer marks each sentence or phrase that may cross the UPL line)_

- [ ] Output translates — it explains what the document says
- [ ] Output surfaces options — it lists possibilities, not instructions
- [ ] Output explains consequences — it states what may happen, not what to do
- [ ] Output does NOT instruct the user which legal action to take
- [ ] Output does NOT use "you should," "you must," "I recommend," or similar
- [ ] Output does NOT predict a legal outcome

**Flagged phrases (copy and underline):**
_________________________________________________________________
_________________________________________________________________

---

### C. Form guide output
- [ ] Explains what the form is and what it is used for
- [ ] Explains what each field asks for — factual description
- [ ] Does NOT tell the user what to write in any field
- [ ] Does NOT advise whether to complete or file the form

**Flagged phrases:**
_________________________________________________________________
_________________________________________________________________

---

### D. Escalation output
- [ ] Escalation recommendation is clearly framed as an option, not an instruction
- [ ] Referral text does not overstate the urgency in a way that causes panic
- [ ] Attorney referral links are accurate
- [ ] No escalation output predicts case outcome

**Flagged phrases:**
_________________________________________________________________
_________________________________________________________________

---

### E. Deadline output
- [ ] Deadline dates are presented as computed information, not legal advice
- [ ] `consequence_if_missed` text uses "may" language, not certainty
- [ ] `computation_trace` citations are accurate (reviewer spot-checks 2 rules)
- [ ] No deadline output tells the user whether to respond to the court

**Spot-check rules verified:**
_________________________________________________________________

---

### F. Overall UPL determination

☐ **PASS** — No output instructs the user which legal action to take.
  All outputs translate, surface options, and explain consequences only.

☐ **CONDITIONAL PASS** — Outputs are acceptable subject to the following
  specific wording changes before public launch:
  _________________________________________________________________
  _________________________________________________________________

☐ **FAIL** — The following outputs require revision before any review
  can be completed:
  _________________________________________________________________
  _________________________________________________________________

---

### G. Consistency with Terms of Service
_(To be completed once the ToS is drafted — parallel workstream, Joe + attorneys)_

- [ ] Disclaimer text is consistent with the ToS disclaimer enforceability language
- [ ] "Legal information, not legal advice" framing is consistent with ToS
- [ ] Escalation referral text is consistent with ToS limitation of liability

---

## Reviewer signature

By signing below, I confirm that I have reviewed the actual generated outputs
provided to me and have assessed them against the Florida UPL standard.

Signature: _________________________________ Date: _____________

**This completed form must be retained in writing. A copy goes to:**
- Joe (product owner)
- LegalClear legal file
- Tech E&O insurance broker (as evidence of UPL review process)
