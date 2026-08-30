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


# ---------------------------------------------------------------------------
# Decision 20 ladder — the ONE implementation every LLM-JSON site routes
# through. (1) deterministic repair (free); (2) one LLM retry via the
# caller-supplied retry_call; (3) degrade gracefully with a logged marker.
# Model output gets resilience; legal data keeps its own rigor (S3-5d).
# ---------------------------------------------------------------------------

import inspect
import logging
import typing

_logger = logging.getLogger(__name__)

TIGHTENED_PROMPT_SUFFIX = (
    "\n\nIMPORTANT: Your previous response was not valid JSON. "
    "Respond with ONLY the JSON — no markdown fences, no prose, "
    "no text before or after the JSON."
)

DEGRADE_MARKER = "LLM_PARSE_DEGRADE"


def _parse_any(raw: str) -> object | None:
    """Deterministic parse of an LLM response that may be any JSON value.

    Fence-strip, then ``json.loads``; on failure extract the largest
    ``{...}`` or ``[...]`` substring and retry once. Never raises.
    """
    cleaned = strip_markdown_fences(raw)
    try:
        return json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        pass
    for open_ch, close_ch in (("{", "}"), ("[", "]")):
        start = cleaned.find(open_ch)
        end = cleaned.rfind(close_ch)
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(cleaned[start : end + 1])
            except (json.JSONDecodeError, TypeError):
                pass
    return None


def _ladder_core(
    raw: str,
    *,
    site: str,
    parser: typing.Callable[[str], object | None],
    retry_result: str | None,
) -> tuple[object | None, bool]:
    """The ONE ladder implementation: deterministic repair, then one retry
    parse of a materialized retry result, then degrade with a marker."""
    parsed = parser(raw)
    if parsed is not None:
        return parsed, False
    if retry_result is not None:
        parsed = parser(retry_result)
    if parsed is None:
        _logger.warning(
            "%s site=%s reason=unrecoverable-after-repair%s",
            DEGRADE_MARKER, site,
            "-and-retry" if retry_result is not None else "",
        )
        return None, True
    return parsed, False


def _parser_for(expect: str):
    if expect == "dict":
        return parse_json_dict
    if expect == "list":
        return parse_json_array
    return _parse_any


async def parse_llm_json_ladder(
    raw: str,
    *,
    site: str,
    expect: typing.Literal["any", "dict", "list"] = "any",
    retry_call: typing.Callable[[], typing.Any] | None = None,
) -> tuple[object | None, bool]:
    """Decision 20 ladder for LLM JSON output (async-capable).

    Returns ``(parsed, degraded)``. Steps:

    1. Deterministic repair (free): fence-strip + largest-bracket recovery.
    2. One LLM retry: if repair fails and ``retry_call`` is provided, call it
       once (sites pass a re-call with ``TIGHTENED_PROMPT_SUFFIX``) and parse
       the result deterministically. A returned awaitable is awaited — the
       ladder works for sync and async call sites alike.
    3. Degrade: if both fail, log ``LLM_PARSE_DEGRADE site=<site> reason=...``
       and return ``(None, True)`` — never raise, never fabricate.

    ``expect`` selects the deterministic parser: ``"dict"`` ->
    :func:`parse_json_dict`, ``"list"`` -> :func:`parse_json_array` (empty
    list is a VALID parse), ``"any"`` -> :func:`_parse_any`.
    """
    parser = _parser_for(expect)
    parsed = parser(raw)
    if parsed is not None:
        return parsed, False

    retry_result: str | None = None
    if retry_call is not None:
        try:
            retried = retry_call()
            if inspect.isawaitable(retried):
                retried = await retried
            retry_result = retried
        except Exception as exc:
            _logger.warning(
                "%s site=%s reason=retry-call-failed: %r",
                DEGRADE_MARKER, site, exc,
            )
            return None, True
    return _ladder_core(
        raw, site=site, parser=parser, retry_result=retry_result
    )


def ladder_call_sync(
    call: typing.Callable[[str], str],
    prompt: str,
    *,
    site: str,
    expect: typing.Literal["any", "dict", "list"] = "any",
) -> tuple[object | None, bool]:
    """Sync variant for non-async call sites: call the model once, run the
    ladder; the one retry (only on repair failure) re-calls with
    ``TIGHTENED_PROMPT_SUFFIX`` appended."""
    raw = call(prompt)
    parser = _parser_for(expect)
    if parser(raw) is not None:
        return parser(raw), False
    try:
        retry_result = call(prompt + TIGHTENED_PROMPT_SUFFIX)
    except Exception as exc:
        _logger.warning(
            "%s site=%s reason=retry-call-failed: %r",
            DEGRADE_MARKER, site, exc,
        )
        return None, True
    return _ladder_core(
        raw, site=site, parser=parser, retry_result=retry_result,
    )


async def ladder_call_async(
    call: typing.Callable[[str], typing.Awaitable[str]],
    prompt: str,
    *,
    site: str,
    expect: typing.Literal["any", "dict", "list"] = "any",
) -> tuple[object | None, bool]:
    """Call the model once, then run the Decision 20 ladder; the one retry
    re-calls with ``TIGHTENED_PROMPT_SUFFIX`` appended to the prompt."""
    raw = await call(prompt)
    return await parse_llm_json_ladder(
        raw,
        site=site,
        expect=expect,
        retry_call=lambda: call(prompt + TIGHTENED_PROMPT_SUFFIX),
    )
