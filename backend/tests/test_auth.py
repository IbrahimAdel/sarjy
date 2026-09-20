from fastapi.testclient import TestClient

import main
from auth.security import ACCESS_TOKEN_TYPE, REFRESH_TOKEN_TYPE, decode_claims
from database import get_settings

PASSWORD = "password123"


def _register(client: TestClient, email: str, password: str = PASSWORD):
    return client.post("/auth/register", json={"email": email, "password": password})


def _login(client: TestClient, email: str, password: str = PASSWORD):
    return client.post("/auth/login", json={"email": email, "password": password})


def test_register_returns_created_user():
    with TestClient(main.app) as client:
        response = _register(client, "Create.User@Example.com")

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "create.user@example.com"
    assert body["name"] == "create.user"
    assert body["id"]
    assert "password" not in body


def test_register_duplicate_email_conflicts():
    with TestClient(main.app) as client:
        assert _register(client, "dupe@example.com").status_code == 201
        assert _register(client, "dupe@example.com").status_code == 409


def test_register_validates_input():
    with TestClient(main.app) as client:
        assert _register(client, "short@example.com", "short").status_code == 422
        assert _register(client, "not-an-email").status_code == 422


def test_login_returns_usable_token():
    with TestClient(main.app) as client:
        assert _register(client, "login@example.com").status_code == 201
        response = _login(client, "login@example.com")

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"

    claims = decode_claims(body["access_token"], ACCESS_TOKEN_TYPE)
    assert claims["email"] == "login@example.com"
    assert claims["name"] == "login"
    assert claims["sub"]

    refresh_claims = decode_claims(body["refresh_token"], REFRESH_TOKEN_TYPE)
    assert refresh_claims["type"] == "refresh"


def test_login_rejects_wrong_password():
    with TestClient(main.app) as client:
        _register(client, "wrongpass@example.com")
        response = _login(client, "wrongpass@example.com", "nope")

    assert response.status_code == 401


def test_login_rejects_unknown_email():
    with TestClient(main.app) as client:
        response = _login(client, "ghost@example.com")

    assert response.status_code == 401


def test_refresh_reissues_tokens():
    with TestClient(main.app) as client:
        _register(client, "refresh@example.com")
        tokens = _login(client, "refresh@example.com").json()
        response = client.post(
            "/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
        )

    assert response.status_code == 200
    claims = decode_claims(response.json()["access_token"], ACCESS_TOKEN_TYPE)
    assert claims["email"] == "refresh@example.com"
    assert claims["name"] == "refresh"


def test_refresh_rejects_access_token():
    with TestClient(main.app) as client:
        _register(client, "refresh-bad@example.com")
        tokens = _login(client, "refresh-bad@example.com").json()
        response = client.post(
            "/auth/refresh", json={"refresh_token": tokens["access_token"]}
        )

    assert response.status_code == 401


def test_cors_allows_configured_origin():
    origin = get_settings().cors_origins()[0]
    with TestClient(main.app) as client:
        response = client.get("/", headers={"Origin": origin})

    assert response.headers["access-control-allow-origin"] == origin
