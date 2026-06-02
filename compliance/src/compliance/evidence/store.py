"""Evidence artifact storage.

StorageBackend is an abstract interface. Swap implementations via config —
the rest of the compliance framework never imports a concrete class directly.

Implementations:
  LocalFSStorage     — default; stores files in compliance/evidence/artifacts/
                       Files are named by SHA-256 for content-addressing.
  SupabaseStorageStub — placeholder; raises NotImplementedError with instructions.

To switch to Supabase Storage, set LEGALCLEAR_STORAGE_BACKEND=supabase and
provide SUPABASE_URL + SUPABASE_SERVICE_KEY in the environment. The stub
documents the expected interface; a production implementation is a config change,
not a refactor.
"""
from __future__ import annotations

import hashlib
import json
import os
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from compliance.schemas.evidence import EvidenceArtifact


_DEFAULT_ARTIFACTS_DIR = Path(__file__).parent.parent.parent.parent / "evidence" / "artifacts"


class StorageBackend(ABC):
    """Abstract content-addressed artifact store."""

    @abstractmethod
    def put(self, content: bytes, filename: str, control_ids: list[str],
            description: str = "") -> EvidenceArtifact:
        """Store content and return the artifact record. Content is SHA-256 keyed."""

    @abstractmethod
    def get(self, sha256: str) -> bytes:
        """Retrieve artifact bytes by SHA-256."""

    @abstractmethod
    def exists(self, sha256: str) -> bool:
        """Return True if an artifact with this SHA-256 is present."""

    @abstractmethod
    def list_artifacts(self) -> list[EvidenceArtifact]:
        """Return all stored artifact metadata."""

    @abstractmethod
    def delete(self, sha256: str) -> bool:
        """Delete artifact; return True if it existed."""


class LocalFSStorage(StorageBackend):
    """Local filesystem content-addressed artifact store.

    Files stored as: {base_dir}/{sha256[:2]}/{sha256}.{ext}
    Metadata stored as: {base_dir}/{sha256}.meta.json
    """

    def __init__(self, base_dir: Path | str | None = None) -> None:
        self.base_dir = Path(base_dir) if base_dir else _DEFAULT_ARTIFACTS_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _meta_path(self, sha256: str) -> Path:
        return self.base_dir / f"{sha256}.meta.json"

    def _artifact_path(self, sha256: str, ext: str) -> Path:
        return self.base_dir / f"{sha256}.{ext}"

    def put(self, content: bytes, filename: str, control_ids: list[str],
            description: str = "") -> EvidenceArtifact:
        sha256 = hashlib.sha256(content).hexdigest()
        ext = Path(filename).suffix.lstrip(".") or "bin"
        artifact_path = self._artifact_path(sha256, ext)

        if not artifact_path.exists():
            artifact_path.write_bytes(content)

        content_type = _guess_content_type(filename)
        artifact = EvidenceArtifact(
            sha256=sha256,
            filename=filename,
            size_bytes=len(content),
            content_type=content_type,
            created_at=datetime.now(tz=timezone.utc),
            control_ids=control_ids,
            description=description,
        )

        meta_path = self._meta_path(sha256)
        meta_path.write_text(
            json.dumps(artifact.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )
        return artifact

    def get(self, sha256: str) -> bytes:
        for path in self.base_dir.glob(f"{sha256}.*"):
            if path.suffix != ".json":
                return path.read_bytes()
        raise FileNotFoundError(f"Artifact not found: {sha256}")

    def exists(self, sha256: str) -> bool:
        return any(
            True for p in self.base_dir.glob(f"{sha256}.*")
            if p.suffix != ".json"
        )

    def list_artifacts(self) -> list[EvidenceArtifact]:
        artifacts = []
        for meta_path in sorted(self.base_dir.glob("*.meta.json")):
            try:
                data = json.loads(meta_path.read_text(encoding="utf-8"))
                artifacts.append(EvidenceArtifact.model_validate(data))
            except Exception:
                continue
        return artifacts

    def delete(self, sha256: str) -> bool:
        deleted = False
        for path in self.base_dir.glob(f"{sha256}.*"):
            path.unlink()
            deleted = True
        return deleted


class SupabaseStorageStub(StorageBackend):
    """Stub for Supabase Storage backend.

    To implement: set LEGALCLEAR_STORAGE_BACKEND=supabase, provide
    SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables, and
    replace this stub with a real implementation using supabase-py's
    storage client (client.storage.from_("compliance-artifacts")).

    This stub documents the expected interface and fails loudly so the
    absence of an implementation is immediately obvious.
    """

    def __init__(self) -> None:
        raise NotImplementedError(
            "SupabaseStorageStub is a placeholder. "
            "Implement using supabase-py storage client and set "
            "LEGALCLEAR_STORAGE_BACKEND=supabase to enable. "
            "See compliance/src/compliance/evidence/store.py for the interface."
        )

    def put(self, content: bytes, filename: str, control_ids: list[str],
            description: str = "") -> EvidenceArtifact:
        raise NotImplementedError

    def get(self, sha256: str) -> bytes:
        raise NotImplementedError

    def exists(self, sha256: str) -> bool:
        raise NotImplementedError

    def list_artifacts(self) -> list[EvidenceArtifact]:
        raise NotImplementedError

    def delete(self, sha256: str) -> bool:
        raise NotImplementedError


def get_storage_backend() -> StorageBackend:
    """Factory — selects backend via LEGALCLEAR_STORAGE_BACKEND env var.

    Supported values: "local" (default), "supabase" (stub, not yet implemented).
    """
    backend = os.environ.get("LEGALCLEAR_STORAGE_BACKEND", "local").lower()
    if backend == "local":
        custom_dir = os.environ.get("LEGALCLEAR_ARTIFACTS_DIR")
        return LocalFSStorage(base_dir=custom_dir or None)
    if backend == "supabase":
        return SupabaseStorageStub()
    raise ValueError(
        f"Unknown LEGALCLEAR_STORAGE_BACKEND={backend!r}. "
        "Supported: 'local', 'supabase'."
    )


def _guess_content_type(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    return {
        ".json": "application/json",
        ".yaml": "application/yaml",
        ".yml": "application/yaml",
        ".md": "text/markdown",
        ".pdf": "application/pdf",
        ".png": "image/png",
        ".sql": "application/sql",
        ".txt": "text/plain",
        ".html": "text/html",
        ".csv": "text/csv",
    }.get(ext, "application/octet-stream")
