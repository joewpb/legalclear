"""LegalClear compliance CLI — `legalclear <command>`.

Commands:
  report    — generate a compliance report for a jurisdiction
  validate  — validate registry.yaml against Pydantic schema
  evidence  — list, submit, or hash evidence artifacts
  project   — print a jurisdiction projection summary

Invoked via: uv run legalclear <command> [options]
"""
from __future__ import annotations

import base64
import json
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console  # type: ignore[import-untyped]
from rich.table import Table  # type: ignore[import-untyped]

app = typer.Typer(
    name="legalclear",
    help="LegalClear AI Governance Compliance Toolkit",
    add_completion=False,
)
console = Console()
err_console = Console(stderr=True)

_VALID_JURISDICTIONS = [
    "eu_ai_act",
    "nist_ai_rmf",
    "colorado_caia",
    "california_admt",
    "florida_fdbr",
]


# ── report ─────────────────────────────────────────────────────────────────────

@app.command()
def report(
    jurisdiction: str = typer.Option(
        ..., "--jurisdiction", "-j",
        help=f"Jurisdiction key. One of: {', '.join(_VALID_JURISDICTIONS)}",
    ),
    fmt: str = typer.Option(
        "markdown", "--format", "-f",
        help="Output format: markdown, html, or pdf",
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o",
        help="Output file path. Default: reports/output/<jurisdiction>_<timestamp>.<ext>",
    ),
) -> None:
    """Generate a compliance report for a jurisdiction.

    Examples:
      legalclear report --jurisdiction=eu_ai_act
      legalclear report --jurisdiction=florida_fdbr --format=pdf --output=report.pdf
    """
    if jurisdiction not in _VALID_JURISDICTIONS:
        err_console.print(
            f"[red]Unknown jurisdiction: {jurisdiction!r}[/red]\n"
            f"Valid: {', '.join(_VALID_JURISDICTIONS)}"
        )
        raise typer.Exit(1)

    if fmt not in ("markdown", "html", "pdf"):
        err_console.print("[red]--format must be one of: markdown, html, pdf[/red]")
        raise typer.Exit(1)

    from compliance.reports.generator import ReportGenerator

    gen = ReportGenerator(output_dir=output.parent if output else None)

    try:
        if output:
            # Use generate_string and write to the specified path
            if fmt == "pdf":
                path = gen.generate(jurisdiction=jurisdiction, fmt="pdf")
                output.write_bytes(path.read_bytes())
                path.unlink()
            else:
                content = gen.generate_string(
                    jurisdiction=jurisdiction,
                    fmt=fmt,  # type: ignore[arg-type]
                )
                output.write_text(content, encoding="utf-8")
                path = output
        else:
            path = gen.generate(jurisdiction=jurisdiction, fmt=fmt)  # type: ignore[arg-type]
    except RuntimeError as exc:
        err_console.print(f"[red]Report generation failed:[/red] {exc}")
        raise typer.Exit(1)

    console.print(f"[green]✓[/green] Report written to: {path}")


# ── validate ───────────────────────────────────────────────────────────────────

@app.command()
def validate() -> None:
    """Validate controls/registry.yaml against the Pydantic schema.

    Exits 0 on success, 1 on validation errors.
    """
    from compliance.schemas.control import reload_registry
    from pydantic import ValidationError

    try:
        registry = reload_registry()
    except FileNotFoundError as exc:
        err_console.print(f"[red]Registry not found:[/red] {exc}")
        raise typer.Exit(1)
    except Exception as exc:
        err_console.print(f"[red]Validation failed:[/red] {exc}")
        raise typer.Exit(1)

    console.print(
        f"[green]✓[/green] Registry valid. "
        f"Version: {registry.version} | Controls: {len(registry.controls)}"
    )

    table = Table(title="Control Summary")
    table.add_column("Category", style="cyan")
    table.add_column("Count", justify="right")
    table.add_column("High-Risk", justify="right")

    categories: dict[str, dict] = {}
    for ctrl in registry.controls:
        cat = categories.setdefault(ctrl.category, {"count": 0, "high": 0})
        cat["count"] += 1
        if ctrl.risk_tier == "high":
            cat["high"] += 1

    for cat, stats in sorted(categories.items()):
        table.add_row(cat, str(stats["count"]), str(stats["high"]))

    console.print(table)


# ── project ────────────────────────────────────────────────────────────────────

