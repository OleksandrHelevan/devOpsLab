from services.orders.app import app


def test_health():
    response = app.test_client().get("/health")

    assert response.status_code == 200
    assert response.json == {"service": "orders", "status": "ok"}


def test_orders():
    response = app.test_client().get("/orders")

    assert response.status_code == 200
    assert response.json["orders"][0]["status"] == "created"