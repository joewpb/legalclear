"""Opinion retrieval service — Stage 1 (no SSE wiring).

Three responsibilities:
  1. derive_situation_tags(v2_result): deterministically map a Police
     Report V2 analysis result to legal_opinions situation_tags.
     No LLM. No baseline tag — [] when nothing matches (precision over
     recall).
  2. _derive_fact_terms(v2_result): deterministically extract search terms
     from the LLM's discrepancy / missing-field / charge text (curated
     legal-phrase vocabulary + signal-gated bigrams). No LLM call.
  3. get_relevant_opinions(tags, analysis_result): fetch opinions from
     Supabase via DatabaseManager. Relevance-ranked: matched search terms
     first, tag overlap second, cite_count last. Junk rows (empty
     case_name) are dropped.

Database access goes through DatabaseManager (decision D) — the app's
existing abstraction, which degrades gracefully (client is None) when
SUPABASE_URL / SUPABASE_SERVICE_KEY are absent. No module-level
supabase client.
"""

from __future__ import annotations

import logging
import re

from src.core.config import settings
from src.memory.db import DatabaseManager

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# DB handle — module-level DatabaseManager, matching the idiom used by the
# routers (deadline/reminders/triage/law/forms). DatabaseManager.__init__
# degrades gracefully (client is None) when SUPABASE_URL / SERVICE_KEY are
# absent, so the guard below handles degraded mode without a lazy factory.
# ---------------------------------------------------------------------------

db = DatabaseManager()


# Columns returned to the API. Verified against legal_opinions schema
# (recon Step 2, 2026-07). All nine columns confirmed present.
_OPINION_COLUMNS = (
    "case_name, citation, court, date_filed, cite_count, "
    "outcome, summary_plain, summary_legal, attorney_prompt"
)

# Scrub chars that break PostgREST or/ilike filter values, including the
# LIKE wildcards % and _ (a literal % or _ inside a term would silently
# broaden the match into a wildcard).
_TERM_SCRUB = re.compile(r"[,():*%_\\]")


def _tag_to_search_terms(tags: set[str]) -> list[str]:
    """Convert snake_case situation tags to human-readable search terms.

    ``self_defense`` → ``self defense``, ``fourth_amendment`` →
    ``fourth amendment``, ``dissolution_of_marriage`` →
    ``dissolution of marriage``.

    Returns deduped list; empty for an empty input set.
    """
    seen: set[str] = set()
    out: list[str] = []
    for tag in sorted(tags):
        term = tag.replace("_", " ").strip()
        if term and term not in seen:
            seen.add(term)
            out.append(term)
    return out


def _sanitize_term(term: str) -> str:
    return _TERM_SCRUB.sub(" ", term).strip()


def _build_ilike_filter(terms: list[str]) -> str:
    """PostgREST ``or=`` filter across ``summary_plain`` for free-text terms.

    Returns "" when no valid terms remain after scrubbing.
    """
    parts = []
    for t in terms:
        clean = _sanitize_term(t)
        if not clean:
            continue
        parts.append(f"summary_plain.ilike.%{clean}%")
    return ",".join(parts)


# ---------------------------------------------------------------------------
# Fact-term extraction — deterministic, no LLM. The Police Report V2 result
# already contains rich discrepancy descriptions ("coercive consent framing",
# "language barrier", "anonymous tip", "Terry stop") that the tag mapper
# discards. These terms carry the facts into the ILIKE search so retrieval
# ranks on relevance instead of global citation popularity.
#
# House style: precision over recall. Curated legal phrases first, then a
# small set of strong unigrams, then description bigrams gated on a legal
# signal wordlist (a bigram like "the officer" matches every police-case
# summary and would rank nothing; it is rejected by the stopword gate).
# ---------------------------------------------------------------------------

_FACT_PHRASES: tuple[str, ...] = (
    # 4A — consent / warrants / stops
    "consent to search", "consented to search", "consented to a search",
    "voluntary consent", "search warrant", "warrantless search",
    "warrantless entry", "warrantless arrest", "without a warrant",
    "probable cause", "reasonable suspicion", "probable cause affidavit",
    "terry stop", "stop and frisk", "investigatory stop", "traffic stop",
    "anonymous tip", "anonymous informant", "confidential informant",
    "exigent circumstances", "plain view", "open fields",
    "knock and announce", "curtilage", "inventory search", "pat down",
    "dog sniff", "canine", "drug dog", "k-9",
    "field sobriety", "breathalyzer", "breath test", "blood test",
    "implied consent", "sobriety test", "search incident to arrest",
    # 5A / 6A — Miranda & counsel
    "miranda warning", "miranda warnings", "miranda rights",
    "custodial interrogation", "waiver of rights", "waived his rights",
    "waived her rights", "right to counsel", "right to remain silent",
    "invocation of rights", "invoked his right", "coerced confession",
    "involuntary confession", "right to an attorney",
    # language access
    "language barrier", "limited english", "english proficiency",
    "spanish-speaking", "non-english",
    # due process / identification / misc
    "due process", "chain of custody", "false arrest", "unlawful arrest",
    "excessive force", "pepper spray", "showup", "show-up", "lineup",
    "photo array", "eyewitness identification", "exclusionary rule",
)

