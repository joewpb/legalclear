"""Deterministic URL/bare-domain stripper for generated agent output.

AGENTS.md invariant: LLMs generate, deterministic code guarantees. Prompt
edits cannot reliably stop a model from emitting URLs it has seen in
training data (clsmf.org, the e-filing portal domain, invented domains like
floridalegalhelpdesk.org) — so this module strips them at the output
boundary instead of trusting the prompt. It only ever runs on text an
agent is about to emit, never on prompt/input text.

No allowlist: every URL and bare domain is stripped, full stop. The
product's own links (e.g. the flcourts.gov self-help link in
core.upl.ATTORNEY_REFERRAL_LINKS) are attached by deterministic code
*after* this filter runs on the agent's generated text, so they are
never subject to it.
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger("legalclear.url_filter")

# Curated, conservative TLD list. Requiring a recognized TLD (rather than
# "any 2+ letter suffix after a dot") is what keeps statute/case cites,
# abbreviations, and initials from matching — "Fla. Stat.", "U.S.", "a.m.",
# "e.g.", "i.e.", "vs.", "J. Smith", "So. 3d" all fail because "Stat",
# "S", "m", "g", nothing, "Smith", "3d" are not in this list.
_TLDS = (
    "com", "org", "net", "gov", "edu", "us", "io", "co", "info", "biz",
    "me", "tv", "app", "dev", "law", "legal", "attorney", "llc", "inc",
    "name", "online", "site", "xyz", "club", "uk", "ca", "gov.uk", "co.uk",
    "state",
)
_TLD_ALT = "|".join(
    sorted({t.replace(".", r"\.") for t in _TLDS}, key=len, reverse=True)
)

_SCHEME_OR_WWW = r'(?:https?://|www\.)[^\s<>"\')]+'
_BARE_DOMAIN = (
    r'\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+'
    rf'(?:{_TLD_ALT})\b(?:/[^\s<>"\')]*)?'
)
_URL_RE = re.compile(rf'(?:{_SCHEME_OR_WWW})|(?:{_BARE_DOMAIN})', re.IGNORECASE)

_TRAILING_PUNCT = ".,;:!?"
_CONTEXT_RADIUS = 60


def _extend_trailing_punct(text: str, end: int) -> int:
    """Absorb one sentence-ending punctuation mark right after a stripped
    URL so removal doesn't leave a dangling '. ' or ', ' artifact."""
    if end < len(text) and text[end] in _TRAILING_PUNCT:
        nxt = end + 1
        if nxt >= len(text) or text[nxt].isspace():
            return end + 1
    return end


def strip_urls(text: str, agent_name: str) -> str:
    """Remove every URL / bare domain from ``text``, logging each strip.

    Replacement strategy: delete the matched span (plus one absorbed
    trailing sentence-punctuation mark, see ``_extend_trailing_punct``),
    then collapse any resulting run of spaces/tabs down to one, so the
    surrounding sentence stays readable instead of leaving a hole. This
    is a mid-stream-safe building block — it does not trim leading/
    trailing whitespace, since callers may be filtering one fragment of
    a larger stream. Use ``strip_urls_final`` for complete, final text.
    """
    if not text:
        return text

    pieces: list[str] = []
    last_end = 0
    for m in _URL_RE.finditer(text):
        start, end = m.span()
        if start < last_end:
            continue
        end = _extend_trailing_punct(text, end)
        value = text[start:m.end()]
        ctx_start = max(0, start - _CONTEXT_RADIUS)
        ctx_end = min(len(text), end + _CONTEXT_RADIUS)
        logger.warning(
            "url_filter stripped agent=%s value=%r context=%r",
            agent_name, value, text[ctx_start:ctx_end],
        )
        pieces.append(text[last_end:start])
        last_end = end
    pieces.append(text[last_end:])

    cleaned = "".join(pieces)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned


def strip_urls_final(text: str, agent_name: str) -> str:
    """Like ``strip_urls``, plus trims stray leading/trailing whitespace.

    Use on complete text (a finished agent response, a fully-parsed JSON
    field) rather than on a mid-stream fragment.
    """
    return strip_urls(text, agent_name).strip()


def filter_json_strings(obj, agent_name: str):
    """Recursively apply ``strip_urls_final`` to every string in a parsed
    JSON value (dict / list / str), leaving other types untouched.

    Intended for the ``parsed = json.loads(...)`` dict an agent builds
    from the model's JSON response, before it is returned or handed to
    ``core.upl.apply_disclaimer`` (which adds the product's own links —
    those must never pass back through this filter).
    """
    if isinstance(obj, dict):
        return {k: filter_json_strings(v, agent_name) for k, v in obj.items()}
    if isinstance(obj, list):
        return [filter_json_strings(v, agent_name) for v in obj]
    if isinstance(obj, str):
        return strip_urls_final(obj, agent_name)
    return obj


class StreamingURLFilter:
    """Buffers streamed text so a URL split across two SSE chunks is still
    caught, releasing text only up to the last whitespace boundary seen so
    far. Call ``feed()`` per chunk and ``flush()`` once at stream end.
    """

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self._buffer = ""

    def feed(self, chunk: str) -> str:
        self._buffer += chunk
        last_ws = None
        for i in range(len(self._buffer) - 1, -1, -1):
            if self._buffer[i].isspace():
                last_ws = i
                break
        if last_ws is None:
            return ""
        ready, self._buffer = self._buffer[: last_ws + 1], self._buffer[last_ws + 1 :]
        return strip_urls(ready, self.agent_name)

    def flush(self) -> str:
        remainder, self._buffer = self._buffer, ""
        if not remainder:
            return ""
        return strip_urls(remainder, self.agent_name)
