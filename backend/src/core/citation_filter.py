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

_STATUTE_CURATED_KEYS: frozenset[str] | None = None
_REGISTERED_RULE_KEYS: set[str] = set()


def _statute_curated_keys() -> frozenset[str]:
    """Lazy union of every module's curated statute base-citation set.

    Lazy on purpose: agents/__init__ imports explainer, and explainer imports
    this module — an eager import of the agents package here creates a cycle
    (citation_filter -> agents -> explainer -> citation_filter). The curated
    sets are agent-module constants, so they load at first filter use, by
    which time the package graph is fully initialized.
    """
    global _STATUTE_CURATED_KEYS
    if _STATUTE_CURATED_KEYS is None:
        from src.agents.eviction_citations import EVICTION_CURATED_CITATIONS
        from src.agents.pc_citations import PC_CURATED_CITATIONS
        from src.agents.small_claims_citations import SMALL_CLAIMS_CURATED_CITATIONS

        _STATUTE_CURATED_KEYS = frozenset(
            set(SMALL_CLAIMS_CURATED_CITATIONS)
            | set(EVICTION_CURATED_CITATIONS)
            | set(PC_CURATED_CITATIONS)
        )
    return _STATUTE_CURATED_KEYS


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


def _curated_keys() -> frozenset[str]:
    return frozenset(_statute_curated_keys() | _REGISTERED_RULE_KEYS)

# Citation-shaped token patterns. Conservative by design: every alternative
# requires an explicit citation marker ("Fla. Stat.", "Florida Statutes",
# "§", or a "Fla. R. ... P." / "Fla. Sm. Cl. R." / "Fla. R. Gen. Prac. & Jud.
# Admin." rule prefix) followed by a numeric section pattern — plain prose
# mentioning "§" with no number after it (e.g. "The § symbol in a
# contract.") never matches.
_SECTION_NUM = r"\d+(?:\.\d+)*(?:\(\w+\))*"
_CITATION_TOKEN_RE = re.compile(
    r"(?:Fla\.\s*Stat\.\s*(?:§\s*)?" + _SECTION_NUM + r")"
    r"|(?:Florida\s+Statutes\s*(?:§\s*)?" + _SECTION_NUM + r")"
    r"|(?:§\s*" + _SECTION_NUM + r")"
    r"|(?:Fla\.\s*R\.\s*Gen\.\s*Prac\.\s*&\s*Jud\.\s*Admin\.\s*" + _SECTION_NUM + r")"
    r"|(?:Fla\.\s*R\.\s*(?:Civ\.|Crim\.|App\.|Fam\.\s*L\.|Jud\.\s*Admin\.|Prob\.)?\s*R?\.?\s*P\.\s*" + _SECTION_NUM + r")"
    r"|(?:Fla\.\s*Sm\.\s*Cl\.\s*R\.\s*" + _SECTION_NUM + r")",
    re.IGNORECASE,
)

# Longest realistic citation token (a rule cite with a two-level subsection
# suffix) is well under this — used to bound how far back a streaming
# consumer must look for a not-yet-complete token near the buffer tail.
_MAX_TOKEN_LEN = 60
_TRIGGER_RE = re.compile(r"Fla\.?|Florida|§", re.IGNORECASE)

_TRAILING_SUFFIX_RE = re.compile(r"(?:\(\w+\)\s*)+$")


def _base_citation(matched_value: str) -> str:
    """Strip a trailing subsection suffix (one or more "(...)" groups) from
    a matched citation token, for lookup purposes only — never mutates what
    gets emitted when the token is kept.
    """
    return _TRAILING_SUFFIX_RE.sub("", matched_value.strip()).strip()


def _resolves(matched_value: str) -> bool:
    base = _base_citation(matched_value)
    return normalize_citation(base) in _curated_keys()


def filter_citations_text(text: str, agent_name: str) -> str:
    """One-shot citation filter for a complete (non-streamed) string.

    Every citation-shaped token whose base citation resolves against the
    curated union map is kept verbatim; every other citation-shaped token is
    removed and logged. Ordinary prose containing "§" or "Fla." with no
    trailing numeric section is left untouched.
    """
    if not text:
        return text

    pieces: list[str] = []
    last_end = 0
    for m in _CITATION_TOKEN_RE.finditer(text):
        start, end = m.span()
        if start < last_end:
            continue
        value = m.group(0)
        if _resolves(value):
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