_FACT_UNIGRAMS: tuple[str, ...] = (
    "interpreter", "miranda", "warrantless", "taser", "tasered",
    "breathalyzer", "curtilage", "frisked", "sobriety", "consent",
    "coerced", "coercive", "confession", "handcuffed",
)

# Words that disqualify a bigram outright — pairs containing them match
# everything ("the officer", "his vehicle") and carry no signal.
_FACT_STOPWORDS: frozenset[str] = frozenset(
    "the a an of and or to in on for with was were be been is are at by from "
    "as it its that this these those who whom whose officer officers police "
    "report reports subject defendant suspect victim witness statement "
    "incident vehicle car during after before while when about into over "
    "under between because also not no yes his her their they them he she "
    "then there would could should did does do had has have said according "
    "described".split()
)

# Words that QUALIFY a bigram — at least one must be present for the bigram
# to be kept.
_FACT_SIGNAL_WORDS: frozenset[str] = frozenset(
    "consent search warrant stop stops stopped seizure seized probable "
    "suspicion reasonable miranda rights waiver waive waived interpreter "
    "language english custodial interrogation custody terry frisk pat "
    "sobriety breath blood refusal detention detained arrest force taser "
    "tasered pepper handcuff counsel attorney silent confession coerced "
    "coercive lineup showup evidence statement interview tip informant "
    "anonymous k9 canine dog sniff plain curtilage exigent inventory "
    "bilingual translation translated warning advisement fingerprint "
    "suppression suppress".split()
)

_MAX_FACT_TERMS = 40
_MAX_FACT_BIGRAMS = 20
_MAX_TERM_LEN = 40
_MAX_ILIKE_TERMS = 40

# Pool anchor terms for the fact-mode ILIKE query — ordered by
# distinctiveness (most report-specific first), restricted to terms that
# CAN complete within the Supabase statement timeout (~8.3s; full 425K-row
# single-ILIKE scan measured ~8.1s, but timing is load-variable — a rare
# anchor is a coin flip, so the caller retries with the next anchor and
# dense terms at the tail are the reliable fallback). Single-anchor by
# design: an OR of two rare terms roughly doubles the scan cost (verified
# 57014). Terms whose full match set fits under the LIMIT-200 window give
# the pool EXACT coverage and ranking; dense terms give a fast sampled
# window.
_POOL_ANCHOR_PRIORITY: tuple[str, ...] = (
    "language barrier",         # 6 rows, exact set (most distinctive)
    "interpreter",              # 94 rows, exact set
    "anonymous tip",            # 41 rows, exact set
    "custodial interrogation",  # 69 rows, exact set
    "terry stop",               # 32 rows, exact set
    "miranda rights",           # 148 rows, exact set
    "miranda warning",          # 102 rows, exact set
    "probable cause",           # dense + fast — sampled fallback
    "miranda",                  # dense + fast — sampled fallback
    "consent",                  # dense + fast — sampled fallback
)


def _pool_anchor_terms(
    fact_terms: list[str], max_anchors: int = 3,
) -> list[str]:
    """Pick anchor candidates from `fact_terms` in priority order.

    The caller tries them in order and stops at the first query that
    completes (rare anchors can hit the statement timeout under load).
    'probable cause'/'miranda'/'consent' sit at the tail, so they are the
    natural fast fallback for reports whose fact terms contain nothing
    more specific. [] only when there is nothing fast to query with — the
    caller then skips the pool and relies on the tag-overlap path."""
    anchors = [t for t in _POOL_ANCHOR_PRIORITY if t in fact_terms]
    return anchors[:max_anchors]


def _derive_fact_terms(v2_result: dict) -> list[str]:
    """Deterministically extract fact search terms from a V2 analysis result.

    Sources: discrepancies[].description / ask_attorney,
    missing_fields[].field_name / why_important, charges_explained[].
    charge / plain_english — text the LLM already emitted; no new LLM call.

    Returns a deduped, lowercase, order-stable list capped at
    _MAX_FACT_TERMS (phrases and unigrams first, bigrams last); [] for
    empty or non-dict input.
    """
    if not isinstance(v2_result, dict):
        return []
    desc_blob = " ".join(
        f"{d.get('description', '')} {d.get('ask_attorney', '')}"
        for d in v2_result.get("discrepancies") or []
        if isinstance(d, dict)
    ) + " " + " ".join(
        f"{d.get('field_name', '')} {d.get('why_important', '')}"
        for d in v2_result.get("missing_fields") or []
        if isinstance(d, dict)
    )
    charge_blob = " ".join(
        f"{c.get('charge', '')} {c.get('plain_english', '')}"
        for c in v2_result.get("charges_explained") or []
        if isinstance(c, dict)
    )
    blob = f"{desc_blob} {charge_blob}".lower()
    if not blob.strip():
        return []

    terms: list[str] = []
    seen: set[str] = set()

    def add(term: str) -> bool:
        term = term.strip()
        if not term or len(term) > _MAX_TERM_LEN or term in seen:
            return False
        seen.add(term)
        terms.append(term)
        return True

    for phrase in _FACT_PHRASES:
        if phrase in blob:
            add(phrase)
    for word in _FACT_UNIGRAMS:
        if word in blob:
            add(word)

    # Bigrams from the discrepancy / missing-field text only (not charges):
    # keep a bigram only when it contains a legal signal word and no stopword.
    words = re.findall(r"[a-z0-9'\-]+", desc_blob.lower())
    bigram_count = 0
    for left, right in zip(words, words[1:]):
        if bigram_count >= _MAX_FACT_BIGRAMS:
            break
        if left in _FACT_STOPWORDS or right in _FACT_STOPWORDS:
            continue
        if left in _FACT_SIGNAL_WORDS or right in _FACT_SIGNAL_WORDS:
            if add(f"{left} {right}"):
                bigram_count += 1
    return terms[:_MAX_FACT_TERMS]


