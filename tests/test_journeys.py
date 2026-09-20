from datetime import datetime, time, timezone
from decimal import Decimal

from sqlalchemy import func, select

from app.models import Appointment, EmployeeService, Service
from tests.booking_support import (
    BOOKING_DATE,
    auth_headers,
    create_booking_domain,
)


def _domain_with_two_services(session):
    domain = create_booking_domain(session, duration_minutes=30)
    second = Service(
        organization_id=domain.organization.id,
        name="Second Service",
        description="Second step",
        duration_minutes=30,
        price=Decimal("15.00"),
        is_active=True,
    )
    session.add(second)
    session.flush()
    session.add(
        EmployeeService(
            employee_id=domain.employee.id,
            service_id=second.id,
            organization_id=domain.organization.id,
        )
    )
    session.commit()
    return domain, second


def _plan_payload(domain, second):
    return {
        "branch_id": str(domain.branch.id),
        "service_ids": [str(domain.service.id), str(second.id)],
        "date": BOOKING_DATE.isoformat(),
        "after_time": "09:00",
        "before_time": "12:00",
    }


def test_journey_returns_three_real_availability_strategies(client, session):
    domain, second = _domain_with_two_services(session)
    response = client.post(
        "/journeys/plan",
        headers=auth_headers(client, domain.client_a),
        json=_plan_payload(domain, second),
    )

    assert response.status_code == 200
    payload = response.json()
    assert [route["strategy"] for route in payload["routes"]] == [
        "FASTEST",
        "EARLIEST",
        "FEWEST_EMPLOYEES",
    ]
    assert all(len(route["steps"]) == 2 for route in payload["routes"])
    assert all(route["wait_minutes"] >= 0 for route in payload["routes"])
    first = payload["routes"][0]["steps"]
    assert first[0]["ends_at"] <= first[1]["starts_at"]


def test_journey_booking_is_atomic_and_idempotent(client, session):
    domain, second = _domain_with_two_services(session)
    headers = auth_headers(client, domain.client_a)
    planned = client.post(
        "/journeys/plan",
        headers=headers,
        json=_plan_payload(domain, second),
    ).json()["routes"][0]
    body = {
        "branch_id": str(domain.branch.id),
        "steps": [
            {
                "service_id": step["service"]["id"],
                "employee_id": step["employee"]["id"],
                "starts_at": step["starts_at"],
            }
            for step in planned["steps"]
        ],
        "client_note": "One visit",
    }
    journey_headers = {**headers, "Idempotency-Key": "journey-success"}

    created = client.post("/journeys/book", headers=journey_headers, json=body)
    replayed = client.post("/journeys/book", headers=journey_headers, json=body)

    assert created.status_code == 201
    assert len(created.json()["appointments"]) == 2
    assert replayed.status_code == 200
    assert replayed.headers["Idempotency-Replayed"] == "true"
    assert [x["id"] for x in replayed.json()["appointments"]] == [
        x["id"] for x in created.json()["appointments"]
    ]


def test_conflict_rolls_back_whole_journey_and_replans_alternative(client, session):
    domain, second = _domain_with_two_services(session)
    client_headers = auth_headers(client, domain.client_a)
    planned = client.post(
        "/journeys/plan",
        headers=client_headers,
        json=_plan_payload(domain, second),
    ).json()["routes"][0]
    second_step = planned["steps"][1]
    occupied = client.post(
        "/appointments",
        headers={
            **auth_headers(client, domain.client_b),
            "Idempotency-Key": "occupy-second-step",
        },
        json={
            "branch_id": str(domain.branch.id),
            "employee_id": second_step["employee"]["id"],
            "service_id": second_step["service"]["id"],
            "starts_at": second_step["starts_at"],
        },
    )
    assert occupied.status_code == 201

    attempted = client.post(
        "/journeys/book",
        headers={**client_headers, "Idempotency-Key": "journey-conflict"},
        json={
            "branch_id": str(domain.branch.id),
            "steps": [
                {
                    "service_id": step["service"]["id"],
                    "employee_id": step["employee"]["id"],
                    "starts_at": step["starts_at"],
                }
                for step in planned["steps"]
            ],
        },
    )
    assert attempted.status_code == 409
    assert attempted.json()["detail"]["code"] == "JOURNEY_CONFLICT"
    assert session.scalar(
        select(func.count(Appointment.id)).where(
            Appointment.client_user_id == domain.client_a.id
        )
    ) == 0

    alternative = client.post(
        "/journeys/plan",
        headers=client_headers,
        json=_plan_payload(domain, second),
    )
    assert alternative.status_code == 200
    assert alternative.json()["routes"]
    assert (
        alternative.json()["routes"][0]["steps"][1]["starts_at"]
        != second_step["starts_at"]
    )
