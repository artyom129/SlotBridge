from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import select

from app.models import (
    Appointment,
    AppointmentStatus,
    Review,
    ReviewAuditAction,
    ReviewAuditLog,
    ReviewStatus,
)
from tests.booking_support import auth_headers, create_booking_domain


def completed_appointment(session, domain, client_user, *, hour: int = 10) -> Appointment:
    starts_at = datetime(2026, 1, 1, hour, tzinfo=timezone.utc)
    appointment = Appointment(
        organization_id=domain.organization.id,
        branch_id=domain.branch.id,
        client_user_id=client_user.id,
        employee_id=domain.employee.id,
        service_id=domain.service.id,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(minutes=domain.service.duration_minutes),
        status=AppointmentStatus.COMPLETED,
        idempotency_key=f"completed-{uuid4()}",
        idempotency_fingerprint=uuid4().hex,
    )
    session.add(appointment)
    session.commit()
    return appointment


def payload(appointment: Appointment, rating: int = 5) -> dict:
    return {
        "appointment_id": str(appointment.id),
        "overall_rating": rating,
        "quality_rating": rating,
        "service_rating": rating,
        "punctuality_rating": rating,
        "comment": "Excellent service",
        "is_anonymous": False,
    }


def create_review(client, domain, appointment, *, rating: int = 5):
    return client.post(
        "/reviews",
        headers=auth_headers(client, domain.client_a),
        json=payload(appointment, rating),
    )


def test_review_requires_completed_owned_appointment_and_is_unique(client, session):
    domain = create_booking_domain(session)
    completed = completed_appointment(session, domain, domain.client_a)
    pending = completed_appointment(session, domain, domain.client_a, hour=12)
    pending.status = AppointmentStatus.BOOKED
    foreign = completed_appointment(session, domain, domain.client_b, hour=14)
    session.commit()
    headers = auth_headers(client, domain.client_a)

    not_completed = client.post("/reviews", headers=headers, json=payload(pending))
    assert not_completed.status_code == 409
    assert not_completed.json()["detail"]["code"] == "APPOINTMENT_NOT_COMPLETED"

    not_owned = client.post("/reviews", headers=headers, json=payload(foreign))
    assert not_owned.status_code == 404

    created = client.post("/reviews", headers=headers, json=payload(completed))
    assert created.status_code == 201
    assert created.json()["employee_id"] == str(domain.employee.id)
    assert created.json()["service_id"] == str(domain.service.id)
    assert created.json()["can_edit"] is True

    duplicate = client.post("/reviews", headers=headers, json=payload(completed))
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"]["code"] == "REVIEW_ALREADY_EXISTS"


def test_rating_uses_only_published_reviews_and_recalculates(client, session):
    domain = create_booking_domain(session)
    first = completed_appointment(session, domain, domain.client_a)
    second = completed_appointment(session, domain, domain.client_b, hour=12)
    assert create_review(client, domain, first, rating=5).status_code == 201
    second_response = client.post(
        "/reviews",
        headers=auth_headers(client, domain.client_b),
        json=payload(second, 3),
    )
    assert second_response.status_code == 201

    rating = client.get(
        f"/employees/{domain.employee.id}/rating",
        headers=auth_headers(client, domain.client_a),
    )
    assert rating.status_code == 200
    assert rating.json()["average_rating"] == 4.0
    assert rating.json()["reviews_count"] == 2
    assert rating.json()["distribution"] == {"1": 0, "2": 0, "3": 1, "4": 0, "5": 1}

    review_id = second_response.json()["id"]
    hidden = client.patch(
        f"/admin/reviews/{review_id}/moderation",
        headers=auth_headers(client, domain.admin),
        json={"status": "HIDDEN", "reason": "Policy violation"},
    )
    assert hidden.status_code == 200
    rating = client.get(
        f"/employees/{domain.employee.id}/rating",
        headers=auth_headers(client, domain.client_a),
    )
    assert rating.json()["average_rating"] == 5.0
    assert rating.json()["reviews_count"] == 1


