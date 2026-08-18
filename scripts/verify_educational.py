#!/usr/bin/env python3
"""verify_educational.py — Educational-framing baseline checker (Decision 11).

Static checks that user-facing outputs obey the educational-framing standard.
BASELINE MODE: reports every violation grouped by check, exits 1 when any
violation exists. NOT yet a required CI check — will be red until the G1
presentation slice lands. When green, wire alongside verify-docs and parity.

Checks:
  1. Every response schema returning a computed legal result carries a
     populated citation field.
  2. Every computed deadline carries a non-empty reasoning trace.
  3. No user-facing string or agent output contains a URL or bare domain
     (explicit allowlist with reasons).
  4. Exactly one canonical disclaimer source, imported by every user-facing
     path.

Usage: python3 scripts/verify_educational.py   (from repo root)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend" / "src"
BACKEND = ROOT / "backend" / "src"

violations: dict[str, list[str]] = {f"check{i}": [] for i in range(1, 5)}
notes: list[str] = []


def add(check: str, msg: str) -> None:
    violations[f"check{check}"].append(msg)


# ─────────────────────────────────────────────────────────────────────────────
# CHECK 1 — computed legal results carry a citation field
# ─────────────────────────────────────────────────────────────────────────────
CITATION_EXPECTATIONS = [
    # (file, [required substrings], label)
    ("backend/src/api/routers/deadline.py", ["governing_rule"], "deadline rows"),
    ("backend/src/api/routers/case_law.py", ["citation", "case_name"], "case-law results"),
    ("backend/src/api/routers/expungement.py", ["applicable_statute"], "eligibility result"),
    ("backend/src/agents/property_casualty.py", ["governing_rule"], "key_deadlines (P&C agent)"),
    ("backend/src/api/routers/forms.py", ["form_number"], "form catalog (form number = official identifier)"),
]
for path, needles, label in CITATION_EXPECTATIONS:
    f = ROOT / path
    if not f.exists():
        add(1, f"{path}: MISSING FILE")
        continue
    text = f.read_text()
    for n in needles:
        if n not in text:
            add(1, f"{path}: no '{n}' field for {label}")

# Prose explainer surfaces — must at least carry a disclaimer field; a citation
# field is absent on all of them today (expected baseline red).
PROSE_SURFACES = [
    ("backend/src/api/routers/criminal.py", "criminal explainer"),
    ("backend/src/api/routers/discovery.py", "discovery analyzer"),
    ("backend/src/api/routers/wills_trusts.py", "wills/trusts explainer"),
    ("backend/src/api/routers/small_claims.py", "small-claims explainer"),
    ("backend/src/api/routers/chat.py", "chat expert"),
]
for path, label in PROSE_SURFACES:
    f = ROOT / path
    if not f.exists():
        add(1, f"{path}: MISSING FILE")
        continue
    text = f.read_text()
    if "disclaimer" not in text:
        add(1, f"{path}: {label} carries no disclaimer field")
    if "citation" not in text and "governing_rule" not in text and "statute" not in text:
        add(1, f"{path}: {label} carries no citation field (prose explainer)")

# ─────────────────────────────────────────────────────────────────────────────
# CHECK 2 — every computed deadline carries a non-empty reasoning trace
# ─────────────────────────────────────────────────────────────────────────────
deadline_router = ROOT / "backend/src/api/routers/deadline.py"
compute = ROOT / "backend/deadline/compute.py"
if deadline_router.exists() and "computation_trace" not in deadline_router.read_text():
    add(2, "backend/src/api/routers/deadline.py: computation_trace not serialized")
if compute.exists():
    ctext = compute.read_text()
    if "computation_trace" not in ctext:
        add(2, "backend/deadline/compute.py: ComputedDeadline carries no computation_trace")
    if "_t(" not in ctext:
        add(2, "backend/deadline/compute.py: no trace-step builder (_t) found")
# The non-empty guarantee is enforced by tests:
trace_tests = [p for p in (ROOT / "backend/tests").rglob("test_*.py")
               if "computation_trace" in p.read_text()]
if not trace_tests:
    add(2, "no test asserts computation_trace contents")

# ─────────────────────────────────────────────────────────────────────────────
# CHECK 3 — no URLs / bare domains in user-facing strings or agent output
# ─────────────────────────────────────────────────────────────────────────────
URL_RE = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)
DOMAIN_RE = re.compile(r"\b[a-z0-9\-]+\.(?:com|org|gov|net|app|io|law)\b", re.IGNORECASE)

# Allowed domains with reasons. Government filing portals and legal-aid
# application sites are deliberate external links (Joe's no-external-links
# rule has these as the standing exceptions).
ALLOWED_DOMAINS: dict[str, str] = {
    "flcourts.gov": "official Florida courts portal — sanctioned external link",
    "myflcourtaccess.com": "official Florida court e-filing portal — sanctioned",
    "flhsmv.gov": "official FLHSMV portal — sanctioned",
    "flclerks.com": "official FL clerks association portal — sanctioned",
    "supabase.co": "infrastructure backend origin (API base URL), not user-facing content",
    "railway.app": "infrastructure deploy origin (API base URL), not user-facing content",
    "floridalawhelp.org": "legal-aid finder org application site — sanctioned",
}
# Infrastructure endpoints appearing in BACKEND API/config code — not
# user-facing strings. Recorded as notes, not violations.
INFRA_DOMAINS = {
    "anthropic.com": "LLM API endpoint",
    "resend.com": "email provider API endpoint",
    "exp.host": "Expo push API endpoint (legacy push_tokens path)",
    "courtlistener.com": "CourtListener REST fallback (off by default)",
    "legalclear.app": "our own (dead) frontend origin in config/CORS",
    "localhost": "dev API base in comments",
    "example.com": "form placeholder sample email",
}
INFRA_MARKERS = ("supabase.co", "railway.app", "localhost")
# Files whose domain/URL mentions are the filter itself, not output.
URL_SELF_ALLOWLIST = {
    "backend/src/core/url_filter.py": "the URL-stripping filter itself",
    "frontend/src/pages/FindLegalHelpFL.tsx": "legal-aid org application sites — sanctioned by the no-external-links exception",
}

SCAN_GLOBS = [
    ("frontend/src/**/*.jsx", "frontend"),
    ("frontend/src/**/*.tsx", "frontend"),
    ("backend/src/**/*.py", "backend"),
]


def _contains_any(text: str, needles: tuple[str, ...]) -> str | None:
    for n in needles:
        if n in text:
            return n
    return None


for glob, _label in SCAN_GLOBS:
    for path in sorted(Path(ROOT).glob(glob)):
        try:
            text = path.read_text()
        except Exception:
            continue
        rel = str(path.relative_to(ROOT))
        if rel in URL_SELF_ALLOWLIST:
            continue
        for m in URL_RE.finditer(text):
            url = m.group(0).rstrip(".,);")
            domain = re.search(r"https?://([\w.\-]+)", url)
            dom = domain.group(1) if domain else url
            if _contains_any(dom, tuple(ALLOWED_DOMAINS)):
                continue
            if _contains_any(dom, tuple(INFRA_DOMAINS)):
                needle = _contains_any(dom, tuple(INFRA_DOMAINS))
                notes.append(f"{rel}: infra endpoint ({INFRA_DOMAINS[needle]})")
                continue
            add(3, f"{rel}:{text[:m.start()].count(chr(10)) + 1}: URL '{url}'")
        for m in DOMAIN_RE.finditer(text):
            dom = m.group(0).lower()
            if dom in ALLOWED_DOMAINS:
                continue
            line = text[:m.start()].count("\n") + 1
            context = text.splitlines()[line - 1].strip()
            if dom in INFRA_DOMAINS:
                notes.append(f"{rel}:{line}: infra endpoint ({INFRA_DOMAINS[dom]})")
                continue
            if context.startswith(("from ", "import ")):
                notes.append(f"{rel}:{line}: module path, not a domain — {context[:60]}")
                continue
            if any(inf in context for inf in INFRA_MARKERS):
                notes.append(f"{rel}:{line}: infra URL context (note) — {context[:80]}")
                continue
            add(3, f"{rel}:{line}: bare domain '{dom}' — {context[:80]}")

# ─────────────────────────────────────────────────────────────────────────────
# CHECK 4 — exactly one canonical disclaimer source
# ─────────────────────────────────────────────────────────────────────────────
upl = ROOT / "backend/src/core/upl.py"
if not upl.exists():
    add(4, "backend/src/core/upl.py MISSING — no canonical disclaimer source")
else:
    utext = upl.read_text()
    if utext.count("def apply_disclaimer") != 1:
        add(4, f"core/upl.py: apply_disclaimer defined {utext.count('def apply_disclaimer')} times (want 1)")
    if "DISCLAIMER_VERSION" not in utext:
        add(4, "core/upl.py: no DISCLAIMER_VERSION marker")

    # every streaming/prose agent must import the canonical disclaimer
    agent_files = sorted((ROOT / "backend/src/agents").glob("*.py"))
    exempt_agents = {
        "scanner.py": "legacy v1 scanner — deprecated for police-report v2 path",
        "classifier.py": "deterministic-adjacent classifier, no prose output",
        "__init__.py": "package marker, not an agent",
        "case_context.py": "deterministic context builder, no prose output",
    }
    for af in agent_files:
        rel = f"backend/src/agents/{af.name}"
        if af.name in exempt_agents:
            continue
        atext = af.read_text()
        if "apply_disclaimer" not in atext and "disclaimer" not in atext.lower():
            add(4, f"{rel}: agent emits prose but references no canonical disclaimer")
    # routers that emit prose must import the canonical source
    prose_routers = ["criminal.py", "discovery.py", "wills_trusts.py",
                     "small_claims.py", "property_casualty.py", "police_report.py",
                     "chat.py", "attorney_referral.py"]
    for name in prose_routers:
        rf = ROOT / "backend/src/api/routers" / name
        if not rf.exists():
            continue
        rtext = rf.read_text()
        if "core.upl" not in rtext and "apply_disclaimer" not in rtext:
            add(4, f"backend/src/api/routers/{name}: prose router does not use canonical disclaimer")

    # frontend hardcoded disclaimers = duplicates of the canonical source
    for glob, _label in [("frontend/src/**/*.jsx", "f"), ("frontend/src/**/*.tsx", "f")]:
        for path in sorted(Path(ROOT).glob(glob)):
            try:
                text = path.read_text()
            except Exception:
                continue
            rel = str(path.relative_to(ROOT))
            for m in re.finditer(r"(LegalClear provides informational tools only|is not legal advice|not legal advice)", text, re.IGNORECASE):
                line = text[:m.start()].count("\n") + 1
                add(4, f"{rel}:{line}: frontend hardcodes a disclaimer string (duplicate of canonical)")

# ─────────────────────────────────────────────────────────────────────────────
# REPORT
# ─────────────────────────────────────────────────────────────────────────────
total = 0
for i in range(1, 5):
    vs = violations[f"check{i}"]
    total += len(vs)
    print(f"\n=== CHECK {i} — {len(vs)} violation(s) ===")
    for v in sorted(vs):
        print(f"  {v}")
print(f"\n=== NOTES ({len(notes)}) ===")
for n in notes:
    print(f"  {n}")
print(f"\nBASELINE: {total} violation(s) across 4 checks.")
sys.exit(1 if total else 0)
