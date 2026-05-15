"""Phase 21 verification — copied verbatim from
phases/source/PHASE_21_police_report.md.

Requires:
  - Backend (FastAPI) running on http://localhost:8001

Note: the test sends junk PDF bytes — PyMuPDF will fail to parse them and
the Scanner Agent may have no API key available. The endpoint is built to
fail-soft in both cases (router catches per-file extraction errors;
agent catches all Anthropic / parse errors). It always returns 200 with
a `findings` list (possibly empty).
"""
import httpx
import io

BACKEND = "http://localhost:8001"


def test_analyze_endpoint_accepts_upload():
    fake_pdf = io.BytesIO(b"%PDF-1.4 fake police report content for testing")
    r = httpx.post(
        f"{BACKEND}/api/police-report/analyze",
        files={"files": ("report.pdf", fake_pdf, "application/pdf")},
        timeout=60.0,
    )
    assert r.status_code == 200
    data = r.json()
    assert "findings" in data
    assert isinstance(data["findings"], list)


def test_multi_file_upload():
    f1 = io.BytesIO(b"%PDF-1.4 primary report")
    f2 = io.BytesIO(b"%PDF-1.4 supplementary witness statement")
    r = httpx.post(
        f"{BACKEND}/api/police-report/analyze",
        files=[
            ("files", ("primary.pdf", f1, "application/pdf")),
            ("files", ("witness.pdf", f2, "application/pdf")),
        ],
        timeout=60.0,
    )
    assert r.status_code == 200
    assert r.json()["documents_analyzed"] == 2


def test_finding_structure():
    """If findings are returned, they must have the required shape."""
    fake = io.BytesIO(b"%PDF-1.4 test")
    r = httpx.post(
        f"{BACKEND}/api/police-report/analyze",
        files={"files": ("report.pdf", fake, "application/pdf")},
        timeout=60.0,
    )
    findings = r.json()["findings"]
    if len(findings) > 0:
        required = {
            "category",
            "severity",
            "page_reference",
            "finding",
            "ask_your_attorney_about",
        }
        assert required.issubset(findings[0].keys())
        assert findings[0]["severity"] in {"high", "medium", "low"}


if __name__ == "__main__":
    test_analyze_endpoint_accepts_upload()
    test_multi_file_upload()
    test_finding_structure()
    print("PHASE 21 COMPLETE — all checks passed.")
