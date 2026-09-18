# Contributing to Moorcheh on-prem

Thanks for your interest in contributing to **Moorcheh Community Edition** ([docs.moorcheh.ai/on-prem](https://docs.moorcheh.ai/on-prem)).

By contributing, you agree that your contributions will be licensed under the [Moorcheh Community Edition License Agreement](LICENSE).

## Ways to contribute

- **Bug reports** — Open an issue with steps to reproduce, expected vs actual behavior, and your OS/Python/Docker versions.
- **Feature requests** — Open an issue describing the use case before large changes.
- **Pull requests** — Bug fixes, tests, docs, and small features are welcome.

## Development setup

**Requirements:** Python 3.10+, Git, and optionally [Docker](https://www.docker.com/) for live integration testing.

```bash
git clone https://github.com/moorcheh-ai/moorcheh-on-prem.git
cd moorcheh-on-prem
pip install -e ".[dev]"
```

Optional web tester UI:

```bash
pip install -e ".[web]"
```

## Running tests

Unit tests do not require Docker:

```bash
pytest -v
```

CI runs the same suite on Python 3.10–3.13 (see `.github/workflows/ci.yml`).

For manual smoke tests against a live server:

```bash
moorcheh up
moorcheh status
moorcheh down
```

## Project layout

| Path | Purpose |
|------|---------|
| `moorcheh/client/` | Python SDK (`MoorchehClient`, resources, HTTP layer) |
| `moorcheh/client/api.py` | `MoorchehApiClient` (legacy wrapper) |
| `moorcheh/cli/` | CLI and Docker runtime |
| `moorcheh/cli/cli.py` | `moorcheh` command handlers |
| `moorcheh/cli/docker_runtime.py` | `moorcheh up` / `down` |
| `moorcheh/cli/user_config.py` | `~/.moorcheh/config.json` handling |
| `moorcheh/cli/compose/` | Docker Compose file |
| `tests/` | Pytest suite |

## Pull request guidelines

1. **Branch** from `main` (or `master`).
2. **Keep changes focused** — one logical change per PR when possible.
3. **Add or update tests** for behavior you change.
4. **Run tests** before opening the PR: `pytest -v`.
5. **Match existing style** — `from __future__ import annotations`, type hints, minimal scope, no unrelated refactors.
6. **Update docs** if you change CLI flags, config, or public API (`README.md`).

### Commit messages

Use clear, imperative subjects, e.g.:

- `Fix namespace delete wait timeout on Windows`
- `Add tests for files.upload job polling`

## Scope notes

- This repo talks to **`moorcheh/server`** (Docker image). Server-side changes may live in a separate repo.
- Do not commit secrets, API keys, or local config (`.env`, `~/.moorcheh/`).
- Generated files (`moorcheh/_version.py`, `dist/`, `__pycache__/`) should not be committed.

## Licensing note for contributors

Moorcheh Community Edition is **source-available** and free for single-node, non-commercial deployments. It is not marketed or licensed as "open source" under OSI criteria. Commercial, multi-node, or SaaS use requires a [Moorcheh Enterprise](https://moorcheh.ai) license.

## Questions

Open a GitHub issue or discussion for questions before starting large work. For product docs, see [docs.moorcheh.ai](https://docs.moorcheh.ai/on-prem).
