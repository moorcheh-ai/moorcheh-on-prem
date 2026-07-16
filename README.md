<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/moorcheh-logo-dark.svg">
    <img alt="Moorcheh" src="assets/moorcheh-logo-light.svg" width="280">
  </picture>
</p>

<p align="center">
  <strong>Self-hosted, open-source Moorcheh</strong> - The Information-Theoretic Search Engine for RAG & Agentic Memory
</p>

<p align="center">
  <a href="https://pypi.org/project/moorcheh-client/">PyPI</a> ·
  <a href="https://docs.moorcheh.ai/on-prem">Documentation</a> ·
  <a href="CONTRIBUTING.md">Contributing</a> ·
  <a href="LICENSE">Apache 2.0</a>
</p>

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

## Test endpoints

With the server running:

```bash
python test.py
```

## Project layout

| Path | Purpose |
|------|---------|
| `moorcheh/client/` | Python SDK |
| `moorcheh/cli/` | CLI and Docker runtime |
| `test.py` | Live endpoint integration test |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[Apache License 2.0](LICENSE)
