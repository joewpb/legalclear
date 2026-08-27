"""Shared helpers for parsing JSON out of LLM responses.

LLMs occasionally wrap JSON in ```json ... ``` markdown fences or trail it
with prose. These helpers normalize that **deterministically** — no LLM,
no invention. Every agent/router that consumes model output should route
through here instead of hand-rolling its own fence-stripper.

Universal rules honored (AGENTS.md §universal):
  - Markdown fences stripped before ``json.loads()``
  - A single JSON-parse retry (recover the largest matching substring)
    before falling back to an empty/None result
"""
from __future__ import annotations

import json


def strip_markdown_fences(raw: str) -> str:
    """Remove optional ```` ``` ```` (optionally ```` ```json ````) fences.

    Safe against a single unclosed fence: returns the inner text rather
    than raising. Always returns a stripped string.
    """
    text = (raw or "").strip()
    if text.startswith("```"):
        parts = text.split("```")
        if len(parts) >= 2:
            text = parts[1].removeprefix("json")
    return text.strip()


def _parse_with_retry(
    raw: str, open_ch: str, close_ch: str
) -> object | None:
    """``json.loads`` after fence-stripping, retrying once by extracting the
    largest ``open_ch``...``close_ch`` substring on failure."""
    cleaned = strip_markdown_fences(raw)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    start = cleaned.find(open_ch)
    end = cleaned.rfind(close_ch)
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError:
            return None
    return None


def parse_json_array(raw: str) -> list | None:
    """Parse an LLM response expected to be a JSON array.

    Element types are preserved (dicts, plain strings) — callers decide how
    to map them. Returns the list on success, ``None`` on any parse failure
    (never raises).
    """
    data = _parse_with_retry(raw, "[", "]")
    return data if isinstance(data, list) else None


def parse_json_list(raw: str) -> list[dict]:
    """Parse an LLM response expected to be a JSON array of objects.

    Returns only the dict elements; non-dict entries are dropped. On any
    parse failure returns ``[]`` (never raises).
    """
    return [d for d in (parse_json_array(raw) or []) if isinstance(d, dict)]


def parse_json_dict(raw: str) -> dict | None:
    """Parse an LLM response expected to be a JSON object.

    Returns the dict on success, ``None`` on any parse failure (never raises).
    """
    data = _parse_with_retry(raw, "{", "}")
    return data if isinstance(data, dict) else None
