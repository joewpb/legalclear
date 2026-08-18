# First-Party Property Claims: Process, Actors, Tactics, and Traps
### Reference build for LegalClear — Property & Casualty module
**Compiled:** 12 August 2026 · **Primary jurisdiction:** Florida (statutes cited) · **General principles:** portable across US states

> Not legal advice. Every conclusion below is subordinate to the actual policy form, its endorsements, and the policy inception date. Verify statutes against the current Florida Statutes before shipping any of this as user-facing guidance.

---

## 0. Fact-check corrections — read this first

Most published content on this topic is stale or wrong. These are errors I found in current (2026) law-firm and vendor content while researching:

| Common claim in the wild | Status | Correct position |
|---|---|---|
| "HB 459 created a mandatory DOAH claim-dispute process" | **FALSE** | HB 459 (2026) was *withdrawn prior to introduction* on 1/9/2026. Companions H 341 and S 108 both **died in committee 3/13/2026**. Multiple 2026 law-firm blogs describe it as enacted law. Voluntary DFS mediation under §627.7015 remains the mechanism. |
| "Statute of limitations is 2 years from date of loss" | **FALSE** | §95.11(2)(e): **5 years**, running from date of loss, for breach of a property insurance contract. The "2 years" claim conflates HB 837's negligence-SOL change. §95.03 voids any policy clause shortening the statutory period. |
| "Insurer has 90 days to pay or deny; 14 days to acknowledge" | **STALE** | SB 2-A (Dec 2022) changed it: **7 calendar days** to acknowledge, **60 days** to pay / deny / pay the undisputed portion (§627.70131). Interest accrues from notice if the 60 days is blown. |
| "The 1-year notice deadline is a hurricane rule" | **FALSE** | §627.70132 applies to **any peril** — fire, pipe burst, theft, everything. |
| "1-year/18-month applies to everyone" | **INCOMPLETE** | Depends on **policy inception date**. Policies effective before 12/16/2022 generally fall under the prior 2-year / 3-year regime. Inception date is a mandatory field in any deadline engine. |

**Design implication:** store *effective dates* alongside every rule, not just rule text. Florida rewrote this body of law in 2019, 2021, 2022, and 2023. Any source not explicitly dated post-March 2023 should be treated as suspect.

---

## 1. The actors — who shows up and whose interests they serve

| Actor | Appears | Serves | What they control | Risk to policyholder |
|---|---|---|---|---|
| Fire department / IC | Hour 0 | Public | Suppression, overhaul, scene release, utility shutoff, limited board-up | Overhaul destroys evidence of contents; document before they finish if safe |
| Fire investigator / FL State Fire Marshal (Bureau of Fire & Arson Investigations) | Hour 0–72 | The State | Origin & cause determination (NFPA 921), scene custody | Their finding shapes the carrier's coverage posture; open investigation is used as a delay lever |
| Law enforcement / ATF | Large loss, fatality, suspected incendiary | The State | Criminal file | Anything said becomes discoverable |
| Building official / code enforcement | Day 1–14 | The municipality | Unsafe-structure determination, red tag, demo orders, permits, 50%-rule findings | Triggers ordinance & law exposure; can force full rebuild economics |
| Utilities | Hour 0 | Themselves | Meter pull, lockout, reconnection inspection | Reconnection delays extend ALE burn |
| American Red Cross | Hour 0–72 | Charitable | Immediate lodging, food, essentials | Not a substitute for ALE; helpful for the paper trail of displacement |
| FNOL rep → field adjuster → desk adjuster → large-loss unit | Day 0–7 | **The carrier** | Claim number, reserve, scope, estimate | Rotation between handlers loses agreements; the *desk* adjuster often edits the *field* adjuster's report |
| SIU (Special Investigation Unit) | Silent from day 1 in most fire claims | The carrier | Fraud/arson referral | Frequently active before the insured knows |
| Coverage counsel / EUO attorney | Week 2+ | The carrier | Examination Under Oath, document demands | This is the point of maximum legal jeopardy |
| Emergency mitigation vendor (board-up, tarp, extraction, drying) | Hour 2–48 | Usually the carrier's network; contractually **you** | Access, demolition, disposal | Work authorization creates *your* personal payment obligation |
| Contents pack-out vendor | Day 1–10 | Carrier network | **The inventory** and chain of custody | Whoever writes the inventory controls the contents claim |
| Textile / electronics / document restorers | Week 1–8 | Carrier network | Clean-vs-replace calls | Restoration economics favor cleaning |
| Structural GC / managed-repair contractor | Week 2+ | Carrier network if MRP | Scope, schedule, quality | Faulty workmanship by *their* contractor can be used to exclude later damage |
| Engineer / industrial hygienist | On dispute | Whoever retains them | Causation opinions | Carrier-retained experts frame causation for denial |
| Mortgage servicer — loss draft dept. | On first check | The lender | Endorsement, escrow, staged disbursement | Can freeze funds for weeks; delinquency changes treatment |
| Public adjuster | Optional | **You** (contingency) | Documentation, valuation, negotiation | Fee caps and cooling-off rules apply; check license |
| Policyholder attorney | Optional | **You** | Legal posture, EUO defense, litigation | Fee economics changed post-HB 837 |
| FL DFS — Consumer Services / Mediation / CRN portal | On dispute | Regulator | Complaint record, mediation, Civil Remedy Notice | Free; creates the regulatory paper trail |
| FL OIR | Systemic | Regulator | Market conduct exams, rate approval | Not a claim remedy, but complaint volume matters |
| FEMA / SBA | Declared disaster only | Federal | IA grants, disaster loans | **Duplication of benefits** — Stafford Act §312 forces offset/recoupment against insurance proceeds |

