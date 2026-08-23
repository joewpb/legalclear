"""Prose-level citation filter (Dispatch J4-1).

Doctrine: the structured ``citations`` field is guarded by
``core.citation_resolver`` (Dispatch J1) — but a citation embedded in
free-form explanation TEXT bypasses that guard entirely. Same shape as the
``core/url_filter.py`` lesson: prompt instructions telling the model to cite
only from an approved list are not a guarantee, so this module strips
unresolvable citation-shaped tokens out of generated prose at the output
boundary, deterministically, after generation.

Subsection rule: a citation-shaped token is matched against the resolution
registry — statute-curated (``agents.small_claims_citations`` ∪
``agents.eviction_citations``) UNION owned rule citations registered via
``register_rule_citations`` (Dispatch J5, backed by the ``court_rules``
table) — on its BASE citation, normalized, with any trailing subsection
suffix like "(2)" or "(2)(a)" stripped for the lookup only. If the base
resolves, the token survives VERBATIM, subsection included — e.g.
"Fla. Stat. § 83.60(2)" survives because "Fla. Stat. § 83.60" is curated.
This preserves the deadline engine's code-declared subsection granularity
(``deadline/rules.py`` cites "§ 83.60(2)" as a computed ``governing_rule``)
while still suppressing fabricated ("§ 83.999") and real-but-uncurated
("§ 83.64") citations.

A rule citation not yet registered in the owned ``court_rules`` set (or seen
before that registry loads) still gets stripped. That is intended — coverage
gaps degrade to silence, not fabrication.

Stripped values are logged at INFO with the agent name for observability.
They are NEVER included in any user-facing output.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable

from src.core.citation_resolver import normalize_citation

logger = logging.getLogger("legalclear.citation_filter")

# ── per-agent curated-set registry (2026-08-23, Joe ruling) ─────────────
# Every agent name that reaches the filter MUST have an explicit registry
# entry — the way every deadline rule declares its counting_regime. No
# inheritance between agents, no fallthrough to a shared union. An
# unregistered agent name RAISES: a new agent the guard does not know
# about must fail loudly, not silently emit unfiltered prose.
#
# The one shared supplement is _REGISTERED_RULE_KEYS: the owned court_rules
# corpus loaded once from the DB at startup. That is a single owned
# dataset, not one agent inheriting from another.

_AGENT_CURATED_SETS: dict[str, frozenset[str]] = {}
_REGISTRY_INITIALIZED = False
_REGISTERED_RULE_KEYS: set[str] = set()


def register_agent_curated_set(agent_name: str, citations: Iterable[str]) -> None:
    """Explicitly declare one agent's curated citation set."""
    _AGENT_CURATED_SETS[agent_name] = frozenset(
        normalize_citation(c) for c in citations
    )


def _agent_curated_keys(agent_name: str) -> frozenset[str]:
    entry = _AGENT_CURATED_SETS.get(agent_name)
    if entry is None:
        raise RuntimeError(
            f"citation_filter: agent {agent_name!r} has no curated-set "
            f"registry entry. Every agent name that emits filtered text "
            f"must be registered via register_agent_curated_set — no "
            f"fallthrough, no implicit union."
        )
    return entry


def _ensure_registry() -> None:
    """Lazy one-time registration of every known agent name.

    Lazy on purpose: agents/__init__ imports explainer, and explainer
    imports this module — an eager import of the agents package here
    creates a cycle. Curated sets are agent-module constants, so they load
    at first filter use, by which time the package graph is initialized.
    """
    global _REGISTRY_INITIALIZED
    if _REGISTRY_INITIALIZED:
        return

    from src.agents.eviction_citations import EVICTION_CURATED_CITATIONS
    from src.agents.pc_citations import PC_CURATED_CITATIONS
    from src.agents.small_claims_citations import SMALL_CLAIMS_CURATED_CITATIONS

    pc = set(PC_CURATED_CITATIONS)
    # Legacy agents historically resolved against the union of all three
    # curated modules (the pre-2026-08-23 behavior). That union is now
    # their EXPLICIT declaration — same coverage, now opt-in and auditable.
    full_union = set(SMALL_CLAIMS_CURATED_CITATIONS) | set(EVICTION_CURATED_CITATIONS) | pc

    for name in (
        "explainer", "property_casualty", "small_claims",
        "criminal_procedure", "discovery_motion", "wills_trusts",
        "chat_expert:small_claims", "chat_expert:criminal_procedure",
        "chat_expert:police_report", "chat_expert:discovery_motion",
        "chat_expert:property_casualty", "chat_expert:wills_trusts",
        "chat_expert:landlord_tenant",
    ):
        register_agent_curated_set(name, full_union)

    # I-8 taps cite P&C only — a deliberately narrower set than the
    # property_casualty explainer's legacy union.
    register_agent_curated_set("pc_llm_tap", pc)

    _REGISTRY_INITIALIZED = True


