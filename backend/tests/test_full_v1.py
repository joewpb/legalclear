"""Full v1 verification — verbatim from
phases/source/PHASE_23_packet_builder.md.

Runs after Phase 23 passes. Requires:
  - Backend on http://localhost:8001 (Phase 23)
  - Frontend on http://localhost:5173 (vite dev) — Phase 15-22 SPA
"""
import httpx

BACKEND = "http://localhost:8001"
FRONTEND = "http://localhost:5173"


def test_all_tiles_reachable():
    for route in [
        "/",
        "/upload",
        "/small-claims",
        "/expungement",
        "/landlord",
        "/forms",
        "/traffic",
        "/police-report",
        "/case-law",
    ]:
        assert httpx.get(f"{FRONTEND}{route}").status_code == 200


def test_packet_endpoint_works():
    r = httpx.post(
        f"{BACKEND}/api/packet/build",
        json={
            "packet_type": "small_claims",
            "language": "en",
            "county": "Miami-Dade",
            "user_id": "smoke",
            "tile_data": {
                "claim_type": "Other",
                "amount": 100,
                "defendant_type": "Individual",
                "defendant_name": "X",
                "defendant_address": "Y",
            },
        },
        timeout=60.0,
    )
    assert r.status_code == 200, r.text


def test_backend_port():
    assert httpx.get(f"{BACKEND}/health").status_code == 200


def test_no_port_8000_collision():
    try:
        r = httpx.get("http://localhost:8000/health", timeout=2.0)
        if r.status_code == 200:
            assert "legalclear" not in r.text.lower()
    except httpx.RequestError:
        pass


if __name__ == "__main__":
    test_all_tiles_reachable()
    test_packet_endpoint_works()
    test_backend_port()
    test_no_port_8000_collision()
    print("FULL V1 VERIFICATION COMPLETE — all checks passed.")
