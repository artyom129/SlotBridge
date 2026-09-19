from __future__ import annotations

from datetime import date, datetime, time, timezone

import pytest
from sqlalchemy import select

from app.database import SessionLocal
from app.models import (
    Appointment,
    AppointmentStatus,
    BlockedSlot,
    EmployeeService,
    ScheduleBreak,
    ScheduleException,
)
from tests.booking_support import (
    BOOKING_DATE,
    auth_headers,
    book,
    booking_payload,
    create_booking_domain,
)


def error_code(response) -> str:
    return response.json()["detail"]["code"]


def post_booking(client, domain, key: str, hour: int, minute: int = 0):
    return client.post(
        "/appointments",
        json=booking_payload(domain, hour, minute),
        headers={
            **auth_headers(client, domain.client_a),
            "Idempotency-Key": key,
        },
    )


def test_booking_rejects_outside_work_break_block_and_day_off(client, session):
    domain = create_booking_domain(session)

    outside = post_booking(client, domain, "outside-work", 8)
    assert outside.status_code == 409
    assert error_code(outside) == "SLOT_UNAVAILABLE"

    session.add(
        ScheduleBreak(
            employee_id=domain.employee.id,
            branch_id=domain.branch.id,
            organization_id=domain.organization.id,
            day_of_week=BOOKING_DATE.weekday(),
            start_time=time(13),
            end_time=time(14),
        )
    )
    session.commit()
    during_break = post_booking(client, domain, "during-break", 13)
    assert during_break.status_code == 409
    assert error_code(during_break) == "SLOT_UNAVAILABLE"

    session.add(
        BlockedSlot(
            employee_id=domain.employee.id,
            branch_id=domain.branch.id,
            organization_id=domain.organization.id,
            starts_at=datetime(2099, 1, 5, 14, tzinfo=timezone.utc),
            ends_at=datetime(2099, 1, 5, 15, tzinfo=timezone.utc),
            reason="Training",
            created_by_user_id=domain.admin.id,
        )
    )
    session.commit()
    during_block = post_booking(client, domain, "during-block", 14)
    assert during_block.status_code == 409
    assert error_code(during_block) == "SLOT_UNAVAILABLE"

    session.add(
        ScheduleException(
            employee_id=domain.employee.id,
            branch_id=domain.branch.id,
            organization_id=domain.organization.id,
            local_date=BOOKING_DATE,
            is_day_off=True,
        )
    )
    session.commit()
    day_off = post_booking(client, domain, "day-off", 10)
    assert day_off.status_code == 409
    assert error_code(day_off) == "SLOT_UNAVAILABLE"


def test_replacement_exception_is_the_only_bookable_window(client, session):
    domain = create_booking_domain(session)
    session.add(
        ScheduleException(
            employee_id=domain.employee.id,
            branch_id=domain.branch.id,
            organization_id=domain.organization.id,
            local_date=BOOKING_DATE,
            is_day_off=False,
            start_time=time(12),
            end_time=time(14),
        )
    )
    session.commit()

    rejected = post_booking(client, domain, "outside-replacement", 10)
    accepted = post_booking(client, domain, "inside-replacement", 12)

    assert rejected.status_code == 409
    assert error_code(rejected) == "SLOT_UNAVAILABLE"
    assert accepted.status_code == 201
    assert accepted.json()["ends_at"] == "2099-01-05T13:00:00Z"


def test_effective_duration_must_fit_and_server_uses_employee_override(client, session):
    domain = create_booking_domain(session, duration_minutes=90)

    too_late = post_booking(client, domain, "too-late", 17)
    assert too_late.status_code == 409
    assert error_code(too_late) == "SLOT_UNAVAILABLE"

    with SessionLocal.begin() as update:
        link = update.get(
            EmployeeService,
            {
                "employee_id": domain.employee.id,
                "service_id": domain.service.id,
            },
        )
        link.duration_override_minutes = 45

    accepted = post_booking(client, domain, "duration-override", 17)
    assert accepted.status_code == 201
    assert accepted.json()["ends_at"] == "2099-01-05T17:45:00Z"


