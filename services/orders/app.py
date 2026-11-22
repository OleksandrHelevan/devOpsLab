import json
import logging
import os
import random
import socket
import time

from flask import Flask, g, jsonify, request
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

app = Flask(__name__)

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("orders")

REQUESTS = Counter(
    "http_requests_total", "HTTP requests", ["method", "route", "status"]
)
LATENCY = Histogram(
    "http_request_duration_seconds", "Request latency", ["route"]
)
FAIL_RATE = float(os.getenv("FAIL_RATE", "0"))
SKIP = {"/metrics", "/health"}


@app.before_request
def before():
    g.t0 = time.perf_counter()
    if request.path not in SKIP and random.random() < FAIL_RATE:
        return {"error": "injected failure"}, 500
    return None


@app.after_request
def after(resp):
    if request.path in SKIP:
        return resp
    # шаблон маршруту, а не сирий URL (щоб не було високої кардинальності)
    route = request.url_rule.rule if request.url_rule else "unknown"
    dt = time.perf_counter() - g.t0
    REQUESTS.labels(request.method, route, str(resp.status_code)).inc()
    LATENCY.labels(route).observe(dt)
    log.info(
        json.dumps(
            {
                "level": "error" if resp.status_code >= 500 else "info",
                "msg": "request",
                "method": request.method,
                "route": route,
                "status": resp.status_code,
                "duration_ms": round(dt * 1000, 1),
                "version": os.getenv("APP_VERSION", "dev"),
            }
        )
    )
    return resp


@app.get("/metrics")
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


@app.get("/health")
def health():
    return jsonify(service="orders", status="ok")


@app.get("/config")
def config():
    return jsonify(
        app_env=os.environ.get("APP_ENV", "development"),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
        orders_region=os.environ.get("ORDERS_REGION", "local"),
    )


@app.get("/version")
def version():
    return jsonify(version=os.environ.get("APP_VERSION", "development"))


@app.get("/instance")
def instance():
    return jsonify(instance=os.environ.get("HOSTNAME", socket.gethostname()))


@app.get("/")
def root():
    return jsonify(service="orders", status="ok")


@app.get("/orders")
def orders():
    return jsonify(orders=[{"id": 1001, "status": "created"}])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8001)
