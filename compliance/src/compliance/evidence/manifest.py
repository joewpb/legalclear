"""Evidence manifest generator.

Reads all artifacts from the storage backend and produces a structured
manifest mapping artifacts to control IDs. The manifest is the link
between the control registry and the physical evidence.

Content addressing: artifacts are indexed by SHA-256. The manifest
records this hash, which report generators embed in compliance reports
for tamper-evident audit trails.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from compliance.schemas.control import Registry, load_registry
from compliance.schemas.evidence import EvidenceArtifact, EvidenceManifest
from compliance.evidence.store import LocalFSStorage, StorageBackend, get_storage_backend

_DEFAULT_MANIFEST_PATH = (
    Path(__file__).parent.parent.parent.parent / "evidence" / "manifest.json"
)


class ManifestGenerator:
    """Generates and persists the evidence manifest."""

    def __init__(
        self,
        storage: StorageBackend | None = None,
        manifest_path: Path | None = None,
    ) -> None:
        self.storage = storage or get_storage_backend()
        self.manifest_path = manifest_path or _DEFAULT_MANIFEST_PATH

    def generate(self, registry: Registry | None = None) -> EvidenceManifest:
        """Scan the artifact store and produce a manifest.

        The manifest includes only artifacts that can be linked to at least
        one control_id. Orphaned artifacts are ignored but logged.
        """
        reg = registry or load_registry()
        known_control_ids = {ctrl.control_id for ctrl in reg.controls}

        artifacts_dict: dict[str, EvidenceArtifact] = {}
        for artifact in self.storage.list_artifacts():
            valid_ids = [cid for cid in artifact.control_ids if cid in known_control_ids]
            if not valid_ids:
                continue
            # Rebuild with only valid control IDs in case of stale metadata
            cleaned = artifact.model_copy(update={"control_ids": valid_ids})
            artifacts_dict[cleaned.sha256] = cleaned

        return EvidenceManifest(
            version="0.1.0",
            generated_at=datetime.now(tz=timezone.utc),
            artifacts=artifacts_dict,
        )

    def save(self, manifest: EvidenceManifest | None = None) -> Path:
        """Write the manifest to disk. Returns the path written."""
        m = manifest or self.generate()
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        self.manifest_path.write_text(
            json.dumps(m.to_dict(), indent=2, default=str),
            encoding="utf-8",
        )
        return self.manifest_path

    def load(self) -> EvidenceManifest | None:
        """Load manifest from disk. Returns None if not yet generated."""
        if not self.manifest_path.exists():
            return None
        data = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        return EvidenceManifest.model_validate(data)

    def artifact_hashes_for_control(self, control_id: str) -> dict[str, str | None]:
        """Return {filename: sha256_or_None} for each evidence_requirement of the control.

        Used by the report generator to embed tamper-evident hashes.
        None means the artifact has not yet been submitted to the store.
        """
        reg = load_registry()
        ctrl = reg.by_id(control_id)
        if ctrl is None:
            return {}

        manifest = self.load()
        result: dict[str, str | None] = {}
        for req_filename in ctrl.evidence_requirements:
            if manifest:
                artifact = manifest.artifact_by_filename(req_filename)
                result[req_filename] = artifact.sha256 if artifact else None
            else:
                result[req_filename] = None
        return result
