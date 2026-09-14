from __future__ import annotations

from tests.booking_support import (
    auth_headers,
    book,
    create_booking_domain,
)


def test_detail_access_is_owned_assigned_and_tenant_scoped(client, session):
    first = create_booking_domain(session)
    second = create_booking_domain(session)
    booked = book(client, first, first.client_a, "security-detail", 15)
    appointment_id = booked.json()["id"]

    assert client.get(
        f"/appointments/{appointment_id}",
        headers=auth_headers(client, first.client_a),
    ).status_code == 200
    assert client.get(
        f"/appointments/{appointment_id}",
        headers=auth_headers(client, first.client_b),
    ).status_code == 404
    assert client.get(
        f"/appointments/{appointment_id}",
        headers=auth_headers(client, first.employee_user),
    ).status_code == 200
    assert client.get(
        f"/appointments/{appointment_id}",
        headers=auth_headers(client, first.admin),
    ).status_code == 200

    assert client.get(
        f"/appointments/{appointment_id}",
        headers=auth_headers(client, second.employee_user),
    ).status_code == 404
    assert client.get(
        f"/appointments/{appointment_id}",
        headers=auth_headers(client, second.admin),
    ).status_code == 404


def test_client_cannot_cancel_another_clients_appointment(client, session):
    domain = create_booking_domain(session)
    booked = book(client, domain, domain.client_a, "owner-cancel", 15)

    response = client.post(
        f"/appointments/{booked.json()['id']}/cancel",
        json={"reason": "Not mine"},
        headers=auth_headers(client, domain.client_b),
    )

    assert response.status_code == 404
    detail = client.get(
        f"/appointments/{booked.json()['id']}",
        headers=auth_headers(client, domain.client_a),
    )
    assert detail.json()["status"] == "BOOKED"


def test_client_cannot_manage_status_and_employee_cannot_cross_tenant(client, session):
    first = create_booking_domain(session)
    second = create_booking_domain(session)
    booked = book(client, first, first.client_a, "status-security", 15)
    appointment_id = booked.json()["id"]

    client_attempt = client.post(
        f"/appointments/{appointment_id}/status",
        json={"status": "CONFIRMED"},
        headers=auth_headers(client, first.client_a),
    )
    assert client_attempt.status_code == 403

    cross_tenant = client.post(
        f"/appointments/{appointment_id}/status",
        json={"status": "CONFIRMED"},
        headers=auth_headers(client, second.employee_user),
    )
    assert cross_tenant.status_code == 404

    cross_tenant_admin = client.post(
        f"/appointments/{appointment_id}/cancel",
        json={"reason": "Wrong organization"},
        headers=auth_headers(client, second.admin),
    )
    assert cross_tenant_admin.status_code == 404


def test_assigned_employee_and_organization_admin_can_manage_allowed_record(client, session):
    domain = create_booking_domain(session)
    employee_booking = book(client, domain, domain.client_a, "employee-status", 15)
    admin_booking = book(client, domain, domain.client_b, "admin-cancel", 16)
    employee_cancel_booking = book(
        client, domain, domain.client_a, "employee-cancel", 17
    )

    confirmed = client.post(
        f"/appointments/{employee_booking.json()['id']}/status",
        json={"status": "CONFIRMED", "reason": "Employee confirmed"},
        headers=auth_headers(client, domain.employee_user),
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["status"] == "CONFIRMED"

    cancelled = client.post(
        f"/appointments/{admin_booking.json()['id']}/cancel",
        json={"reason": "Admin cancellation"},
        headers=auth_headers(client, domain.admin),
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "CANCELLED"

    employee_cancelled = client.post(
        f"/appointments/{employee_cancel_booking.json()['id']}/cancel",
        json={"reason": "Assigned employee cancellation"},
        headers=auth_headers(client, domain.employee_user),
    )
    assert employee_cancelled.status_code == 200
    assert employee_cancelled.json()["status"] == "CANCELLED"
