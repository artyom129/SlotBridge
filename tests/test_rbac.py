from __future__ import annotations

from app.database import SessionLocal
from app.models import User, UserRole
from app.security import hash_password


PASSWORD = "Role-Test-Password-2026!"


def create_user(email: str, role: UserRole) -> None:
    with SessionLocal.begin() as session:
        session.add(
            User(
                email=email,
                password_hash=hash_password(PASSWORD),
                first_name="Role",
                last_name=role.value.title(),
                role=role,
                is_active=True,
            )
        )


def token_for(client, email: str) -> str:
    response = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_only_admin_can_create_organization(client):
    create_user("client-role@example.com", UserRole.CLIENT)
    create_user("employee-role@example.com", UserRole.EMPLOYEE)
    create_user("admin-role@example.com", UserRole.ADMIN)
    payload = {"name": "RBAC Organization", "slug": "rbac-org", "timezone": "UTC"}

    for email in ("client-role@example.com", "employee-role@example.com"):
        response = client.post(
            "/admin/organizations",
            json=payload,
            headers={"Authorization": f"Bearer {token_for(client, email)}"},
        )
        assert response.status_code == 403

    admin_response = client.post(
        "/admin/organizations",
        json=payload,
        headers={"Authorization": f"Bearer {token_for(client, 'admin-role@example.com')}"},
    )
    assert admin_response.status_code == 201
    assert admin_response.json()["slug"] == "rbac-org"
