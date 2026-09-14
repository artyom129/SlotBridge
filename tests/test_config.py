import pytest
from pydantic import ValidationError

from app.config import Settings


VALID_SECRET = "configuration-test-secret-with-32-characters"


def test_production_requires_postgresql():
    with pytest.raises(ValidationError):
        Settings(
            database_url="sqlite+pysqlite:///production.db",
            jwt_secret=VALID_SECRET,
            slotbridge_environment="production",
        )


def test_production_rejects_unsigned_demo_webhooks():
    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql+psycopg://user:password@db/slotbridge",
            jwt_secret=VALID_SECRET,
            slotbridge_environment="production",
            allow_unsigned_demo_webhooks=True,
        )


def test_managed_postgresql_url_uses_installed_psycopg_driver():
    settings = Settings(
        database_url="postgresql://user:password@db/slotbridge?sslmode=require",
        jwt_secret=VALID_SECRET,
        slotbridge_environment="production",
    )

    assert (
        settings.database_url
        == "postgresql+psycopg://user:password@db/slotbridge?sslmode=require"
    )


@pytest.mark.parametrize("ssl_query", ("", "?sslmode=disable", "?sslmode=prefer"))
def test_production_requires_postgresql_ssl(ssl_query):
    with pytest.raises(ValidationError):
        Settings(
            database_url=f"postgresql://user:password@db/slotbridge{ssl_query}",
            jwt_secret=VALID_SECRET,
            slotbridge_environment="production",
        )


@pytest.mark.parametrize(
    "jwt_secret",
    (
        "change-this-demo-only-jwt-secret-before-real-use",
        "replace-with-a-generated-random-secret-of-at-least-32-characters",
        "test-only-jwt-secret-with-at-least-32-characters",
    ),
)
def test_production_rejects_known_placeholder_jwt_secrets(jwt_secret):
    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql://user:password@db/slotbridge?sslmode=require",
            jwt_secret=jwt_secret,
            slotbridge_environment="production",
        )


@pytest.mark.parametrize(
    "origins",
    ("*", "http://mobile.example.com", "https://mobile.example.com/path"),
)
def test_production_rejects_unsafe_cors_origins(origins):
    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql://user:password@db/slotbridge?sslmode=require",
            jwt_secret=VALID_SECRET,
            slotbridge_environment="production",
            cors_allowed_origins=origins,
        )


def test_production_accepts_explicit_https_cors_origins():
    settings = Settings(
        database_url="postgresql://user:password@db/slotbridge?sslmode=require",
        jwt_secret=VALID_SECRET,
        slotbridge_environment="production",
        cors_allowed_origins="https://app.example.com, https://admin.example.com/",
    )

    assert settings.cors_origins == (
        "https://app.example.com",
        "https://admin.example.com",
    )


def test_production_demo_seed_requires_non_development_password():
    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql://user:password@db/slotbridge?sslmode=require",
            jwt_secret=VALID_SECRET,
            slotbridge_environment="production",
            production_demo_seed_enabled=True,
        )

    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql://user:password@db/slotbridge?sslmode=require",
            jwt_secret=VALID_SECRET,
            slotbridge_environment="production",
            production_demo_seed_enabled=True,
            demo_password="SlotBridgeDemo!2026",
        )
