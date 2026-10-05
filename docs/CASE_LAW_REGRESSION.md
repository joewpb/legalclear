# Case-Law Regression Suite (Phase 7)

Permanent acceptance gates for the case-law search + SYG analysis. Every
item maps to a failure found in the Sep 29 blind test (A1-A12) or the
Oct 2 rebuild. Run the whole suite:

    cd backend
    .venv/bin/python -m pytest tests/test_case_law_search_p3.py \
        tests/test_syg_synthesis.py -q
    python3 ../scripts/case_law_acceptance_battery.py [base_url] --reps 2

## Gate map

| Gate | Blind-test failure it locks out | Where enforced |
|---|---|---|
| A1 | Example chips returned 0/6 | battery `CHIPS` group (expect >0) |
| A2 | "Bush v. Gore" dead | battery `CASENAME` (SCOTUS: honest 0 documented) |
| A3 | "Dennis v. State" dead | battery `CASENAME` + unit test name-query path |
| A4 | "self defense" vs "self-defense" split | battery TOKEN group |
| A5 | Same famous cases for every report | SYG tests: two documents differ |
| A6 | Junk "Unknown case name" rows | battery junk counter == 0 |
| A7 | Malformed JSON (`\f` control chars) | battery strict_json gate |
| A8 | `total_results` lies (10 vs 2 shipped) | battery total-vs-shipped per query |
| A9 | Corrupted dates (0013-04-10) | battery bad_dates == 0 |
| A10 | Sentinel citations shipped | battery sentinels == 0 |
| A11 | Nondeterministic same-call flips | battery stability signature |
| A12 | External links on result cards | frontend review (fix/p4-search-cards) |

## Known honest zeros

- "Bush v. Gore", "Terry v. Ohio" are SCOTUS cases — not in the FL corpus;
  a 0 is correct. Do not "fix" by widening the corpus silently.
- Pre-1870 territorial cases have no date in the source data.
- Pre-1930s Florida Reports citations are deliberately not regexed
  (false-positive risk exceeds value).

## Latency note

Full-speed token searches require the pg_trgm GIN indexes
(`idx_opinions_summary_plain_trgm`, `idx_opinions_case_name_trgm`). Without
them the battery shows timeout-driven 0s and flaky queries — the index DDL
is the gate that separates "data fixed" from "search fixed".