def test_edit_window_and_soft_delete_are_audited(client, session):
    domain = create_booking_domain(session)
    appointment = completed_appointment(session, domain, domain.client_a)
    created = create_review(client, domain, appointment)
    review_id = created.json()["id"]
    review = session.get(Review, UUID(review_id))
    review.created_at = datetime.now(timezone.utc) - timedelta(hours=25)
    session.commit()

    expired = client.patch(
        f"/reviews/{review_id}",
        headers=auth_headers(client, domain.client_a),
        json={"comment": "Too late"},
    )
    assert expired.status_code == 409
    assert expired.json()["detail"]["code"] == "REVIEW_EDIT_WINDOW_EXPIRED"

    review.created_at = datetime.now(timezone.utc)
    session.commit()
    removed = client.delete(
        f"/reviews/{review_id}", headers=auth_headers(client, domain.client_a)
    )
    assert removed.status_code == 204
    session.refresh(review)
    assert review.status == ReviewStatus.HIDDEN
    actions = list(
        session.scalars(
            select(ReviewAuditLog.action).where(ReviewAuditLog.review_id == review.id)
        )
    )
    assert ReviewAuditAction.REVIEW_CREATED in actions
    assert ReviewAuditAction.REVIEW_HIDDEN in actions


def test_anonymous_review_hides_identity_but_owner_and_admin_keep_audit_identity(client, session):
    domain = create_booking_domain(session)
    appointment = completed_appointment(session, domain, domain.client_a)
    review_payload = payload(appointment)
    review_payload["is_anonymous"] = True
    created = client.post(
        "/reviews",
        headers=auth_headers(client, domain.client_a),
        json=review_payload,
    )
    assert created.status_code == 201
    assert created.json()["client_user_id"] == str(domain.client_a.id)

    public = client.get(
        f"/employees/{domain.employee.id}/reviews",
        headers=auth_headers(client, domain.client_b),
    )
    item = public.json()["items"][0]
    assert item["client_display_name"] == "Anonymous"
    assert item["client_user_id"] is None
    assert item["appointment_id"] is None

    admin = client.get(
        f"/reviews/{created.json()['id']}",
        headers=auth_headers(client, domain.admin),
    )
    assert admin.json()["client_user_id"] == str(domain.client_a.id)


