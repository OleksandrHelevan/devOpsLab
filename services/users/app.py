from flask import Flask, jsonify

app = Flask(__name__)


@app.get("/health")
def health():
    return jsonify(service="users", status="ok")


@app.get("/users")
def users():
    return jsonify(users=[{"id": 1, "name": "Ada Lovelace"}])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)