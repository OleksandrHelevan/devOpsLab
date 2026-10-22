import os
import socket

from flask import Flask, jsonify

app = Flask(__name__)


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


@app.get("/orders")
def orders():
    return jsonify(orders=[{"id": 1001, "status": "created"}])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8001)