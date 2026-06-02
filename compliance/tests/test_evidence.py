"""Tests: evidence artifact storage and manifest linking.

Coverage:
  - LocalFSStorage stores and retrieves content by SHA-256
  - Content addressing: same content → same SHA-256
  - Different content → different SHA-256
  - Manifest generation links artifacts to control IDs
  - artifact_hashes_for_control returns correct hashes
  - Orphaned artifacts (no valid control_ids) excluded from manifest
  - artifact_by_filename lookup
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from compliance.evidence.store import LocalFSStorage
from compliance.evidence.manifest import ManifestGenerator
from compliance.schemas.control import reload_registry


@pytest.fixture()
def storage(tmp_path: Path) -> LocalFSStorage:
    return LocalFSStorage(base_dir=tmp_path / "artifacts")


@pytest.fixture()
def manifest_gen(tmp_path: Path, storage: LocalFSStorage) -> ManifestGenerator:
    return ManifestGenerator(
        storage=storage,
        manifest_path=tmp_path / "manifest.json",
    )


# ── Storage backend ────────────────────────────────────────────────────────────

def test_put_returns_artifact(storage: LocalFSStorage) -> None:
    content = b"test content"
    artifact = storage.put(content, "test.md", ["CTRL-001"])
    assert artifact.sha256 == hashlib.sha256(content).hexdigest()
    assert artifact.filename == "test.md"
    assert artifact.size_bytes == len(content)
    assert "CTRL-001" in artifact.control_ids


def test_content_addressing_same_content(storage: LocalFSStorage) -> None:
    """Same content always produces same SHA-256 regardless of filename."""
    content = b"deterministic content"
    a1 = storage.put(content, "file_a.md", ["CTRL-001"])
    a2 = storage.put(content, "file_b.md", ["CTRL-002"])
    assert a1.sha256 == a2.sha256


def test_content_addressing_different_content(storage: LocalFSStorage) -> None:
    """Different content produces different SHA-256."""
    a1 = storage.put(b"content one", "one.md", ["CTRL-001"])
    a2 = storage.put(b"content two", "two.md", ["CTRL-001"])
    assert a1.sha256 != a2.sha256


def test_exists_after_put(storage: LocalFSStorage) -> None:
    content = b"check exists"
    artifact = storage.put(content, "check.md", ["CTRL-001"])
    assert storage.exists(artifact.sha256)


def test_not_exists_before_put(storage: LocalFSStorage) -> None:
    assert not storage.exists("a" * 64)


def test_get_returns_content(storage: LocalFSStorage) -> None:
    content = b"retrieve me"
    artifact = storage.put(content, "retrieve.md", ["CTRL-001"])
    retrieved = storage.get(artifact.sha256)
    assert retrieved == content


def test_get_missing_raises(storage: LocalFSStorage) -> None:
    with pytest.raises(FileNotFoundError):
        storage.get("b" * 64)


def test_list_artifacts_empty(storage: LocalFSStorage) -> None:
    assert storage.list_artifacts() == []


def test_list_artifacts_after_put(storage: LocalFSStorage) -> None:
    storage.put(b"artifact 1", "a1.md", ["CTRL-001"])
    storage.put(b"artifact 2", "a2.json", ["CTRL-002"])
    artifacts = storage.list_artifacts()
    assert len(artifacts) == 2


def test_delete_artifact(storage: LocalFSStorage) -> None:
    artifact = storage.put(b"delete me", "delete.md", ["CTRL-001"])
    assert storage.exists(artifact.sha256)
    deleted = storage.delete(artifact.sha256)
    assert deleted is True
    assert not storage.exists(artifact.sha256)


def test_delete_nonexistent(storage: LocalFSStorage) -> None:
    assert storage.delete("c" * 64) is False


def test_sha256_field_validated(storage: LocalFSStorage) -> None:
    from pydantic import ValidationError
    from compliance.schemas.evidence import EvidenceArtifact

    with pytest.raises(ValidationError):
        EvidenceArtifact(
            sha256="not-a-valid-sha256",
            filename="test.md",
            size_bytes=10,
            created_at=datetime.now(tz=timezone.utc),
            control_ids=["CTRL-001"],
        )


def test_artifact_requires_control_id(storage: LocalFSStorage) -> None:
    from pydantic import ValidationError
    from compliance.schemas.evidence import EvidenceArtifact

    with pytest.raises(ValidationError):
        EvidenceArtifact(
            sha256="a" * 64,
            filename="test.md",
            size_bytes=10,
            created_at=datetime.now(tz=timezone.utc),
            control_ids=[],  # must not be empty
        )


# ── Manifest generator ─────────────────────────────────────────────────────────

def test_manifest_generate_empty(manifest_gen: ManifestGenerator) -> None:
    registry = reload_registry()
    manifest = manifest_gen.generate(registry)
    assert manifest.artifacts == {}


def test_manifest_includes_artifact(
    manifest_gen: ManifestGenerator, storage: LocalFSStorage
) -> None:
    registry = reload_registry()
    storage.put(b"evidence content", "model_card.md", ["CTRL-001"])

    manifest = manifest_gen.generate(registry)
    filenames = [a.filename for a in manifest.artifacts.values()]
    assert "model_card.md" in filenames


def test_manifest_excludes_orphaned_artifacts(
    manifest_gen: ManifestGenerator, storage: LocalFSStorage
) -> None:
    """Artifacts linked to non-existent control IDs are excluded from manifest."""
    registry = reload_registry()
    storage.put(b"orphan", "orphan.md", ["CTRL-999"])  # non-existent control

    manifest = manifest_gen.generate(registry)
    filenames = [a.filename for a in manifest.artifacts.values()]
    assert "orphan.md" not in filenames


def test_manifest_save_and_load(
    manifest_gen: ManifestGenerator, storage: LocalFSStorage
) -> None:
    registry = reload_registry()
    storage.put(b"saved artifact", "risk_assessment_v1.md", ["CTRL-019"])

    manifest = manifest_gen.generate(registry)
    path = manifest_gen.save(manifest)

    assert path.exists()
    loaded = manifest_gen.load()
    assert loaded is not None
    assert len(loaded.artifacts) == len(manifest.artifacts)


def test_manifest_load_returns_none_when_missing(
    manifest_gen: ManifestGenerator,
) -> None:
    assert manifest_gen.load() is None


def test_artifact_hashes_for_control_missing(
    manifest_gen: ManifestGenerator,
) -> None:
    """Returns None for each requirement when artifact not yet submitted."""
    hashes = manifest_gen.artifact_hashes_for_control("CTRL-001")
    assert isinstance(hashes, dict)
    assert all(v is None for v in hashes.values())


def test_artifact_hashes_for_control_present(
    manifest_gen: ManifestGenerator, storage: LocalFSStorage
) -> None:
    registry = reload_registry()
    ctrl = registry.by_id("CTRL-001")
    assert ctrl is not None

    # Submit the first evidence requirement
    first_req = ctrl.evidence_requirements[0]
    artifact = storage.put(b"ctrl001 evidence", first_req, ["CTRL-001"])
    manifest_gen.save(manifest_gen.generate(registry))

    hashes = manifest_gen.artifact_hashes_for_control("CTRL-001")
    assert hashes[first_req] == artifact.sha256


def test_artifact_by_filename(
    manifest_gen: ManifestGenerator, storage: LocalFSStorage
) -> None:
    registry = reload_registry()
    storage.put(b"findable", "model_card.md", ["CTRL-006", "CTRL-013"])
    manifest = manifest_gen.generate(registry)

    artifact = manifest.artifact_by_filename("model_card.md")
    assert artifact is not None
    assert "CTRL-006" in artifact.control_ids


def test_artifacts_for_control(
    manifest_gen: ManifestGenerator, storage: LocalFSStorage
) -> None:
    registry = reload_registry()
    storage.put(b"content A", "training_data_card.md", ["CTRL-001"])
    storage.put(b"content B", "validation_dataset_manifest.json", ["CTRL-001"])
    manifest = manifest_gen.generate(registry)

    artifacts = manifest.artifacts_for_control("CTRL-001")
    filenames = {a.filename for a in artifacts}
    assert "training_data_card.md" in filenames
    assert "validation_dataset_manifest.json" in filenames