---

## 2. Master timeline — fire loss

### Hour 0–24
1. Do not re-enter until the fire department releases the structure. Overhaul, hot spots, CO, structural compromise.
2. **Photograph and video before anything moves.** Wide → medium → close on labels, serials, brands. Open drawers, closets, cabinets. This record is the single highest-leverage asset in the entire claim.
3. FNOL to the carrier. Capture: claim number, adjuster name + license + supervisor, carrier's claim email of record.
4. Ask three questions on the first call: *Is there an ALE advance? What is the emergency-mitigation limit on this policy? Who authorized which vendors?*
5. Obtain the fire incident report number. In most jurisdictions the report is a public record.
6. Secure the site — board-up, tarp, lock. Site security after release is the **owner's** duty; failure to secure invites uncovered further loss.
7. Extract irreplaceables if safe and permitted: IDs, passports, deeds, titles, policies, medications, firearms, cash, jewelry, hard drives. If investigators are working the scene, they may escort and inventory what you remove.
8. Notify the mortgage servicer.

### Day 1–7
- Adjuster inspection. Attend it. Take your own photos of what they photograph.
- **Request the complete certified policy** — dec page, form, all endorsements. In writing. Not the summary.
- Open a claim diary: date, time, name, title, phone, what was said, what was agreed. Confirm every material agreement by email the same day.
- Scope every vendor authorization in writing before signing. Cap dollar amounts. Strike open-ended terms.
- Start ALE receipts immediately — lodging, meals *above baseline*, laundry, pet boarding, mileage, storage.
- If a pack-out is proposed: see §4.

### Week 2–8
- Build the contents inventory (§5). This is the long pole.
- Get your own independent structural estimate. Do not rely solely on the carrier's Xactimate output.
- Florida: carrier must send you a copy of its detailed estimate **within 7 days of the estimate being generated**.
- Florida: coverage decision — pay, deny, or pay the undisputed portion — **within 60 days** of notice.
- Watch for a **reservation of rights** letter. That is the formal signal the file has an adversarial posture.

### Month 2–6
- Negotiate scope and depreciation. Submit supplements as concealed damage is exposed during demolition.
- Permits, code-upgrade requirements, ordinance & law claim.
- Mortgage draw cycle: initial release (often ~1/3), mid-repair inspection, final inspection.
- Recover withheld depreciation as work is completed and invoiced.

### Month 6–24 and out
- ALE exhaustion management — track the limit and the time cap separately.
- Supplemental claim: **Florida 18 months from date of loss** (§627.70132).
- Suit: **5 years from date of loss** (§95.11(2)(e)), subject to pre-suit conditions.

---

## 3. The credit question — direct answer

**Q: Does the insurance company run your credit after a fire?**

Three separate mechanisms, routinely conflated:

