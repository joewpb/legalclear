"""Tests: report generation correctness and performance.

Coverage:
  - All 5 jurisdictions generate valid Markdown reports
  - Reports embed registry SHA-256
  - Reports include generation timestamp
  - Reports include registry version
  - Missing evidence is surfaced (MISSING marker)
  - Performance: 500 controls → Markdown report < 2 seconds
  - HTML generation produces valid HTML structure
"""
from __future__ import annotations

import re
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from compliance.reports.generator import ReportGenerator
from compliance.schemas.control import Registry, reload_registry, Registry


_JURISDICTIONS = [
    "eu_ai_act",
    "nist_ai_rmf",
    "colorado_caia",
    "california_admt",
    "florida_fdbr",
]


@pytest.fixture(scope="module")
def registry() -> Registry:
    return reload_registry()


@pytest.fixture(scope="module")
def generator(tmp_path_factory: pytest.TempPathFactory) -> ReportGenerator:
    out = tmp_path_factory.mktemp("reports")
    return ReportGenerator(output_dir=out)


@pytest.mark.parametrize("jurisdiction", _JURISDICTIONS)
def test_report_generates_without_error(
    jurisdiction: str, generator: ReportGenerator
) -> None:
    content = generator.generate_string(jurisdiction=jurisdiction, fmt="markdown")
    assert isinstance(content, str)
    assert len(content) > 100


@pytest.mark.parametrize("jurisdiction", _JURISDICTIONS)
def test_report_contains_registry_sha256(
    jurisdiction: str, generator: ReportGenerator
) -> None:
    content = generator.generate_string(jurisdiction=jurisdiction, fmt="markdown")
    # SHA-256 is a 64-char hex string
    sha_pattern = re.compile(r"[0-9a-f]{64}")
    assert sha_pattern.search(content), (
        f"Report for {jurisdiction} does not contain a SHA-256 hash"
    )


@pytest.mark.parametrize("jurisdiction", _JURISDICTIONS)
def test_report_contains_registry_version(
    jurisdiction: str, generator: ReportGenerator, registry: Registry
) -> None:
    content = generator.generate_string(jurisdiction=jurisdiction, fmt="markdown")
    assert registry.version in content, (
        f"Report for {jurisdiction} does not contain registry version {registry.version}"
    )


@pytest.mark.parametrize("jurisdiction", _JURISDICTIONS)
def test_report_contains_timestamp(
    jurisdiction: str, generator: ReportGenerator
) -> None:
    content = generator.generate_string(jurisdiction=jurisdiction, fmt="markdown")
    # ISO-8601 timestamp format YYYY-MM-DDTHH:MM:SSZ
    ts_pattern = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
    assert ts_pattern.search(content), (
        f"Report for {jurisdiction} does not contain ISO-8601 timestamp"
    )


@pytest.mark.parametrize("jurisdiction", _JURISDICTIONS)
def test_report_contains_jurisdiction_name(
    jurisdiction: str, generator: ReportGenerator
) -> None:
    content = generator.generate_string(jurisdiction=jurisdiction, fmt="markdown")
    from compliance.reports.generator import _load_projection
    proj = _load_projection(jurisdiction)
    # At minimum the jurisdiction key should appear
    assert jurisdiction in content or proj.jurisdiction_name[:20] in content


def test_report_surfaces_missing_evidence(
    generator: ReportGenerator,
) -> None:
    """When no manifest exists, all evidence_requirements show as MISSING."""
    with patch.object(generator.manifest_gen, "load", return_value=None):
        content = generator.generate_string(
            jurisdiction="eu_ai_act", fmt="markdown"
        )
    assert "MISSING" in content, (
        "Report should surface MISSING for controls with no evidence artifacts"
    )


def test_html_report_contains_doctype(generator: ReportGenerator) -> None:
    content = generator.generate_string(jurisdiction="florida_fdbr", fmt="html")
    assert "<!DOCTYPE html>" in content or "<html" in content


def test_html_report_contains_control_blocks(generator: ReportGenerator) -> None:
    content = generator.generate_string(jurisdiction="florida_fdbr", fmt="html")
    assert "ctrl-block" in content or "CTRL-" in content


def test_report_written_to_file(
    generator: ReportGenerator,
) -> None:
    path = generator.generate(jurisdiction="eu_ai_act", fmt="markdown")
    assert path.exists()
    assert path.stat().st_size > 0
    assert path.suffix == ".md"


# ── Performance ────────────────────────────────────────────────────────────────

def _make_large_registry(base_registry: Registry, n: int) -> Registry:
    """Clone controls to reach n total, with unique CTRL-IDs."""
    from compliance.schemas.control import Control
    import copy

    controls = list(base_registry.controls)
    base_count = len(controls)
    extra = []
    for i in range(n - base_count):
        src = controls[i % base_count]
        new_id = f"CTRL-{(i + base_count + 1):03d}"
        clone = src.model_copy(update={"control_id": new_id})
        extra.append(clone)
    return base_registry.model_copy(update={"controls": controls + extra})


def test_performance_500_controls_under_2_seconds(
    generator: ReportGenerator, registry: Registry
) -> None:
    """Projection + Markdown report for 500 controls must complete in < 2 seconds."""
    large = _make_large_registry(registry, 500)

    start = time.perf_counter()
    _ = generator.generate_string(
        jurisdiction="eu_ai_act",
        fmt="markdown",
        registry=large,
    )
    elapsed = time.perf_counter() - start

    assert elapsed < 2.0, (
        f"Report generation for 500 controls took {elapsed:.2f}s (limit: 2.0s)"
    )


def test_performance_all_jurisdictions_500_controls(
    generator: ReportGenerator, registry: Registry
) -> None:
    """All 5 jurisdiction projections + reports for 500 controls < 10 seconds total."""
    large = _make_large_registry(registry, 500)

    start = time.perf_counter()
    for j in _JURISDICTIONS:
        generator.generate_string(jurisdiction=j, fmt="markdown", registry=large)
    elapsed = time.perf_counter() - start

    assert elapsed < 10.0, (
        f"All 5 jurisdiction reports for 500 controls took {elapsed:.2f}s (limit: 10.0s)"
    )
