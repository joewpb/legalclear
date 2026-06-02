"""Pydantic v2 schema for the unified control registry."""
from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, field_validator, model_validator


Category = Literal[
    "data_governance",
    "transparency",
    "human_oversight",
    "risk_management",
    "technical_robustness",
    "record_keeping",
    "accuracy_bias",
    "security",
    "incident_response",
]

RiskTier = Literal["high", "limited", "minimal"]
AutomationStatus = Literal["automated", "semi_automated", "manual"]

_CTRL_ID_RE = re.compile(r"^CTRL-\d{3}$")
_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


class JurisdictionMappings(BaseModel):
    eu_ai_act: list[str] = []
    nist_ai_rmf: list[str] = []
    colorado_caia: list[str] = []
    california_admt: list[str] = []
    florida_fdbr: list[str] = []

    def references_for(self, jurisdiction_key: str) -> list[str]:
        return getattr(self, jurisdiction_key, [])


class Control(BaseModel):
    control_id: str
    title: str
    description: str
    category: Category
    risk_tier: RiskTier
    jurisdiction_mappings: JurisdictionMappings
    evidence_requirements: list[str]
    automation_status: AutomationStatus
    owner_role: str

    @field_validator("control_id")
    @classmethod
    def control_id_format(cls, v: str) -> str:
        if not _CTRL_ID_RE.match(v):
            raise ValueError(f"control_id must match CTRL-NNN, got: {v!r}")
        return v

    @field_validator("evidence_requirements")
    @classmethod
    def evidence_nonempty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("evidence_requirements must contain at least one artifact")
        return v

    @model_validator(mode="after")
    def high_risk_needs_eu_mapping(self) -> "Control":
        if (
            self.risk_tier == "high"
            and not self.jurisdiction_mappings.eu_ai_act
        ):
            raise ValueError(
                f"{self.control_id}: high-risk controls must have at least one "
                "eu_ai_act jurisdiction mapping"
            )
        return self


class Registry(BaseModel):
    version: str
    generated: str
    controls: list[Control]

    @field_validator("version")
    @classmethod
    def version_is_semver(cls, v: str) -> str:
        if not _SEMVER_RE.match(v):
            raise ValueError(f"version must be semver (X.Y.Z), got: {v!r}")
        return v

    @field_validator("controls")
    @classmethod
    def control_ids_unique(cls, v: list[Control]) -> list[Control]:
        seen: set[str] = set()
        for ctrl in v:
            if ctrl.control_id in seen:
                raise ValueError(f"Duplicate control_id: {ctrl.control_id}")
            seen.add(ctrl.control_id)
        return v

    def by_id(self, control_id: str) -> Control | None:
        for ctrl in self.controls:
            if ctrl.control_id == control_id:
                return ctrl
        return None

    def by_category(self, category: Category) -> list[Control]:
        return [c for c in self.controls if c.category == category]


def _find_registry_path() -> Path:
    env = os.environ.get("LEGALCLEAR_REGISTRY_PATH")
    if env:
        p = Path(env)
        if p.exists():
            return p
        raise FileNotFoundError(f"LEGALCLEAR_REGISTRY_PATH={env!r} does not exist")

    # src/compliance/schemas/control.py → up 4 → project root → controls/registry.yaml
    candidate = Path(__file__).parent.parent.parent.parent / "controls" / "registry.yaml"
    if candidate.exists():
        return candidate
    raise FileNotFoundError(
        "Cannot locate controls/registry.yaml. "
        "Set LEGALCLEAR_REGISTRY_PATH environment variable to override."
    )


@lru_cache(maxsize=1)
def load_registry() -> Registry:
    path = _find_registry_path()
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return Registry.model_validate(data)


def reload_registry() -> Registry:
    """Force reload — clears the cache. Used in tests and after registry edits."""
    load_registry.cache_clear()
    return load_registry()