def test_report_reply_moderation_permissions_and_tenant_isolation(client, session):
    first = create_booking_domain(session)
    second = create_booking_domain(session)
    appointment = completed_appointment(session, first, first.client_a)
    created = create_review(client, first, appointment)
    review_id = created.json()["id"]

    cross_tenant = client.get(
        f"/reviews/{review_id}", headers=auth_headers(client, second.admin)
    )
    assert cross_tenant.status_code == 404

    wrong_employee = client.put(
        f"/reviews/{review_id}/reply",
        headers=auth_headers(client, second.employee_user),
        json={"text": "Not allowed"},
    )
    assert wrong_employee.status_code == 404

    reply = client.put(
        f"/reviews/{review_id}/reply",
        headers=auth_headers(client, first.employee_user),
        json={"text": "Thank you!"},
    )
    assert reply.status_code == 200
    assert reply.json()["author_label"] == first.employee.display_name

    report = client.post(
        f"/reviews/{review_id}/reports",
        headers=auth_headers(client, first.client_b),
        json={"reason": "inappropriate", "comment": "Please review"},
    )
    assert report.status_code == 201
    own_report = client.post(
        f"/reviews/{review_id}/reports",
        headers=auth_headers(client, first.client_a),
        json={"reason": "own"},
    )
    assert own_report.status_code == 409
    assert own_report.json()["detail"]["code"] == "CANNOT_REPORT_OWN_REVIEW"
    duplicate = client.post(
        f"/reviews/{review_id}/reports",
        headers=auth_headers(client, first.client_b),
        json={"reason": "inappropriate"},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["detail"]["code"] == "REVIEW_ALREADY_REPORTED"

    flagged_by_admin = client.patch(
        f"/admin/reviews/{review_id}/moderation",
        headers=auth_headers(client, first.admin),
        json={"status": "FLAGGED", "reason": "Needs moderation review"},
    )
    assert flagged_by_admin.status_code == 200

    flagged = client.get(
        f"/admin/organizations/{first.organization.id}/reviews?status=FLAGGED",
        headers=auth_headers(client, first.admin),
    )
    assert flagged.status_code == 200
    assert flagged.json()["items"][0]["reports"][0]["reason"] == "inappropriate"
    resolved = client.patch(
        f"/admin/review-reports/{report.json()['id']}",
        headers=auth_headers(client, first.admin),
        json={"status": "RESOLVED"},
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "RESOLVED"

    restored = client.patch(
        f"/admin/reviews/{review_id}/moderation",
        headers=auth_headers(client, first.admin),
        json={"status": "PUBLISHED", "reason": "Report reviewed"},
    )
    assert restored.status_code == 200
    assert restored.json()["status"] == "PUBLISHED"


def test_admin_analytics_filters_and_invalid_rating(client, session):
    domain = create_booking_domain(session)
    first = completed_appointment(session, domain, domain.client_a)
    second = completed_appointment(session, domain, domain.client_b, hour=12)
    assert create_review(client, domain, first, rating=5).status_code == 201
    assert client.post(
        "/reviews",
        headers=auth_headers(client, domain.client_b),
        json=payload(second, 2),
    ).status_code == 201

    analytics = client.get(
        f"/admin/organizations/{domain.organization.id}/reviews/analytics",
        headers=auth_headers(client, domain.admin),
    )
    assert analytics.status_code == 200
    assert analytics.json()["reviews_count"] == 2
    assert analytics.json()["average_rating"] == 3.5
    assert analytics.json()["negative_reviews_count"] == 1
    assert analytics.json()["by_employee"][0]["reviews_count"] == 2

    invalid = client.post(
        "/reviews",
        headers=auth_headers(client, domain.client_a),
        json={**payload(first), "overall_rating": 6},
    )
    assert invalid.status_code == 422


def test_ai_summary_sends_only_minimal_sanitized_review_data(
    client, session, monkeypatch
):
    domain = create_booking_domain(session)
    appointment = completed_appointment(session, domain, domain.client_a)
    review_data = payload(appointment)
    review_data["comment"] = "Call +7 777 123 45 67 or client@example.com. Great service."
    created = client.post(
        "/reviews",
        headers=auth_headers(client, domain.client_a),
        json=review_data,
    )
    assert created.status_code == 201
    captured = {}

    def fake_summary(_settings, rows, locale):
        captured["rows"] = rows
        captured["locale"] = locale
        return "Безопасная сводка"

    monkeypatch.setattr("app.api.reviews.summarize_reviews", fake_summary)
    response = client.get(
        f"/admin/organizations/{domain.organization.id}/reviews/ai-summary?locale=ru",
        headers=auth_headers(client, domain.admin),
    )
    assert response.status_code == 200
    assert response.json()["generated_by"] == "gemini"
    assert captured["locale"] == "ru"
    assert "client_user_id" not in captured["rows"][0]
    assert "appointment_id" not in captured["rows"][0]
    assert "client@example.com" not in captured["rows"][0]["comment"]
    assert "777 123" not in captured["rows"][0]["comment"]


def test_admin_can_configure_only_official_https_2gis_url(client, session):
    domain = create_booking_domain(session)
    headers = auth_headers(client, domain.admin)
    endpoint = f"/admin/organizations/{domain.organization.id}/review-settings"

    invalid = client.patch(
        endpoint,
        headers=headers,
        json={"external_review_url_2gis": "http://example.com/reviews"},
    )
    assert invalid.status_code == 422

    updated = client.patch(
        endpoint,
        headers=headers,
        json={"external_review_url_2gis": "https://2gis.kz/almaty/firm/example"},
    )
    assert updated.status_code == 200
    assert updated.json()["external_review_url_2gis"].startswith("https://2gis.kz/")