**1. Credit-based insurance scores — underwriting, not claims.**
Insurers use a credit-based insurance (CBI) score at application and renewal in most states to price the policy. It is a soft pull; it does not damage your consumer credit score. It is not part of adjudicating the claim. Some carriers do re-run credit at the renewal that follows a claim. Seven states restrict or ban CBI scores (California, Hawaii, Maryland, Massachusetts, Michigan, Oregon, Utah — verify current list).

**2. Loss-history databases — this is what actually follows you.**
The claim is reported to CLUE / A-PLUS. It attaches to **the property as well as the person**, for roughly five to seven years. It affects future insurability, pricing, and the next buyer's ability to insure. It does not appear on your credit report.

**3. SIU / arson investigation — this is the real financial dig, and it is deep.**
In fire losses with fraud indicators, the carrier's Special Investigation Unit builds a circumstantial case on **means, motive, and opportunity**. Motive means financial distress. Under the policy's cooperation clause and via the Examination Under Oath, carriers routinely demand:

- Bank and credit card statements
- Tax returns, often multiple years
- Mortgage statements, foreclosure/lis pendens status
- Loan and vehicle payment records
- Investment and retirement account statements
- Employment and salary information
- **Signed authorizations to pull credit and obtain records directly from financial institutions**

Red flags that escalate a fire claim into this track: coverage increased shortly before the loss; valuables removed from the home shortly before the loss; fire while the home was unoccupied; pending foreclosure or business failure; property listed and not selling; prior fire claims; insured amount well above market value; inconsistent statements between the recorded statement and the EUO.

**The traps:**
- **Open-ended authorizations.** Carriers present blanket, undated, unlimited financial authorizations. These should be scoped: named institutions, defined date range, defined account types, expiration date.
- **The Fifth Amendment is not a shield here.** Federal courts have held that the privilege against self-incrimination does not excuse an insured from answering material questions at an EUO — refusal can be treated as breach of the cooperation condition and used as a defense to the entire claim. *Pervis v. State Farm Fire & Cas. Co.*, 901 F.2d 944 (11th Cir.). So the play is never refusal — it is scoped, counseled compliance.
- **The recorded statement is the soft version of the EUO.** It is taken early, without counsel, before the insured has read the policy. Inconsistencies between it and the later EUO are the primary impeachment material.
- **Florida-specific:** §627.702(1)(a) — the Valued Policy Law's payment obligation is expressly conditioned on the **absence of fraudulent or criminal fault** by the insured or someone acting on their behalf. Arson findings do not just reduce the claim; they eliminate the statutory total-loss guarantee.

**Operating rule:** cooperate fully, in writing, with scope negotiated by counsel before production. Never refuse. Never produce blind.

---

## 4. The mitigation / pack-out / storage question — direct answer

**Q: Is the fast dispatch of movers and cleaners actually helping the carrier?**

The instinct is correct, but the mechanism is more specific than "they're stalling your inventory." Both things are true simultaneously:

### The legitimate half
- The policy imposes a duty to protect property from further damage. Delay is itself a coverage risk.
- Smoke residue is acidic and corrosive; damage compounds hourly. Soot etches metal, glass, and finishes.
- Mold can establish on wet materials in **24–48 hours**. A slow response converts a covered sudden loss into a "gradual damage / neglect" coverage fight.
- Carriers genuinely have an incentive to reduce total severity by moving fast.

### The structural conflict
| Mechanism | How it cuts against the insured |
|---|---|
| **The vendor writes the inventory** | The pack-out list becomes the operative record of what existed. Box-level entries ("Kitchen misc — 1 box") functionally cap the contents claim at whatever that document describes. |
| **The vendor is selected, paid, and reviewed by the carrier** | Repeat-business economics run one direction. The vendor's continued referral flow depends on the carrier, not on you. |
| **Clean-vs-replace is decided by the party paid to clean** | Restoration is cheaper than replacement. Items marked "restorable" that still hold odor or embedded soot resurface as disputes months later — after the leverage is gone. |
| **Once cleaned and returned, an item is presumptively not a total loss** | The burden flips. Proving a returned sofa is unusable is far harder than proving it before cleaning. |
| **Storage** | Contents sit in a warehouse under vendor control. Risks: loss, transit damage, commingling with other jobs, and a lien or possessory hold pending payment. Confirm in writing **which coverage pays storage** — contents limit vs. ALE — because that choice quietly consumes a limit. |
| **Extended storage** | If the rebuild drags, storage charges accrue for months against a fixed limit. |
| **Work authorizations** | Not an AOB, but it is a direct contract between **you** and the vendor. Whatever the carrier does not pay, the vendor pursues from you personally. In Florida, post-1/1/2023 policies cannot be assigned at all (§627.7152(13) — any attempt is void), so the vendor's only recourse *is* the homeowner. |
| **Emergency-measures sub-limit** | Newer Florida forms cap reasonable emergency measures at **the greater of $3,000 or 1% of Coverage A**, exceeded only with carrier approval — with a 48-hour response window on a request to exceed. Florida courts have enforced this strictly: no documented pre-approval request, no payment above the cap. The balance lands on the homeowner. |

