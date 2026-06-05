from __future__ import annotations

import json
import os
from typing import Any

import requests
from flask import Flask, jsonify, render_template, request
from werkzeug.utils import secure_filename

from moorcheh.docker_runtime import ensure_upload_dir, host_path_to_container_upload_path
from moorcheh.user_config import LLM_PROVIDER_MODELS, load_embedding_config, load_llm_config


SERVER_BASE_URL = os.getenv("SERVER_BASE_URL", "http://localhost:8080")
FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))
DEFAULT_PROXY_TIMEOUT = int(os.getenv("MOORCHEH_PROXY_TIMEOUT", "30"))
ANSWER_PROXY_TIMEOUT = int(os.getenv("MOORCHEH_ANSWER_TIMEOUT", "180"))
FILE_PROXY_TIMEOUT = int(os.getenv("MOORCHEH_FILE_TIMEOUT", "600"))

app = Flask(__name__)


def _llm_models_for_template() -> dict[str, list[str]]:
    return {provider: [model_id for model_id, _ in models] for provider, models in LLM_PROVIDER_MODELS.items()}


@app.route("/", methods=["GET"])
def index():
    embedding = load_embedding_config()
    llm = load_llm_config(embedding=embedding)
    upload_dir = ensure_upload_dir()
    return render_template(
        "index.html",
        default_server_url=SERVER_BASE_URL,
        upload_dir=str(upload_dir),
        llm_models_json=json.dumps(_llm_models_for_template()),
        saved_llm_provider=llm.provider if llm else "ollama",
        saved_llm_model=llm.model if llm else "qwen2.5",
    )


@app.route("/files/stage", methods=["POST"])
def stage_file():
    """Save an uploaded browser file into ~/.moorcheh/uploads for Docker bind mount."""
    uploaded = request.files.get("file")
    if uploaded is None or not uploaded.filename:
        return jsonify({"ok": False, "message": "file is required"}), 400

    upload_root = ensure_upload_dir()
    safe_name = secure_filename(uploaded.filename)
    if not safe_name:
        return jsonify({"ok": False, "message": "invalid filename"}), 400

    destination = upload_root / safe_name
    uploaded.save(destination)
    container_path = host_path_to_container_upload_path(destination, upload_root)
    return jsonify(
        {
            "ok": True,
            "host_path": str(destination.resolve()),
            "container_path": container_path,
            "filename": safe_name,
            "upload_dir": str(upload_root.resolve()),
        }
    ), 200


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
    if path == "/answer":
        timeout = ANSWER_PROXY_TIMEOUT
    elif "/files" in path or "/file-jobs" in path:
        timeout = FILE_PROXY_TIMEOUT
    else:
        timeout = DEFAULT_PROXY_TIMEOUT
    try:
        if method == "GET":
            res = requests.get(target_url, timeout=timeout)
        elif method == "POST":
            res = requests.post(target_url, json=payload, timeout=timeout)
        else:
            res = requests.delete(target_url, json=payload, timeout=timeout)
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
