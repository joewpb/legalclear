from src.core.config import settings


def check_access(user: dict,
                 session: dict | None = None) -> dict:
    # Master switch: when payments are off, every feature is free.
    if not settings.PAYMENTS_ENABLED:
        return {
            "allowed": True,
            "reason": "Payments disabled — features free",
            "payment_type": "free",
        }
    sub_status = user.get(
        "subscription_status", "free")
    free_used = user.get("free_doc_used", False)
    payment_status = (session or {}).get(
        "payment_status", "pending")

    if sub_status == "active":
        return {
            "allowed": True,
            "reason": "Active subscription",
            "payment_type": "subscription"
        }
    if not free_used:
        return {
            "allowed": True,
            "reason": "First document free",
            "payment_type": "free"
        }
    if payment_status == "paid":
        return {
            "allowed": True,
            "reason": "Payment confirmed",
            "payment_type": "payg"
        }
    return {
        "allowed": False,
        "reason": "Payment required",
        "payment_type": "none"
    }