### Counter-protocol
1. **No pack-out begins until your independent visual record exists.** Non-negotiable. Room by room, drawer by drawer, on video with narration.
2. Demand the vendor's inventory **in writing before items leave the property**, at **item level**, with photos of each box's contents and a copy of the barcode/chain-of-custody manifest.
3. Get a written **non-salvageable list** agreed early, with photos, before disposal.
4. **Nothing gets discarded without your written authorization plus photographs.** Get this in the authorization document.
5. Keep irreplaceables, high-value items, and all documentation **out of the pack-out** entirely.
6. Get storage location, your right of access, duration, rate, and payer in writing.
7. Add a reservation to any acceptance of restored items: acceptance is not a waiver if odor, soot, or residue recurs.
8. Scope the work authorization: dollar cap, defined scope, no lien clause, no assignment, no direction-of-payment beyond the specific work.

---

## 5. Contents inventory — the core doctrine

The contents claim is where the largest recoverable delta sits and where policyholders are least equipped. This is the module worth building well.

### Required fields per item
`room` · `category` · `description` · `brand` · `model` · `serial` · `quantity` · `age / purchase date` · `original price` · `condition` · `RCV` · `RCV source (URL + screenshot)` · `proposed depreciation %` · `ACV` · `evidence type` · `evidence file` · `damage disposition (destroyed / cleanable / questionable)` · `status (claimed / agreed / disputed / paid)`

### Evidence reconstruction sources
Credit card and bank statements · email receipt archives · retailer order history (Amazon, Home Depot, Best Buy) · warranty registrations · scheduled-property endorsements and appraisals · prior real-estate listing photos of the home · social media photos · family and friend photos taken inside the home · video walkthroughs · moving company inventories from prior moves · store gift-registry scanners used in reverse to rebuild and price a list.

### Valuation mechanics
- **ACV** = pre-loss value. **RCV** = cost to replace new, like kind and quality. **Recoverable depreciation** = the gap, released only after you actually replace and submit proof.
- **Depreciation is subjective and negotiable.** There is no legally binding depreciation schedule in general use. Ask the carrier for the schedule it applied and challenge it item by item.
- Categories that commonly should not be depreciated, or barely: antiques, fine art, jewelry, collectibles, software and media, light fixtures, masonry, insulation, concrete.
- Depreciation should reflect actual condition, not category averages — guest-room furniture used twice a year is not master-bedroom furniture.
- Price replacements at **standard retailers**, not discount or clearance pricing.
- Contents limits are typically set as a percentage of dwelling coverage — commonly 50–70%.
- On a genuine total loss, negotiating a **limits cash-out** in lieu of a line-item inventory is a legitimate ask. Carriers rarely grant it, but the request costs nothing and sometimes lands, particularly where the insured followed the agent's own coverage recommendations and is already near the limit partway through the list.

### Hard rule
**Never claim an item you did not own.** Innocent errors on a reconstructed inventory are normal and forgivable. Intentional inflation is material misrepresentation — it voids the claim and is a felony. Padding also hands the carrier the fraud narrative it needs to justify the SIU track described in §3.

---

## 6. Money mechanics

