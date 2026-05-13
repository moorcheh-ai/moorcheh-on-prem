from __future__ import annotations

import json
import os
from typing import Any

import requests
from flask import Flask, jsonify, render_template, request


SERVER_BASE_URL = os.getenv("SERVER_BASE_URL", "http://localhost:8080")
FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))

app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", default_server_url=SERVER_BASE_URL)


@app.route("/proxy", methods=["POST"])
def proxy():
    body = request.get_json(silent=True) or {}
    method = str(body.get("method", "GET")).upper()
    path = str(body.get("path", ""))
    payload = body.get("payload")
    port = str(body.get("port", "8080"))

    if method not in {"GET", "POST", "DELETE"}:
        return jsonify({"ok": False, "status": 400, "data": {"message": "unsupported method"}}), 400
    if not path.startswith("/"):
        return jsonify({"ok": False, "status": 400, "data": {"message": "path must start with /"}}), 400

    target_url = f"http://localhost:{port}{path}"
    try:
        if method == "GET":
            res = requests.get(target_url, timeout=30)
        elif method == "POST":
            res = requests.post(target_url, json=payload, timeout=30)
        else:
            res = requests.delete(target_url, json=payload, timeout=30)
    except Exception as exc:  # pragma: no cover
        app.logger.exception("Proxy request failed: %s", exc)
        return jsonify({"ok": False, "status": 0, "data": {"message": "request to upstream service failed"}}), 200

    response_data: Any
    try:
        response_data = res.json()
    except Exception:
        response_data = {"raw": res.text}

    return jsonify({"ok": res.ok, "status": res.status_code, "data": response_data}), 200


if __name__ == "__main__":
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=True)