@pytest.mark.parametrize(
    ("attribute", "expected_code"),
    [
        ("organization", "ORGANIZATION_INACTIVE"),
        ("branch", "BRANCH_INACTIVE"),
        ("employee", "EMPLOYEE_INACTIVE"),
        ("service", "SERVICE_INACTIVE"),
    ],
)
def test_inactive_booking_scope_is_rejected(
    client, session, attribute, expected_code
):
    domain = create_booking_domain(session)
    target = getattr(domain, attribute)
    target.is_active = False
    session.commit()

    response = post_booking(client, domain, f"inactive-{attribute}", 15)

    assert response.status_code == 409
    assert error_code(response) == expected_code


def test_unassigned_service_and_cross_tenant_resources_are_rejected(client, session):
    unassigned = create_booking_domain(session, with_assignment=False)
    mismatch = post_booking(client, unassigned, "unassigned", 15)
    assert mismatch.status_code == 422
    assert error_code(mismatch) == "EMPLOYEE_SERVICE_MISMATCH"

    first = create_booking_domain(session)
    second = create_booking_domain(session)
    headers = {
        **auth_headers(client, first.client_a),
        "Idempotency-Key": "cross-tenant-service",
    }
    payload = {
        **booking_payload(first, 15),
        "service_id": str(second.service.id),
    }
    cross_tenant = client.post("/appointments", json=payload, headers=headers)
    assert cross_tenant.status_code == 404
    assert error_code(cross_tenant) == "RESOURCE_NOT_FOUND"

    no_membership = client.post(
        "/appointments",
        json=booking_payload(second, 15),
        headers={
            **auth_headers(client, first.client_a),
            "Idempotency-Key": "cross-tenant-branch",
        },
    )
    assert no_membership.status_code == 404
    assert error_code(no_membership) == "BOOKING_SCOPE_NOT_FOUND"


def test_booking_in_the_past_is_rejected_before_schedule_lookup(client, session):
    domain = create_booking_domain(session)
    past_monday = date(2000, 1, 3)
    response = client.post(
        "/appointments",
        json=booking_payload(
            domain,
            10,
            booking_date=past_monday,
        ),
        headers={
            **auth_headers(client, domain.client_a),
            "Idempotency-Key": "past-booking",
        },
    )

    assert response.status_code == 422
    assert error_code(response) == "BOOKING_IN_PAST"


def test_status_lifecycle_is_strict_and_every_transition_is_recorded(client, session):
    domain = create_booking_domain(session)
    booked = book(client, domain, domain.client_a, "lifecycle", 15)
    appointment_id = booked.json()["id"]
    employee_headers = auth_headers(client, domain.employee_user)

    confirmed = client.post(
        f"/appointments/{appointment_id}/status",
        json={"status": "CONFIRMED", "reason": "Accepted"},
        headers=employee_headers,
    )
    invalid_skip = client.post(
        f"/appointments/{appointment_id}/status",
        json={"status": "COMPLETED"},
        headers=employee_headers,
    )
    in_progress = client.post(
        f"/appointments/{appointment_id}/status",
        json={"status": "IN_PROGRESS"},
        headers=employee_headers,
    )
    completed = client.post(
        f"/appointments/{appointment_id}/status",
        json={"status": "COMPLETED"},
        headers=employee_headers,
    )
    invalid_terminal = client.post(
        f"/appointments/{appointment_id}/status",
        json={"status": "CONFIRMED"},
        headers=employee_headers,
    )

    assert confirmed.json()["status"] == "CONFIRMED"
    assert invalid_skip.status_code == 409
    assert error_code(invalid_skip) == "INVALID_APPOINTMENT_STATUS_TRANSITION"
    assert in_progress.json()["status"] == "IN_PROGRESS"
    assert completed.json()["status"] == "COMPLETED"
    assert invalid_terminal.status_code == 409

    detail = client.get(
        f"/appointments/{appointment_id}",
        headers=auth_headers(client, domain.client_a),
    ).json()
    assert [item["new_status"] for item in detail["status_history"]] == [
        "BOOKED",
        "CONFIRMED",
        "IN_PROGRESS",
        "COMPLETED",
    ]
    assert [item["action"] for item in detail["audit_events"]] == [
        "CREATED",
        "STATUS_CHANGED",
        "STATUS_CHANGED",
        "STATUS_CHANGED",
    ]