| Mechanism | Rule | Florida authority |
|---|---|---|
| Initial dwelling payment | At least **ACV** up front, less deductible; balance paid as work is performed and expenses incurred | §627.7011(3)(a) |
| Total loss of dwelling | Replacement cost **without holdback of depreciation** | §627.7011(3)(a) |
| Valued Policy Law | Total loss of a building from a covered peril → liability is **the amount for which it was insured as specified in the policy**. Does not apply where loss was caused in part by a non-covered peril (unless covered perils alone would have caused total loss), where undisclosed other insurance exists, blanket forms, or builder's risk. Conditioned on absence of fraudulent or criminal fault. | §627.702(1), (3) |
| Partial fire loss | Actual amount of the loss, capped at the amount of insurance specified for that property and peril | §627.702(2) |
| Law & ordinance | **Deemed included at 25% of dwelling limit** unless the policyholder rejected it in writing on an approved form. 50% option available. Applies only to the damaged portion unless total damage exceeds 50% of replacement cost. | §627.7011(1)(b), (2) |
| Insurer's option to repair | Carrier may repair or replace at its own expense in lieu of paying, with premium refund conditions | §627.702(7) |
| Emergency measures cap | Greater of **$3,000 or 1% of Coverage A** in many current forms; 48-hour approval mechanic to exceed | Policy form; enforced in FL case law |
| Acknowledge claim | **7 calendar days** | §627.70131 |
| Begin investigation / physical inspection | 7 days after proof of loss / inspection within 30 days | §627.70131 |
| Deliver detailed estimate | **7 days** after it is generated | §627.7142 (Homeowner Claims Bill of Rights) |
| Pay, deny, or pay undisputed portion | **60 days** from notice; interest accrues from date of notice if missed | §627.70131(7)(a) |
| Public adjuster fee cap | **20%** standard; **10%** for events under a Governor-declared state of emergency, for one year after declaration; nothing on payments made before the contract | §626.854(11)(b) |
| PA contract cancellation | **10 business days** per DFS; extended window for declared-emergency claims — verify current statutory text | §626.854(7) |
| PA solicitation hours | Mon–Sat, 8am–8pm | §626.854 |
| AOB | **Void and unenforceable** for policies issued on or after **1/1/2023** | §627.7152(13) |

### Deductibles
Fire uses the all-other-perils (AOP) deductible — a flat dollar figure. Hurricane deductibles are percentage-based (2%/5%/10% of Coverage A) and apply per calendar-year hurricane season in Florida. Roof deductibles are a separate mechanic under §627.701(10) and interact with the ACV limitation in §627.7011(3)(a).

### Additional Living Expense (ALE) / Loss of Use
Typically a percentage of Coverage A **and** a time cap (12 or 24 months). Covers the *increase* over normal living costs, not total costs. Track lodging, meals above baseline, laundry, pet boarding, storage, extra commuting, furniture rental. **NFIP standard flood policies do not provide ALE at all** — a frequent and expensive surprise. Ask for an advance in the first 48 hours.

### Mortgagee / loss draft
Checks are issued jointly to borrower and servicer. Above the servicer's threshold (commonly ~$40k, but servicer- and investor-specific), funds go into a restricted escrow and are released in stages against inspections — commonly an initial release around one-third, a mid-repair inspection, and a final inspection. Packet contents: carrier loss statement, contractor contract, W-9, contractor license and COI, signed loss draft application. **Every incomplete submission adds 5–14 days.** Loan delinquency changes the servicer's handling posture.

---

## 7. Dispute escalation ladder — Florida

| # | Step | Mechanics | Notes |
|---|---|---|---|
| 1 | Written demand to adjuster, then supervisor | Your estimate vs. theirs, line-item delta | Everything in writing, always |
| 2 | DFS Consumer Helpline complaint | 1-877-MY-FL-CFO | Free; creates a regulatory record; often produces movement alone |
| 3 | **DFS residential mediation** — §627.7015 | Request via DFS; **21-day** window before conference; **insurer bears the cost**; non-binding; confidential | Available before appraisal or litigation. Insurer must notify you of this right at issuance, renewal, and claim filing. **Failure to give that notice waives the insurer's right to compel appraisal.** Not available to third-party assignees. |
| 4 | **Appraisal** — policy clause | Each side names an appraiser; they select an umpire | Resolves **amount of loss only**, not coverage. Some Florida carriers have removed the clause entirely — check the form. Filing suit first can waive it. §627.70151 governs conflicts of interest. |
| 5 | **Pre-suit Notice of Intent** — §627.70152 | DFS form; **10 business days** before suit; cannot be filed before the coverage determination; must state the statute, the acts complained of, the damages estimate, and a numerical settlement demand (with attorney fees stated separately) | Condition precedent — suit filed without it is dismissed without prejudice. Insurer may reinspect within **14 business days**. Limitations tolled during ADR; if ADR is not concluded within 90 days after the 10-day period expires, you may file. |
| 6 | **Civil Remedy Notice** — §624.155 | Filed on the DFS portal; identify specific statutory violations, facts, and the cure amount; insurer gets **60 days to cure** | Prerequisite to statutory first-party bad faith. HB 837 (2023) repealed the general one-way attorney-fee statute — model the fee economics before recommending this path. |
| 7 | **Suit** | **5 years from date of loss**, §95.11(2)(e) | §95.03 voids shorter contractual periods |

