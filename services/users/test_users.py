from services.users.app import app


def test_health():
    response = app.test_client().get("/health")

    assert response.status_code == 200
    assert response.json == {"service": "users", "status": "ok"}


def test_users():
    response = app.test_client().get("/users")

    assert response.status_code == 200
    assert response.json["users"][0]["name"] == "Ada Lovelace"