def test_no_show_is_terminal_and_releases_the_time(client, session):
    domain = create_booking_domain(session)
    booked = book(client, domain, domain.client_a, "no-show", 15)
    appointment_id = booked.json()["id"]
    employee_headers = auth_headers(client, domain.employee_user)

    assert client.post(
        f"/appointments/{appointment_id}/status",
        json={"status": "CONFIRMED"},
        headers=employee_headers,
    ).status_code == 200
    no_show = client.post(
        f"/appointments/{appointment_id}/status",
        json={"status": "NO_SHOW", "reason": "Client absent"},
        headers=employee_headers,
    )
    assert no_show.status_code == 200
    assert no_show.json()["status"] == "NO_SHOW"

    replacement = book(client, domain, domain.client_b, "after-no-show", 15)
    assert replacement.status_code == 201
    assert client.post(
        f"/appointments/{appointment_id}/status",
        json={"status": "IN_PROGRESS"},
        headers=employee_headers,
    ).status_code == 409


def test_reschedule_conflict_rolls_back_old_time_then_success_is_audited(client, session):
    domain = create_booking_domain(session)
    first = book(client, domain, domain.client_a, "reschedule-first", 15)
    second = book(client, domain, domain.client_b, "reschedule-second", 16)
    first_id = first.json()["id"]
    headers = auth_headers(client, domain.client_a)

    conflict = client.post(
        f"/appointments/{first_id}/reschedule",
        json={"starts_at": "2099-01-05T16:00:00Z", "reason": "Try occupied"},
        headers=headers,
    )
    assert conflict.status_code == 409
    assert error_code(conflict) == "SLOT_ALREADY_BOOKED"

    after_failure = client.get(f"/appointments/{first_id}", headers=headers)
    assert after_failure.json()["starts_at"] == "2099-01-05T15:00:00Z"
    assert after_failure.json()["ends_at"] == "2099-01-05T16:00:00Z"

    moved = client.post(
        f"/appointments/{first_id}/reschedule",
        json={"starts_at": "2099-01-05T17:00:00Z", "reason": "Move later"},
        headers=headers,
    )
    assert moved.status_code == 200
    assert moved.json()["starts_at"] == "2099-01-05T17:00:00Z"
    assert moved.json()["ends_at"] == "2099-01-05T18:00:00Z"

    detail = client.get(f"/appointments/{first_id}", headers=headers).json()
    assert [item["action"] for item in detail["audit_events"]] == [
        "CREATED",
        "RESCHEDULED",
    ]

    replacement = book(client, domain, domain.client_b, "old-time-released", 15)
    assert replacement.status_code == 201
    assert second.status_code == 201


def test_client_cannot_cancel_past_or_cancel_twice(client, session):
    domain = create_booking_domain(session)
    with SessionLocal.begin() as direct:
        appointment = Appointment(
            organization_id=domain.organization.id,
            branch_id=domain.branch.id,
            client_user_id=domain.client_a.id,
            employee_id=domain.employee.id,
            service_id=domain.service.id,
            starts_at=datetime(2000, 1, 3, 10, tzinfo=timezone.utc),
            ends_at=datetime(2000, 1, 3, 11, tzinfo=timezone.utc),
            status=AppointmentStatus.BOOKED,
            idempotency_key="past-cancellation",
            idempotency_fingerprint="b" * 64,
        )
        direct.add(appointment)
        direct.flush()
        past_id = appointment.id

    headers = auth_headers(client, domain.client_a)
    past_cancel = client.post(
        f"/appointments/{past_id}/cancel",
        json={"reason": "Too late"},
        headers=headers,
    )
    assert past_cancel.status_code == 409
    assert error_code(past_cancel) == "CANCELLATION_WINDOW_CLOSED"

    past_reschedule = client.post(
        f"/appointments/{past_id}/reschedule",
        json={"starts_at": "2099-01-05T17:00:00Z"},
        headers=headers,
    )
    assert past_reschedule.status_code == 409
    assert error_code(past_reschedule) == "RESCHEDULE_WINDOW_CLOSED"

    future = book(client, domain, domain.client_a, "cancel-twice", 15)
    assert client.post(
        f"/appointments/{future.json()['id']}/cancel",
        json={"reason": "First"},
        headers=headers,
    ).status_code == 200
    second_cancel = client.post(
        f"/appointments/{future.json()['id']}/cancel",
        json={"reason": "Second"},
        headers=headers,
    )
    assert second_cancel.status_code == 409
    assert error_code(second_cancel) == "INVALID_APPOINTMENT_STATUS_TRANSITION"

    with SessionLocal() as check:
        stored = check.scalar(select(Appointment).where(Appointment.id == past_id))
        assert stored.status is AppointmentStatus.BOOKED
