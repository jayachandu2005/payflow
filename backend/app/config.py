"""Application settings loaded from environment variables and .env."""

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root: d:\payment (two levels up from backend/app/config.py)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"


def _is_configured_value(value: str | None) -> bool:
    """Return True if a secret/key is present and not an example placeholder."""
    if not value:
        return False
    lowered = value.strip().lower()
    if not lowered:
        return False
    placeholders = ("replace_with", "your_", "example", "changeme", "xxx")
    return not any(p in lowered for p in placeholders)


class Settings(BaseSettings):
    """Typed configuration for PayFlow backend."""

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE) if ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "PayFlow"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    SECRET_KEY: str = "dev-only-insecure-fallback-change-in-env-32bytes"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 120

    FRONTEND_URL: str = "http://localhost:5173"
    BACKEND_URL: str = "http://localhost:8000"
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000"

    DATABASE_URL: str = f"sqlite:///{(PROJECT_ROOT / 'database' / 'payflow.db').as_posix()}"

    # Stripe Sandbox
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # Razorpay Test Mode
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""

    DEFAULT_CURRENCY: str = "USD"
    USD_TO_INR_RATE: float = 84.0

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def stripe_configured(self) -> bool:
        return (
            _is_configured_value(self.STRIPE_SECRET_KEY)
            and _is_configured_value(self.STRIPE_PUBLISHABLE_KEY)
            and self.STRIPE_SECRET_KEY.startswith("sk_test_")
            and self.STRIPE_PUBLISHABLE_KEY.startswith("pk_test_")
        )

    @property
    def razorpay_configured(self) -> bool:
        return (
            _is_configured_value(self.RAZORPAY_KEY_ID)
            and _is_configured_value(self.RAZORPAY_KEY_SECRET)
            and self.RAZORPAY_KEY_ID.startswith("rzp_test_")
        )

    @property
    def stripe_webhook_configured(self) -> bool:
        return _is_configured_value(self.STRIPE_WEBHOOK_SECRET)

    @property
    def razorpay_webhook_configured(self) -> bool:
        return _is_configured_value(self.RAZORPAY_WEBHOOK_SECRET)


@lru_cache
def get_settings() -> Settings:
    """Return cached Settings instance."""
    return Settings()
