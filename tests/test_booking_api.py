from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select

from app.database import SessionLocal
from app.models import (
    Appointment,
    AppointmentAuditLog,
    AppointmentStatus,
    AppointmentStatusHistory,
)
from tests.booking_support import (
    BOOKING_DATE,
    auth_headers,
    book,
    booking_payload,
    create_booking_domain,
)


def test_create_requires_auth_valid_jwt_and_server_owned_fields(client, session):
    domain = create_booking_domain(session)
    payload = booking_payload(domain, 15)

    assert client.post(
        "/appointments",
        json=payload,
        headers={"Idempotency-Key": "unauthenticated"},
    ).status_code == 401
    assert client.post(
        "/appointments",
        json=payload,
        headers={
            "Authorization": "Bearer invalid-token",
            "Idempotency-Key": "invalid-token",
        },
    ).status_code == 401

    headers = {
        **auth_headers(client, domain.client_a),
        "Idempotency-Key": "server-owned-fields",
    }
    response = client.post(
        "/appointments",
        json={
            **payload,
            "ends_at": "2099-01-05T16:00:00Z",
            "client_user_id": str(domain.client_b.id),
            "organization_id": str(domain.organization.id),
        },
        headers=headers,
    )
    assert response.status_code == 422
    assert client.post(
        "/appointments",
        json=payload,
        headers=auth_headers(client, domain.client_a),
    ).status_code == 422


def test_create_computes_end_and_persists_idempotent_result(client, session):
    domain = create_booking_domain(session)
    headers = {
        **auth_headers(client, domain.client_a),
        "Idempotency-Key": "mobile-retry-1",
    }
    payload = booking_payload(domain, 15, note="Window seat")
    first = client.post("/appointments", json=payload, headers=headers)

    assert first.status_code == 201
    body = first.json()
    assert body["status"] == "BOOKED"
    assert body["client_user_id"] == str(domain.client_a.id)
    assert body["starts_at"] == "2099-01-05T15:00:00Z"
    assert body["ends_at"] == "2099-01-05T16:00:00Z"
    assert body["branch"] == {
        "id": str(domain.branch.id),
        "name": "Booking Branch",
    }
    assert body["employee"]["name"] == "Assigned Employee"
    assert body["service"]["name"] == "Booking Service"

    replay = client.post("/appointments", json=payload, headers=headers)
    assert replay.status_code == 200
    assert replay.headers["Idempotency-Replayed"] == "true"
    assert replay.json()["id"] == body["id"]

    changed_request = client.post(
        "/appointments",
        json=booking_payload(domain, 16, note="Window seat"),
        headers=headers,
    )
    assert changed_request.status_code == 409
    assert changed_request.json()["detail"]["code"] == "IDEMPOTENCY_KEY_REUSED"

    with SessionLocal() as check:
        assert check.scalar(select(func.count()).select_from(Appointment)) == 1
        assert (
            check.scalar(select(func.count()).select_from(AppointmentStatusHistory))
            == 1
        )
        assert check.scalar(select(func.count()).select_from(AppointmentAuditLog)) == 1


