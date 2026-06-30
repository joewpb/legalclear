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
    API_KEY: str = os.getenv("API_KEY", "testkey123")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    # Email provider for the deadline-reminder fallback (web users have no
    # Expo push token). Empty = delivery disabled (reminders fail honestly).
    EMAIL_PROVIDER: str = os.getenv("EMAIL_PROVIDER", "")  # "resend" | "sendgrid" | ""
    RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "")
    SENDGRID_API_KEY: str = os.getenv("SENDGRID_API_KEY", "")
    MESSAGING_PLATFORM: str = os.getenv(
        "MESSAGING_PLATFORM", "log")
    BACKEND_PORT: int = int(os.getenv("BACKEND_PORT", "8001"))

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"


settings = Settings()