def register_rule_citations(citations: Iterable[str]) -> None:
    """Merge normalized owned rule citations into the resolution registry.

    Idempotent — normalization plus a set means registering the same
    citation twice (or many times, e.g. re-running startup load) is a no-op
    beyond the first insert. Additive-only: never removes a previously
    registered key, so repeated partial loads can only widen coverage.
    """
    for citation in citations:
        _REGISTERED_RULE_KEYS.add(normalize_citation(citation))


def load_rule_citations_from_db(db) -> None:
    """Fetch owned rule citations from ``court_rules`` and register them.

    There is no dedicated backend startup hook that calls
    ``load_owned_citations`` today (it is currently wired nowhere but its
    own tests), so this has the same shape: a callable meant to be invoked
    once wherever the backend constructs its ``DatabaseManager`` singleton
    (see ``src.api.routes``), not triggered automatically by importing or
    using this module. Guarded by try/except: on any failure (missing DB,
    network, schema) the registry simply stays at whatever was already
    registered — degrading to the statute-curated set, never loosening the
    filter. Deliberately NOT called from ``_curated_keys()`` — that path is
    exercised by pure unit tests (``test_citation_filter.py``) that must
    never reach the network.
    """
    try:
        from src.core.citation_resolver import load_owned_rule_citations

        register_rule_citations(load_owned_rule_citations(db))
    except Exception as e:
        logger.error("citation_filter: rule-citation load failed: %s", e)


def _resolves(matched_value: str, agent_name: str) -> bool:
    base = _base_citation(matched_value)
    return normalize_citation(base) in (
        _agent_curated_keys(agent_name) | _REGISTERED_RULE_KEYS
    )

# Citation-shaped token patterns. Conservative by design: every alternative
# requires an explicit citation marker ("Fla. Stat.", "Fla. Stats.",
# "Florida Statute(s)", "F.S.", "§", a trailing "section N, Florida
# Statutes" phrase, a "Fla. R. ... P." / "Fla. Sm. Cl. R." / "Fla. R. Gen.
# Prac. & Jud. Admin." rule prefix, or a Florida Administrative Code rule
# marker) followed by a numeric section pattern — plain prose mentioning "§"
# with no number after it (e.g. "The § symbol in a contract.") never
# matches.
_SECTION_NUM = r"\d+(?:\.\d+)*(?:\(\w+\))*"
# Admin Code rule numbers carry a leading agency-code letter/hyphen shape
# ("69O-166.031") that bare statute sections never do.
_ADMIN_NUM = r"\d+[A-Za-z]?-\d+(?:\.\d+)*(?:\(\w+\))*"
# Every word/abbreviation form the models use for "Fla. Stat." — merged into
# one alternative so each new phrasing doesn't need its own top-level branch.
_STATUTE_PREFIX = (
    r"(?:Fla\.\s*Stats?\.\s*(?:§\s*)?"
    r"|Florida\s+Statutes?\s*(?:§\s*)?"
    r"|F\.S\.\s*(?:§\s*)?)"
)
_CITATION_TOKEN_RE = re.compile(
    r"(?:" + _STATUTE_PREFIX + _SECTION_NUM + r")"
    # "section 626.9541, Florida Statutes" / "Section 626.9541 of the
    # Florida Statutes" — the number comes before the statute marker.
    r"|(?:(?:section|sec\.)\s+" + _SECTION_NUM + r"\s*(?:,\s*|\s+of\s+(?:the\s+)?)Florida\s+Statutes?)"
    r"|(?:§\s*" + _SECTION_NUM + r")"
    r"|(?:(?:Fla\.\s*)?R\.\s*Gen\.\s*Prac\.\s*&\s*Jud\.\s*Admin\.\s*" + _SECTION_NUM + r")"
    r"|(?:(?:Fla\.\s*)?R\.\s*(?:Civ\.|Crim\.|App\.|Fam\.\s*L\.|Jud\.\s*Admin\.|Prob\.)?\s*R?\.?\s*P\.\s*" + _SECTION_NUM + r")"
    r"|(?:(?:Fla\.\s*)?Sm\.\s*Cl\.\s*R\.\s*" + _SECTION_NUM + r")"
    r"|(?:(?:Fla\.\s*)?Prob\.\s*R\.\s*" + _SECTION_NUM + r")"
    # Florida Administrative Code rule cites — matched so the filter can
    # strip them; there is no regulatory curated set, so these never
    # resolve and are always removed.
    r"|(?:(?:Fla\.\s*Admin\.\s*Code\s*R(?:ule)?\.?|Florida\s+Administrative\s+Code\s+Rule|F\.A\.C\.)\s*" + _ADMIN_NUM + r")",
    re.IGNORECASE,
)

