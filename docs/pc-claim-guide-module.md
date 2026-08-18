# P&C Claim Guide — user-facing module
### Layers on the existing deterministic deadline engine. No LLM in date arithmetic. No LLM without explicit user action.

---

## 1. What the user actually gets

Not a chatbot. A **claim state machine with a timeline UI**. The user's loss has a phase; the phase has three lists; the engine emits deadlines beside it.

```
┌─────────────────────────────────────┐
│  Your claim · Fire · Day 3 of 365   │
│  ████░░░░░░░░  Phase 2 of 7         │
├─────────────────────────────────────┤
│  ⚠ 2 things due this week           │
│  ✅ Do now            (4)           │
│  🚫 Never do          (3)           │
│  👁 Watch for         (2)           │
│  📄 Documents to save (5)           │
└─────────────────────────────────────┘
```

**Design rule:** a person three days after a house fire has no working memory. Three items per screen, one action per item, everything else collapsed.

---

## 2. Content schema

Static, versioned, jurisdiction-keyed. Ships as data, not as generation. Slots beside the deadline engine.

```json
{
  "phase_id": "fire.p2.adjuster_inspection",
  "peril": ["fire", "smoke"],
  "jurisdiction": "FL",
  "policy_inception_after": "2022-12-16",
  "sequence": 2,
  "entry_trigger": "claim_number_received",
  "exit_trigger": "carrier_estimate_received",
  "typical_window_days": [1, 7],
  "title": "The adjuster inspects your home",
  "plain_summary": "…",
  "do_now": [{ "id": "…", "text": "…", "artifact": "…", "why": "…" }],
  "never_do": [{ "id": "…", "text": "…", "consequence": "…" }],
  "watch_for": [{ "id": "…", "signal": "…", "escalates_to": "…" }],
  "documents": ["…"],
  "deadlines": ["fl.627_70131.acknowledge_7d"],
  "authority": ["Fla. Stat. § 627.70131"],
  "effective_date": "2023-03-24",
  "superseded_by": null
}
```

Every content record carries `authority` + `effective_date`. Nothing renders without them. That is what keeps the module honest when Florida rewrites the statute again.

---

## 3. The seven phases — fire

### Phase 0 · Right now (hour 0–24)

**Plain summary:** The next 24 hours decide how much of this claim you can prove later. Almost nothing here is about insurance paperwork. It is about evidence and safety.

| ✅ Do now | Why |
|---|---|
| Do not go back inside until the fire department releases the building | Hot spots, carbon monoxide, collapse |
| **Video every room before anything is moved or cleaned** — slow, narrate, open every drawer and closet | This is the single most valuable thing you will ever do for this claim. Once cleanup starts, it cannot be recreated |
| Call your insurance company and get a claim number | Starts the legal clocks in your favor |
| Ask three questions on that first call: *Can I get an advance for living expenses? What is the emergency repair limit on my policy? Which companies are you sending?* | All three become disputes later if unasked |
| Write down the fire report number | It is usually a public record you can request |
| Get your documents and valuables out if allowed — IDs, passports, deeds, policies, medications, jewelry | If investigators are working, they will escort you and list what you take |
| Board up, tarp, lock | After the fire department leaves, securing the building is **your** responsibility |
| Call your mortgage company | They will be on every check |

| 🚫 Never do | What happens |
|---|---|
| Let anyone remove, clean, or throw away anything before you have video | Your contents claim shrinks to whatever someone else wrote down |
| Sign anything a contractor hands you at the curb | Those are contracts. You become personally liable for whatever insurance does not pay |
| Guess at numbers on the phone | Early guesses get quoted back at you for the next two years |

**📄 Save:** claim number · adjuster name and phone · fire report number · every photo and video · Red Cross paperwork

---

### Phase 1 · The first week

**Plain summary:** Two things matter this week. Getting your actual policy in your hands, and controlling who touches your belongings.

| ✅ Do now |
|---|
| Request your **complete policy** in writing — declarations page, full form, every endorsement. Not the summary they email you |
| Start a claim log. Date, time, who you spoke to, their title, what they said. Confirm anything important by email the same day |
| Start keeping every receipt — hotel, meals above what you normally spend, laundry, pet boarding, extra driving, storage |
| Before signing any repair or cleanup authorization: write a dollar cap on it, define exactly what work it covers, and cross out anything that assigns your insurance benefits |
| Tell your insurer **in writing** that the house is now unoccupied because of the fire | Many policies restrict coverage on vacant homes after 30–60 days. This notice protects you |

| 🚫 Never do | What happens |
|---|---|
| Let a pack-out crew load a truck before you have your own video and their written item list | Boxes labeled "kitchen misc" become the ceiling on what you get paid |
| Let anyone discard an item without your written OK and a photo | You cannot claim what nobody can prove existed |
| Give a recorded statement before you have read your policy | It gets compared line by line to anything you say later |

