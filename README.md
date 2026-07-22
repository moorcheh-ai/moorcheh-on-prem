<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/moorcheh-logo-dark.svg">
    <img alt="Moorcheh" src="assets/moorcheh-logo-light.svg" width="280">
  </picture>
</p>

<p align="center">
  <strong>Moorcheh Community Edition: Free for single-node and non-commercial deployments.</strong>
</p>

<p align="center">
  The Information-Theoretic Search Engine for RAG & Agentic Memory - self-hosted on your infrastructure.
</p>

<p align="center">
  <img alt="License: Moorcheh Community (Free Single-Node)" src="https://img.shields.io/badge/License-Moorcheh%20Community%20(Free%20Single--Node)-blue">
</p>

<p align="center">
  <a href="https://pypi.org/project/moorcheh-client/">PyPI</a> ·
  <a href="https://docs.moorcheh.ai/on-prem">Documentation</a> ·
  <a href="CONTRIBUTING.md">Contributing</a> ·
  <a href="LICENSE">Community License</a>
</p>

> **Licensing:** Moorcheh Community Edition is **source-available** and **free** for non-commercial and single-node self-hosted deployments (at most one active server node). If you need multi-node high availability, enterprise features, or commercial SaaS usage, see [Moorcheh Enterprise](https://moorcheh.ai) or contact [sales@moorcheh.ai](mailto:sales@moorcheh.ai).

---

## Install

```bash
pip install moorcheh-client
```

**Requirements:** Python 3.10+, [Docker](https://www.docker.com/), and an embedding provider (Ollama, OpenAI, or Cohere).

## Quick start

```bash
moorcheh up          # first run prompts for embedding/LLM config
moorcheh status      # health + quota
```

API: `http://localhost:8080` · Data: `~/.moorcheh/data`

The [`moorcheh/server`](https://hub.docker.com/r/moorcheh/server) Docker image is governed by the same [Community Edition license](LICENSE). The license file should be included at `/LICENSE` inside the server image and linked from the Docker Hub repository description.

```python
from moorcheh import MoorchehClient

client = MoorchehClient("http://localhost:8080")

client.namespaces.create("docs", type="text")
job = client.documents.upload("docs", documents=[
    {"id": "doc-1", "text": "Hello from Moorcheh on-prem"},
])
# poll job["job_id"] until completed, then search or answer

results = client.similarity_search.query(
    namespaces=["docs"],
    query="Hello",
    top_k=5,
)

answer = client.answer.generate(
    namespace="docs",
    query="What is in my documents?",
)
```

```bash
moorcheh down        # stops containers; data is kept
```

## CLI

Common commands: `moorcheh up`, `moorcheh down`, `moorcheh status`, `moorcheh namespace-create`, `moorcheh upload-documents`, `moorcheh search`, `moorcheh answer`.

Run `moorcheh --help` or see [docs.moorcheh.ai/on-prem](https://docs.moorcheh.ai/on-prem) for the full CLI and API reference.

## Project layout

| Path | Purpose |
|------|---------|
| `moorcheh/client/` | Python SDK |
| `moorcheh/cli/` | CLI and Docker runtime |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[Moorcheh Community Edition License Agreement](LICENSE) - free for single-node, non-commercial use. Not an OSI-approved open-source license. Enterprise licensing: [sales@moorcheh.ai](mailto:sales@moorcheh.ai).