# A bare "N.NNN" chapter-dot-section shape with no citation marker at all is
# only citation-shaped when it sits next to statute language — otherwise
# it's indistinguishable from an ordinary decimal number in prose.
_BARE_SECTION_NUM_RE = re.compile(r"\b\d{1,4}\.\d{2,5}\b")
_STATUTE_LANGUAGE_RE = re.compile(r"florida|statute|section|chapter", re.IGNORECASE)
_BARE_NUM_CONTEXT_WINDOW = 30

# Longest realistic citation token (a rule cite with a two-level subsection
# suffix) is well under this — used to bound how far back a streaming
# consumer must look for a not-yet-complete token near the buffer tail.
_MAX_TOKEN_LEN = 60
_TRIGGER_RE = re.compile(r"Fla\.?|Florida|F\.S\.|section|sec\.|§", re.IGNORECASE)

_TRAILING_SUFFIX_RE = re.compile(r"(?:\(\w+\)\s*)+$")

# Word/abbreviation forms of "Fla. Stat." that appear AFTER the section
# number ("section N, Florida Statutes") — rewritten to the canonical
# leading form before normalization so lookup works the same as every other
# phrasing.
_TRAILING_STAT_ALIAS_RE = re.compile(
    r"^(?:section|sec\.)\s+(?P<num>" + _SECTION_NUM + r")\s*"
    r"(?:,\s*|\s+of\s+(?:the\s+)?)Florida\s+Statutes?\.?$",
    re.IGNORECASE,
)
# Word/abbreviation forms that appear BEFORE the section number — rewritten
# to "Fla. Stat. §" so normalize_citation's existing "Fla. Stat." handling
# covers them without needing its own alias logic.
_LEADING_STAT_ALIAS_RE = re.compile(
    r"^(?:Florida\s+Statutes?|F\.S\.|Fla\.\s*Stats?\.)\s*",
    re.IGNORECASE,
)


def _canonicalize_statute_alias(value: str) -> str:
    """Rewrite any word/abbreviation phrasing of a statute citation to the
    canonical "Fla. Stat. § N" shape ``normalize_citation`` already
    understands, for lookup purposes only.
    """
    trailing = _TRAILING_STAT_ALIAS_RE.match(value)
    if trailing:
        return f"Fla. Stat. § {trailing.group('num')}"
    leading = _LEADING_STAT_ALIAS_RE.match(value)
    if leading:
        rest = value[leading.end():].strip().lstrip("§").strip()
        return f"Fla. Stat. § {rest}"
    return value


def _base_citation(matched_value: str) -> str:
    """Strip a trailing subsection suffix (one or more "(...)" groups) from
    a matched citation token, then canonicalize word/abbreviation statute
    phrasings, for lookup purposes only — never mutates what gets emitted
    when the token is kept.
    """
    stripped = _TRAILING_SUFFIX_RE.sub("", matched_value.strip()).strip()
    return _canonicalize_statute_alias(stripped)