**👁 Watch for:** a letter using the words *reservation of rights* → the insurer is preserving the right to deny. Escalate.

---

### Phase 2 · The adjuster inspects

**Plain summary:** The adjuster works for the insurance company. Most are decent people. That does not make them your representative.

| ✅ Do now |
|---|
| Be there for the inspection |
| Photograph everything they photograph |
| Write down what they say is covered and email it back to them that day |
| Get your **own** repair estimate from a contractor you chose |
| Ask for a copy of the **field adjuster's report**, not just the final estimate |

**Why that last one matters:** post-Hurricane Ian, licensed adjusters told CBS that carriers altered their damage reports downward while leaving the adjuster's name and license number on them. Those allegations are contested and in litigation. But comparing the field report against the final estimate costs you nothing and catches the discrepancy if it exists.

**⏱ Florida clocks now running:**

| Obligation | Deadline |
|---|---|
| Insurer acknowledges your claim | 7 calendar days |
| Insurer begins investigation / inspects | 7 / 30 days |
| Insurer sends you its detailed estimate | 7 days after it is written |
| Insurer pays, denies, or pays the undisputed part | **60 days from notice** — interest accrues if missed |

---

### Phase 3 · Your belongings (the contents claim)

**Plain summary:** This is where most people lose the most money, because it is tedious and nobody helps them do it. Whoever writes the list controls the payment.

**If the insurer offers to pack out and store your things — the honest version:**

Moving fast is genuinely good for you. Smoke residue is corrosive and gets worse by the hour. Mold starts on wet material in 24–48 hours. Waiting can turn a covered loss into a coverage fight.

And: the moving company is chosen and paid by your insurer, it writes the only inventory, it decides what gets cleaned instead of replaced, and it holds your property in a warehouse you cannot walk into.

Both are true. So accept the speed and take the paperwork.

| ✅ Before the truck loads |
|---|
| Your own video is done |
| You have their inventory list **in writing**, item by item, not box by box |
| Photos of what went in each box |
| A written list of what they consider unsalvageable, agreed before disposal |
| Storage location, your right of access, the daily rate, and **who pays it** — contents limit or living expenses? Ask. It quietly eats one of them |
| Irreplaceable items stayed with you and never went on the truck |

| 👁 Watch for |
|---|
| Items returned "cleaned" that still smell of smoke → say in writing that accepting them is not a waiver |
| Storage bills climbing while the rebuild stalls |

**Florida:** many current policies cap emergency measures at **$3,000 or 1% of your dwelling coverage, whichever is greater** — more only if the insurer approves within a 48-hour window after you ask. Courts have enforced this strictly. If nobody filed that request, the overage lands on you.

**Building your inventory** — one row per item:

`room · what it is · brand · model · serial · qty · how old · what you paid · condition · what it costs new today · where you found that price`

Where to find proof when the receipts burned: credit card and bank statements · email order confirmations · Amazon and retailer order history · warranty registrations · old listing photos of your house · social media · photos friends and family took inside your home · a prior mover's inventory.

**On depreciation:** there is no legally binding depreciation schedule. The numbers are subjective and negotiable. Ask the insurer for the schedule it used, then argue it item by item. Some things should barely depreciate at all — antiques, art, jewelry, collectibles, light fixtures.

**One hard rule:** never claim something you did not own. Honest mistakes on a reconstructed list are normal and expected. Deliberate padding is a felony, voids the whole claim, and hands the insurer the fraud theory it needs.

---

### Phase 4 · The money

**Plain summary:** You will usually get paid twice. Understand why, or you will think you were underpaid when you were not — or think you were paid in full when you were not.

| Term | What it means to you |
|---|---|
| **ACV** — actual cash value | What your stuff was worth used, on the day of the fire. This is the first check |
| **Recoverable depreciation** | The rest. You get it after you actually replace things and send receipts. **Insurers do not volunteer this. You have to go get it** |
| **RCV** — replacement cost | What it costs to buy new today |
| **Deductible** | For fire, this is the flat all-other-perils amount, not the percentage hurricane deductible |
| **Sub-limits** | Separate, much lower caps hiding inside your policy on jewelry, firearms, cash, business property |
| **Loss of use / ALE** | Pays the *extra* cost of living elsewhere, capped by both a dollar limit and a time limit. Track both |

**Florida protections worth knowing:**

- On a **total loss** of the house by a covered peril, the insurer generally owes **the amount the structure was insured for** — no depreciation holdback (Valued Policy Law, § 627.702). Exceptions apply, including where the loss was partly caused by a non-covered peril, and it does not apply where there was fraud or criminal fault.
- **Building code upgrades** are deemed included at **25% of your dwelling limit** unless you signed a rejection (§ 627.7011). Ask for it. Code upgrades on an older home can exceed the repair itself.
- On a dwelling loss the insurer must pay **at least ACV up front**, with the rest as work is performed.

