"""Report generator — Markdown and PDF compliance manifests.

Each generated report embeds:
  - SHA-256 of controls/registry.yaml (registry integrity)
  - SHA-256 of each cited evidence artifact (from the manifest)
  - Generation timestamp (UTC ISO-8601)
  - Registry version (semver from registry.yaml)

SHA-256 of the report file itself is not embedded (chicken-and-egg problem).
The content-addressed artifact store handles tamper-evidence for evidence files.

Performance: projection + rendering must complete in < 2 seconds for up to
500 controls. Tested in tests/test_reports.py.
"""
from __future__ import annotations

import hashlib
import importlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from jinja2 import Environment, FileSystemLoader, select_autoescape

from compliance.evidence.manifest import ManifestGenerator
from compliance.jurisdictions.base import ProjectedControl, ProjectionBase, ProjectionResult
from compliance.schemas.control import Registry, load_registry
from compliance.schemas.evidence import EvidenceArtifact

try:
    from weasyprint import HTML as _WeasyHTML
    _WEASYPRINT_AVAILABLE = True
except Exception:
    _WEASYPRINT_AVAILABLE = False

_TEMPLATES_DIR = Path(__file__).parent / "templates"
_DEFAULT_OUTPUT_DIR = Path(__file__).parent.parent.parent.parent / "reports" / "output"

_REGISTRY_PATH = Path(__file__).parent.parent.parent.parent / "controls" / "registry.yaml"

_JURISDICTION_MAP: dict[str, str] = {
    "eu_ai_act": "compliance.jurisdictions.eu_ai_act",
    "nist_ai_rmf": "compliance.jurisdictions.nist_ai_rmf",
    "colorado_caia": "compliance.jurisdictions.colorado_caia",
    "california_admt": "compliance.jurisdictions.california_admt",
    "florida_fdbr": "compliance.jurisdictions.florida_fdbr",
}

_PROJECTION_CLASS: dict[str, str] = {
    "eu_ai_act": "EUAIActProjection",
    "nist_ai_rmf": "NISTAIRMFProjection",
    "colorado_caia": "ColoradoCAIAProjection",
    "california_admt": "CaliforniaADMTProjection",
    "florida_fdbr": "FloridaFDBRProjection",
}


def _load_projection(jurisdiction: str) -> ProjectionBase:
    module_path = _JURISDICTION_MAP.get(jurisdiction)
    class_name = _PROJECTION_CLASS.get(jurisdiction)
    if not module_path or not class_name:
        raise ValueError(
            f"Unknown jurisdiction: {jurisdiction!r}. "
            f"Valid: {list(_JURISDICTION_MAP)}"
        )
    module = importlib.import_module(module_path)
    return getattr(module, class_name)()


def _registry_sha256() -> str:
    if _REGISTRY_PATH.exists():
        return hashlib.sha256(_REGISTRY_PATH.read_bytes()).hexdigest()
    return "registry-file-not-found"


class ReportGenerator:
    """Generates Markdown and PDF compliance manifests for any jurisdiction."""

    def __init__(
        self,
        output_dir: Path | None = None,
        manifest_gen: ManifestGenerator | None = None,
    ) -> None:
        self.output_dir = output_dir or _DEFAULT_OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_gen = manifest_gen or ManifestGenerator()
        self._jinja = Environment(
            loader=FileSystemLoader(str(_TEMPLATES_DIR)),
            autoescape=select_autoescape(["html"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def generate(
        self,
        jurisdiction: str,
        fmt: Literal["markdown", "html", "pdf"] = "markdown",
        registry: Registry | None = None,
    ) -> Path:
        """Generate a compliance report for *jurisdiction* in the given format.

        Returns the path to the written report file.
        """
        reg = registry or load_registry()
        projection = _load_projection(jurisdiction)
        result = projection.project(reg)

        context = self._build_context(result, reg)
        return self._render(context, fmt, jurisdiction)

    def generate_string(
        self,
        jurisdiction: str,
        fmt: Literal["markdown", "html"] = "markdown",
        registry: Registry | None = None,
    ) -> str:
        """Return the report content as a string (no file written)."""
        reg = registry or load_registry()
        projection = _load_projection(jurisdiction)
        result = projection.project(reg)
        context = self._build_context(result, reg)
        template_name = "report.html.j2" if fmt == "html" else "report.md.j2"
        return self._jinja.get_template(template_name).render(**context)

    def _build_context(self, result: ProjectionResult, reg: Registry) -> dict:
        manifest = self.manifest_gen.load()
        now = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Enrich each projected control with evidence hashes
        enriched: list[dict] = []
        for ctrl in result.applicable_controls:
            hashes: dict[str, str | None] = {}
            for req in ctrl.evidence_requirements:
                if manifest:
                    artifact = manifest.artifact_by_filename(req)
                    hashes[req] = artifact.sha256 if artifact else None
                else:
                    hashes[req] = None
            d = ctrl.to_dict()
            d["evidence_hashes"] = hashes
            enriched.append(d)

        # Group by category for template rendering
        categories: dict[str, list[dict]] = {}
        for d in enriched:
            categories.setdefault(d["category"], []).append(d)

        # Evidence artifacts relevant to this jurisdiction
        all_control_ids = {c.control_id for c in result.applicable_controls}
        evidence_artifacts: list[EvidenceArtifact] = []
        if manifest:
            for artifact in manifest.artifacts.values():
                if any(cid in all_control_ids for cid in artifact.control_ids):
                    evidence_artifacts.append(artifact)

        return {
            "jurisdiction_key": result.jurisdiction_key,
            "jurisdiction_name": result.jurisdiction_name,
            "registry_version": reg.version,
            "registry_sha256": _registry_sha256(),
            "generated_at": now,
            "total_controls": result.total_controls,
            "applicable_count": result.applicable_count,
            "auto_satisfied_count": result.auto_satisfied_count,
            "independent_verification_count": result.independent_verification_count,
            "controls_by_category": categories,
            "evidence_artifacts": sorted(
                evidence_artifacts, key=lambda a: a.filename
            ),
        }

    def _render(
        self,
        context: dict,
        fmt: Literal["markdown", "html", "pdf"],
        jurisdiction: str,
    ) -> Path:
        timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%S")
        if fmt == "markdown":
            template = self._jinja.get_template("report.md.j2")
            content = template.render(**context)
            out_path = self.output_dir / f"{jurisdiction}_{timestamp}.md"
            out_path.write_text(content, encoding="utf-8")
            return out_path

        if fmt == "html":
            template = self._jinja.get_template("report.html.j2")
            content = template.render(**context)
            out_path = self.output_dir / f"{jurisdiction}_{timestamp}.html"
            out_path.write_text(content, encoding="utf-8")
            return out_path

        if fmt == "pdf":
            if not _WEASYPRINT_AVAILABLE:
                raise RuntimeError(
                    "WeasyPrint is not installed or failed to import. "
                    "Install it with: uv add weasyprint. "
                    "On Ubuntu/Pop OS: apt-get install libpango-1.0-0 libpangoft2-1.0-0"
                )
            html_template = self._jinja.get_template("report.html.j2")
            html_content = html_template.render(**context)
            out_path = self.output_dir / f"{jurisdiction}_{timestamp}.pdf"
            _WeasyHTML(string=html_content).write_pdf(str(out_path))
            return out_path

        raise ValueError(f"Unknown format: {fmt!r}. Valid: markdown, html, pdf")
