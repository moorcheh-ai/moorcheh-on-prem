from __future__ import annotations

import json
import subprocess
import time
import urllib.error
import urllib.request
DEFAULT_OLLAMA_HOST = "127.0.0.1"
DEFAULT_OLLAMA_PORT = 11434
OLLAMA_WAIT_TIMEOUT_SEC = 120.0
OLLAMA_WAIT_INTERVAL_SEC = 2.0


def ollama_base_url(host: str = DEFAULT_OLLAMA_HOST, port: int = DEFAULT_OLLAMA_PORT) -> str:
    return f"http://{host}:{port}"


def ollama_is_reachable(
    host: str = DEFAULT_OLLAMA_HOST,
    port: int = DEFAULT_OLLAMA_PORT,
    timeout: float = 2.0,
) -> bool:
    url = f"{ollama_base_url(host, port)}/"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return 200 <= response.status < 300
    except (urllib.error.URLError, TimeoutError, ValueError):
        return False


def wait_for_ollama(
    host: str = DEFAULT_OLLAMA_HOST,
    port: int = DEFAULT_OLLAMA_PORT,
    *,
    timeout_sec: float = OLLAMA_WAIT_TIMEOUT_SEC,
) -> bool:
    """Wait until Ollama HTTP API accepts /api/tags (not just the root page)."""
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            list_ollama_models(host, port)
            return True
        except (urllib.error.URLError, TimeoutError, ValueError, ConnectionResetError):
            pass
        time.sleep(OLLAMA_WAIT_INTERVAL_SEC)
    return False


def list_ollama_models(host: str = DEFAULT_OLLAMA_HOST, port: int = DEFAULT_OLLAMA_PORT) -> list[str]:
    url = f"{ollama_base_url(host, port)}/api/tags"
    with urllib.request.urlopen(url, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    models = payload.get("models")
    if not isinstance(models, list):
        return []
    names: list[str] = []
    for entry in models:
        if isinstance(entry, dict) and isinstance(entry.get("name"), str):
            names.append(entry["name"])
    return names


def ollama_has_model(
    model: str,
    host: str = DEFAULT_OLLAMA_HOST,
    port: int = DEFAULT_OLLAMA_PORT,
) -> bool:
    installed = list_ollama_models(host, port)
    return _model_matches(model, installed)


def _model_matches(model: str, installed: list[str]) -> bool:
    for name in installed:
        base = name.split(":", 1)[0]
        if base == model or name == model or name.startswith(f"{model}:"):
            return True
    return False


def pull_ollama_model_http(
    model: str,
    host: str = DEFAULT_OLLAMA_HOST,
    port: int = DEFAULT_OLLAMA_PORT,
) -> None:
    url = f"{ollama_base_url(host, port)}/api/pull"
    body = json.dumps({"name": model}).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    print(f"Pulling Ollama model '{model}' (this may take a few minutes)...")
    last_status: str | None = None
    last_pct: int | None = None
    with urllib.request.urlopen(request, timeout=None) as response:
        while True:
            line = response.readline()
            if not line:
                break
            try:
                event = json.loads(line.decode("utf-8"))
            except json.JSONDecodeError:
                continue
            if event.get("error"):
                raise RuntimeError(str(event["error"]))

            status = event.get("status")
            if not isinstance(status, str) or not status.strip():
                continue

            completed = event.get("completed")
            total = event.get("total")
            if isinstance(completed, int) and isinstance(total, int) and total > 0:
                pct = min(100, int(completed * 100 / total))
                if pct != last_pct:
                    last_pct = pct
                    print(f"  {status} ({pct}%)")
                continue

            if status != last_status:
                last_status = status
                print(f"  {status}")


def pull_ollama_model_cli(model: str) -> None:
    print(f"Pulling Ollama model '{model}' via ollama CLI...")
    subprocess.run(["ollama", "pull", model], check=True)


def pull_ollama_model(
    model: str,
    host: str = DEFAULT_OLLAMA_HOST,
    port: int = DEFAULT_OLLAMA_PORT,
) -> None:
    if ollama_is_reachable(host, port):
        pull_ollama_model_http(model, host, port)
        return
    try:
        pull_ollama_model_cli(model)
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"Ollama is not reachable at {host}:{port} and the 'ollama' CLI was not found. "
            "Install Ollama from https://ollama.com or run 'moorcheh up' to start bundled Ollama."
        ) from exc


def _prompt_yes_no(prompt: str, *, default_yes: bool = True) -> bool:
    suffix = "[Y/n]" if default_yes else "[y/N]"
    raw = input(f"{prompt} {suffix}: ").strip().lower()
    if not raw:
        return default_yes
    return raw in ("y", "yes")


def _ollama_model_role_label(model_kind: str) -> tuple[str, str]:
    if model_kind == "llm":
        return "LLM", "/answer will fail until you run: ollama pull {model}"
    return "Embedding", "Text upload/search will fail until you run: ollama pull {model}"


def ensure_ollama_model(
    model: str,
    *,
    host: str = DEFAULT_OLLAMA_HOST,
    port: int = DEFAULT_OLLAMA_PORT,
    interactive: bool = True,
    pull_if_missing: bool = True,
    model_kind: str = "embedding",
) -> None:
    """
    Verify Ollama is reachable and the model is available; optionally pull if missing.
    Used during moorcheh configure and moorcheh up. Raises RuntimeError when Ollama is required but not ready.
    """
    role_label, skip_hint = _ollama_model_role_label(model_kind)
    if not wait_for_ollama(host, port, timeout_sec=30):
        raise RuntimeError(
            f"Ollama is not running at http://{host}:{port}. "
            "Start the Ollama app, or run 'moorcheh up' without --use-host-ollama to use bundled Ollama."
        )

    if ollama_has_model(model, host, port):
        print(f"{role_label} model '{model}' is already available at http://{host}:{port}.")
        return

    if not pull_if_missing:
        print(
            f"{role_label} model '{model}' is not installed at http://{host}:{port}.\n"
            f"  Run: ollama pull {model}"
        )
        return

    print(f"{role_label} model '{model}' is not installed at http://{host}:{port}.")
    if not interactive:
        print(f"Pulling {role_label.lower()} model '{model}'...")
    elif not _prompt_yes_no(f"Pull '{model}' now?", default_yes=True):
        print(f"Skipped pull. {skip_hint.format(model=model)}")
        return

    pull_ollama_model(model, host, port)
    if not ollama_has_model(model, host, port):
        raise RuntimeError(f"{role_label} model '{model}' is still not available after pull.")


def prepare_ollama_at_configure(
    model: str,
    *,
    host: str = DEFAULT_OLLAMA_HOST,
    port: int = DEFAULT_OLLAMA_PORT,
    model_kind: str = "embedding",
) -> None:
    """
    During moorcheh configure: check host Ollama if already running; defer otherwise.
    """
    if ollama_is_reachable(host, port):
        print(f"Ollama detected at http://{host}:{port}.")
        ensure_ollama_model(model, host=host, port=port, interactive=True, model_kind=model_kind)
        return

    print(
        f"Ollama is not running on http://{host}:{port} yet.\n"
        "  • Install from https://ollama.com and start it, or\n"
        "  • Run 'moorcheh up' — Moorcheh can start bundled Ollama in Docker.\n"
        f"Model '{model}' will be pulled automatically when you run 'moorcheh up'."
    )
