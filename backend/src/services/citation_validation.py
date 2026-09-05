"""Phase C1 — deterministic citation validation for the Police Report Analyzer.

Zero LLM. Three jobs:

1. ``extract_fs_citations`` — every statute/rule-shaped citation in free
   text, including the SINGULAR ``Florida Statute N`` form (handoff open
   item #7) and ``section N, Florida Statutes`` trailing form.
2. Court-only classification (deterministic hard list) — Ch. 90 (Florida
   Evidence Code), rules of court, and Rules Regulating The Florida Bar
   govern COURT PROCEEDINGS. A citation from those sets in an analysis
   field is a wrong-scope claim (the 2026-08-30 prod run claimed
   F.S. § 90.606 imposes interpreter obligations at the roadside — wrong;
   90.606 is a court-proceedings/witness-competency rule). The citation is
   stripped and a scope note added. The deterministic override always wins
   over the LLM.
3. Corpus lookup — every other statute citation is looked up in the owned
   ``statutes`` table (by chapter + section). Found → kept and logged
   ``verified``. Not found → stripped, logged ``not_found``, and a
   plain-English note is added.

Document-fact citations (``charges_explained[].charge`` — the report's OWN
charge statutes) are NEVER stripped: they are facts from the uploaded
document, not LLM claims. Any citation in another field that matches one
of them is also kept (it references the same charge).

The validator never breaks the caller: when the DB is unreachable it
returns the analysis unchanged with an empty log (coverage gaps degrade to
no validation, never to corruption). Any exception is caught at the call
site.
"""

from __future__ import annotations

import copy
import logging
import re

from src.memory.db import DatabaseManager

logger = logging.getLogger(__name__)

# Module-level DatabaseManager, matching the opinion_retrieval idiom.
db = DatabaseManager()

# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

# Chapter-dot-section with optional subsection suffix, e.g. 90.606,
# 893.13(6)(a), 83.60(2).
_SECTION_NUM = r"\d+(?:\.\d+)?(?:\([A-Za-z0-9]+\))*"

# Statute citations: leading prefix forms (F.S. § / Fla. Stat. § /
# Florida Statute(s) § — singular included per handoff open item #7),
# bare § forms, and the trailing "section N, Florida Statutes" form.
_STATUTE_CITE_RE = re.compile(
    r"(?:(?:Fla\.\s*Stats?\.|Florida\s+Statutes?|F\.S\.)\s*§?\s*)"
    r"(?P<num>" + _SECTION_NUM + r")"
    r"|(?:§\s*)(?P<num2>" + _SECTION_NUM + r")"
    r"|(?:(?:section|sec\.)\s+)(?P<num3>" + _SECTION_NUM + r")"
    r"\s*(?:,\s*|\s+of\s+(?:the\s+)?)Florida\s+Statutes?",
    re.IGNORECASE,
)

# Rules of court: "Fla. R. Crim. P. 3.111", "Fla. R. Civ. P. 1.140(a)",
# "Florida Rule of Criminal Procedure 3.111", "R. Gen. Prac. & Jud. Admin.".
_RULE_CITE_RE = re.compile(
    r"(?:(?:Fla\.\s*)?R\.\s*(?:Civ\.|Crim\.|App\.|Prob\.|Gen\.\s*Prac\.\s*"
    r"&\s*Jud\.\s*Admin\.|Jud\.\s*Admin\.)?\s*P\.\s*)"
    r"(?P<num>" + _SECTION_NUM + r")"
    r"|(?:Florida\s+Rules?\s+of\s+(?:Civil|Criminal|Appellate|Judicial\s+"
    r"Administration)\s+Procedure)\s*,?\s*(?P<num2>" + _SECTION_NUM + r")",
    re.IGNORECASE,
)