def _merge_search_terms(
    fact_terms: list[str], tag_terms: list[str],
) -> list[str]:
    """Merged, case-insensitively deduped search terms — fact terms first so
    the ILIKE cap favors them over tag names."""
    merged: list[str] = []
    seen: set[str] = set()
    for term in (*fact_terms, *tag_terms):
        key = term.casefold()
        if not key or key in seen or len(term) > _MAX_TERM_LEN:
            continue
        seen.add(key)
        merged.append(term)
    return merged


def _substantive_search_terms(
    tag_set: set[str], fact_terms: list[str],
) -> set[str]:
    """Lowercase terms that count as a relevance match.

    All fact terms plus the tag-name terms of non-charge-class tags.
    Charge-class names ('misdemeanor', 'felony', ...) are generic — matching
    one of them alone is not relevance, so they never count.
    """
    substantive = {t.casefold() for t in fact_terms}
    for tag in tag_set:
        if tag in _CHARGE_CLASS_TAGS:
            continue
        term = tag.replace("_", " ").strip().casefold()
        if term:
            substantive.add(term)
    return substantive


def _count_matched_terms(summary: str | None, terms: set[str]) -> int:
    """Count distinct lowercase search terms appearing in `summary`."""
    if not summary:
        return 0
    text = summary.casefold()
    return sum(1 for term in terms if term in text)


def _has_case_name(row: dict) -> bool:
    """True when the row carries a non-empty case_name.

    Corpus junk rows (page-header text like 'NOT FINAL UNTIL TIME EXPIRES
    ...') have empty case_name and must never surface.
    """
    name = row.get("case_name")
    return bool(isinstance(name, str) and name.strip())


# ── Charge-context exclusion (Joe ruling 2026-08-27) ────────────────────────
# Logged rule: case-law results never present a charge class more severe than
# the report's own charges. Operational form (hard, deterministic, testable):
# when the report carries no homicide charge, homicide cases are EXCLUDED.
# Joe's explicit example: Caldwell (a burglary-felony case) stays for a
# misdemeanor-report user; McWatters (murder narrative) goes. Non-homicide
# charge classes are therefore NOT filtered — only the homicide rung is hard.
# Where exclusion thins results below the limit, they stay thin — no backfill
# from excluded rows (gaps degrade to silence). Deterministic, text-based,
# no LLM.


def _report_has_homicide_charge(analysis_result: dict | None) -> bool:
    """True when the report's own charge text carries a homicide indicator."""
    if not isinstance(analysis_result, dict):
        return False
    blob = " ".join(
        f"{c.get('charge', '')} {c.get('plain_english', '')}"
        for c in analysis_result.get("charges_explained") or []
        if isinstance(c, dict)
    )
    return bool(blob and _CHARGE_HOMICIDE.search(blob))


def _row_is_homicide(row: dict) -> bool:
    """True when the row's own text marks it a homicide case.

    Precision over recall: only explicit indicators classify; rows whose
    text reveals nothing are never excluded.
    """
    text = " ".join(
        str(row.get(k) or "") for k in ("summary_plain", "summary_legal", "outcome")
    )
    return bool(text and _CHARGE_HOMICIDE.search(text))


def _filter_by_charge_context(
    rows: list[dict], analysis_result: dict | None,
) -> list[dict]:
    """Drop homicide rows whenever the report has no homicide charge.

    Report with a homicide charge → no exclusion (the user's own charge
    class is on the table). No analysis_result (legacy callers) → rows
    returned unchanged. Unclassified rows pass.
    """
    if not isinstance(analysis_result, dict):
        return rows
    if _report_has_homicide_charge(analysis_result):
        return rows
    out: list[dict] = []
    for row in rows:
        if _row_is_homicide(row):
            logger.info(
                "charge-context exclusion: dropping %r (homicide case vs "
                "report without a homicide charge)",
                row.get("case_name"),
            )
            continue
        out.append(row)
    return out


# A successful anchor query that returns fewer real rows than this does not
# consume the anchor budget — the loop advances to the next anchor
# (Joe ruling 2026-08-27: junk-only / below-threshold results must not stop
# the search; pools from multiple anchors are unioned, deduped by cluster_id).
_ANCHOR_MIN_USABLE_ROWS = 2