### Parallel track — NFIP flood
Entirely separate and far less forgiving:
- **Sworn Proof of Loss within 60 days of loss**, absent a FEMA waiver. 44 C.F.R. pt. 61, app. A(2), art. VII(G)(4). Courts enforce this rigidly — non-compliance bars recovery even where the carrier investigated and made partial payments.
- **FEMA appeal within 60 calendar days** of the written denial letter. Free; no representative required. Does not extend the suit deadline.
- **Suit in federal district court within one year** of the written denial.
- Mitigation reimbursements are small and capped. Contents are ACV. Basement coverage is severely limited. No ALE.

---

## 8. The peril taxonomy — beyond fire and flood

### Group A — sudden physical damage, generally covered under an HO-3
Windstorm · hurricane · tornado · hail · lightning · explosion · smoke · vehicle impact · aircraft · riot and civil commotion · vandalism and malicious mischief · theft · falling objects · weight of ice, snow, or sleet · accidental discharge or overflow of water or steam from plumbing, HVAC, appliances, or sprinklers · freezing of plumbing · sudden tearing, cracking, burning, or bulging of a steam or hot-water system · artificially generated electrical current (power surge) · volcanic eruption · tree fall · limited collapse.

### Group B — separate policy or endorsement required
Flood (NFIP or private) · earthquake and earth movement · sinkhole (Florida: **catastrophic ground cover collapse is mandatory**; broader sinkhole coverage is optional by endorsement — §627.706) · sewer and drain backup · equipment breakdown · service line · ordinance & law above the deemed limit · mold above the sub-limit · scheduled personal property (jewelry, art, firearms, collectibles) · home business · wind/hurricane where excluded from the base policy (Citizens wind-only) · builder's risk during renovation · terrorism (commercial).

### Group C — generally excluded
Wear and tear · deterioration · neglect · gradual or repeated seepage over time · rot and mold from long-term leakage · settling, cracking, shrinking, bulging · vermin, insects, rodents · faulty workmanship, design, or materials (watch the ensuing-loss carve-back) · intentional acts by the insured · war · nuclear hazard · government seizure · **vacancy beyond the policy's stated period** · earth movement · off-premises power failure · smog, rust, corrosion.

### Group D — liability-side incidents that also arise on property
Guest injury · dog bite · pool and attractive nuisance · contractor injury on premises · your fire spreading to a neighbor (their carrier subrogates against you) · your tree falling on a neighbor's structure · water escaping into an adjacent condo unit · host liquor liability.

### Group E — other lines that intersect
Business interruption and extra expense · contingent BI · spoilage · inland marine · builder's risk · condominium association vs. unit-owner split (FL §718.111(11) — the "walls-in" allocation) · renters (HO-4) · landlord dwelling forms (DP-1/DP-3, loss of rents) · autos and boats (not on the HO policy) · farm and ranch.

### Frequency and severity — the shape of the problem
Based on Triple-I / ISO data (2019–2023 window):

| Peril | Frequency | Average severity |
|---|---|---|
| Wind and hail | ~1 in 36 insured homes/yr | ~$11–13k |
| Water damage and freezing | ~1 in 67 | ~$15.4k |
| **Fire and lightning** | **~1 in 430** | **~$84–88k** |
| Theft | ~1 in 850 | ~$5.5k |
| Liability | ~1 in 1,150 | ~$29.9k |

Roughly **1 in 18 insured homes** files a claim in a given year; property damage is ~97% of claims. Fire is the rare, catastrophic tail — low frequency, severity that exceeds most households' entire financial cushion. **This is why the fire workflow, not the wind workflow, is the one that has to be airtight.**

---

## 9. Peril-specific traps

