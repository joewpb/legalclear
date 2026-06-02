"""Schema for evidence artifacts and the evidence manifest."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, field_validator


class EvidenceArtifact(BaseModel):
    sha256: str
    filename: str
    size_bytes: int
    content_type: str = "application/octet-stream"
    created_at: datetime
    control_ids: list[str]
    description: str = ""

    @field_validator("sha256")
    @classmethod
    def sha256_format(cls, v: str) -> str:
        if len(v) != 64 or not all(c in "0123456789abcdef" for c in v.lower()):
            raise ValueError(f"sha256 must be a 64-char hex string, got: {v!r}")
        return v.lower()

    @field_validator("control_ids")
    @classmethod
    def control_ids_nonempty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("An evidence artifact must link to at least one control")
        return v


class EvidenceManifest(BaseModel):
    version: str
    generated_at: datetime
    artifacts: dict[str, EvidenceArtifact]  # keyed by sha256

    def artifacts_for_control(self, control_id: str) -> list[EvidenceArtifact]:
        return [a for a in self.artifacts.values() if control_id in a.control_ids]

    def artifact_by_filename(self, filename: str) -> EvidenceArtifact | None:
        for artifact in self.artifacts.values():
            if artifact.filename == filename:
                return artifact
        return None

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")