def _run_fact_anchor_queries(fact_terms: list[str]) -> list[dict]:
    """Run fact-mode ILIKE anchor queries until one yields real rows.

    Advances on query failure AND on junk-only / below-threshold results.
    Returns the union of usable rows from all anchors tried (deduped by
    cluster_id); [] when every anchor fails or yields only junk.
    """
    pool: list[dict] = []
    seen: set[str] = set()
    for anchor in _pool_anchor_terms(fact_terms):
        try:
            result = (
                db.client.table("legal_opinions")
                .select(_OPINION_COLUMNS + ", cluster_id")
                .or_(_build_ilike_filter([anchor]))
                .eq("quality_flagged", False)
                .limit(200)
                .execute()
            )
        except Exception:
            logger.warning("ILIKE anchor %r failed; trying next anchor", anchor)
            continue
        usable: list[dict] = []
        for row in result.data or []:
            if not _has_case_name(row):
                continue
            cid = row.get("cluster_id")
            if cid is not None:
                if cid in seen:
                    continue
                seen.add(cid)
            usable.append(row)
        pool.extend(usable)
        if len(usable) >= _ANCHOR_MIN_USABLE_ROWS:
            break
        logger.info(
            "ILIKE anchor %r: %d usable row(s) < %d; trying next anchor",
            anchor, len(usable), _ANCHOR_MIN_USABLE_ROWS,
        )
    return pool


