"""Pydantic content-record models for the P&C Claim Guide content layer
(Dispatch I-2a).

Doctrine: phase content is data, never generated (see
``docs/pc-claim-guide-module.md`` §2, §7). These models are the typed
boundary every seed record must cross before the loader (``content.loader``)
will accept it — no raw dicts past this point.

Two rulings override the spec's original render rules (Joe, 2026-08-20),
enforced here at the schema level:

1. Citations render inline and visible — the spec's collapsed footer /
   section-symbol ban is overruled by Decision 11. ``authority`` is a plain
   list of citation strings with no footer-only framing.
2. ``do_now``/``never_do`` render as conditional pairs (Decision 13 voice):
   the ``why`` (do_now) and ``consequence`` (never_do) fields carry the
   material the renderer needs, so they are REQUIRED, not optional — content
   without them fails validation rather than rendering thin.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class DoNowItem(BaseModel):
    """A single "do now" action. ``why`` is required — it is the material
    the conditional-pair renderer pairs against a corresponding risk."""

    model_config = ConfigDict(extra="forbid")

    id: str
    text: str
    artifact: str | None = None
    why: str
    consequence: str | None = None


class NeverDoItem(BaseModel):
    """A single "never do" warning. ``consequence`` is required — it is the
    material the conditional-pair renderer pairs against the action."""

    model_config = ConfigDict(extra="forbid")

    id: str
    text: str
    consequence: str
    reasonable_inaction: str | None = None


class WatchForItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    signal: str
    escalates_to: str


class ContentRecord(BaseModel):
    """A single versioned phase-content record, per
    ``docs/pc-claim-guide-module.md`` §2."""

    model_config = ConfigDict(extra="forbid")

    phase_id: str
    peril: list[str] = Field(min_length=1)
    jurisdiction: Literal["FL"]
    policy_inception_after: date | Literal["any"]
    sequence: int
    title: str
    plain_summary: str

    entry_trigger: str | None = None
    exit_trigger: str | None = None
    typical_window_days: tuple[int, int] | None = None

    do_now: list[DoNowItem] = Field(default_factory=list)
    never_do: list[NeverDoItem] = Field(default_factory=list)
    watch_for: list[WatchForItem] = Field(default_factory=list)
    documents: list[str] = Field(default_factory=list)
    deadlines: list[str] = Field(default_factory=list)

    authority: list[str] = Field(min_length=1)
    effective_date: date
    version: int | str
    superseded_by: int | str | None = None

    @field_validator("typical_window_days")
    @classmethod
    def _window_is_ordered(cls, value: tuple[int, int] | None) -> tuple[int, int] | None:
        if value is not None and value[0] > value[1]:
            raise ValueError(
                f"typical_window_days must be [min, max] with min <= max, got {value}"
            )
        return value

    @model_validator(mode="after")
    def _authority_strings_nonempty(self) -> "ContentRecord":
        if any(not a.strip() for a in self.authority):
            raise ValueError("authority entries must be non-empty strings")
        return self