def _bare_number_tokens(text: str, consumed: list[tuple[int, int]]) -> list[tuple[int, int, str]]:
    """Find bare "N.NNN" numbers that sit within ``_BARE_NUM_CONTEXT_WINDOW``
    characters of statute language, skipping spans already claimed by the
    main token regex.
    """
    found = []
    for m in _BARE_SECTION_NUM_RE.finditer(text):
        start, end = m.span()
        if any(cs <= start < ce for cs, ce in consumed):
            continue
        ctx_start = max(0, start - _BARE_NUM_CONTEXT_WINDOW)
        ctx_end = min(len(text), end + _BARE_NUM_CONTEXT_WINDOW)
        context = text[ctx_start:start] + text[end:ctx_end]
        if _STATUTE_LANGUAGE_RE.search(context):
            found.append((start, end, m.group(0)))
    return found


def filter_citations_text(text: str, agent_name: str) -> str:
    """One-shot citation filter for a complete (non-streamed) string.

    Every citation-shaped token whose base citation resolves against the
    calling agent's REGISTERED curated set (plus the owned court_rules
    registry) is kept verbatim; every other citation-shaped token is
    removed and logged. Ordinary prose containing "§" or "Fla." with no
    trailing numeric section is left untouched.

    An agent name with no registry entry RAISES — see
    register_agent_curated_set.
    """
    if not text:
        return text

    _ensure_registry()
    main_matches = [(m.start(), m.end(), m.group(0)) for m in _CITATION_TOKEN_RE.finditer(text)]
    bare_matches = _bare_number_tokens(text, [(s, e) for s, e, _ in main_matches])
    all_matches = sorted(main_matches + bare_matches, key=lambda t: t[0])

    pieces: list[str] = []
    last_end = 0
    for start, end, value in all_matches:
        if start < last_end:
            continue
        if _resolves(value, agent_name):
            continue
        ctx_start = max(0, start - 60)
        ctx_end = min(len(text), end + 60)
        logger.info(
            "citation_filter stripped agent=%s value=%r context=%r",
            agent_name, value, text[ctx_start:ctx_end],
        )
        pieces.append(text[last_end:start])
        last_end = end
    pieces.append(text[last_end:])

    cleaned = "".join(pieces)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned


def _safe_release_point(buffer: str) -> int:
    """Return the index up to which ``buffer`` can be released without
    risking splitting a not-yet-complete citation token across a chunk
    boundary.

    Looks for the last citation "trigger" character sequence ("Fla",
    "Florida", "§") within the trailing ``_MAX_TOKEN_LEN`` window. If that
    trigger already anchors a complete, terminated match (one that ends
    strictly before the end of the buffer, i.e. more text has arrived after
    it), everything is safe to release. Otherwise the buffer is held back
    from the trigger's start, since more incoming characters (digits, a
    subsection suffix) could still extend it into a citation.
    """
    window_start = max(0, len(buffer) - _MAX_TOKEN_LEN)
    last_trigger_start = None
    for match in _TRIGGER_RE.finditer(buffer, window_start):
        last_trigger_start = match.start()
    if last_trigger_start is None:
        return len(buffer)

    full_match = _CITATION_TOKEN_RE.match(buffer, last_trigger_start)
    if full_match and full_match.end() < len(buffer):
        # A digit, dot, or open-paren right after the match means more
        # characters (a continuing decimal, or a subsection suffix) could
        # still be on the way in the next chunk — not actually terminated.
        if buffer[full_match.end()] not in ".0123456789(":
            return len(buffer)
    return last_trigger_start


class StreamingCitationFilter:
    """Buffers streamed text so a citation token split across two SSE chunks
    is still caught. Call ``feed()`` per chunk and ``flush()`` once at
    stream end — mirrors ``core.url_filter.StreamingURLFilter``.
    """

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self._buffer = ""

    def feed(self, chunk: str) -> str:
        self._buffer += chunk
        release_at = _safe_release_point(self._buffer)
        if release_at == 0:
            return ""
        ready, self._buffer = self._buffer[:release_at], self._buffer[release_at:]
        return filter_citations_text(ready, self.agent_name)

    def flush(self) -> str:
        remainder, self._buffer = self._buffer, ""
        if not remainder:
            return ""
        return filter_citations_text(remainder, self.agent_name)