def get_relevant_opinions(
    situation_tags: list[str],
    limit: int = 3,
    analysis_result: dict | None = None,
) -> list[dict]:
    """Return up to `limit` opinions relevant to `situation_tags`.

    Relevance ranking (deterministic, no LLM):
      - `analysis_result` (the parsed Police Report V2 JSON) is optional.
        When provided, fact terms are extracted from the LLM's discrepancy /
        missing-field / charge text — the facts the LLM already emitted
        finally reach the retrieval query (2026-08 relevance fix). The ILIKE
        candidate query is anchored on up to 2 COMMON fact terms (rare-term
        ORs exceed the DB statement timeout; wide terms would collapse the
        candidate window back to famous cases), and candidates are ranked
        in Python by distinct matched terms: (matched DESC, tag-overlap
        DESC, cite_count DESC). ILIKE rows must match >=1 substantive term
        and rows matching >=2 terms are preferred.
      - Without `analysis_result` (legacy callers, e.g. Criminal Procedure),
        the tag-overlap path stays primary — behavior unchanged apart from
        junk filtering: (overlap DESC, matched DESC, cite_count DESC).

    Paths: tag-overlap query first (precision set, junk rows dropped), then
    the ILIKE fallback across summary_plain (candidate set ~200, relevance-
    ranked in Python — PostgREST cannot rank term overlap). When fact terms
    exist the ILIKE always runs, so facts reach the corpus even if tagged
    opinions already filled the limit. Rows with null/empty case_name are
    dropped everywhere. quality_flagged=False only. Charge-class gate and
    Orin fallback unchanged. Returns [] on empty input, a charge-class-only
    tag set, degraded mode, or query error — retrieval never breaks the
    parent response. Output shape = _OPINION_COLUMNS (unchanged).
    """
    if not situation_tags:
        return []
    # Charge-class-only set -> no legal issue to retrieve case law for.
    # Short-circuit before the DB round-trip. A substantive tag (any tag
    # outside _CHARGE_CLASS_TAGS) must accompany the class label(s).
    tag_set = set(situation_tags)
    if not (tag_set - _CHARGE_CLASS_TAGS):
        logger.info(
            "get_relevant_opinions class-only tags=%r -> [] "
            "(no substantive tag present)",
            sorted(tag_set),
        )
        return []
    if db.client is None:
        return []
    query_tags = tag_set
    tag_terms = _tag_to_search_terms(query_tags)
    fact_terms = (
        _derive_fact_terms(analysis_result)
        if isinstance(analysis_result, dict)
        else []
    )
    fact_mode = bool(fact_terms)
    search_terms = _merge_search_terms(fact_terms, tag_terms)
    substantive_terms = _substantive_search_terms(query_tags, fact_terms)
    if fact_mode:
        # Fact mode: single-anchor ILIKE queries, tried in priority order
        # inside the fallback block (rare-term ORs exceed the Supabase
        # statement timeout — verified 57014). The filter below is only the
        # outer-run gate ("" when there is no anchor at all -> pool skipped,
        # tag-overlap path carries). All fact terms + tag names still count
        # when ranking candidates in Python.
        anchors = _pool_anchor_terms(fact_terms)
        ilike_filter = _build_ilike_filter(anchors[:1])
    else:
        filter_terms = search_terms[:_MAX_ILIKE_TERMS]
        ilike_filter = _build_ilike_filter(filter_terms)
    logger.info(
        "get_relevant_opinions tags=%r fact_terms=%d fact_mode=%s",
        sorted(tag_set), len(fact_terms), fact_mode,
    )

    try:
        rows: list[dict] = []
        tagged_ids: set[str] = set()

        # ── Tag-overlap query (pre-tagged opinions, high precision) ──────
        result = (
            db.client.table("legal_opinions")
            .select(_OPINION_COLUMNS + ", situation_tags, cluster_id")
            .overlaps("situation_tags", situation_tags)
            .eq("quality_flagged", False)
            .limit(500)
            .execute()
        )
        for row in result.data or []:
            if not _has_case_name(row):
                continue  # junk: header-text rows with empty case_name
            opinion_tags = set(row.get("situation_tags") or [])
            row["_overlap"] = len(opinion_tags & query_tags)
            row["_matched"] = _count_matched_terms(
                row.get("summary_plain"), substantive_terms,
            )
            rows.append(row)
        tagged_ids = {r.get("cluster_id") for r in rows if r.get("cluster_id")}

        # ── ILIKE fallback: search ALL summaries ─────────────────────────
        # Runs when the tag-overlap path didn't fill the limit, and ALWAYS
        # when fact terms exist (facts must reach the corpus even when
        # tagged opinions already filled the limit — a famous murder case
        # tagged 5a/6a/4a must not outrank a fact-matched consent case).
        # Fact mode: single-anchor queries, tried in priority order (rare
        # anchors can hit the Supabase statement timeout under load; the
        # dense tail anchors are the reliable fallback).
        if ilike_filter and (len(rows) < limit or fact_mode):
            try:
                if fact_mode:
                    # Anchor loop with junk/below-threshold advancement
                    # (Joe ruling 2026-08-27) — see _run_fact_anchor_queries.
                    ilike_rows = _run_fact_anchor_queries(fact_terms)
                else:
                    # Legacy: keep the historical popularity pre-filter
                    # (tag-name terms are wide, so matching rows are found
                    # quickly in cite order).
                    ilike_result = (
                        db.client.table("legal_opinions")
                        .select(_OPINION_COLUMNS + ", cluster_id")
                        .or_(ilike_filter)
                        .eq("quality_flagged", False)
                        .order("cite_count", desc=True)
                        .limit(200)
                        .execute()
                    )
                    ilike_rows = ilike_result.data or []
                for row in ilike_rows:
                    if not _has_case_name(row):
                        continue  # junk: header-text rows with empty case_name
                    cid = row.get("cluster_id")
                    if cid is not None and cid in tagged_ids:
                        continue  # dedup — already have this one via tags
                    matched = _count_matched_terms(
                        row.get("summary_plain"), substantive_terms,
                    )
                    if fact_mode and matched < 1:
                        # Rows that matched only charge-class terms (e.g.
                        # bare 'misdemeanor') carry no relevance signal.
                        continue
                    row["_overlap"] = 0
                    row["_matched"] = matched
                    rows.append(row)
            except Exception:
                logger.warning(
                    "ILIKE fallback failed; returning tag-only results",
                    exc_info=True,
                )

        if fact_mode:
            # Facts are the primary relevance signal: distinct matched terms
            # first (>=2-match rows preferred), tag overlap as the precision
            # tiebreak, cite_count last.
            rows.sort(
                key=lambda r: (
                    r.get("_matched", 0),
                    r.get("_overlap", 0),
                    r.get("cite_count") or 0,
                ),
                reverse=True,
            )
        else:
            # Legacy: tag-overlap path stays primary (unchanged behavior);
            # text matches only break ties.
            rows.sort(
                key=lambda r: (
                    r.get("_overlap", 0),
                    r.get("_matched", 0),
                    r.get("cite_count") or 0,
                ),
                reverse=True,
            )

        # ── Charge-context exclusion (Joe ruling 2026-08-27) ──────────────
        # Never present a charge class more severe than the report's own
        # charges. Runs AFTER ranking so it can only thin, never reorder;
        # no backfill from excluded rows (gaps degrade to silence).
        rows = _filter_by_charge_context(rows, analysis_result)

        top = rows[:limit]
        # Strip helper keys so the returned dicts match _OPINION_COLUMNS.
        for row in top:
            row.pop("_overlap", None)
            row.pop("_matched", None)
            row.pop("situation_tags", None)
            row.pop("cluster_id", None)

        # ── Orin fallback: kept as last resort ───────────────────────────
        if len(top) < limit:
            try:
                from src.services.orin_opinions import search_orin_opinions

                orin_results = search_orin_opinions(
                    situation_tags, limit=limit - len(top),
                )
                for opinion in orin_results:
                    opinion.pop("_source", None)
                    opinion.pop("_opinion_id", None)
                # The exclusion ladder applies to Orin rows too (best effort:
                # rows without charge text pass through unclassified).
                orin_results = _filter_by_charge_context(
                    orin_results, analysis_result,
                )
                top.extend(orin_results)
            except Exception:
                logger.warning(
                    "Orin opinion search failed, continuing with "
                    "Supabase-only results",
                )

        return top
    except Exception as e:
        logger.error("get_relevant_opinions failed: %s", e)
        return []