@app.command()
def project(
    jurisdiction: str = typer.Option(
        ..., "--jurisdiction", "-j",
        help=f"Jurisdiction key. One of: {', '.join(_VALID_JURISDICTIONS)}",
    ),
) -> None:
    """Print a summary of controls projected for a jurisdiction."""
    if jurisdiction not in _VALID_JURISDICTIONS:
        err_console.print(f"[red]Unknown jurisdiction:[/red] {jurisdiction!r}")
        raise typer.Exit(1)

    from compliance.reports.generator import _load_projection
    from compliance.schemas.control import load_registry

    registry = load_registry()
    proj = _load_projection(jurisdiction)
    result = proj.project(registry)

    console.print(f"\n[bold]{result.jurisdiction_name}[/bold]")
    console.print(f"Registry version: {registry.version}")
    console.print(f"Applicable controls: {result.applicable_count} / {result.total_controls}")
    console.print(f"Auto-satisfied via EU AI Act: {result.auto_satisfied_count}")
    console.print(f"Independent verification required: {result.independent_verification_count}\n")

    table = Table(title=f"Controls — {jurisdiction}")
    table.add_column("ID", style="cyan", width=10)
    table.add_column("Title", width=45)
    table.add_column("Category", width=20)
    table.add_column("Tier", width=8)
    table.add_column("EU Auto", width=8)

    for ctrl in result.applicable_controls:
        table.add_row(
            ctrl.control_id,
            ctrl.title[:44],
            ctrl.category,
            ctrl.risk_tier,
            "[green]✓[/green]" if ctrl.auto_satisfied_by_eu else "[yellow]–[/yellow]",
        )

    console.print(table)


# ── evidence ───────────────────────────────────────────────────────────────────

evidence_app = typer.Typer(help="Manage evidence artifacts.")
app.add_typer(evidence_app, name="evidence")


@evidence_app.command("list")
def evidence_list() -> None:
    """List all evidence artifacts in the store."""
    from compliance.evidence.manifest import ManifestGenerator

    gen = ManifestGenerator()
    manifest = gen.load()
    if manifest is None:
        console.print("[yellow]No manifest found. Run 'legalclear evidence refresh' first.[/yellow]")
        return

    table = Table(title="Evidence Artifacts")
    table.add_column("SHA-256 (16)", style="dim", width=18)
    table.add_column("Filename", width=35)
    table.add_column("Controls", width=30)
    table.add_column("Submitted", width=12)

    for artifact in sorted(manifest.artifacts.values(), key=lambda a: a.filename):
        table.add_row(
            artifact.sha256[:16] + "…",
            artifact.filename,
            ", ".join(artifact.control_ids[:3]) + ("…" if len(artifact.control_ids) > 3 else ""),
            artifact.created_at.strftime("%Y-%m-%d"),
        )

    console.print(table)


@evidence_app.command("submit")
def evidence_submit(
    file: Path = typer.Argument(..., help="Path to the artifact file to submit"),
    control_ids: str = typer.Option(
        ..., "--controls", "-c",
        help="Comma-separated control IDs (e.g. CTRL-001,CTRL-007)",
    ),
    description: str = typer.Option("", "--description", "-d"),
) -> None:
    """Submit an evidence artifact to the store."""
    if not file.exists():
        err_console.print(f"[red]File not found:[/red] {file}")
        raise typer.Exit(1)

    ids = [cid.strip() for cid in control_ids.split(",") if cid.strip()]
    from compliance.evidence.manifest import ManifestGenerator
    from compliance.evidence.store import get_storage_backend

    storage = get_storage_backend()
    content = file.read_bytes()
    artifact = storage.put(
        content=content,
        filename=file.name,
        control_ids=ids,
        description=description,
    )
    ManifestGenerator(storage=storage).save()
    console.print(f"[green]✓[/green] Submitted: {file.name}")
    console.print(f"  SHA-256: {artifact.sha256}")
    console.print(f"  Size: {artifact.size_bytes:,} bytes")
    console.print(f"  Controls: {', '.join(artifact.control_ids)}")


@evidence_app.command("refresh")
def evidence_refresh() -> None:
    """Regenerate the evidence manifest from the artifact store."""
    from compliance.evidence.manifest import ManifestGenerator

    gen = ManifestGenerator()
    manifest = gen.generate()
    path = gen.save(manifest)
    console.print(f"[green]✓[/green] Manifest updated: {path}")
    console.print(f"  Artifacts: {len(manifest.artifacts)}")


# ── entrypoint ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app()
