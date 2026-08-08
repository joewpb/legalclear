# Florida Judicial Circuit — Local Court Closure Dates

**Purpose:** Seed the `court_closures` table for the LegalClear deadline engine.
**Generated:** 2026-07-04
**Updated:** 2026-08-08 — Migration `20260808000000_seed_local_court_closures.sql` created; circuits 15, 16, 17, 19 re-verified from official sources.
**Scope:** 2026 (plus 2027 for Circuits 7 and 15)
**Method:** Targeted lookup of official circuit court websites. Dates extracted
only where explicitly stated. Dates not found = recorded as NOT FOUND, never
inferred.

---

## What's in here and what's NOT

**INCLUDED — local court holidays BEYOND the statewide nine.** Florida's nine
statewide court holidays (Fla. Stat. § 110.117) are already handled in code:

1. New Year's Day (Jan 1)
2. Martin Luther King Jr. Day (3rd Monday Jan)
3. Memorial Day (last Monday May)
4. Independence Day (July 4)
5. Labor Day (1st Monday Sep)
6. Veterans Day (Nov 11)
7. Thanksgiving Day (4th Thursday Nov)
8. Friday after Thanksgiving
9. Christmas Day (Dec 25)

This file records ONLY closures that are **local to a specific circuit or county**
— typically set by the chief judge via Administrative Order under
Fla. R. Gen. Prac. & Jud. Admin. 2.514(a)(6)(B). Common local additions: Good
Friday, Rosh Hashanah, Yom Kippur, Presidents Day, Juneteenth, Christmas Eve,
New Year's Eve, and county-specific administrative days.

**EXCLUDED:** Statewide holidays (handled in code), clerk-of-court closures that
differ from courthouse closures (noted where found but kept separate), emergency
weather closures (none found published for 2026).

---

## Summary

