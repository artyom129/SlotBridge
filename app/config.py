from __future__ import annotations

from functools import lru_cache
from typing import Literal
from urllib.parse import parse_qs, urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    database_url: str
    jwt_secret: SecretStr = Field(min_length=32)
    jwt_algorithm: Literal["HS256"] = "HS256"
    jwt_access_token_expire_minutes: int = Field(default=30, ge=5, le=1440)
    availability_slot_interval_minutes: int = Field(default=15, ge=1, le=60)
    review_edit_window_hours: int = Field(default=24, ge=1, le=720)
    slotbridge_environment: Literal["development", "test", "demo", "production"] = (
        "development"
    )
    cors_allowed_origins: str = ""
    public_demo_registration_enabled: bool = False
    public_demo_organization_slug: str = Field(default="slotbridge-demo", min_length=1)
    production_demo_seed_enabled: bool = False
    demo_password: SecretStr | None = Field(default=None, min_length=12)
    ai_provider: Literal["gemini"] = "gemini"
    gemini_api_key: SecretStr | None = None
    gemini_model: str = Field(default="gemini-3.6-flash", pattern=r"^[a-zA-Z0-9._-]+$")
    gemini_fallback_model: str = Field(
        default="gemini-3.5-flash-lite",
        pattern=r"^[a-zA-Z0-9._-]+$",
    )

    allow_unsigned_demo_webhooks: bool = False
    mindbody_webhook_secret: SecretStr | None = Field(default=None, min_length=32)
    vagaro_webhook_secret: SecretStr | None = Field(default=None, min_length=32)
    google_webhook_secret: SecretStr | None = Field(default=None, min_length=32)

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_postgresql_driver(cls, value: object) -> object:
        """Managed providers supply postgresql://; use the installed psycopg driver."""
        if not isinstance(value, str):
            return value
        if value.startswith("postgres://"):
            return "postgresql+psycopg://" + value.removeprefix("postgres://")
        if value.startswith("postgresql://"):
            return "postgresql+psycopg://" + value.removeprefix("postgresql://")
        return value

    @property
    def cors_origins(self) -> tuple[str, ...]:
        return tuple(
            origin.strip().rstrip("/")
            for origin in self.cors_allowed_origins.split(",")
            if origin.strip()
        )

    @model_validator(mode="after")
    def prevent_unsafe_production_configuration(self) -> "Settings":
        for origin in self.cors_origins:
            parsed = urlsplit(origin)
            if (
                origin == "*"
                or parsed.scheme not in {"http", "https"}
                or not parsed.netloc
                or parsed.path not in {"", "/"}
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError(
                    "CORS_ALLOWED_ORIGINS must contain comma-separated HTTP(S) origins"
                )

        if self.slotbridge_environment == "production":
            if self.allow_unsigned_demo_webhooks:
                raise ValueError("Unsigned demo webhooks cannot be enabled in production")
            if not self.database_url.startswith("postgresql+psycopg://"):
                raise ValueError("Production DATABASE_URL must use PostgreSQL with psycopg")
            sslmode = parse_qs(urlsplit(self.database_url).query).get("sslmode", [""])[0]
            if sslmode.lower() not in {"require", "verify-ca", "verify-full"}:
                raise ValueError(
                    "Production DATABASE_URL must enforce PostgreSQL SSL with "
                    "sslmode=require, verify-ca, or verify-full"
                )
            if any(urlsplit(origin).scheme != "https" for origin in self.cors_origins):
                raise ValueError("Production CORS origins must use HTTPS")

            jwt_secret = self.jwt_secret.get_secret_value()
            unsafe_secret_markers = ("change-this", "replace-with", "test-only")
            if any(marker in jwt_secret.lower() for marker in unsafe_secret_markers):
                raise ValueError("Production JWT_SECRET must be a generated random secret")

            if self.production_demo_seed_enabled:
                if self.demo_password is None:
                    raise ValueError(
                        "DEMO_PASSWORD is required while production demo seeding is enabled"
                    )
                if self.demo_password.get_secret_value() == "SlotBridgeDemo!2026":
                    raise ValueError(
                        "The development demo password cannot be used in production"
                    )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
