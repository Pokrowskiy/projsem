def test_register_login_and_me(client):
    registration = client.post(
        "/api/v1/auth/register",
        json={"email": "buyer@example.com", "password": "strong-password", "role": "buyer"},
    )
    assert registration.status_code == 201
    token = registration.json()["access_token"]

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "buyer@example.com", "password": "strong-password"},
    )
    assert login.status_code == 200
    profile = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert profile.status_code == 200
    assert profile.json()["email"] == "buyer@example.com"
    updated = client.patch(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
        json={"full_name": "Buyer Example"},
    )
    assert updated.status_code == 200
    assert updated.json()["full_name"] == "Buyer Example"


def test_registration_rejects_admin_role(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "admin@example.com", "password": "strong-password", "role": "admin"},
    )
    assert response.status_code == 403


def test_registration_rejects_duplicate_email(client):
    payload = {"email": "duplicate@example.com", "password": "strong-password", "role": "buyer"}
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    assert client.post("/api/v1/auth/register", json=payload).status_code == 409


def test_auth_rejects_passwords_over_bcrypt_byte_limit(client):
    registration = client.post(
        "/api/v1/auth/register",
        json={"email": "long-password@example.com", "password": "x" * 73},
    )
    assert registration.status_code == 422

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "missing@example.com", "password": "я" * 37},
    )
    assert login.status_code == 422


def test_login_is_rate_limited(client):
    for _ in range(10):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "missing@example.com", "password": "incorrect-password"},
        )
        assert response.status_code == 401

    limited = client.post(
        "/api/v1/auth/login",
        json={"email": "missing@example.com", "password": "incorrect-password"},
    )
    assert limited.status_code == 429
