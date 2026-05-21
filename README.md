# moorcheh-client (Python)

This directory publishes the **`moorcheh-client`** distribution on PyPI. The importable module is still `moorcheh` (`from moorcheh import MoorchehApiClient`).

## Install

- `pip install moorcheh-client` (from this directory: `pip install .`)

Default server image: `moorcheh/server:latest` (override with `moorcheh up --server-image …` or `MOORCHEH_SERVER_IMAGE` to pin a specific release).

## Data directory

`moorcheh up` stores your vectors and documents at:

- `~/.moorcheh/data` (e.g. `C:\Users\<you>\.moorcheh\data` on Windows)
- `moorcheh_data_store.json`, `namespace_registry.json`

`moorcheh down` stops containers but **keeps** `~/.moorcheh`. Back up that folder to save everything.

## CLI Commands

- `moorcheh up` — start Moorcheh; uses host Ollama on `127.0.0.1:11434` when already running
- `moorcheh down` — stop Moorcheh containers (does not stop host Ollama)
- `moorcheh status` — `GET /health` (items, max_items, remaining)
- `moorcheh namespace-create` — create a text or vector namespace
- `moorcheh namespace-list` — list namespaces and per-namespace `item_count`
- `moorcheh upload-documents` — `POST /namespaces/{namespace_name}/documents` (async job)
- `moorcheh upload-vectors` — `POST /namespaces/{namespace_name}/vectors` (async job)
- `moorcheh upload-job-status` — poll upload job (documents or vectors)
- `moorcheh items-get` — get items by id within a namespace
- `moorcheh items-delete` — delete items by id within a namespace
- `moorcheh namespace-delete` — delete a namespace and all its items
- `moorcheh search` — semantic search

## Global item limit (100k)

Moorcheh stores at most **100,000 items total** across all namespaces (text + vectors).

- Check quota: `moorcheh status` → `items`, `max_items`, `remaining`
- Uploads that would add **new** ids over the cap return **409** (entire batch rejected)
- Re-uploading an existing id in the same namespace is an update and does not use extra quota
- Deleting items or a namespace frees quota immediately

Item ids are **unique per namespace** (the same id string may exist in different namespaces).

## Examples

```bash
moorcheh up
moorcheh status
moorcheh namespace-create --name docs --type text
moorcheh namespace-create --name products_vec --type vector --vector-dimension 768
moorcheh upload-documents --namespace-name docs --documents-file docs-upload.json
moorcheh upload-vectors --namespace-name products_vec --vectors-file vectors-upload.json
moorcheh upload-job-status --namespace-name docs --job-id job-abc123
moorcheh items-get --namespace-name docs --ids-json "[\"doc-1\"]"
moorcheh items-delete --namespace-name docs --ids-json "[\"doc-1\"]"
moorcheh search --query "on prem retrieval" --namespaces docs --top-k 5
```

Documents upload payload (`docs-upload.json`):

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

## Python API

```python
from moorcheh import MoorchehApiClient, MoorchehApiError

client = MoorchehApiClient("http://localhost:8080")
health = client.health()
print(health["items"], health["remaining"])

try:
    client.upload_namespace_vectors("products_vec", {"vectors": [...]})
except MoorchehApiError as e:
    if e.is_item_limit_exceeded:
        print(e.body)  # items, max_items, requested_new
```

## Optional Flask Demo App

```bash
pip install .[web]
python client/app.py
```

## Ollama: host vs Docker

By default, `moorcheh up` uses Ollama on `http://127.0.0.1:11434` when it is already running (typical on Windows/macOS). It does **not** start a second Ollama container in that case.

```bash
moorcheh up
# Using Ollama already running at http://127.0.0.1:11434 (moorcheh-ollama container not started)
```

Force behavior:

```bash
moorcheh up --use-host-ollama    # never start moorcheh-ollama
moorcheh up --bundled-ollama     # always start moorcheh-ollama container
moorcheh up --bundled-ollama --ollama-port 11435   # bundled Ollama on another host port
```

## Port conflict fallback

If **8080** is busy:

```bash
moorcheh up --server-port 8081
moorcheh status --base-url http://localhost:8081
```

`moorcheh up` removes stale `moorcheh-onprem-server` (and `moorcheh-ollama` only when starting bundled Ollama). Data persists under `~/.moorcheh/data` across restarts.
