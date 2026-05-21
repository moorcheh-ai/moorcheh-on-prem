# moorcheh-client

Python package for **Moorcheh on-prem**: start the runtime with one command and call the API from your application.

- **PyPI name:** `moorcheh-client`
- **Import:** `from moorcheh import MoorchehApiClient, MoorchehApiError`
- **CLI:** `moorcheh` (after install)

Requires [Docker](https://www.docker.com/). Pulls `moorcheh/server:latest` from Docker Hub on first `moorcheh up`.

## Install

```bash
pip install moorcheh-client
```

Local development:

```bash
pip install -e .
```

## Quick start

**1. Start Moorcheh**

```bash
moorcheh up
```

API: `http://localhost:8080`  
Data: `~/.moorcheh/data` (e.g. `C:\Users\<you>\.moorcheh\data` on Windows)

**2. Use from Python**

```python
from moorcheh import MoorchehApiClient

client = MoorchehApiClient("http://localhost:8080")
print(client.health())  # items, max_items, remaining
```

**3. Stop (data is kept)**

```bash
moorcheh down
```

---

## Python API

Use `MoorchehApiClient` in your app. Moorcheh must already be running (`moorcheh up` or your own deployment on port 8080).

### Connect

```python
from moorcheh import MoorchehApiClient, MoorchehApiError

client = MoorchehApiClient("http://localhost:8080", timeout=30)
```

### Health and quota

```python
health = client.health()
# status, model, items, max_items, remaining
```

### Namespaces

```python
client.create_namespace({
    "namespace_name": "docs",
    "type": "text",
})

client.create_namespace({
    "namespace_name": "products_vec",
    "type": "vector",
    "vector_dimension": 768,
})

namespaces = client.list_namespaces()
client.delete_namespace("docs")  # async; returns job_id
```

### Upload documents (async)

```python
resp = client.upload_namespace_documents("docs", {
    "documents": [
        {
            "id": "doc-1",
            "text": "Moorcheh on-prem retrieval test",
            "team": "ai",
        }
    ],
})
job_id = resp["job_id"]

# Poll until status == "completed"
status = client.upload_job_status("docs", job_id)
```

### Upload vectors (async)

```python
resp = client.upload_namespace_vectors("products_vec", {
    "vectors": [
        {
            "id": "vec-1",
            "vector": [0.1, 0.2, 0.3],  # length must match namespace dimension
            "source": "demo",
        }
    ],
})
job_id = resp["job_id"]
client.upload_job_status("products_vec", job_id)
```

### Search

```python
# Text query (text namespaces)
results = client.search({
    "query": "on prem retrieval",
    "namespaces": ["docs"],
    "top_k": 5,
    "threshold": 0.0,
    "metadata": {"team": "ai"},  # optional filter
})

# Vector query (vector namespaces)
results = client.search({
    "query": [0.1, 0.2, 0.3],
    "namespaces": ["products_vec"],
    "top_k": 5,
})
```

### Get and delete items

Item ids are **unique per namespace** (the same id string may exist in different namespaces).

```python
client.get_namespace_items("docs", {"ids": ["doc-1"]})
client.delete_namespace_items("docs", {"ids": ["doc-1"]})
```

### Errors (including 100k limit)

```python
try:
    client.upload_namespace_documents("docs", {"documents": [...]})
except MoorchehApiError as e:
    if e.is_item_limit_exceeded:  # HTTP 409
        print(e.body)  # items, max_items, requested_new
    else:
        print(e.status_code, e)
```

### Typical app flow

```python
client = MoorchehApiClient("http://localhost:8080")

client.create_namespace({"namespace_name": "myapp", "type": "text"})
resp = client.upload_namespace_documents("myapp", {"documents": [...]})

import time
job_id = resp["job_id"]
while True:
    job = client.upload_job_status("myapp", job_id)
    if job.get("status") == "completed":
        break
    time.sleep(0.5)

hits = client.search({
    "query": "user question here",
    "namespaces": ["myapp"],
    "top_k": 10,
})
```

---

## Data storage

Vectors and documents are stored on your machine at:

| Path | Contents |
|------|----------|
| `~/.moorcheh/data/moorcheh_data_store.json` | All items |
| `~/.moorcheh/data/namespace_registry.json` | Namespace definitions |

- Created automatically on first `moorcheh up`
- **Not** inside your Python project folder
- Survives `moorcheh down` — back up `~/.moorcheh` to save everything

---

## Global item limit (100k)

- At most **100,000 items** total (text + vectors, all namespaces)
- `client.health()` or `moorcheh status` → `items`, `max_items`, `remaining`
- New ids over the cap → **409** (whole batch rejected)
- Re-uploading an existing id in the same namespace = update (no extra quota)
- Delete items or a namespace to free quota

---

## CLI reference

For local ops and testing. Most app code should use the **Python API** above.

| Command | Description |
|---------|-------------|
| `moorcheh up` | Start Moorcheh (`moorcheh/server:latest`) |
| `moorcheh down` | Stop containers; keeps `~/.moorcheh` |
| `moorcheh status` | Health + quota |
| `moorcheh namespace-create --name X --type text` | Create text namespace |
| `moorcheh namespace-create --name X --type vector --vector-dimension 768` | Create vector namespace |
| `moorcheh namespace-list` | List namespaces |
| `moorcheh namespace-delete --namespace-name X` | Delete namespace (async) |
| `moorcheh upload-documents --namespace-name X --documents-file file.json` | Upload documents |
| `moorcheh upload-vectors --namespace-name X --vectors-file file.json` | Upload vectors |
| `moorcheh upload-job-status --namespace-name X --job-id JOB` | Poll upload job |
| `moorcheh items-get --namespace-name X --ids-json '["id1"]'` | Get items |
| `moorcheh items-delete --namespace-name X --ids-json '["id1"]'` | Delete items |
| `moorcheh search --query "..." --namespaces docs --top-k 5` | Semantic search |

API commands accept `--base-url http://localhost:8080` (default).

### `moorcheh up` options

| Flag | Default | Purpose |
|------|---------|---------|
| `--server-port` | `8080` | Host port for API |
| `--server-image` | `moorcheh/server:latest` | Docker image |
| `--ollama-port` | `11434` | Host port to detect/use Ollama |
| `--use-host-ollama` | off | Never start `moorcheh-ollama` container |
| `--bundled-ollama` | off | Always start Ollama in Docker |
| `--bundled-ollama --ollama-port 11435` | — | Bundled Ollama on another port if 11434 is taken |

By default, if Ollama is already running on `127.0.0.1:11434`, `moorcheh up` reuses it and does not start a second Ollama container.

### CLI example (documents file)

`docs-upload.json`:

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

```bash
moorcheh upload-documents --namespace-name docs --documents-file docs-upload.json
moorcheh upload-job-status --namespace-name docs --job-id <job_id from response>
```

---

## Optional: endpoint tester (Flask)

Internal browser UI to hit all endpoints (not for production apps):

```bash
pip install .[web]
python app.py
```

Open `http://localhost:5000`. Requires `moorcheh up` on port 8080.

---

## Requirements

- Python 3.10+
- Docker Desktop (or Docker Engine)
- Ollama for embeddings (host install or started via `--bundled-ollama`)
