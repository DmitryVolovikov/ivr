def test_docs_is_json(client):
    response = client.get("/docs")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    payload = response.json()
    assert isinstance(payload, (list, dict))


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_auth_flow(client):
    register_payload = {
        "email": "user@example.com",
        "display_name": "User",
        "password": "password123",
        "confirm_password": "password123",
    }
    register_response = client.post("/auth/register", json=register_payload)
    assert register_response.status_code == 200

    login_payload = {"email": "user@example.com", "password": "password123"}
    login_response = client.post("/auth/login", json=login_payload)
    assert login_response.status_code == 200
    token = login_response.json().get("access_token")
    assert token

    me_response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "user@example.com"
