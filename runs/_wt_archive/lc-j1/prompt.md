# Dispatch J1 — citation resolution guard (build BEFORE any citation ships)

Repo: joewpb/legalclear. Worktree: ~/code/lc-j1 (branch fix/j1-citation-resolver, cut from origin/main).

## Doctrine

Before any citation reaches a user it must resolve to a row in the owned
`statutes` or `court_rules` tables. Unresolvable citations are stripped or
suppressed — never displayed, never passed through. Coverage gaps degrade to
silence, not fabrication. Same doctrine as the URL filter: deterministic code
guarantees what the prompt cannot.

## Task

1. Create `backend/src/core/citation_resolver.py`:
   - `CitationResolution` dataclass: `citation` (canonical form, e.g.
     "Fla. Stat. § 34.01"), `source_url`, `section` (or rule_number), `title`.
   - `normalize_citation(raw: str) -> str` — collapse whitespace, unify
     section-sign variants ("§" / "s." / "Sec."), uppercase "FLA. STAT." and
     rule-set abbreviations deterministically. Keep it conservative: normalize
     formatting only, never fuzzy-match substance.
   - `resolve_citation(citation: str, owned: Mapping[str, CitationResolution]) -> CitationResolution | None`
     — pure function, exact match on normalized form against a preloaded map.
   - `resolve_citations(citations: Iterable[str], owned: Mapping[str, CitationResolution]) -> list[CitationResolution]`
     — returns only the resolvable ones, in input order, deduped.
   - `load_owned_citations(db) -> dict[str, CitationResolution]` — queries the
     Supabase `statutes` and `court_rules` tables (citation, section,
     rule_number, title, source_url) via the existing DatabaseManager pattern
     used in `backend/src/memory/db.py`; builds the map keyed by normalized
     citation. Read how other modules query (e.g. how deadline.py or
     case_law.py talk to db) and follow it. Must handle a failed lookup
     gracefully (empty map → everything suppressed, never an exception to the
     caller).
2. Tests — `backend/tests/test_citation_resolver.py`, pure Python with a small
   fixture map (3 owned citations incl. "Fla. Stat. § 34.01"): 
   - a valid ch. 34 cite resolves to its fixture row;
   - a Rules 7.x cite ("Fla. Sm. Cl. R. 7.050") is suppressed (not owned);
   - a fabricated cite ("Fla. Stat. § 34.999") is suppressed;
   - normalization variants ("fla. stat.   s.34.01", "§ 34.01") resolve;
   - empty/failed lookup → suppression, no exception.
3. Checker rule — `scripts/verify_educational.py`: add check 5 (renumber if the
   script's report loop assumes 1..4 — update the loop and docstring):
   "citation resolution guard present". Static assertions:
   - `backend/src/core/citation_resolver.py` exists and defines
     `resolve_citation` and `load_owned_citations`;
   - `backend/tests/test_citation_resolver.py` exists and covers the three
     required cases (grep for 34.01, 7.050, 34.999);
   - any file under backend/src/ that emits citation fields (grep: a prompt
     mentioning "citation" AND a schema field named citation) must import
     citation_resolver — today that set is empty, so no violation; the rule
     becomes live when the small-claims pilot lands.
4. Do NOT wire the small-claims agent yet (next dispatch does).

## Verify

Suite with CI-scope ignores (baseline 374 passed, 1 skipped). Zero new failures.
`python3 scripts/verify_educational.py` must list 5 checks and show check 5
passing (0 violations in it).

## Hard rules

No git push/merge/checkout/reset/clean/stash/add/commit/branch. No network
(curl/WebFetch forbidden) — load_owned_citations must not be CALLED against
prod in tests; tests use fixtures only. No railway/supabase CLI. Final answer:
file:line of each new function, test results, checker delta, turn count.
