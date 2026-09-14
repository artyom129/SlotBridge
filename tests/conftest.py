from __future__ import annotations

import os

import pytest


os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-only-jwt-secret-with-at-least-32-characters")
os.environ["SLOTBRIDGE_ENVIRONMENT"] = "test"
os.environ.setdefault(
    "MINDBODY_WEBHOOK_SECRET", "test-webhook-secret-with-at-least-32-chars"
)
os.environ["SLOTBRIDGE_DB_PATH"] = "data/test-stage2-legacy.db"

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.database import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402


@pytest.fixture(autouse=True)
def clean_domain_database():
    """create_all is deliberately limited to isolated SQLite tests.

    Development and production schemas are created only through Alembic.
    """
    if engine.dialect.name == "sqlite":
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
    else:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "TRUNCATE TABLE appointment_audit_log, appointment_status_history, "
                    "appointments, organization_memberships, blocked_slots, "
                    "schedule_exceptions, schedule_breaks, "
                    "work_schedules, employee_services, employees, services, branches, "
                    "organizations, users RESTART IDENTITY CASCADE"
                )
            )
    app.dependency_overrides.clear()
    yield
    if engine.dialect.name == "sqlite":
        Base.metadata.drop_all(engine)
    else:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "TRUNCATE TABLE appointment_audit_log, appointment_status_history, "
                    "appointments, organization_memberships, blocked_slots, "
                    "schedule_exceptions, schedule_breaks, "
                    "work_schedules, employee_services, employees, services, branches, "
                    "organizations, users RESTART IDENTITY CASCADE"
                )
            )


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def session():
    with SessionLocal() as db_session:
        yield db_session
        db_session.rollback()
