import sys, os, asyncio
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.config import settings
from src.core.disclaimer import get_disclaimer
from src.core.escalation import EscalationRouter
from src.core.i18n import get_lang
from src.core.notifications import NotificationService


def test():
    assert hasattr(settings, "is_development")
    assert settings.BACKEND_PORT == 8001, (
        f"Port must be 8001, got {settings.BACKEND_PORT}")
    print(f"1. Config OK — port: {settings.BACKEND_PORT}")

    d = get_disclaimer("es", "criminal")
    assert "defensor" in d.lower()
    print("2. ES criminal disclaimer OK")

    d = get_disclaimer("en", "plea")
    assert "plea" in d.lower()
    print("3. EN plea disclaimer OK")

    router = EscalationRouter()
    r = router.route(
        {"document_category": "plea_agreement",
         "jurisdiction_name": "Florida"}, "es")
    assert r["escalation_color"] == "red"
    assert r["pre_analysis_warning"] is not None
    assert r["show_public_defender_info"] == True
    print("4. Escalation plea=red OK")

    r2 = router.route(
        {"document_category": "contract",
         "jurisdiction_name": "unknown"}, "en")
    assert r2["escalation_color"] == "green"
    print("5. Escalation contract=green OK")

    assert get_lang("en", "es") == "es"
    assert get_lang("es", None) == "es"
    assert get_lang("unknown", None) == "en"
    print("6. get_lang OK")

    async def _notify():
        n = NotificationService()
        r = await n.send("user_1", "Test", "Hello")
        assert r["sent"] == True
        assert r["method"] == "log"
        print("7. Notification log OK")

    asyncio.run(_notify())
    print("\nALL PHASE 2 ASSERTIONS PASSED")


test()
