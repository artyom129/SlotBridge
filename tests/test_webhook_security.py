from __future__ import annotations

import hashlib
import hmac
import json

from app.database import SessionLocal
from app.models import User, UserRole
from app.security import hash_password


def admin_token(client) -> str:
    password = "Legacy-Admin-2026!"
    with SessionLocal.begin() as session:
        session.add(
            User(
                email="legacy-admin@example.com",
                password_hash=hash_password(password),
                first_name="Legacy",
                last_name="Admin",
                role=UserRole.ADMIN,
            )
        )
    response = client.post(
        "/auth/login",
        json={"email": "legacy-admin@example.com", "password": password},
    )
    return response.json()["access_token"]


def test_unsigned_webhook_is_rejected_and_valid_hmac_is_accepted(client):
    payload = {
        "messageId": "stage2-secure-event",
        "eventId": "appointmentBooking.created",
        "eventData": {
            "appointmentId": "stage2-secure-appointment",
            "startDateTime": "2026-09-10T10:00:00+00:00",
            "endDateTime": "2026-09-10T11:00:00+00:00",
        },
    }
    body = json.dumps(payload, separators=(",", ":")).encode()

    assert client.post("/webhooks/mindbody", content=body).status_code == 401
    signature = hmac.new(
        b"test-webhook-secret-with-at-least-32-chars", body, hashlib.sha256
    ).hexdigest()
    accepted = client.post(
        "/webhooks/mindbody",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-SlotBridge-Signature": f"sha256={signature}",
        },
    )
    assert accepted.status_code == 200


def test_legacy_operational_data_requires_admin_and_omits_raw_payload(client):
    assert client.get("/api/appointments").status_code == 401
    token = admin_token(client)
    response = client.get(
        "/api/appointments", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    for item in response.json()["items"]:
        assert "raw" not in item
        assert "origin_token" not in item


def test_readiness_uses_database(client):
    assert client.get("/api/v1/health/live").status_code == 200
    assert client.get("/api/v1/health/ready").status_code == 200
