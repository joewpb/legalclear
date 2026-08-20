"""Deterministic loader + validator for P&C Claim Guide content records
(Dispatch I-2a).

No LLM anywhere in this module. Loads JSONL seed files from ``content/data/``,
validates each record through ``content.models.ContentRecord`` (pydantic —
raw dicts never cross this boundary), then applies load-time invariants the
type system alone can't express:

- every ``authority`` citation must resolve against the P&C owned corpus
  (``agents.pc_citations.PC_CURATED_CITATIONS``, the same map
  ``core.citation_filter`` unions in for this module) via
  ``core.citation_resolver.resolve_citation`` — an unresolvable citation
  fails the load by name. An unverifiable claim is impossible to store, not
  merely discouraged.
- ``sequence`` is unique per peril within the active set.
- ``phase_id`` + ``version`` pairs are unique (no duplicate version in a
  chain).
- ``superseded_by`` must point at a real version within its own phase_id
  chain.
- the newest version per ``phase_id`` wins; the loader returns only that
  active set.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.agents.pc_citations import PC_CURATED_CITATIONS
from src.content.models import ContentRecord
from src.core.citation_resolver import resolve_citation

_DATA_DIR = Path(__file__).parent / "data"


class ContentLoadError(Exception):
    """Raised when a seed file fails validation. Fails loudly by design —
    there is no partial/best-effort load."""


def _version_sort_key(version: int | str) -> tuple[int, int | str]:
    """Order ints before strings only when mixed (never expected in a real
    chain); within a single type, ordinary ordering applies."""
    return (0, version) if isinstance(version, int) else (1, version)


def _iter_seed_lines(data_dir: Path) -> list[tuple[Path, int, str]]:
    lines: list[tuple[Path, int, str]] = []
    if not data_dir.is_dir():
        return lines
    for path in sorted(data_dir.glob("*.jsonl")):
        for lineno, raw_line in enumerate(path.read_text().splitlines(), start=1):
            stripped = raw_line.strip()
            if not stripped:
                continue
            lines.append((path, lineno, stripped))
    return lines


def _parse_records(data_dir: Path) -> list[ContentRecord]:
    records: list[ContentRecord] = []
    for path, lineno, raw_line in _iter_seed_lines(data_dir):
        try:
            payload = json.loads(raw_line)
        except json.JSONDecodeError as e:
            raise ContentLoadError(f"{path}:{lineno}: invalid JSON: {e}") from e
        try:
            records.append(ContentRecord(**payload))
        except Exception as e:
            raise ContentLoadError(f"{path}:{lineno}: schema validation failed: {e}") from e
    return records


def _validate_authorities(records: list[ContentRecord]) -> None:
    for record in records:
        for citation in record.authority:
            if resolve_citation(citation, PC_CURATED_CITATIONS) is None:
                raise ContentLoadError(
                    f"phase_id={record.phase_id!r} version={record.version!r}: "
                    f"authority {citation!r} does not resolve against the "
                    f"owned P&C citation corpus"
                )


def _validate_version_chains(records: list[ContentRecord]) -> dict[str, list[ContentRecord]]:
    by_phase: dict[str, list[ContentRecord]] = {}
    for record in records:
        by_phase.setdefault(record.phase_id, []).append(record)

    for phase_id, chain in by_phase.items():
        seen_versions: set[int | str] = set()
        for record in chain:
            if record.version in seen_versions:
                raise ContentLoadError(
                    f"phase_id={phase_id!r}: duplicate version {record.version!r} "
                    f"in version chain"
                )
            seen_versions.add(record.version)

        for record in chain:
            if record.superseded_by is not None and record.superseded_by not in seen_versions:
                raise ContentLoadError(
                    f"phase_id={phase_id!r} version={record.version!r}: "
                    f"superseded_by {record.superseded_by!r} does not point at "
                    f"any version in its own chain"
                )

    return by_phase


def _validate_sequence_uniqueness(active: list[ContentRecord]) -> None:
    seen: dict[str, set[int]] = {}
    for record in active:
        for peril in record.peril:
            bucket = seen.setdefault(peril, set())
            if record.sequence in bucket:
                raise ContentLoadError(
                    f"peril={peril!r}: duplicate sequence {record.sequence!r} "
                    f"(phase_id={record.phase_id!r})"
                )
            bucket.add(record.sequence)


def load_active_content(data_dir: Path | str | None = None) -> list[ContentRecord]:
    """Load, validate, and return the active (newest-per-phase_id) content
    set. Raises ``ContentLoadError`` on any invariant violation."""
    directory = Path(data_dir) if data_dir is not None else _DATA_DIR

    records = _parse_records(directory)
    if not records:
        return []

    _validate_authorities(records)
    by_phase = _validate_version_chains(records)

    active = [
        max(chain, key=lambda record: _version_sort_key(record.version))
        for chain in by_phase.values()
    ]

    _validate_sequence_uniqueness(active)

    return active
