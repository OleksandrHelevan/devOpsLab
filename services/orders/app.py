import os

from flask import Flask, jsonify

app = Flask(__name__)


@app.get("/health")
def health():
    return jsonify(service="orders", status="ok")


@app.get("/orders")
def orders():
    return jsonify(orders=[{"id": 1001, "status": "created"}])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8001)