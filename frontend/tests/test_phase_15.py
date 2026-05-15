"""Phase 15 verification — copied verbatim from
phases/source/PHASE_15_hub_restructure.md.

Requires:
  - Vite dev server running on http://localhost:5173
  - Backend (FastAPI) running on http://localhost:8001
"""
import httpx

BASE = "http://localhost:5173"  # Vite dev port


def test_home_loads():
    r = httpx.get(f"{BASE}/")
    assert r.status_code == 200
    html = r.text.lower()
    for title in ["i have a document", "small claims", "expungement",
                  "landlord", "court forms", "traffic", "police report", "case law"]:
        assert title in html, f"Missing tile: {title}"


def test_upload_route_exists():
    r = httpx.get(f"{BASE}/upload")
    assert r.status_code == 200


def test_brutalist_loaded():
    """Check brutalist tokens reach the page."""
    r = httpx.get(f"{BASE}/")
    text = r.text.lower()
    # At least one Brutalist token should appear in the served HTML/CSS bundle reference
    assert "brutalist" in text or "0a0a0a" in text or "var(--bg)" in text


def test_existing_upload_endpoint_unchanged():
    """Backend /api/upload still responds."""
    r = httpx.get("http://localhost:8001/health")
    assert r.status_code == 200


if __name__ == "__main__":
    test_home_loads()
    test_upload_route_exists()
    test_brutalist_loaded()
    test_existing_upload_endpoint_unchanged()
    print("PHASE 15 COMPLETE — all checks passed.")
