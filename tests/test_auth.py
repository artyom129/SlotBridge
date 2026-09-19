from __future__ import annotations

from sqlalchemy import select

from app.config import Settings, get_settings
from app.main import app
from app.models import Organization, OrganizationMembership, User, UserRole


REGISTER_PAYLOAD = {
    "email": "client@example.com",
    "password": "Correct-Horse-2026!",
    "first_name": "Demo",
    "last_name": "Client",
}


def test_registration_hashes_password_and_forces_client_role(client, session):
    response = client.post("/auth/register", json=REGISTER_PAYLOAD)

    assert response.status_code == 201
    assert response.json()["role"] == UserRole.CLIENT.value
    assert "password_hash" not in response.json()
    user = session.scalar(select(User).where(User.email == REGISTER_PAYLOAD["email"]))
    assert user is not None
    assert user.password_hash != REGISTER_PAYLOAD["password"]
    assert user.password_hash.startswith("$argon2")


def test_registration_joins_existing_demo_organization_in_non_production(client, session):
    organization = Organization(
        name="SlotBridge Demo",
        slug="slotbridge-demo",
        timezone="Asia/Almaty",
        is_active=True,
    )
    session.add(organization)
    session.commit()

    response = client.post("/auth/register", json=REGISTER_PAYLOAD)

    assert response.status_code == 201
    user = session.scalar(select(User).where(User.email == REGISTER_PAYLOAD["email"]))
    assert user is not None
    assert (
        session.get(
            OrganizationMembership,
            {"user_id": user.id, "organization_id": organization.id},
        )
        is not None
    )


def test_registration_can_join_configured_public_demo_in_production(client, session):
    organization = Organization(
        name="SlotBridge Demo",
        slug="portfolio-demo",
        timezone="Asia/Almaty",
        is_active=True,
    )
    session.add(organization)
    session.commit()
    production_settings = Settings(
        database_url="postgresql://user:password@db/slotbridge?sslmode=require",
        jwt_secret="production-test-secret-with-more-than-32-characters",
        slotbridge_environment="production",
        public_demo_registration_enabled=True,
        public_demo_organization_slug="portfolio-demo",
    )
    app.dependency_overrides[get_settings] = lambda: production_settings

    response = client.post("/auth/register", json=REGISTER_PAYLOAD)

    assert response.status_code == 201
    user = session.scalar(select(User).where(User.email == REGISTER_PAYLOAD["email"]))
    assert user is not None
    assert (
        session.get(
            OrganizationMembership,
            {"user_id": user.id, "organization_id": organization.id},
        )
        is not None
    )


def test_duplicate_email_is_rejected_case_insensitively(client):
    assert client.post("/auth/register", json=REGISTER_PAYLOAD).status_code == 201
    duplicate = {**REGISTER_PAYLOAD, "email": "CLIENT@EXAMPLE.COM"}
    response = client.post("/auth/register", json=duplicate)

    assert response.status_code == 409


def test_login_success_wrong_password_and_me_authentication(client):
    client.post("/auth/register", json=REGISTER_PAYLOAD)

    wrong = client.post(
        "/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": "wrong-password"},
    )
    assert wrong.status_code == 401
    assert client.get("/auth/me").status_code == 401

    login = client.post(
        "/auth/login",
        json={"email": REGISTER_PAYLOAD["email"], "password": REGISTER_PAYLOAD["password"]},
    )
    assert login.status_code == 200
    assert login.json()["token_type"] == "bearer"
    assert login.json()["expires_in"] == 1800

    me = client.get(
        "/auth/me", headers={"Authorization": f"Bearer {login.json()['access_token']}"}
    )
    assert me.status_code == 200
    assert me.json()["email"] == REGISTER_PAYLOAD["email"]
