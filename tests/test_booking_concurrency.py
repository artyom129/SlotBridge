from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Barrier
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text

from app.database import SessionLocal, engine
from app.main import app
from app.models import Appointment, AppointmentStatus
from tests.booking_support import (
    auth_headers,
    book,
    booking_payload,
    create_booking_domain,
)


pytestmark = pytest.mark.skipif(
    engine.dialect.name != "postgresql",
    reason="Requires a real PostgreSQL database and GiST exclusion constraint",
)


def concurrent_posts(payload: dict, token: str, keys: list[str]) -> list:
    barrier = Barrier(len(keys))

    def send(key: str):
        barrier.wait()
        with TestClient(app) as thread_client:
            return thread_client.post(
                "/appointments",
                json=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Idempotency-Key": key,
                },
            )

    with ThreadPoolExecutor(max_workers=len(keys)) as executor:
        return list(executor.map(send, keys))


def test_ten_concurrent_http_requests_produce_one_booking_and_nine_conflicts(
    client, session
):
    domain = create_booking_domain(session)
    token = auth_headers(client, domain.client_a)["Authorization"].removeprefix(
        "Bearer "
    )
    with engine.connect() as connection:
        assert connection.scalar(
            text(
                "SELECT EXISTS ("
                "SELECT 1 FROM pg_constraint "
                "WHERE conname = 'ex_appointments_employee_time_active' "
                "AND contype = 'x'"
                ")"
            )
        )

    responses = concurrent_posts(
        booking_payload(domain, 15),
        token,
        [f"concurrent-{index}" for index in range(10)],
    )

    assert sum(response.status_code == 201 for response in responses) == 1
    assert sum(response.status_code == 409 for response in responses) == 9
    assert {
        response.json()["detail"]["code"]
        for response in responses
        if response.status_code == 409
    } == {"SLOT_ALREADY_BOOKED"}
    with SessionLocal() as check:
        assert check.scalar(
            select(func.count())
            .select_from(Appointment)
            .where(Appointment.status.in_(
                {
                    AppointmentStatus.BOOKED,
                    AppointmentStatus.CONFIRMED,
                    AppointmentStatus.IN_PROGRESS,
                }
            ))
        ) == 1


def test_partially_overlapping_requests_conflict(client, session):
    domain = create_booking_domain(session)
    first = book(client, domain, domain.client_a, "partial-first", 15)
    second = book(client, domain, domain.client_b, "partial-second", 15, 30)

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["detail"]["code"] == "SLOT_ALREADY_BOOKED"


def test_half_open_adjacent_ranges_are_both_allowed(client, session):
    domain = create_booking_domain(session)
    first = book(client, domain, domain.client_a, "adjacent-first", 15)
    second = book(client, domain, domain.client_b, "adjacent-second", 16)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["ends_at"] == second.json()["starts_at"]


def test_cancelled_appointment_no_longer_blocks_postgresql_range(client, session):
    domain = create_booking_domain(session)
    first = book(client, domain, domain.client_a, "cancel-release-first", 15)
    cancelled = client.post(
        f"/appointments/{first.json()['id']}/cancel",
        json={"reason": "Release"},
        headers=auth_headers(client, domain.client_a),
    )
    second = book(client, domain, domain.client_b, "cancel-release-second", 15)

    assert first.status_code == 201
    assert cancelled.status_code == 200
    assert second.status_code == 201


def test_two_concurrent_same_idempotency_key_create_one_appointment(client, session):
    domain = create_booking_domain(session)
    token = auth_headers(client, domain.client_a)["Authorization"].removeprefix(
        "Bearer "
    )

    responses = concurrent_posts(
        booking_payload(domain, 15),
        token,
        ["same-mobile-key", "same-mobile-key"],
    )

    assert sorted(response.status_code for response in responses) == [200, 201]
    assert len({response.json()["id"] for response in responses}) == 1
    assert sum(
        response.headers.get("Idempotency-Replayed") == "true"
        for response in responses
    ) == 1
    with SessionLocal() as check:
        assert check.scalar(select(func.count()).select_from(Appointment)) == 1


def test_reschedule_to_occupied_range_rolls_back_original_postgresql_row(
    client, session
):
    domain = create_booking_domain(session)
    first = book(client, domain, domain.client_a, "pg-reschedule-first", 15)
    second = book(client, domain, domain.client_b, "pg-reschedule-second", 16)

    response = client.post(
        f"/appointments/{first.json()['id']}/reschedule",
        json={"starts_at": "2099-01-05T16:00:00Z"},
        headers=auth_headers(client, domain.client_a),
    )

    assert second.status_code == 201
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "SLOT_ALREADY_BOOKED"
    with SessionLocal() as check:
        stored = check.get(Appointment, UUID(first.json()["id"]))
        assert stored.starts_at.astimezone(timezone.utc) == datetime(
            2099, 1, 5, 15, tzinfo=timezone.utc
        )
        assert stored.ends_at.astimezone(timezone.utc) == datetime(
            2099, 1, 5, 16, tzinfo=timezone.utc
        )