# Rules Regulating The Florida Bar — leading form ("Rule 4-1.5, Rules
# Regulating The Florida Bar") and trailing form ("R. Regulating Fla. Bar.
# 4-1.5").
_BAR_RULE_RE = re.compile(
    r"(?:(?:Rules?\s+Regulating\s+(?:the\s+)?Florida\s+Bar|"
    r"R\.\s*Regulating\s+Fla\.\s*Bar\.?)\s*,?\s*(?:rule\s*)?)"
    r"(?P<num>\d+-\d+(?:\.\d+)*)"
    r"|(?:Rule\s+)(?P<num2>\d+-\d+(?:\.\d+)*)\s*,?\s*"
    r"(?:Rules?\s+Regulating\s+(?:the\s+)?Florida\s+Bar|"
    r"R\.\s*Regulating\s+Fla\.\s*Bar\.?)",
    re.IGNORECASE,
)

# Florida statute chapters that govern COURT PROCEEDINGS only. A claim
# citing one of these about field/officer conduct is wrong-scope by
# definition — the hard deterministic override.
_COURT_ONLY_CHAPTERS: frozenset[int] = frozenset({90})  # Evidence Code


def _iter_citations(text: str):
    """Yield (start, end, info) for every citation-shaped token in text."""
    for pattern, kind in (
        (_RULE_CITE_RE, "rule"),
        (_BAR_RULE_RE, "bar_rule"),
        (_STATUTE_CITE_RE, "statute"),
    ):
        for m in pattern.finditer(text):
            num = m.group("num") or m.group("num2") or m.group("num3")
            yield m.start(), m.end(), {
                "text": m.group(0).strip(),
                "kind": kind,
                "num": num,
            }


def _chapter_of(num: str) -> str | None:
    """'90.606' -> '90'; '893.13(6)(a)' -> '893'; None when no dot."""
    if "." not in num:
        return None
    return num.split(".", 1)[0]


def _base_section(num: str) -> str:
    """'893.13(6)(a)' -> '893.13' — subsection suffixes are stripped for
    the corpus LOOKUP only (matches the law.py statutes-table section
    shape); emitted text is never mutated by this."""
    return re.sub(r"(\([A-Za-z0-9]+\))+$", "", num)


def _is_court_only(info: dict) -> bool:
    """Deterministic court-proceedings classification."""
    if info["kind"] in ("rule", "bar_rule"):
        return True
    if info["kind"] == "statute":
        chapter = _chapter_of(info["num"])
        if chapter is not None and chapter.isdigit():
            return int(chapter) in _COURT_ONLY_CHAPTERS
    return False


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

# Fields the LLM generates (claims) — scan these. charges_explained[].charge
# is deliberately EXCLUDED: it is the report's own charge text, a document
# fact, never an LLM claim.
_SCAN_FIELDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("incident_summary", ()),
    ("probable_cause_summary", ()),
    ("what_happens_next", ()),
    ("discrepancies", ("description", "ask_attorney")),
    ("missing_fields", ("why_important",)),
    ("charges_explained", ("plain_english",)),
)

_COURT_ONLY_NOTE = (
    "{cite} is a rule for court proceedings. It does not create "
    "obligations for officers in the field."
)
_NOT_FOUND_NOTE = (
    "The analysis mentioned {cite}. This citation could not be verified "
    "against the Florida Statutes, so it was removed."
)


def _charge_citations(analysis: dict) -> frozenset[str]:
    """Normalized citation texts from the report's own charge fields."""
    cites: set[str] = set()
    for c in analysis.get("charges_explained") or []:
        if not isinstance(c, dict):
            continue
        charge_text = c.get("charge") or ""
        for _start, _end, info in _iter_citations(charge_text):
            cites.add(info["text"].casefold())
    return frozenset(cites)


def _strip_citations_from_text(text: str, spans: list[tuple[int, int]]) -> str:
    """Remove the given spans and collapse doubled whitespace."""
    pieces: list[str] = []
    last = 0
    for start, end in spans:
        pieces.append(text[last:start])
        last = end
    pieces.append(text[last:])
    return re.sub(r"[ \t]{2,}", " ", "".join(pieces)).strip()