**Your mortgage company:** the check comes to both of you. Above their threshold (often around $40,000) the money goes into escrow and is released in stages against inspections — commonly a third up front, a mid-repair inspection, a final. Every incomplete document packet adds one to two weeks. Call their loss draft department and ask for their checklist *before* you mail anything.

| 🚫 Never do | What happens |
|---|---|
| Cash a check marked "full and final settlement" | You may have just closed the claim |
| Sign a release to get paid | Nothing in your policy requires signing away rights to be paid what you are owed |
| Assume the first offer is the number | It is an opening position |

---

### Phase 5 · Rebuilding

| ✅ Do now |
|---|
| Submit a **supplement** every time demolition exposes damage nobody could see before — this is normal and expected, not a new claim |
| Keep every invoice and proof of payment; that is what releases your withheld depreciation |
| If the insurer wants you to use its contractor, read the "managed repair" or "right to repair" wording in your policy before agreeing. You may be able to decline — and it may affect what they pay |
| Track your living-expense limit against your construction schedule. If the rebuild will outrun the coverage, raise it early, in writing |

**👁 Watch for:** poor work by the insurer's own contractor. Some carriers have later relied on faulty-workmanship exclusions for damage their own network caused. Document the work as it happens.

---

### Phase 6 · If they say no, or not enough

Florida ladder, in order. Each step is cheap before the next one.

| Step | What it is | Cost | Notes |
|---|---|---|---|
| 1 | Written demand to the adjuster, then the supervisor | Free | Your estimate against theirs, line by line |
| 2 | **DFS complaint** — 1-877-MY-FL-CFO | Free | Creates a regulator record. Often moves the file by itself |
| 3 | **DFS mediation** (§ 627.7015) | **Insurer pays** | Non-binding, confidential, 21-day window before the conference. If the insurer never told you this right existed, it waives its right to force appraisal |
| 4 | **Appraisal** (if your policy still has the clause) | Shared | Settles *how much*, not *whether covered*. Some Florida carriers removed it — check your form |
| 5 | **Notice of Intent to litigate** (§ 627.70152) | Attorney | Required before suit. 10 business days. Cannot be filed before the coverage decision |
| 6 | **Civil Remedy Notice** (§ 624.155) | Attorney | Bad-faith prerequisite. Insurer gets 60 days to fix it |
| 7 | Lawsuit | Attorney | **5 years from the date of loss** (§ 95.11(2)(e)) |

**If you hire help:** a public adjuster in Florida can charge no more than **20%** — or **10%** for claims from a Governor-declared emergency, for a year after the declaration. They cannot charge on money paid to you before you signed with them. You can cancel within 10 business days. Check the license on the DFS site before you sign.

---

### Phase 7 · Deadlines you cannot miss

Deterministic engine output. Never generated, never estimated, always shown with the statute.

| Clock | Florida | Runs from |
|---|---|---|
| Report a new or reopened claim | **1 year** | Date of loss |
| Supplemental claim | **18 months** | Date of loss |
| Loss assessment claim | 3 years | Date of loss |
| File suit | **5 years** | Date of loss |
| **Flood (NFIP) sworn proof of loss** | **60 days** | Date of loss |
| Flood — appeal a denial to FEMA | 60 days | Date of denial letter |
| Flood — file suit | 1 year | Date of written denial |

**Two warnings the engine must always surface:**

1. **Your policy may require notice far sooner than the statute.** The statute is the outer wall. The policy's "prompt notice" clause controls. Show both; default to the stricter.
2. **The 1-year / 18-month rules depend on when your policy was issued.** Policies in force before 16 Dec 2022 generally fall under the older, longer regime. The engine cannot run without `policy_inception_date`.

---

## 4. Other perils — same skeleton, different content

| Peril | Phase content that changes |
|---|---|
| **Hurricane / wind** | Percentage deductible instead of flat; roof repair-vs-replace fight; matching and line-of-sight on tile, siding, shingles |
| **Water (burst pipe, appliance)** | The most common claim of all. Fight is sudden vs. gradual. Many policies now cap water damage at $10,000. Mold has its own sub-limit stacked on top |
| **Flood** | Entirely separate policy. 30-day waiting period. **No living-expense coverage at all** under the standard NFIP form. Contents paid at ACV. Basement coverage severely limited. Unforgiving 60-day proof of loss |
| **Theft** | Police report required; sub-limits on jewelry, firearms, cash; proof of ownership is the whole battle |
| **Lightning / power surge** | Electronics, HVAC boards, well pumps often fail weeks later → supplement window matters |
| **Sinkhole (FL)** | Catastrophic ground cover collapse is mandatory coverage; broader sinkhole coverage is optional. Separate neutral-evaluation process (§ 627.7074) |
| **Tree fall** | Covered when it hits a structure; removal often limited or excluded when it does not |
| **Mold** | Needs a covered water event and prompt reporting; typical $10k cap; delay is the standard denial theory |
| **Condo** | Two policies, two deductibles. Association vs. unit owner split under § 718.111(11) |
| **Vandalism after the fire** | Vacancy exclusions bite after 30–60 days — which is why the Phase 1 written vacancy notice exists |

