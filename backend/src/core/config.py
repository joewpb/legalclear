import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")
    SUPABASE_SERVICE_KEY: str = os.getenv(
        "SUPABASE_SERVICE_KEY", "")
    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET: str = os.getenv(
        "STRIPE_WEBHOOK_SECRET", "")
    STRIPE_PRICE_SMALL: str = os.getenv(
        "STRIPE_PRICE_SMALL", "")
    STRIPE_PRICE_MEDIUM: str = os.getenv(
        "STRIPE_PRICE_MEDIUM", "")
    STRIPE_PRICE_LARGE: str = os.getenv(
        "STRIPE_PRICE_LARGE", "")
    STRIPE_SUBSCRIPTION_PRICE_ID: str = os.getenv(
        "STRIPE_SUBSCRIPTION_PRICE_ID", "")
    # CourtListener v4 token. Empty (default) = the case-law search is
    # corpus-only (Supabase legal_opinions); CL is never called. Set only to
    # enable the optional v4 fallback when the corpus returns nothing.
    COURTLISTENER_TOKEN: str = os.getenv("COURTLISTENER_TOKEN", "")
    API_KEY: str = os.getenv("API_KEY", "")
    # Retired (Decision 7, 2026-08): all call sites repointed to Claude
    # Haiku. Unused in production paths; kept only so the env var doesn't
    # dangle undefined until Joe unsets it in Railway.
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    # Master payment switch. False (default) = every paywalled feature runs
    # FREE (no Stripe checkout, no paywall, no upgrade prompt). True =
    # billing re-enabled exactly as-is. One switch governs all payment
    # surfaces: chat limit, $35 packet, filing count, subscription, webhook,
    # check_access.
    PAYMENTS_ENABLED: bool = os.getenv(
        "PAYMENTS_ENABLED", "false").lower() in ("true", "1", "yes", "on")
    # Email provider for the deadline-reminder fallback (web users have no
    # Expo push token). Empty = delivery disabled (reminders fail honestly).
    EMAIL_PROVIDER: str = os.getenv("EMAIL_PROVIDER", "")  # "resend" | "sendgrid" | ""
    RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "")
    SENDGRID_API_KEY: str = os.getenv("SENDGRID_API_KEY", "")
    MESSAGING_PLATFORM: str = os.getenv(
        "MESSAGING_PLATFORM", "log")
    BACKEND_PORT: int = int(os.getenv("BACKEND_PORT", "8001"))
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "https://legalclear.app")

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"


settings = Settings()

if not settings.API_KEY:
    raise RuntimeError(
        "API_KEY environment variable is not set. Refusing to start: "
        "protected endpoints must never fall back to a default secret."
    )

# Required outside local dev: without these the product silently degrades to
# an empty/broken state (no DB access, no LLM calls) instead of failing
# loudly. Called from FastAPI startup, not import time, so pytest collection
# (no .env, no secrets) is unaffected.
REQUIRED_SETTINGS = ("SUPABASE_URL", "SUPABASE_SERVICE_KEY", "ANTHROPIC_API_KEY")


def validate_startup_config() -> None:
    if settings.is_development:
        return
    missing = [name for name in REQUIRED_SETTINGS if not getattr(settings, name)]
    if missing:
        raise RuntimeError(
            f"Missing required config in ENVIRONMENT={settings.ENVIRONMENT!r}: "
            f"{', '.join(missing)}"
        )