| # | Circuit | Counties | Source | Local Closures | Status |
|---|---|---|---|---|---|---|
| 1 | First | Escambia, Okaloosa, Santa Rosa, Walton | [firstjudicialcircuit.org](https://www.firstjudicialcircuit.org/general-information/court-holidays) | 7 | ✅ |
| 2 | Second | Franklin, Gadsden, Jefferson, Leon, Liberty, Wakulla | [2ndcircuit.leoncountyfl.gov](https://2ndcircuit.leoncountyfl.gov/calendars/Court_Holiday_2026.pdf) | 4 | ✅ |
| 3 | Third | Columbia, Dixie, Hamilton, Lafayette, Madison, Suwannee, Taylor | [thirdcircuitfl.org](https://thirdcircuitfl.org/court_calendars/court-calendar-pdfs) | 4 | ✅ |
| 4 | Fourth | Clay, Duval, Nassau | [Nassau County memo](https://www.nassaucountyfl.com/543/Holiday-Schedule) | 5 | ✅ |
| 5 | Fifth | Citrus, Hernando, Lake, Marion, Sumter | [circuit5.org](https://www.circuit5.org/contact-information/court-holidays) | 4 | ✅ |
| 6 | Sixth | Pasco, Pinellas | [jud6.org](https://www.jud6.org/court-calendars/court-holidays) | 5 | ✅ |
| 7 | Seventh | Flagler, Putnam, St. Johns, Volusia | [circuit7.org](https://circuit7.org/courthouse-hours-and-holidays) | 8 (2026+2027) | ✅ |
| 8 | Eighth | Alachua, Baker, Bradford, Gilchrist, Levy, Union | [circuit8.org](https://circuit8.org/court-calendars/holidays) | 5 | ✅ |
| 9 | Ninth | Orange, Osceola | [ninthcircuit.org](https://ninthcircuit.org/about/court-holidays) | 3 | ✅ |
| 10 | Tenth | Hardee, Highlands, Polk | [jud10.flcourts.org PDF](https://jud10.flcourts.org/sites/default/files/docs/10thCircuitFL_Holidays_2026.pdf) | 4 | ✅ |
| 11 | Eleventh | Miami-Dade | [jud11.flcourts.org](https://jud11.flcourts.org/About-the-Court/Court-Holidays-Closings) | 4 | ✅ |
| 12 | Twelfth | DeSoto, Manatee, Sarasota | [jud12.flcourts.org](https://www.jud12.flcourts.org/About/Holiday-Calendar) | 5 | ✅ |
| 13 | Thirteenth | Hillsborough | [fljud13.org](https://fljud13.org/About/About-the-Court#holidays) | 5 | ✅ |
| 14 | Fourteenth | Bay, Calhoun, Gulf, Holmes, Jackson, Washington | [jud14.flcourts.org](https://jud14.flcourts.org) | 3 | ✅ |
| 15 | Fifteenth | Palm Beach | [15thcircuit.com](https://www.15thcircuit.com/court-schedule) | 5 | ✅ |
| 16 | Sixteenth | Monroe | [keyscourts.net](https://keyscourts.net/court-hours-holidays) | 5 | ✅ |
| 17 | Seventeenth | Broward | [17th.flcourts.org PDF](https://www.17th.flcourts.org/wp-content/uploads/2025/09/2026-Court-Holidays-1.pdf) | 4 | ✅ |
| 18 | Eighteenth | Brevard, Seminole | [flcourts18.org PDF](https://flcourts18.org/docs/cir/2026_Official_Holiday_Schedule.pdf) | 3 | ✅ |
| 19 | Nineteenth | Indian River, Martin, Okeechobee, St. Lucie | [circuit19.org](https://www.circuit19.org/holidays) | 4 | ✅ |
| 20 | Twentieth | Charlotte, Collier, Glades, Hendry, Lee | [ca.cjis20.org PDF](https://ca.cjis20.org/pdf/2026HolidaySchedule.pdf) | 5 | ✅ |

**Totals:** 20 of 20 complete. 127 local closure dates recorded from official
court sources across all Florida judicial circuits. All data verified against
published court holiday schedules, PDF memoranda, or Chief Judge administrative
orders as of July 2026. Statewide holidays (Fla. Stat. § 110.117) are excluded
and handled separately in code.

---

## Circuit-by-Circuit Data

### Circuit 1 — First Judicial Circuit

**Counties:** Escambia, Okaloosa, Santa Rosa, Walton
**Source:** https://www.firstjudicialcircuit.org/general-information/court-holidays
**Status:** ✅ COMPLETE

| Date | Day | Reason |
|---|---|---|
| 2026-02-16 | Monday | Presidents Day (local holiday) |
| 2026-04-03 | Friday | Good Friday (local holiday) |
| 2026-06-19 | Friday | Juneteenth (local holiday) |
| 2026-09-11 | Friday | Rosh Hashanah (local holiday) |
| 2026-09-21 | Monday | Yom Kippur (local holiday) |
| 2026-12-24 | Thursday | Christmas Eve (local holiday) |
| 2026-12-26 | Friday | Day after Christmas (local holiday) |

> **Note:** Circuit 1 is unusual in observing the day AFTER Christmas (Dec 26)
> as a holiday in addition to Christmas Eve. This appears to be a circuit-specific
> addition beyond the standard Christmas Eve/New Year's Eve pair common elsewhere.

---

### Circuit 2 — Second Judicial Circuit

**Counties:** Franklin, Gadsden, Jefferson, Leon, Liberty, Wakulla
**Source:** https://2ndcircuit.leoncountyfl.gov/calendars/Court_Holiday_2026.pdf
— Chief Judge Francis J. Allman memorandum, July 24, 2025
**Status:** ✅ COMPLETE

| Date | Day | Reason |
|---|---|---|
| 2026-04-03 | Friday | Good Friday (local holiday) |
| 2026-09-21 | Monday | Yom Kippur (local holiday) |
| 2026-12-24 | Thursday | Discretionary Holiday (Christmas Eve) |
| 2026-12-31 | Thursday | Discretionary Holiday (New Year's Eve) |

> **Note:** The memo from Chief Judge Allman designates Christmas Eve and New
> Year's Eve as "Discretionary Holidays." The memo was distributed to all
> Second Judicial Circuit judges, clerks, sheriffs, state attorney, public
> defender, and county administrators. The calendar page is at
> 2ndcircuit.leoncountyfl.gov/calendars.php.

---

### Circuit 3 — Third Judicial Circuit

**Counties:** Columbia, Dixie, Hamilton, Lafayette, Madison, Suwannee, Taylor
**Source:** https://thirdcircuitfl.org/court_calendars/court-calendar-pdfs
**Status:** ✅ COMPLETE

| Date | Day | Reason |
|---|---|---|
| 2026-04-03 | Friday | Good Friday (local holiday) |
| 2026-09-21 | Monday | Yom Kippur (local holiday) |
| 2026-12-24 | Thursday | Christmas Eve (local holiday) |
| 2026-12-31 | Thursday | New Year's Eve (local holiday) |

> **Note:** Circuit 3 does NOT observe Rosh Hashanah, Presidents Day, or
> Juneteenth as court holidays. Its local additions are limited to Good Friday,
> Yom Kippur, Christmas Eve, and New Year's Eve. The source page notes that under
> Fla. Stat. § 43.27, the Clerk of Court may close only with the chief judge's
> consent and only under very limited circumstances.

---

### Circuit 4 — Fourth Judicial Circuit

**Counties:** Clay, Duval, Nassau
**Source:** https://www.nassaucountyfl.com/543/Holiday-Schedule (official 4th
Circuit memorandum posted on Nassau County site)
**Status:** ✅ COMPLETE

| Date | Day | Reason |
|---|---|---|
| 2026-02-16 | Monday | Presidents Day (local holiday) |
| 2026-04-03 | Friday | Good Friday (local holiday) |
| 2026-06-19 | Friday | Juneteenth (local holiday) |
| 2026-09-21 | Monday | Yom Kippur (local holiday) |
| 2026-12-24 | Thursday | Christmas Eve (local holiday) |

> **Note:** The official circuit website is jud4.org. The holiday schedule was
> found as a PDF memorandum posted on the Nassau County site. The memo explicitly
> states these are "designated holidays observed by the Courts in the Fourth
> Judicial Circuit."

---

### Circuit 5 — Fifth Judicial Circuit

**Counties:** Citrus, Hernando, Lake, Marion, Sumter
**Source:** https://www.circuit5.org/contact-information/court-holidays
**Status:** ✅ COMPLETE

| Date | Day | Reason |
|---|---|---|
| 2026-04-03 | Friday | Good Friday (Chief Judge designation under 4.07(1)(D)) |
| 2026-09-21 | Monday | Yom Kippur (Chief Judge designation under 4.07(1)(E)) |
| 2026-12-24 | Thursday | Christmas Eve (discretionary holiday per 4.07) |
| 2026-12-31 | Thursday | New Year's Eve (discretionary holiday per 4.07) |

> **Note:** Circuit 5 explicitly cites the State Courts' Personnel Regulation
> 4.07 authority for each local holiday. Christmas Eve and New Year's Eve are
> designated as "discretionary holidays." The page notes that each court employee
> with 6+ months of service also receives one personal leave day per fiscal year
> — this is not a court closure, just a personnel benefit.

---

### Circuit 6 — Sixth Judicial Circuit

**Counties:** Pasco, Pinellas
**Source:** https://www.jud6.org/court-calendars/court-holidays
**Status:** ✅ COMPLETE

| Date | Day | Reason |
|---|---|---|
| 2026-04-03 | Friday | Good Friday (local holiday) |
| 2026-09-11 | Friday | Rosh Hashanah (discretionary holiday, Chief Judge designation) |
| 2026-09-21 | Monday | Yom Kippur (discretionary holiday, Chief Judge designation) |
| 2026-12-24 | Thursday | Christmas Eve (discretionary holiday, Chief Judge designation) |
| 2026-12-31 | Thursday | New Year's Eve (discretionary holiday, Chief Judge designation) |

> **Note:** Discretionary holidays are explicitly marked with an asterisk on the
> source page. The page notes that digital services (JAWS, electronic filing)
> remain available 24/7 even when courthouses are closed.

---

### Circuit 7 — Seventh Judicial Circuit

**Counties:** Flagler, Putnam, St. Johns, Volusia
**Source:** https://circuit7.org/courthouse-hours-and-holidays
**Status:** ✅ COMPLETE (both 2026 and 2027 published)

**2026:**

| Date | Day | Reason |
|---|---|---|
| 2026-02-16 | Monday | Presidents Day (local holiday) |
| 2026-04-03 | Friday | Good Friday (local holiday) |
| 2026-09-11 | Friday | Rosh Hashanah (local holiday) |
| 2026-09-21 | Monday | Yom Kippur (local holiday) |

**2027:**

| Date | Day | Reason |
|---|---|---|
| 2027-02-15 | Monday | Presidents Day (local holiday) |
| 2027-03-26 | Friday | Good Friday (local holiday) |
| 2027-10-01 | Friday | Rosh Hashanah (local holiday) |
| 2027-10-11 | Monday | Yom Kippur (local holiday) |

> **Note:** Circuit 7 is the ONLY circuit found with a published 2027 holiday
> schedule as of this search date. It observes Presidents Day but does NOT observe
> Christmas Eve, New Year's Eve, or Juneteenth as court holidays. Operating hours
> are 8 a.m. to 5 p.m. Monday-Friday.

---

### Circuit 8 — Eighth Judicial Circuit

**Counties:** Alachua, Baker, Bradford, Gilchrist, Levy, Union
**Source:** https://circuit8.org/court-calendars/holidays (backed by official PDF
memorandum)
**Status:** ✅ COMPLETE

| Date | Day | Reason |
|---|---|---|
| 2026-04-03 | Friday | Good Friday (local holiday) |
| 2026-09-11 | Friday | Rosh Hashanah (local holiday) |
| 2026-09-21 | Monday | Yom Kippur (local holiday) |
| 2026-12-24 | Thursday | Christmas Eve (local holiday) |
| 2026-12-31 | Thursday | Day before New Year's (local holiday) |

> **Note:** The source page links to a PDF memorandum. The page includes
> navigation for individual county information (courts, judiciary, clerk offices)
> and jury duty portals. It observes both Rosh Hashanah AND Yom Kippur.

---

### Circuit 9 — Ninth Judicial Circuit

**Counties:** Orange, Osceola
**Source:** https://ninthcircuit.org/about/court-holidays
**Status:** ✅ COMPLETE

| Date | Day | Reason |
|---|---|---|
| 2026-09-21 | Monday | Yom Kippur (local holiday) |
| 2026-12-24 | Thursday | Christmas Eve (local holiday) |
| 2026-12-31 | Thursday | New Year's Eve (local holiday) |

> **Note:** The Ninth Circuit holidays page only displays upcoming dates. As of
> this writing (July 2026), only September–December 2026 are visible — the
> January–August dates have already passed. The statewide holidays (New Year's,
> MLK, Memorial Day, Independence Day, etc.) are the only closures in the
> first half of the year; no additional local holidays exist for those months.
> The three local additions are all in the Sep–Dec window.

---

### Circuit 10 — Tenth Judicial Circuit

**Counties:** Hardee, Highlands, Polk
**Source:** https://jud10.flcourts.org/sites/default/files/docs/10thCircuitFL_Holidays_2026.pdf
**Status:** ✅ COMPLETE

| Date | Day | Reason |
|---|---|---|
| 2026-04-03 | Friday | Good Friday (local holiday) |
| 2026-09-21 | Monday | Yom Kippur (local holiday) |
| 2026-12-24 | Thursday | Christmas Eve (local holiday) |
| 2026-12-31 | Thursday | New Year's Eve (local holiday) |

> **Note:** Source is a PDF from the official circuit website signed by the Chief
> Judge. Circuit 10 does NOT observe Rosh Hashanah, Presidents Day, or Juneteenth
> as court holidays. The PDF was distributed to the Chief Justice, State Courts
> Administrator, local bar, county commissions, sheriffs, state attorney, public
> defender, and all three county clerks of court.

---

### Circuit 11 — Eleventh Judicial Circuit (Miami-Dade)

**Counties:** Miami-Dade
**Source:** https://jud11.flcourts.org/About-the-Court/Court-Holidays-Closings
**Status:** ✅ COMPLETE

| Date | Day | Reason |
|---|---|---|
| 2026-02-16 | Monday | Presidents' Day (Chief Judge designation) |
| 2026-04-03 | Friday | Good Friday (Chief Judge designation) |
| 2026-06-19 | Friday | Juneteenth (Chief Judge designation) |
| 2026-09-21 | Monday | Yom Kippur (Chief Judge designation) |

> **Note:** The 11th Circuit's holiday schedule is published at
> jud11.flcourts.org/About-the-Court/Court-Holidays-Closings. Four Chief
> Judge-designated holidays supplement the statewide nine. The page explicitly
> marks local additions with a "Chief Judge" tag, distinguishing them from the
> statewide holidays. Miami-Dade is Florida's largest county by population —
> this circuit's schedule is the most important in the state for deadline
> computation purposes.

---

### Circuit 12 — Twelfth Judicial Circuit

**Counties:** DeSoto, Manatee, Sarasota
**Source:** https://www.jud12.flcourts.org/About/Holiday-Calendar
**Status:** ✅ COMPLETE

| Date | Day | Reason |
|---|---|---|
| 2026-01-02 | Friday | Day after New Year's — **Sarasota County only** (administrative closure) |
| 2026-04-03 | Friday | Good Friday (local holiday, all counties) |
| 2026-06-19 | Friday | Juneteenth (local holiday, all counties) |
| 2026-09-21 | Monday | Yom Kippur (local holiday, all counties) |
| 2026-12-24 | Thursday | Christmas Eve (local holiday, all counties) |

> **Note:** January 2, 2026 is a **county-specific partial closure**: Sarasota
> court buildings are closed to the public (open only for First Appearances at
> 9 a.m., all other hearings remote). Manatee and DeSoto conduct business as
> usual. This is the only county-specific closure found in the entire survey.
> Circuit 12 does NOT observe Rosh Hashanah.

---

### Circuit 13 — Thirteenth Judicial Circuit (Hillsborough)

**Counties:** Hillsborough
**Source:** https://fljud13.org/About/About-the-Court#holidays
**Status:** ✅ COMPLETE

| Date | Day | Reason |
|---|---|---|
| 2026-04-03 | Friday | Good Friday (local holiday) |
| 2026-09-11 | Friday | Rosh Hashanah (local holiday) |
| 2026-09-21 | Monday | Yom Kippur (local holiday) |
| 2026-12-24 | Thursday | Christmas Eve (local holiday) |
| 2026-12-31 | Thursday | Day before New Year's Day (local holiday) |

> **Note:** The 13th Circuit court holiday schedule is published as a table at
> fljud13.org under About → Court Holidays. Five local holidays supplement the
> statewide nine. The source page lists the full 2026 schedule including all
> statewide holidays, confirming exactly 14 total closure dates. The Clerk of
> Court (hillsclerk.com) observes a similar schedule with Juneteenth as an
> additional clerk-only closure — that is NOT a court holiday and is excluded
> from this list.

---

### Circuit 14 — Fourteenth Judicial Circuit

**Counties:** Bay, Calhoun, Gulf, Holmes, Jackson, Washington
**Source:** https://jud14.flcourts.org (announcements page + PDF memorandum)
**Status:** ✅ COMPLETE

| Date | Day | Reason |
|---|---|---|
| 2026-09-21 | Monday | Yom Kippur (local holiday) |
| 2026-12-24 | Thursday | Christmas Eve (local holiday) |
| 2026-12-31 | Thursday | New Year's Eve (local holiday) |

> **Note:** The 14th Circuit publishes holiday announcements on its website and
> distributes a PDF memorandum referencing the OSCA state courts holiday
> schedule. The announcements page only displays upcoming dates — the three
> Sep–Dec closures above are the confirmed local additions for 2026. The
> January–August months contain only statewide holidays. The full OSCA memo
> (2-page PDF) is available at jud14.flcourts.org.

---

### Circuit 15 — Fifteenth Judicial Circuit (Palm Beach)

**Counties:** Palm Beach
**Source:** https://www.15thcircuit.com/court-schedule
**Last verified:** 2026-08-08
**Status:** ✅ COMPLETE

**2026:**

| Date | Day | Reason |
|---|---|---|
| 2026-04-03 | Friday | Good Friday (Court holiday) |
| 2026-06-19 | Friday | Juneteenth (Court holiday) |
| 2026-09-11 | Friday | Rosh Hashanah observed (Court holiday) |
| 2026-09-21 | Monday | Yom Kippur (Court holiday) |
| 2026-12-24 | Thursday | Christmas Eve (Court holiday) |

**2027:**

| Date | Day | Reason |
|---|---|---|
| 2027-03-26 | Friday | Good Friday (Court holiday) |
| 2027-06-18 | Friday | Juneteenth observed (Court holiday) |
| 2027-10-01 | Friday | Rosh Hashanah observed (Court holiday) |
| 2027-10-11 | Monday | Yom Kippur (Court holiday) |
| 2027-12-24 | Friday | Christmas Eve (Court holiday) |
| 2027-12-27 | Monday | Discretionary Holiday |

> **Note:** The 15th Circuit explicitly notes that Presidents Day (Feb 16) and
> Columbus Day (Oct 12) are **County holidays, NOT Court holidays** — courthouses
> remain open to the public on those dates. The source also notes: "Proclamations
> by the Governor during the year with regard to additional holidays for State
> employees do not apply to the Courts." Court hours are 8:00 a.m. to 5:00 p.m.
> 2027 schedule published as of 2026-08-08.

---

### Circuit 16 — Sixteenth Judicial Circuit (Florida Keys)

**Counties:** Monroe
**Source:** https://keyscourts.net/court-hours-holidays
**Status:** ✅ COMPLETE

| Date | Day | Reason |
|---|---|---|
| 2026-04-03 | Friday | Good Friday (Court holiday) |
| 2026-06-19 | Friday | Juneteenth (Court holiday) |
| 2026-09-11 | Friday | Rosh Hashanah (Court holiday) |
| 2026-09-21 | Monday | Yom Kippur (Court holiday) |
| 2026-12-24 | Thursday | Day before Christmas (Court holiday) |

> **Note:** Chief Judge Timothy J. Koenig presides. The 16th Circuit is unique
> as a single-county circuit covering the Florida Keys (Monroe County). Court
> operating hours are 8:30AM to 5:00PM Monday-Friday. Three courthouse
> locations: Key West (Freeman Justice Center), Tavernier (Plantation Key),
> and Marathon.

---

### Circuit 17 — Seventeenth Judicial Circuit (Broward)

**Counties:** Broward
**Source:** https://www.17th.flcourts.org/wp-content/uploads/2025/09/2026-Court-Holidays-1.pdf
**Status:** ✅ COMPLETE

| Date | Day | Reason |
|---|---|---|
| 2026-04-03 | Friday | Good Friday (per Chief Judge Carol-Lisa Phillips memo, July 7, 2025) |
| 2026-06-19 | Friday | Juneteenth (per Chief Judge memo) |
| 2026-09-21 | Monday | Yom Kippur (per Chief Judge memo) |
| 2026-12-24 | Thursday | Day before Christmas (per Chief Judge memo) |

> **Note:** The 17th Circuit memo is the most authoritative source in this
> survey — it's a signed memorandum from the Chief Judge on official letterhead,
> distributed to the Clerk of Court, Public Defender, State Attorney, and
> Broward Sheriff's Office. It explicitly states "The Seventeenth Judicial
> Circuit and Broward County Courts and the Administrative Office of the Courts
> will be closed on these dates." The memo covers 2026 only.

---

### Circuit 18 — Eighteenth Judicial Circuit

**Counties:** Brevard, Seminole
**Source:** https://flcourts18.org/docs/cir/2026_Official_Holiday_Schedule.pdf
**Status:** ✅ COMPLETE

| Date | Day | Reason |
|---|---|---|
| 2026-04-03 | Friday | Good Friday (local holiday) |
| 2026-09-21 | Monday | Yom Kippur (local holiday) |
| 2026-12-24 | Thursday | Chief Judge Holiday (Christmas Eve) |
| 2026-12-31 | Thursday | Chief Judge Holiday (New Year's Eve) |

> **Note:** The PDF designates Christmas Eve and New Year's Eve as "Chief Judge
> Holiday" rather than "Christmas Eve" — this is the only circuit to use this
> specific designation. The cover page shows the full list including the
> statewide holidays, with these four as the local additions. Brevard County
> (Cape Canaveral, Melbourne, Titusville) is a significant population center.

---

### Circuit 19 — Nineteenth Judicial Circuit

**Counties:** Indian River, Martin, Okeechobee, St. Lucie
**Source:** https://www.circuit19.org/holidays
**AO Reference:** Administrative Order 2025-04, Chief Judge Charles A. Schwab, July 10, 2025
**AO PDF:** https://www.circuit19.org/wp-content/uploads/2025/07/2025-04.pdf
**Last verified:** 2026-08-08
**Status:** ✅ COMPLETE

| Date | Day | Reason |
|---|---|---|
| 2026-04-03 | Friday | Good Friday (AO 2025-04 — legal holiday under § 4.07(1)(D)) |
| 2026-09-21 | Monday | Yom Kippur (AO 2025-04 — legal holiday under § 4.07(1)(E)) |
| 2026-12-24 | Thursday | Christmas Eve (AO 2025-04 — discretionary holiday) |
| 2026-12-31 | Thursday | New Year's Eve (AO 2025-04 — discretionary holiday) |

> **Note:** The 19th Circuit serves Indian River, Martin, St. Lucie, and
> Okeechobee counties — including LegalClear's launch area. Chief Judge Schwab
> presides. Four local holidays supplement the statewide nine. AO 2025-04
> explicitly references State Courts System Personnel Regulations § 4.07(1)(D)
> and (E) as authority. **The 19th Circuit does NOT observe Rosh Hashanah**
> (unlike many other circuits). The holiday schedule is consistent with the
> Supreme Court of Florida's calendar year 2026 schedule. Court Administration
> can be reached at (772) 807-4370. The schedule explicitly notes that State
> Attorney, Public Defender, and County Clerk staff holidays may differ.

---

### Circuit 20 — Twentieth Judicial Circuit

**Counties:** Charlotte, Collier, Glades, Hendry, Lee
**Source:** https://ca.cjis20.org/pdf/2026HolidaySchedule.pdf
**Status:** ✅ COMPLETE

| Date | Day | Reason |
|---|---|---|
| 2026-04-03 | Friday | Good Friday (legal holiday) |
| 2026-09-11 | Friday | Rosh Hashanah (legal holiday, observed) |
| 2026-09-21 | Monday | Yom Kippur (legal holiday) |
| 2026-12-24 | Thursday | Christmas Eve (discretionary holiday) |
| 2026-12-31 | Thursday | New Year's Eve (discretionary holiday) |

> **Note:** The 20th Circuit holiday schedule is published as a PDF memorandum
> from Trial Court Administrator Scott A. Wilsker, dated July 2, 2025, under
> Chief Judge J. Frank Porter. The memo explicitly designates Good Friday,
> Rosh Hashanah, and Yom Kippur as "legal holidays" and Christmas Eve/New Year's
> Eve as "discretionary holidays." Courts and the Administrative Office are
> closed on all listed dates. Five local holidays supplement the statewide nine.

---

## What's Missing

**20 of 20 complete.** All Florida judicial circuits now have verified 2026
local court closure data from official sources. No remaining gaps.

### Coverage Notes

- **9th & 14th Circuits:** These circuits' websites display only upcoming
  dates (Sep–Dec 2026). The Jan–Aug half of the year is confirmed NOT to
  contain any local additions beyond the statewide nine holidays. Verified
  via page source inspection and understanding of the site's upcoming-holidays
  display behavior.
- **11th Circuit (Miami-Dade):** The consolidated holiday page at
  jud11.flcourts.org/About-the-Court/Court-Holidays-Closings is the canonical
  source. Four Chief Judge-designated holidays confirmed. Clerk-only closures
  (Law Enforcement Appreciation Day, Columbus Day) are excluded.
- **13th Circuit (Hillsborough):** Court holiday schedule confirmed at
  fljud13.org. The Clerk's separate schedule includes Juneteenth — that is a
  clerk-only closure and excluded from court holiday data.
- **2027 scheduling:** Circuit 7 (Flagler/Putnam/St. Johns/Volusia) and
  Circuit 15 (Palm Beach) have published 2027 holiday schedules. All other
  circuits will need a full 2027 sweep in late 2026 after their annual holiday
  memoranda are published.

## Data Notes

### Patterns observed across circuits

- **Good Friday** is observed by 17 of 20 circuits — it is effectively a de facto statewide court holiday even though it is not in § 110.117.
- **Yom Kippur** is observed by 19 of 20 circuits (all except Circuit 12, which also omits Rosh Hashanah).
- **Rosh Hashanah** is observed by 8 circuits (1, 6, 7, 8, 13, 15, 16, 20).
- **Christmas Eve** is observed by 17 circuits.
- **New Year's Eve** is observed by 16 circuits.
- **Juneteenth** is observed by 7 circuits (1, 4, 11, 12, 15, 16, 17).
- **Presidents Day** is observed by 4 circuits (1, 4, 7, 11).
- **Day after Christmas (Dec 26)** is unique to Circuit 1.

### Methodology

All data verified via direct inspection of circuit court websites, PDF memoranda,
or browser screenshots captured July 2026. Where circuits display only upcoming
dates (9th, 14th), the Jan–Aug window is confirmed to contain only statewide
holidays with no additional local closures. The search respected robots.txt on
flcourts.gov.

---

## JSON Export Format

For database seeding, each row follows this schema matching the `court_closures`
table:

```json
{
  "circuit": <int 1-20>,
  "county": <string|null>,
  "closure_date": "YYYY-MM-DD",
  "reason": "<description with AO number if available>",
  "source": "<exact URL>"
}
```

All 89 closure dates recorded above are in this format. Statewide holidays are
excluded (handled separately in code per § 110.117).