| Peril | Trap |
|---|---|
| Hurricane / wind | Separate percentage deductible; 1-year notice; roof age schedules; carriers scoping "repair not replace"; matching / line-of-sight disputes on siding, tile, and shingles |
| Non-weather water | Highest-frequency claim; sudden-vs-gradual causation fight; **$10,000 sub-limits** on many current FL forms; managed-repair steering; mold sub-limit stacked on top |
| Flood | Not covered by any HO policy; NFIP 30-day waiting period; **no ALE**; contents at ACV; basement limits; 60-day sworn POL; 1-year federal suit deadline |
| Sinkhole (FL) | CGCC ≠ sinkhole coverage; neutral evaluation process under §627.7074; testing standards under §627.7072 |
| Theft | Police report required; sub-limits on jewelry, firearms, cash, silverware; proof of ownership burden |
| Lightning / surge | Damage to electronics, HVAC control boards, and well pumps often surfaces weeks later → supplemental claim window matters |
| Mold | Requires a covered water event and prompt reporting; typical $10k sub-limit; delay in mitigation is the standard denial theory |
| Tree fall | Covered when it strikes a structure; removal cost limited or excluded when it does not |
| Vandalism / vacancy | **Vacancy exclusions bite after 30–60 days** — this is a live risk in every fire claim, because the house is empty by definition. Read the vacancy provision on day one and notify the carrier in writing that the property is unoccupied due to the covered loss. |
| Wildfire smoke without flame contact | Actively contested; requires industrial hygienist testing to establish physical loss |
| Ordinance & law | Code upgrades, flood-zone elevation requirements, and the **50% substantial-damage rule** can exceed the repair cost itself and are capped at 25% of Coverage A by default |
| Condo | Association vs. unit-owner allocation determines who claims what; two carriers, two deductibles, two timelines |

---

## 10. What history says — recurring patterns

1. **Post-catastrophe adjuster churn.** Files rotate through multiple handlers with varying training. Verbal agreements evaporate. The claim diary is the only defense.
2. **Report alteration.** In September 2024, CBS *60 Minutes* aired testimony from licensed adjusters alleging that carriers altered post-Hurricane Ian damage reports downward while leaving the field adjuster's name and license on them. One adjuster stated 44 of his 46 Ian reports were changed, always downward; another said 18 of 20 were altered, with instructions to omit roof damage. The allegations named multiple carriers and are **contested** — Heritage acknowledged some reports were edited but characterized it as normal collaboration, and sued one whistleblower for defamation. Treat as serious allegation, not adjudicated fact. The operational lesson stands regardless: **obtain the field adjuster's report directly, and compare it against the carrier's final estimate.**
3. **High closed-without-payment rates** after named storms — one 2026 industry analysis put residential claims closed without payment at 68%. Single-source figure; directionally consistent with FL OIR data patterns, but verify before publishing.
4. **First offers are opening positions.** Large deltas between initial offers and final settlements are well documented, though the dramatic case-result numbers circulated by plaintiff firms and public adjusters are marketing and should not be repeated as base rates.
5. **Systemic underinsurance.** Coverage A limits set years ago against replacement costs that have risen 30–40%+. The total-loss claim is where this surfaces, and it is unfixable at that point.
6. **Depreciation applied aggressively and inconsistently.** No binding schedule exists; the numbers are negotiable and rarely negotiated.
7. **Release pressure.** Checks marked "full and final settlement"; releases presented as routine paperwork. Nothing in the policy requires signing away rights to be paid on a covered loss.
8. **Post-disaster solicitation swarms.** Unlicensed adjusters, storm-chaser contractors, AOB abuse. Florida's response — the AOB ban and PA fee caps — reduced the abuse but also removed leverage tools from legitimate policyholders.
9. **Legislative whipsaw.** Florida rewrote notice deadlines, fee-shifting, AOB rules, and payment timelines in 2019, 2021, 2022, and 2023. Content written before March 2023 is unreliable. The 2026 session produced no enacted change to the dispute-resolution framework despite widespread reporting to the contrary.
10. **Arson suspicion as leverage.** Even where no incendiary finding is ever made, the pendency of an origin-and-cause or SIU investigation is used to hold payment. There is no statutory tolling of the insurer's obligations for an open investigation — the 60-day clock still runs.

---

## 11. Red-flag checklist — the claim has gone adversarial

