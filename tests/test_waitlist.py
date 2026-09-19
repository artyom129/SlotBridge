from tests.booking_support import BOOKING_DATE, auth_headers, book, create_booking_domain


def test_waitlist_matches_after_cancellation_without_auto_booking(client, session):
    domain = create_booking_domain(session)
    booked = book(client, domain, domain.client_a, "owner-slot", 10)
    assert booked.status_code == 201
    created = client.post("/waitlist", headers=auth_headers(client, domain.client_b), json={
        "branch_id": str(domain.branch.id), "service_id": str(domain.service.id),
        "employee_id": str(domain.employee.id), "preferred_date": BOOKING_DATE.isoformat(),
        "preferred_start_time": "10:00:00", "preferred_end_time": "11:00:00",
    })
    assert created.status_code == 201
    cancelled = client.post(f"/appointments/{booked.json()['id']}/cancel", headers=auth_headers(client, domain.client_a), json={"reason":"waitlist test"})
    assert cancelled.status_code == 200
    items = client.get("/waitlist/me", headers=auth_headers(client, domain.client_b)).json()["items"]
    assert items[0]["status"] == "MATCHED"
    assert client.get("/appointments/me", headers=auth_headers(client, domain.client_b)).json()["items"] == []
    accepted = client.post(f"/waitlist/{items[0]['id']}/accept", headers={**auth_headers(client, domain.client_b), "Idempotency-Key":"accept-waitlist"})
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "ACCEPTED"
    assert len(client.get("/appointments/me", headers=auth_headers(client, domain.client_b)).json()["items"]) == 1
