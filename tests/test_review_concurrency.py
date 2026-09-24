from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.database import SessionLocal, engine
from app.main import app
from app.models import Appointment, AppointmentStatus, Review
from tests.booking_support import auth_headers, create_booking_domain


pytestmark = pytest.mark.skipif(
    engine.dialect.name != "postgresql",
    reason="Requires PostgreSQL transaction-level concurrency",
)


def test_concurrent_duplicate_review_creation_produces_one_review(client, session):
    domain = create_booking_domain(session)
    starts_at = datetime(2026, 1, 1, 10, tzinfo=timezone.utc)
    appointment = Appointment(
        organization_id=domain.organization.id,
        branch_id=domain.branch.id,
        client_user_id=domain.client_a.id,
        employee_id=domain.employee.id,
        service_id=domain.service.id,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=1),
        status=AppointmentStatus.COMPLETED,
        idempotency_key=f"review-concurrency-{uuid4()}",
        idempotency_fingerprint=uuid4().hex,
    )
    session.add(appointment)
    session.commit()
    token = auth_headers(client, domain.client_a)["Authorization"]
    barrier = Barrier(2)

    def send():
        barrier.wait()
        with TestClient(app) as thread_client:
            return thread_client.post(
                "/reviews",
                headers={"Authorization": token},
                json={"appointment_id": str(appointment.id), "overall_rating": 5},
            )

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(lambda _: send(), range(2)))

    assert sorted(response.status_code for response in responses) == [201, 409]
    with SessionLocal() as check:
        assert check.scalar(select(func.count()).select_from(Review)) == 1