def _corpus_sections(client, nums: list[str]) -> dict[str, dict]:
    """Batch lookup of statute sections in the owned corpus.

    Returns {section: row} for every hit. One PostgREST round trip.
    """
    if client is None or not nums:
        return {}
    try:
        result = (
            client.table("statutes")
            .select("chapter,section,title")
            .in_("section", sorted(set(nums)))
            .execute()
        )
    except Exception:
        logger.warning(
            "citation_validation: statutes corpus lookup failed",
            exc_info=True,
        )
        return {}
    found: dict[str, dict] = {}
    for row in result.data or []:
        section = row.get("section")
        if isinstance(section, str) and section:
            found[section] = row
    return found


def validate_analysis_citations(
    analysis: dict,
) -> tuple[dict, list[dict]]:
    """Validate and scrub every LLM-emitted citation in the analysis.

    Returns (scrubbed_analysis, citations_log). Never raises for corpus
    problems: DB unreachable → unchanged analysis + empty log. Charge
    citations (document facts) are never touched.
    """
    if not isinstance(analysis, dict):
        return analysis, []
    if db.client is None:
        return analysis, []

    out = copy.deepcopy(analysis)
    charge_cites = _charge_citations(out)

    notes: list[str] = []
    log: list[dict] = []
    pending_nums: list[str] = []
    pending_spans: dict[str, list[tuple[str, tuple[int, int]]]] = {}
    pending_texts: dict[str, str] = {}

    def _record(info: dict, status: str, **extra) -> dict:
        entry = {
            "citation": info["text"],
            "status": status,
        }
        if info["num"]:
            entry["section"] = info["num"]
        chapter = _chapter_of(info["num"] or "")
        if chapter:
            entry["chapter"] = chapter
        entry.update(extra)
        log.append(entry)
        return entry

    # ── pass 1: walk every scanned field, collect decisions ──────────────
    # field_path is the list of keys to reach the text (e.g.
    # ["discrepancies", 0, "description"]); edits are applied in pass 2.
    edits: list[tuple[list, tuple[int, int]]] = []

    def _scan(path: list, text: str | None) -> None:
        if not text:
            return
        for start, end, info in _iter_citations(text):
            if info["text"].casefold() in charge_cites:
                _record(info, "from_report")
                continue
            if _is_court_only(info):
                edits.append((path, (start, end)))
                _record(info, "scrubbed_court_only")
                notes.append(_COURT_ONLY_NOTE.format(cite=info["text"]))
                continue
            # corpus decision deferred to the batch lookup (base section:
            # subsection suffixes are stripped for the lookup only)
            key = _base_section(info["num"] or info["text"])
            pending_nums.append(key)
            pending_spans.setdefault(key, []).append((path, (start, end)))
            pending_texts.setdefault(key, info["text"])

    # top-level string fields
    for field, subfields in _SCAN_FIELDS:
        if not subfields:
            _scan([field], out.get(field))
            continue
        for i, item in enumerate(out.get(field) or []):
            if not isinstance(item, dict):
                continue
            for sub in subfields:
                _scan([field, i, sub], item.get(sub))

    # ── pass 2: corpus lookup for pending statutes ───────────────────────
    corpus = _corpus_sections(db.client, pending_nums)
    for key in list(pending_spans):
        row = corpus.get(key)
        spans = pending_spans[key]
        # Log the ORIGINAL matched text (educational value, C2 input);
        # `section` carries the base number used for the lookup.
        info = {
            "text": pending_texts.get(key, key),
            "kind": "statute",
            "num": key,
        }
        if row is not None:
            _record(info, "verified", title=row.get("title"))
            continue
        for path, span in spans:
            edits.append((path, span))
        _record(info, "not_found")
        notes.append(_NOT_FOUND_NOTE.format(cite=info["text"]))

    # ── pass 3: apply text edits (group spans per path) ──────────────────
    # A path is a hashable tuple of keys, e.g. ("discrepancies", 0,
    # "description") or ("incident_summary",).
    spans_by_path: dict[tuple, list[tuple[int, int]]] = {}
    for path, span in edits:
        spans_by_path.setdefault(tuple(path), []).append(span)

    for path, spans in spans_by_path.items():
        container = out
        for key in path[:-1]:
            container = container[key]
        text = container[path[-1]]
        container[path[-1]] = _strip_citations_from_text(text, sorted(spans))

    out["citation_notes"] = notes
    return out, log