def generate_attorney_questions(
    analysis_result: dict,
    opinions: list[dict],
) -> list[dict]:
    """Generate specific questions the user should ask their attorney about each opinion.

    Uses Claude Haiku to connect each opinion's holding to the user's specific
    situation (from the police report analysis). Returns the opinions list
    with enriched attorney_prompt fields.

    On failure, returns opinions unchanged (with generic prompts).
    """
    import json as _json

    key = settings.ANTHROPIC_API_KEY
    if not key or not opinions:
        return opinions

    # Build context from analysis: discrepancies + charges
    discrepancies = analysis_result.get("discrepancies", [])
    charges = analysis_result.get("charges_explained", [])

    ctx = "User situation:\n"
    for d in discrepancies[:5]:
        ctx += f"  - Finding: {d.get('finding','')}. Ask attorney about: {d.get('ask_attorney','')}\n"
    for c in charges[:3]:
        ctx += f"  - Charge: {c.get('charge','')}\n"

    # Build opinion summaries
    opinions_text = ""
    for i, op in enumerate(opinions[:5]):
        opinions_text += (
            f"--- OPINION {i} ---\n"
            f"Case: {op.get('case_name','')}\n"
            f"Court: {op.get('court','')}\n"
            f"Summary: {op.get('summary_plain','')[:300]}\n\n"
        )

    try:
        import requests as _requests
        resp = _requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": "claude-haiku-4-5-20251001",
                "messages": [{
                    "role": "user",
                    "content": (
                        "A person had their police report analyzed. Their situation:\n"
                        f"{ctx}\n"
                        "These Florida court opinions may relate to their case:\n"
                        f"{opinions_text}\n"
                        "For EACH opinion, provide TWO things:\n"
                        "1. A PLAIN-LANGUAGE EXPLANATION bridging the opinion to "
                        "their situation. Explain what the case means for THEM. "
                        "Use simple language anyone can understand. "
                        "Example: 'This case is about what happens when police search "
                        "without a warrant — the court said evidence found that way "
                        "can be thrown out. In your situation, the officer searched "
                        "your car without asking permission or getting a warrant, "
                        "which means this ruling could apply to you.'\n"
                        "2. A SPECIFIC QUESTION they should ask their attorney. "
                        "Example: 'Ask: In my case, the officer searched my car "
                        "without a warrant or my consent. Under Florida v. Jardines, "
                        "could that evidence be suppressed?'\n"
                        "Return ONLY a JSON array of objects, one per opinion:\n"
                        '[{"explanation":"...","question":"..."}]'
                    ),
                }],
                "max_tokens": 600,
                "temperature": 0.3,
            },
            timeout=15,
        )
        if resp.status_code == 200:
            raw = resp.json()["content"][0]["text"].strip()
            raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            questions = _json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(questions, list):
                for i, item in enumerate(questions):
                    if i < len(opinions) and isinstance(item, dict):
                        opinions[i]["attorney_explanation"] = str(item.get("explanation", ""))
                        opinions[i]["attorney_prompt"] = str(item.get("question", ""))
                    elif i < len(opinions):
                        # Backward compat: plain string = question only
                        opinions[i]["attorney_explanation"] = ""
                        opinions[i]["attorney_prompt"] = str(item)
    except Exception:
        logger.warning("Claude Haiku attorney question generation failed, returning opinions unchanged", exc_info=True)

    return opinions


# ---------------------------------------------------------------------------
# Deterministic mapper: V2 analysis result -> situation_tags.
#
# Governing principle: the structured `defect_category` enum on each
# discrepancy is the PRIMARY constitutional signal. The curated booleans
# (miranda_noted, probable_cause_present) are kept as a SECONDARY,
# backward-compatible signal. Free-text keyword scan is reserved only for
# signals that have no dedicated boolean or category (excessive force ->
# police_misconduct). Searching free text for bare "search"/"miranda"
# produced false positives (neutral narration), so those branches remain
# removed — precision over recall on the free-text path.
#
# Emits ONLY tags confirmed in the legal_opinions vocabulary (recon
# Step 1, 2026-07), EXCEPT `due_process` and `language_access`, which are
# emitted ahead of corpus support — see _DEFECT_CATEGORY_TAGS note.
# ---------------------------------------------------------------------------

_CHARGE_DUI = re.compile(
    r"\b(dui|dwi|driv(?:er|ing)? under the influence|b\.?a\.?c|"
    r"breath(?:alizer)?|blood[- ]?alcohol)\b", re.IGNORECASE)
# Stem forms (no trailing \b) so Trafficking / Burglary / Robbery /
# Kidnapping match. "possess" intentionally excluded — possession is
# not trafficking, and the corpus has no drug_possession tag.
_CHARGE_DRUG_VERB = re.compile(
    r"\b(traffick|deliver|manufactur|distribut)", re.IGNORECASE)
_DRUG_SUBSTANCE = re.compile(
    r"\b(cocaine|heroin|meth(?:amphetamine)?|cannabis|marijuana|"
    r"controlled substance|fentanyl|oxycodone|narcotic|opium|mdma)\b", re.IGNORECASE)