def test_my_appointments_filters_are_client_owned(client, session):
    domain = create_booking_domain(session)
    first = book(client, domain, domain.client_a, "client-a-upcoming", 15)
    cancelled = book(client, domain, domain.client_a, "client-a-cancelled", 17)
    other = book(client, domain, domain.client_b, "client-b-upcoming", 16)
    assert [first.status_code, cancelled.status_code, other.status_code] == [201, 201, 201]

    client_a_headers = auth_headers(client, domain.client_a)
    cancel = client.post(
        f"/appointments/{cancelled.json()['id']}/cancel",
        json={"reason": "Plans changed"},
        headers=client_a_headers,
    )
    assert cancel.status_code == 200

    with SessionLocal.begin() as direct:
        direct.add(
            Appointment(
                organization_id=domain.organization.id,
                branch_id=domain.branch.id,
                client_user_id=domain.client_a.id,
                employee_id=domain.employee.id,
                service_id=domain.service.id,
                starts_at=datetime(2000, 1, 3, 10, tzinfo=timezone.utc),
                ends_at=datetime(2000, 1, 3, 11, tzinfo=timezone.utc),
                status=AppointmentStatus.COMPLETED,
                idempotency_key="client-a-historical",
                idempotency_fingerprint="a" * 64,
            )
        )

    all_items = client.get("/appointments/me", headers=client_a_headers).json()["items"]
    upcoming = client.get(
        "/appointments/me?view=upcoming", headers=client_a_headers
    ).json()["items"]
    past = client.get(
        "/appointments/me?view=past", headers=client_a_headers
    ).json()["items"]
    cancelled_items = client.get(
        "/appointments/me?view=cancelled", headers=client_a_headers
    ).json()["items"]
    booked = client.get(
        "/appointments/me?status=BOOKED", headers=client_a_headers
    ).json()["items"]

    assert len(all_items) == 3
    assert [item["id"] for item in upcoming] == [first.json()["id"]]
    assert [item["status"] for item in past] == ["COMPLETED"]
    assert [item["id"] for item in cancelled_items] == [cancelled.json()["id"]]
    assert [item["id"] for item in booked] == [first.json()["id"]]


def test_original_idempotency_request_replays_after_reschedule(client, session):
    domain = create_booking_domain(session)
    payload = booking_payload(domain, 15)
    headers = {
        **auth_headers(client, domain.client_a),
        "Idempotency-Key": "retry-after-reschedule",
    }
    created = client.post("/appointments", json=payload, headers=headers)
    moved = client.post(
        f"/appointments/{created.json()['id']}/reschedule",
        json={"starts_at": "2099-01-05T16:00:00Z"},
        headers=auth_headers(client, domain.client_a),
    )
    replay = client.post("/appointments", json=payload, headers=headers)

    assert created.status_code == 201
    assert moved.status_code == 200
    assert replay.status_code == 200
    assert replay.headers["Idempotency-Replayed"] == "true"
    assert replay.json()["id"] == created.json()["id"]
    with SessionLocal() as check:
        assert check.scalar(select(func.count()).select_from(Appointment)) == 1


def test_cancellation_audits_and_immediately_frees_availability(client, session):
    domain = create_booking_domain(session)
    booked = book(client, domain, domain.client_a, "cancel-and-release", 15)
    assert booked.status_code == 201
    client_a_headers = auth_headers(client, domain.client_a)
    availability_params = {
        "branch_id": str(domain.branch.id),
        "employee_id": str(domain.employee.id),
        "service_id": str(domain.service.id),
        "date": BOOKING_DATE.isoformat(),
    }

    before = client.get(
        "/availability",
        params=availability_params,
        headers=client_a_headers,
    )
    before_starts = {item["start"] for item in before.json()["slots"]}
    assert "2099-01-05T15:00:00Z" not in before_starts

    cancelled = client.post(
        f"/appointments/{booked.json()['id']}/cancel",
        json={"reason": "Client request"},
        headers=client_a_headers,
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "CANCELLED"
    assert cancelled.json()["cancelled_at"] is not None
    assert cancelled.json()["cancellation_reason"] == "Client request"

    after = client.get(
        "/availability",
        params=availability_params,
        headers=client_a_headers,
    )
    after_starts = {item["start"] for item in after.json()["slots"]}
    assert "2099-01-05T15:00:00Z" in after_starts

    replacement = book(client, domain, domain.client_b, "replacement-booking", 15)
    assert replacement.status_code == 201
    detail = client.get(
        f"/appointments/{booked.json()['id']}",
        headers=client_a_headers,
    )
    assert detail.status_code == 200
    assert [item["new_status"] for item in detail.json()["status_history"]] == [
        "BOOKED",
        "CANCELLED",
    ]
    assert [item["action"] for item in detail.json()["audit_events"]] == [
        "CREATED",
        "CANCELLED",
    ]
