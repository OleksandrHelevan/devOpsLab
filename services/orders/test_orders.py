from services.orders import app as app_module
from services.orders.app import app


def test_health():
    response = app.test_client().get("/health")

    assert response.status_code == 200
    assert response.json == {"service": "orders", "status": "ok"}


def test_config_defaults(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    monkeypatch.delenv("ORDERS_REGION", raising=False)

    response = app.test_client().get("/config")

    assert response.status_code == 200
    assert response.json == {
        "app_env": "development",
        "log_level": "INFO",
        "orders_region": "local",
    }


def test_version_default(monkeypatch):
    monkeypatch.delenv("APP_VERSION", raising=False)

    response = app.test_client().get("/version")

    assert response.status_code == 200
    assert response.json == {"version": "development"}


def test_instance_is_reported():
    response = app.test_client().get("/instance")

    assert response.status_code == 200
    assert response.json["instance"]


def test_orders():
    response = app.test_client().get("/orders")

    assert response.status_code == 200
    assert response.json["orders"][0]["status"] == "created"

def test_metrics_endpoint_counts_requests():
    client = app_module.app.test_client()
    client.get("/orders")
    body = client.get("/metrics").get_data(as_text=True)
    assert 'http_requests_total{method="GET",route="/orders",status="200"}' in body
    assert "http_request_duration_seconds_bucket" in body


def test_fail_rate_injects_500(monkeypatch):
    monkeypatch.setattr(app_module, "FAIL_RATE", 1.0)
    client = app_module.app.test_client()
    assert client.get("/orders").status_code == 500
    assert client.get("/health").status_code == 200
