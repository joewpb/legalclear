# Dispatch I-2b — gate report

Governs `backend/src/content/data/fire.jsonl` (seven fire-peril phase records,
`fire.p0.immediate` … `fire.p6.dispute_ladder`). For each of Joe's six gate
items: what the playbook said, why it can't ship, and whether the fire-phase
content left a visible gap where it would otherwise have appeared.

## 1. PA contract cancellation window

**Playbook said:** "PA contract cancellation | 10 business days per DFS;
extended window for declared-emergency claims — **verify current statutory
text** | §626.854(7)" (`property-casualty-claim-playbook.md` §6). The module
spec (`pc-claim-guide-module.md` §3, Phase 6) repeats it as "You can cancel
within 10 business days."

**Why it can't ship:** the playbook flags this specific day-count as
unverified against current statutory text. The owned `pc_citations.py` row
for §626.854 carries only the section title ("Public adjusters"), not a
verified subsection value — nothing in the owned corpus confirms "10
business days" is still correct.

**Gap left:** yes, visible. `fire.p6.dispute_ladder`'s public-adjuster
`do_now` item (`fire.p6.donow.paconsider`) keeps the two facts that *are*
sourced with confidence (the 20%/10% fee caps, license verification) and
drops the cancellation-window sentence entirely rather than repeating an
unverified number.

## 2. CBI-score state list

**Playbook said:** "Seven states restrict or ban CBI scores (California,
Hawaii, Maryland, Massachusetts, Michigan, Oregon, Utah — **verify current
list**)" (`property-casualty-claim-playbook.md` §3).

**Why it can't ship:** explicitly flagged "verify current list" with no
owned authority behind any state's inclusion, and it's an underwriting
fact (not a claims-process fact) with no fire-phase relevance in the first
place.

**Gap left:** no — this content never had a natural home in the seven fire
phases (module spec §3, phases 0–6 cover claim-handling only, not
underwriting). Omitted globally; not referenced anywhere in `fire.jsonl`.

## 3. IRS casualty-loss treatment

**Playbook said:** "IRS casualty-loss deduction treatment for tax year 2026
… confirm with a CPA rather than inferring" (`property-casualty-claim-playbook.md`
§13, "Verify before shipping").

**Why it can't ship:** not in the owned corpus (it's federal tax law, not a
Florida insurance statute), and the playbook itself defers to a CPA rather
than asserting a position.

**Gap left:** no — the module spec's seven fire phases never mention tax
treatment. Omitted globally.

## 4. SFIP/NFIP ALE language

**Playbook said:** "NFIP standard flood policies do not provide ALE at all"
and flags "the exact SFIP form language on ALE and contents valuation" as
unverified (`property-casualty-claim-playbook.md` §6, §13). This is federal
flood-policy language, not a Florida HO statute.

**Why it can't ship:** federal, not owned; and fire is not a flood peril —
asserting NFIP specifics in fire content would also be a peril-scope error.

**Gap left:** no explicit gap, but a deliberate scope boundary:
`fire.p4.the_money`'s `do_now.trackale` item discusses only the HO-policy ALE
mechanic (dollar limit + time limit, general knowledge, no NFIP claim). No
NFIP/SFIP language appears anywhere in the fire seed.

## 5. 60 Minutes report-alteration allegation

**Playbook said:** post-Ian, CBS *60 Minutes* aired allegations that carriers
altered field-adjuster damage reports downward; explicitly logged as
"**Reported but contested** … active litigation, carrier denial on record"
(`property-casualty-claim-playbook.md` §10.2, §13). The module spec repeats
this verbatim as the "why" for Phase 2's field-report request
(`pc-claim-guide-module.md` §3, Phase 2: "post-Hurricane Ian, licensed
adjusters told CBS that carriers altered their damage reports downward...").

**Why it can't ship:** contested, single-source-for-the-underlying-claim,
active litigation with denials on the record — exactly the "no watch_for row
citing it" instruction.

**Gap left:** yes, visible. `fire.p2.adjuster_inspection`'s
`fire.p2.donow.fieldreport` item keeps the operationally identical advice
("ask for the field adjuster's report, compare it to the final estimate")
but the `why` is rewritten to a neutral, source-free justification —
"costs nothing and surfaces a discrepancy if the scope changed between the
two" — with no allegation, no CBS/60 Minutes reference, and no `watch_for`
row built around it.

## 6. 68% closed-without-payment figure

**Playbook said:** "one 2026 industry analysis put residential claims closed
without payment at 68%. Single-source figure … verify before publishing"
(`property-casualty-claim-playbook.md` §10.3).

**Why it can't ship:** explicitly flagged single-source and unverified.

**Gap left:** no — the module spec's phase tables never quote this figure
(it appears only in the playbook's own "recurring patterns" research
section, §10). Omitted globally; not referenced anywhere in `fire.jsonl`.

## Other content omitted for lack of owned authority

- **Emergency-measures sub-limit dollar figure** ("greater of $3,000 or 1%
  of Coverage A," 48-hour approval window) — playbook itself sources this to
  "Policy form; enforced in FL case law" (`property-casualty-claim-playbook.md`
  §6), not a statute. No case citations are in the owned corpus. Omitted
  entirely rather than attaching a fabricated statutory citation — it does
  not appear in `fire.p3.contents_claim` or anywhere else in the seed.
- **`Pervis v. State Farm Fire & Cas. Co.`, 901 F.2d 944 (11th Cir.)** — cited
  in the playbook (§3) for the EUO/Fifth-Amendment point. Not a Florida
  statute and not in `pc_citations.py`. `fire.p6.dispute_ladder`'s
  `fire.p6.never.refuseeuo` item keeps the underlying practical guidance
  (don't refuse outright, don't sign a blank authorization) without citing
  the case.
- **§627.701(10) roof deductible mechanics** and **§95.03** (voids
  shorter contractual limitations periods) — real Florida statutes
  referenced in the playbook but not present in `pc_citations.py`'s owned
  14. Roof deductibles are hurricane/wind-specific and out of scope for a
  fire seed regardless; the §95.03 point is folded into the SOL discussion
  in `fire.p6.dispute_ladder` without a separate citation, since §95.11 (the
  owned SOL authority) already covers the sourced fact (5-year period from
  date of loss).
- **§627.706 / §627.7074 (sinkhole)** and **§718.111 (condo association
  split)** — owned citations, but out of scope for the fire peril; not used.
- **HB 459 / DOAH claim-dispute process** — playbook flags this as false
  (bill withdrawn/died in committee) and it never appears in the module
  spec's fire phases; not referenced.