---

## 5. Red-flag detector → escalation prompt

Deterministic. Two or more fire simultaneously → escalation banner recommending independent representation.

- [ ] Reservation of rights letter
- [ ] Recorded statement requested a second time
- [ ] Contact from SIU or a "special investigator"
- [ ] Request for tax returns, bank statements, or a blank financial authorization
- [ ] Examination Under Oath demanded, especially by an outside law firm
- [ ] Insurer retains an engineer or origin-and-cause expert
- [ ] Third adjuster assigned within 60 days
- [ ] No written estimate 7+ days after inspection
- [ ] Insurer estimate omits scope your own contractor documented
- [ ] Check annotated "full and final"
- [ ] Silence past day 60

**Special case — financial document demands after a fire.** The screen should say plainly:

> Insurers investigating a fire look for a financial motive. They may ask for bank statements, tax returns, and signed authorizations to pull your credit and records. Refusing outright can breach your policy's cooperation clause and sink the claim — courts have held the Fifth Amendment does not excuse you from an Examination Under Oath. **Do not refuse. Do not sign a blank authorization either.** Talk to an attorney about narrowing what you produce.

That is the single highest-stakes screen in the module. It is where a well-meaning refusal destroys an otherwise valid claim.

---

## 6. Artifacts the module generates

Doctrine: the summary is narration, the artifact is truth. Every phase should end in a file the user can send.

| Artifact | Phase |
|---|---|
| Claim log (append-only, timestamped, exportable PDF) | All |
| Written policy request letter | 1 |
| Vacancy notice to insurer | 1 |
| Scoped work authorization rider (dollar cap, no-assignment, no-disposal-without-consent) | 1 |
| Pack-out inventory demand letter | 3 |
| Contents inventory — CSV + PDF, adjuster-ingestible column order | 3 |
| Depreciation challenge letter | 4 |
| Supplement submission cover letter | 5 |
| Demand letter with line-item delta | 6 |
| DFS mediation request prefill | 6 |
| Deadline calendar (.ics) | 7 |

---

## 7. Where the LLM is allowed

Consistent with the existing doctrine — **no LLM call without explicit user action**, and none in date arithmetic.

| Allowed, on explicit tap | Forbidden |
|---|---|
| "Explain this letter I received" (user uploads it) | Computing any deadline |
| "Turn my notes into a demand letter" | Deciding whether a peril is covered |
| "Help me describe this item for my inventory" | Generating phase content on the fly |
| "What does *reservation of rights* mean?" | Predicting settlement value |
| Classify an uploaded document into a known type | Telling the user what to do without a cited authority |

Phase content is data. Deadlines are Python. The model writes prose on request and nothing else.

---

## 8. Voice rules

- Second person. Short sentences. No Latin, no section symbols in body copy — statutes go in a collapsed "authority" footer.
- Never say "you should have." Many users arrive at day 40 having already made three of these mistakes. Every phase needs a "you are already past this — here is what still helps" path.
- Never promise an outcome. Never estimate what they will recover.
- Say what the insurer's incentive is, plainly, without calling them villains. The adjuster is not the enemy; the adjuster is the counterparty. That framing is both accurate and calmer.

---

## 9. One thing to settle before you ship

This module tells people what to do about a legal dispute in a named jurisdiction. That sits close to the unauthorized-practice-of-law line, and Florida enforces it — including under § 626.854(20), which reserves preparing, filing, or negotiating a claim for licensed public adjusters and attorneys.

Practical mitigations, in rough order of cost:

1. Frame everything as **information and document preparation the consumer performs themselves**, never as a recommendation about their specific matter.
2. Do not negotiate, do not contact the carrier on the user's behalf, do not take a percentage of any recovery.
3. Persistent, non-dismissible disclaimer on every phase screen — not a one-time modal at signup.
4. A licensed Florida attorney reviews the content corpus before launch and signs off on the version. Version the corpus so the sign-off attaches to a specific hash.
5. Escalation prompts should point to representation, not away from it.

Worth an hour with a Florida attorney before this ships, not after. The engineering is the easy part here.
