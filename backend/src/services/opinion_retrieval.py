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

    Ranked by cite_count desc, quality_flagged=False only. Returns []
    on empty input, degraded mode, or query error — retrieval never
    breaks the parent response.
    """
    if not situation_tags:
        return []
    if db.client is None:
        return []
    try:
        result = (
            client.table("legal_opinions")
            .select(_OPINION_COLUMNS)
            .overlaps("situation_tags", situation_tags)
            .eq("quality_flagged", False)
            .order("cite_count", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []
    except Exception as e:  # noqa: BLE001 — fail-soft, never break response
        logger.error("get_relevant_opinions failed: %s", e)
        return []


# ---------------------------------------------------------------------------
# Deterministic mapper: V2 analysis result -> situation_tags.
#
# Governing principle: the curated booleans (miranda_noted,
# probable_cause_present) OWN their signals. Free-text keyword scan is
# reserved only for signals that have no dedicated boolean (excessive
# force -> police_misconduct). Searching free text for bare
# "search"/"miranda" produced false positives (neutral narration), so
# those branches were removed — precision over recall.
#
# Emits ONLY tags confirmed in the legal_opinions vocabulary (recon
# Step 1, 2026-07).
# ---------------------------------------------------------------------------

_CHARGE_DUI = re.compile(
    r"\b(dui|dwi|driv(?:er|ing)? under the influence|b\.?a\.?c|"
    r"breath(?:alizer)?|blood[- ]?alcohol)\b", re.I)
# Stem forms (no trailing \b) so Trafficking / Burglary / Robbery /
# Kidnapping match. "possess" intentionally excluded — possession is
# not trafficking, and the corpus has no drug_possession tag.
_CHARGE_DRUG_VERB = re.compile(
    r"\b(traffick|deliver|manufactur|distribut)", re.I)
_DRUG_SUBSTANCE = re.compile(
    r"\b(cocaine|heroin|meth(?:amphetamine)?|cannabis|marijuana|"
    r"controlled substance|fentanyl|oxycodone|narcotic|opium|mdma)\b", re.I)
# Felony-class indicators. Bare "assault" is intentionally EXCLUDED — in
# Florida, simple assault (a threat) is a first-degree misdemeanor, so matching
# it here would surface felony-level opinions for misdemeanor defendants (a
# precision regression). Felony assault/battery variants are caught by the
# explicit "aggravated" / "sexual batter" qualifiers below.
_CHARGE_FELONY = re.compile(
    r"\b(felony|murder|homicide|burglar|robber|kidnap|rape|"
    r"sexual batter|aggravated assault|aggravated batter|"
    r"arson|manslaughter)", re.I)
_CHARGE_MISD = re.compile(r"\bmisdemeanor\b", re.I)

# Free-text keyword scan — ONLY for signals with no dedicated boolean.
_DESC_FORCE = re.compile(
    r"\b(excessive force|beat(?:en)?|taser|tased|choke|choked|"
    r"pepper spray|body ?slam)\b", re.I)


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

    Deterministic — boolean flags + keyword matching only. Returns the
    deduped, sorted tag list; [] when no signal matches. Booleans own
    the Miranda / probable-cause signals; free text only contributes
    excessive-force -> police_misconduct.

    V2 result shape (per PoliceReportAnalyzerV2 prompt):
        miranda_noted: bool | None
        probable_cause_present: bool | None
        charges_explained: [{ charge, plain_english }]
        discrepancies:    [{ severity, description, ask_attorney, page_ref }]
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
    if _is_explicit_false(raw_pc):
        tags |= {"probable_cause", "fourth_amendment", "unlawful_search"}

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
