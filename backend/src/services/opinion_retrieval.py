"""Opinion retrieval service — Stage 1 (no SSE wiring).

Two responsibilities:
  1. derive_situation_tags(v2_result): deterministically map a Police
     Report V2 analysis result to legal_opinions situation_tags.
     No LLM. No baseline tag — [] when nothing matches (precision over
     recall).
  2. get_relevant_opinions(tags): fetch opinions overlapping those tags
     from Supabase via DatabaseManager.

Database access goes through DatabaseManager (decision D) — the app's
existing abstraction, which degrades gracefully (client is None) when
SUPABASE_URL / SUPABASE_SERVICE_KEY are absent. No module-level
supabase client.
"""

from __future__ import annotations

import logging
import re

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


def get_relevant_opinions(
    situation_tags: list[str],
    limit: int = 3,
) -> list[dict]:
    """Return up to `limit` opinions matching any of `situation_tags`.

    Ranking: PRIMARY key = number of derived situation_tags the opinion
    shares (tag-overlap count, a relevance signal), SECONDARY/tiebreaker =
    cite_count desc. quality_flagged=False only. Returns [] on empty input,
    a charge-class-only tag set, degraded mode, or query error — retrieval
    never breaks the parent response.

    Charge-class gate: a tag set consisting ONLY of offense-seriousness
    labels (`_CHARGE_CLASS_TAGS`: misdemeanor/felony/dui/drug_trafficking)
    describes the charge grade, not a legal issue, and short-circuits to []
    before any DB work — same outcome as an empty tag set. At least one
    substantive tag (anything outside that set) must be present to retrieve.
    When one is, ALL tags — class tags included — still inform ranking
    exactly as before (e.g. felony + fourth_amendment is unaffected).

    PostgREST `.overlaps` filters to candidates matching ≥1 tag but cannot
    express overlap *count*, so we fetch the candidate set and rank in
    Python. `situation_tags` is selected solely to compute the overlap
    count and is stripped before returning so the API shape is unchanged.
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
    try:
        result = (
            db.client.table("legal_opinions")
            .select(_OPINION_COLUMNS + ", situation_tags")
            .overlaps("situation_tags", situation_tags)
            .eq("quality_flagged", False)
            .limit(500)
            .execute()
        )
        rows = result.data or []
        # Annotate each row with its overlap count, then sort by
        # (overlap_count desc, cite_count desc).
        for row in rows:
            opinion_tags = set(row.get("situation_tags") or [])
            row["_overlap"] = len(opinion_tags & query_tags)
        rows.sort(
            key=lambda r: (r["_overlap"], r.get("cite_count") or 0),
            reverse=True,
        )
        top = rows[:limit]
        # Strip helper keys so the returned dicts match _OPINION_COLUMNS.
        for row in top:
            row.pop("_overlap", None)
            row.pop("situation_tags", None)
        return top
    except Exception as e:
        logger.error("get_relevant_opinions failed: %s", e)
        return []


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
