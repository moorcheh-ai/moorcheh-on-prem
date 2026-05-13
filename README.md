# Moorcheh Python client

Python **CLI** (and optional **Flask** demo) for the Moorcheh on-prem HTTP API. The `moorcheh up` / `moorcheh down` commands start and stop the bundled Docker Compose stack (server + Ollama) using images from Docker Hub—see the **server** repository for API behavior, image tags, and operational details.

## Requirements

- Python 3.10+
- Docker (for `moorcheh up` / `moorcheh down` only)

## Install

- From PyPI: `pip install moorcheh`
- From a checkout of this repo: `pip install .` (optional web UI: `pip install .[web]`)

## Quick start

- `moorcheh up` — start server and Ollama containers (pulls images as needed).
- `moorcheh status` — call `GET /health` on `http://localhost:8080` by default.
- `moorcheh down` — stop the stack.

Use `--base-url` on commands that call the API if the server is not on the default host/port.

## CLI commands

- `moorcheh up` — start server + Ollama via Compose.
- `moorcheh down` — stop Compose stack.
- `moorcheh status` — `GET /health`.
- `moorcheh namespace-create` — `POST /namespaces`.
- `moorcheh namespace-list` — `GET /namespaces`.
- `moorcheh namespace-delete` — `DELETE /namespaces/{namespace_name}`.
- `moorcheh namespace-delete-job-status` — `GET /namespaces/{namespace_name}/delete-jobs/{job_id}`.
- `moorcheh upload-documents` — `POST /namespaces/{namespace_name}/documents`.
- `moorcheh upload-vectors` — `POST /namespaces/{namespace_name}/vectors`.
- `moorcheh upload-job-status` — `GET /namespaces/{namespace_name}/upload-jobs/{job_id}`.
- `moorcheh items-get` — `POST /namespaces/{namespace_name}/items/get`.
- `moorcheh items-delete` — `POST /namespaces/{namespace_name}/items/delete`.
- `moorcheh search` — `POST /search`.

## Examples

- `moorcheh up`
- `moorcheh status`
- `moorcheh namespace-create --name docs --type text`
- `moorcheh upload-documents --namespace-name docs --documents-file docs-upload.json`
- `moorcheh upload-vectors --namespace-name products_vec --vectors-file vectors-upload.json`
- `moorcheh upload-job-status --namespace-name docs --job-id job-1`
- `moorcheh namespace-delete --namespace-name docs`
- `moorcheh namespace-delete-job-status --namespace-name docs --job-id job-abc123`
- `moorcheh items-get --namespace-name docs --ids-json "[\"doc-1\"]"`
- `moorcheh items-delete --namespace-name docs --ids-json "[\"doc-1\"]"`
- `moorcheh search --query "on prem retrieval" --namespaces docs --top-k 5 --threshold 0.0 --metadata-json "{\"team\":\"ai\"}"`

Documents upload payload file example (`docs-upload.json`):

```json
{
  "documents": [
    {
      "id": "doc-1",
      "text": "Moorcheh on-prem retrieval test",
      "team": "ai"
    }
  ]
}
```

## Optional Flask demo

Install web extras (`pip install .[web]` from this repo, or include `web` if you publish extras on PyPI), then run:

- `python app.py`

Set `SERVER_BASE_URL` if the API is not at `http://localhost:8080`. The demo proxies requests to `localhost` on the port you choose in the UI.

## If the default API port is in use

- Start the stack on another host port: `moorcheh up --server-port 8081`
- Point CLI calls at it: add `--base-url http://localhost:8081` (and set `SERVER_BASE_URL` for the Flask app).

Ollama’s default host port is `11434`; resolving conflicts is part of your Docker/host setup and is documented with the **server** runtime, not duplicated here.