# Felony-class indicators. Bare "assault" is intentionally EXCLUDED — in
# Florida, simple assault (a threat) is a first-degree misdemeanor, so matching
# it here would surface felony-level opinions for misdemeanor defendants (a
# precision regression). Felony assault/battery variants are caught by the
# explicit "aggravated" / "sexual batter" qualifiers below.
_CHARGE_FELONY = re.compile(
    r"\b(felony|murder|homicide|burglar|robber|kidnap|rape|"
    r"sexual batter|aggravated assault|aggravated batter|"
    r"arson|manslaughter)", re.IGNORECASE)
# Homicide-class indicators — the charge-context exclusion ladder's top rung
# (Joe ruling 2026-08-27). Deterministic, text-based, testable. Stem forms
# (murder\w*, homicid\w+) so "murdering", "homicidal" classify too.
_CHARGE_HOMICIDE = re.compile(
    r"\b(murder\w*|homicid\w+|manslaughter\w*|death[- ]?(penalty|sentence)|"
    r"capital[- ]?(murder|case|felony))\b", re.IGNORECASE)
_CHARGE_MISD = re.compile(r"\bmisdemeanor\b", re.IGNORECASE)

# Charge-class / offense-seriousness tags. These describe the *grade* of the
# charge, not a legal issue. A tag set containing ONLY these carries no
# constitutional signal — there is no actual legal issue corroborating the
# class label (e.g. a bare "misdemeanor" disorderly-conduct summons with no
# defect) — so get_relevant_opinions() short-circuits to [] for class-only
# sets. When a substantive tag (anything outside this set) is also present,
# ALL tags including the class tag still inform ranking, unchanged.
# `traffic_stop` is included because it is emitted automatically whenever a
# DUI charge is present, so it corroborates nothing beyond the charge itself
# — a bare DUI with no substantive defect short-circuits like the others.
_CHARGE_CLASS_TAGS = frozenset(
    {"misdemeanor", "felony", "dui", "drug_trafficking", "traffic_stop"}
)

# Free-text keyword scan — ONLY for signals with no dedicated boolean.
_DESC_FORCE = re.compile(
    r"\b(excessive force|beat(?:en)?|taser|tased|choke|choked|"
    r"pepper spray|body ?slam)\b", re.IGNORECASE)

# ---------------------------------------------------------------------------
# Structured defect_category -> situation_tag mapping.
#
# The LLM now emits a `defect_category` enum on each discrepancy (see
# PoliceReportAnalyzerV2 SYSTEM_PROMPT). This is the PRIMARY constitutional
# signal: it fires regardless of the miranda_noted / probable_cause_present
# booleans (which are kept as a secondary, backward-compatible signal).
# `due_process` and `language_access` have no boolean equivalent, so the
# category is their only path to retrieval.
#
# NOTE (corpus gap, 2026-07-23): `due_process` and `language_access` are
# emitted as-is but are NOT present in the current Florida-only legal_opinions
# corpus (the corpus has `due process` with a space; `language_access` is
# absent entirely). Retrieval will return nothing for those two categories
# until a separate corpus-scope decision normalizes/adds them. Implemented
# per instruction; corpus intentionally left untouched.
# ---------------------------------------------------------------------------
_DEFECT_CATEGORY_TAGS: dict[str, tuple[str, ...]] = {
    "miranda": ("fifth_amendment", "sixth_amendment"),
    "fourth_amendment": (
        "fourth_amendment",
        "unlawful_search",
        "probable_cause",
    ),
    "due_process": ("due_process",),
    "language_access": ("language_access",),
    # chain_of_custody / procedural have no dedicated opinion vocabulary.
    "chain_of_custody": (),
    "procedural": (),
}


def _is_explicit_false(value) -> bool:
    """True only for an explicitly-negated boolean signal.

    Accepts real ``False`` plus the common LLM-JSON drift forms (the strings
    "false"/"False", and ``0``). ``None`` (unknown) and any truthy/``True``
    value return False — preserving the precision-over-recall contract that
    constitutional-violation tags fire ONLY on an explicit negation, never on
    an absent/unknown field.
    """
    if isinstance(value, str):
        return value.strip().lower() == "false"
    return value is False or value == 0