- [ ] Reservation of rights letter received
- [ ] Recorded statement requested early, or requested a second time
- [ ] Contact from SIU or a "special investigator"
- [ ] Demand for tax returns, bank statements, or a blanket financial authorization
- [ ] EUO demand, especially one issued by outside counsel
- [ ] Carrier retains an engineer or origin-and-cause expert
- [ ] Third adjuster assigned in under 60 days
- [ ] No written estimate delivered within 7 days of generation
- [ ] Carrier estimate omits scope items your own contractor documented
- [ ] Check endorsed or annotated "full and final"
- [ ] Pressure to use the carrier's contractor; refusal to consider your estimate
- [ ] Silence past the 60-day statutory decision deadline

Any two of these together should trigger, in the product, an escalation prompt and a recommendation to obtain independent representation.

---

## 12. Build implications for LegalClear

### Data model
`Loss` · `Policy` (**must include `inception_date`** — it determines which deadline regime applies) · `Coverage` · `Peril` · `Actor` · `Document` · `Deadline` · `InventoryItem` · `Estimate` · `Payment` · `Dispute` · `CommunicationLogEntry`

### Deadline engine
Keyed off `date_of_loss` × `jurisdiction` × `policy_inception_date` × `peril`. Must resolve the conflict between the **statutory outer boundary** and the **contractual prompt-notice clause** — the stricter controls, and policies routinely require notice far faster than the statute. Surface both, flag the conflict, default to the stricter.

Distinct clocks to model for Florida: initial notice (1 yr) · supplemental (18 mo) · loss-assessment notice (3 yr, §627.70132(4)) · insurer acknowledgment (7 d) · insurer inspection (30 d) · estimate delivery (7 d) · coverage decision (60 d) · mediation window (21 d) · pre-suit NOI (10 bd) · insurer reinspection (14 bd) · CRN cure (60 d) · suit (5 yr) · NFIP POL (60 d) · NFIP appeal (60 d) · NFIP suit (1 yr).

### Inventory module — this is the differentiator
Voice and photo capture → item extraction → category classification → replacement-cost lookup with source capture → depreciation table with per-category defaults and manual override → evidence attachment → dispute flagging → **export in a format an adjuster will actually ingest.** The pack-out timing problem in §4 is a product opportunity: a guided pre-pack-out capture flow, time-stamped and geotagged, executed in the first 24 hours.

### Document classifier
Reservation of rights · sworn proof of loss · EUO demand · financial authorization · work authorization · AOB · release/waiver · loss draft packet · carrier estimate · field adjuster report · non-salvageable list · pack-out manifest. Each maps to a distinct user action and urgency level.

### Escalation state machine
Model §7 as explicit states with jurisdiction-specific transitions and preconditions (e.g. NOI cannot precede the coverage determination; appraisal may be waived by filing suit; mediation notice failure waives the insurer's appraisal right).

### Citation hygiene
Store `effective_date` and `superseded_by` on every rule. Auto-flag any authority sourced before 2023-03-24 for Florida. Build a source-tier ranking: primary statute > appellate decision > DFS/OIR publication > practitioner commentary > SEO content. As demonstrated in §0, the bottom tier is wrong often enough to be dangerous.

---

## 13. Source notes and confidence

**High confidence — primary sources verified directly:** Fla. Stat. §§ 95.11(2)(e), 627.702, 627.7011, 627.70131, 627.70132, 627.7015, 627.70152, 627.7152, 626.854; 44 C.F.R. §§ 61.13, 62.20; Florida Senate bill history for HB 459 (2026).

**Medium confidence — reputable secondary, cross-checked:** United Policyholders claim guidance; Triple-I / ISO claim frequency and severity data; U.S. Fire Administration post-fire guidance; FEMA duplication-of-benefits policy; mortgage servicer loss-draft practice (varies by servicer and investor).

**Reported but contested:** the post-Ian report-alteration allegations (§10.2) — active litigation, carrier denial on record.

**Verify before shipping:** the current list of states restricting credit-based insurance scores; the exact PA contract cancellation window under the current §626.854(7) text; IRS casualty-loss deduction treatment for tax year 2026 (TCJA-era limitation to federally declared disasters interacts with subsequent legislation — confirm with a CPA rather than inferring); the exact SFIP form language on ALE and contents valuation.

**Known-unstable:** everything in the Florida dispute-resolution framework. Re-verify each legislative session.
