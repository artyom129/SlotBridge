from tests.booking_support import PASSWORD, auth_headers, create_booking_domain


def test_current_client_can_edit_only_profile_fields(client, session):
    domain = create_booking_domain(session)
    response = client.patch(
        "/auth/me",
        headers=auth_headers(client, domain.client_a),
        json={
            "first_name": "Новый",
            "last_name": "Клиент",
            "phone": "+7 700 000 00 00",
            "role": "ADMIN",
        },
    )
    assert response.status_code == 200
    assert response.json()["first_name"] == "Новый"
    assert response.json()["role"] == "CLIENT"


def test_public_version_manifest_has_expected_shape(client):
    response = client.get("/api/v1/app/version")
    assert response.status_code == 200
    assert response.json()["version_code"] == 9
    assert response.json()["required"] is False
    assert response.json()["apk_url"].startswith("https://")
    assert set(response.json()["changelog"]) == {"ru", "en"}
    assert len(response.json()["sha256"]) == 64