def derive_situation_tags(v2_result: dict) -> list[str]:
    """Map a Police Report V2 analysis result to legal_opinions tags.

    Deterministic — defect_category enum + boolean flags + keyword matching.
    Returns the deduped, sorted tag list; [] when no signal matches. The
    `defect_category` on each discrepancy is the PRIMARY constitutional
    signal (fires regardless of booleans); booleans are a secondary,
    backward-compatible signal; free text only contributes excessive-force
    -> police_misconduct.

    V2 result shape (per PoliceReportAnalyzerV2 prompt):
        miranda_noted: bool | None
        probable_cause_present: bool | None
        charges_explained: [{ charge, plain_english }]
        discrepancies:    [{ severity, defect_category, description,
                             ask_attorney, page_ref }]
        missing_fields:   [{ severity, field_name, why_important, page_ref }]
    """
    if not isinstance(v2_result, dict):
        return []
    tags: set[str] = set()

    # --- Curated boolean signals (explicit False only; null = unknown) ---
    # Raw flag values (as received from the LLM, BEFORE normalization) captured
    # for observability: if a future report surfaces zero opinions because a
    # flag arrived in a shape the normalizer doesn't recognize, this log line
    # shows exactly what the model emitted — turning a silent miss into a
    # diagnosable one. No PII: flag values and tag names only, never report text.
    raw_miranda = v2_result.get("miranda_noted")
    raw_pc = v2_result.get("probable_cause_present")

    if _is_explicit_false(raw_miranda):
        tags |= {"fifth_amendment", "sixth_amendment"}
    # NOTE: probable_cause_present is deliberately NOT mapped to tags here.
    # Per the V2 SYSTEM_PROMPT it answers "is a PC affidavit present in the
    # report paperwork" — not "did a search/seizure occur without valid PC."
    # The two are unrelated: a summons-only report with no search can
    # legitimately lack a PC affidavit, so mapping False -> 4A/unlawful_search
    # tags produced false positives (irrelevant search/seizure case law). The
    # accurate 4A signal is the defect_category="fourth_amendment" path below.
    # raw_pc is still captured for the observability log line.

    # --- Structured defect_category signals (PRIMARY constitutional path) ---
    # Each discrepancy may carry a `defect_category` enum assigned by the
    # LLM. This is independent of the booleans above: a Miranda defect
    # flagged via category fires even when miranda_noted is True/null.
    # Categories map to the full set in _DEFECT_CATEGORY_TAGS; unknown /
    # out-of-vocab values are ignored (no baseline tag).
    for d in v2_result.get("discrepancies") or []:
        if not isinstance(d, dict):
            continue
        category = d.get("defect_category")
        if not isinstance(category, str):
            continue
        tags.update(_DEFECT_CATEGORY_TAGS.get(category, ()))

    # --- Charge text -> offense-class tags ---
    charge_blob = " ".join(
        f"{c.get('charge', '')} {c.get('plain_english', '')}"
        for c in v2_result.get("charges_explained") or []
        if isinstance(c, dict)
    )
    if charge_blob:
        if _CHARGE_DUI.search(charge_blob):
            tags |= {"dui", "traffic_stop"}
        if _CHARGE_DRUG_VERB.search(charge_blob) and _DRUG_SUBSTANCE.search(charge_blob):
            tags.add("drug_trafficking")
        if _CHARGE_FELONY.search(charge_blob):
            tags.add("felony")
        if _CHARGE_MISD.search(charge_blob):
            tags.add("misdemeanor")

    # --- Discrepancy / missing-field free text -> excessive force only ---
    desc_blob = " ".join(
        f"{d.get('description', '')} {d.get('field_name', '')} "
        f"{d.get('why_important', '')}"
        for key in ("discrepancies", "missing_fields")
        for d in (v2_result.get(key) or [])
        if isinstance(d, dict)
    )
    if desc_blob and _DESC_FORCE.search(desc_blob):
        tags.add("police_misconduct")

    # One structured line per mapper invocation: raw flag shapes (pre-
    # normalization) + emitted tags. Surfaces normalizer-miss shape drift that
    # would otherwise silently yield [] and render no opinions. No PII.
    logger.info(
        "derive_situation_tags miranda_noted=%r probable_cause_present=%r "
        "tags=%r",
        raw_miranda, raw_pc, sorted(tags),
    )

    return sorted(tags)


# ---------------------------------------------------------------------------
# Criminal Procedure mapper: explainer result -> situation_tags.
#
# Deterministic precision-over-recall — maps the structured input params
# (severity, current_stage) to the verified legal_opinions vocabulary.
# The LLM output text is NOT keyword-scanned because the explainer always
# discusses Miranda/search/probable cause as standard criminal-procedure
# topics, producing false positives. Only stage-derived tags that describe
# a concrete legal context (bail, plea, sentencing, public defender) plus
# the charge class (felony/misdemeanor) are emitted.
# ---------------------------------------------------------------------------


def derive_criminal_tags(
    criminal_result: dict,
    charge_type: str = "",
    severity: str = "",
    current_stage: str = "",
) -> list[str]:
    """Map a Criminal Procedure explainer result to legal_opinions tags.

    Deterministic — no LLM, no free-text scan. Returns the deduped, sorted
    tag list; [] when no signal matches.  Precision over recall: prefer []
    over wrong tags.
    """
    if not isinstance(criminal_result, dict):
        return []
    tags: set[str] = set()

    # ── Charge class tags (from severity) ──
    if severity == "felony":
        tags.add("felony")
    elif severity == "misdemeanor":
        tags.add("misdemeanor")
    # infraction ↔ no tag

    # ── Stage-derived tags ──
    stage = current_stage.lower().strip() if current_stage else ""
    if stage == "sentencing":
        tags.add("criminal_sentencing")
    if stage in ("pretrial", "trial"):
        tags.add("plea_bargain")
    if stage in ("arrested", "charged", "arraigned"):
        tags.add("bail_bond")
        tags.add("public_defender")

    logger.info(
        "derive_criminal_tags severity=%r current_stage=%r tags=%r",
        severity,
        current_stage,
        sorted(tags),
    )
    return sorted(tags)
