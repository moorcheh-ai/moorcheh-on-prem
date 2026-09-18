from __future__ import annotations

import os
import subprocess
import urllib.error
import urllib.request
from importlib import resources
from pathlib import Path

from moorcheh.cli.ollama_setup import ensure_ollama_model, wait_for_ollama
from moorcheh.cli.user_config import EmbeddingConfig, LlmConfig, ensure_embedding_config, load_embedding_config, load_llm_config


DEFAULT_SERVER_IMAGE = "moorcheh/server:latest"
DEFAULT_OLLAMA_IMAGE = "ollama/ollama:latest"
DEFAULT_OLLAMA_HOST = "127.0.0.1"
DEFAULT_OLLAMA_PORT = 11434
HOST_OLLAMA_URL = "http://host.docker.internal:11434"
BUNDLED_OLLAMA_URL = "http://ollama:11434"

# Must match container_name in compose/docker-compose.yml
COMPOSE_CONTAINER_NAMES = ("moorcheh-ollama", "moorcheh-onprem-server")

MOORCHEH_DATA_DIR_ENV = "MOORCHEH_DATA_DIR"
MOORCHEH_UPLOAD_DIR_ENV = "MOORCHEH_UPLOAD_DIR"


def default_data_dir() -> Path:
    """Per-user data directory: ~/.moorcheh/data (e.g. C:\\Users\\you\\.moorcheh\\data on Windows)."""
    return Path.home() / ".moorcheh" / "data"


def ensure_data_dir() -> Path:
    """Create and return ~/.moorcheh/data for the current user."""
    path = default_data_dir().resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def default_upload_dir() -> Path:
    """Per-user upload mount source: ~/.moorcheh/uploads."""
    return Path.home() / ".moorcheh" / "uploads"


def ensure_upload_dir() -> Path:
    path = default_upload_dir().resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def host_path_to_container_upload_path(host_path: Path, upload_dir: Path | None = None) -> str:
    """Map a host file under the upload dir to the in-container /uploads path."""
    root = (upload_dir or ensure_upload_dir()).resolve()
    resolved = host_path.resolve()
    if resolved == root:
        raise ValueError(f"Path must be a file under {root}")
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(
            f"File must be inside the Moorcheh upload directory ({root}). "
            f"Copy or move the file there, then retry."
        ) from exc
    relative = resolved.relative_to(root).as_posix()
    return f"/uploads/{relative}"


def docker_bind_path(path: Path) -> str:
    """Absolute host path for docker compose bind mounts (forward slashes on Windows)."""
    return path.resolve().as_posix()


class ComposeCommandError(RuntimeError):
    """docker compose failed; includes captured stdout/stderr."""

    def __init__(self, command: list[str], returncode: int, stdout: str, stderr: str) -> None:
        self.command = command
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        message = stderr.strip() or stdout.strip() or f"exit code {returncode}"
        super().__init__(message)


def compose_file_path() -> str:
    return str(resources.files("moorcheh.cli").joinpath("compose/docker-compose.yml"))


def ollama_is_reachable(host: str = DEFAULT_OLLAMA_HOST, port: int = DEFAULT_OLLAMA_PORT, timeout: float = 2.0) -> bool:
    """Return True if an Ollama HTTP server responds on host:port."""
    url = f"http://{host}:{port}/"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return 200 <= response.status < 300
    except (urllib.error.URLError, TimeoutError, ValueError):
        return False


def should_use_bundled_ollama(
    *,
    bundled_ollama: bool | None,
    ollama_host: str,
    ollama_port: int,
) -> bool:
    """
    bundled_ollama: True = always start container; False = always use host;
    None = auto-detect (use host Ollama when already reachable).
    """
    if bundled_ollama is True:
        return True
    if bundled_ollama is False:
        return False
    return not ollama_is_reachable(ollama_host, ollama_port)


def run_compose(command: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    full_env = os.environ.copy()
    if env:
        full_env.update(env)

    cmd = ["docker", "compose", "-f", compose_file_path(), *command]
    result = subprocess.run(
        cmd,
        text=True,
        capture_output=True,
        env=full_env,
    )
    if result.returncode != 0:
        raise ComposeCommandError(cmd, result.returncode, result.stdout, result.stderr)
    return result


def remove_stale_compose_containers(*, include_ollama: bool) -> None:
    """Remove leftover containers that block fixed container_name in compose."""
    names = list(COMPOSE_CONTAINER_NAMES) if include_ollama else ("moorcheh-onprem-server",)
    for name in names:
        subprocess.run(
            ["docker", "rm", "-f", name],
            capture_output=True,
            text=True,
        )


def _resolve_ollama_url(*, use_bundled: bool, ollama_port: int) -> str:
    if use_bundled:
        return BUNDLED_OLLAMA_URL
    return HOST_OLLAMA_URL.replace(":11434", f":{ollama_port}")


def up(
    server_image: str,
    ollama_image: str,
    server_port: int,
    ollama_port: int,
    *,
    bundled_ollama: bool | None = None,
    ollama_host: str = DEFAULT_OLLAMA_HOST,
    embedding_provider: str | None = None,
    embedding_model: str | None = None,
    embedding_api_key: str | None = None,
    configure: bool = False,
    no_configure: bool = False,
    skip_ollama_model_pull: bool = False,
) -> tuple[subprocess.CompletedProcess[str], bool, Path, EmbeddingConfig, LlmConfig]:
    """
    Start the Moorcheh stack. Returns (compose result, whether bundled Ollama was started, data_dir, embedding config).

    When embedding provider is ollama, uses host Ollama if reachable; otherwise starts bundled Ollama.
    For openai/cohere, only the server container is started.
    """
    embedding = ensure_embedding_config(
        provider=embedding_provider,
        model=embedding_model,
        api_key=embedding_api_key,
        interactive=not no_configure and (configure or embedding_provider is None),
    )
    llm = load_llm_config(embedding=embedding) or LlmConfig.default_for_embedding(embedding)

    use_bundled = False
    if embedding.provider == "ollama" or llm.provider == "ollama":
        use_bundled = should_use_bundled_ollama(
            bundled_ollama=bundled_ollama,
            ollama_host=ollama_host,
            ollama_port=ollama_port,
        )
    elif bundled_ollama is True:
        print("Note: --bundled-ollama is ignored when embedding provider is not ollama.")

    remove_stale_compose_containers(include_ollama=use_bundled)

    resolved_data_dir = ensure_data_dir()
    resolved_upload_dir = ensure_upload_dir()
    base_env = {
        "MOORCHEH_SERVER_IMAGE": server_image,
        "OLLAMA_IMAGE": ollama_image,
        "SERVER_PORT": str(server_port),
        MOORCHEH_DATA_DIR_ENV: docker_bind_path(resolved_data_dir),
        MOORCHEH_UPLOAD_DIR_ENV: docker_bind_path(resolved_upload_dir),
    }

    if embedding.provider == "ollama" or llm.provider == "ollama":
        if use_bundled:
            print("Starting bundled Ollama container...")
            run_compose(
                ["--profile", "bundled-ollama", "up", "-d", "ollama"],
                env={**base_env, "OLLAMA_PORT": str(ollama_port)},
            )
            print(f"Waiting for Ollama on http://{ollama_host}:{ollama_port}...")
            if not wait_for_ollama(ollama_host, ollama_port):
                raise RuntimeError(
                    f"Bundled Ollama did not become ready on http://{ollama_host}:{ollama_port} in time."
                )
            if embedding.provider == "ollama":
                ensure_ollama_model(
                    embedding.model,
                    host=ollama_host,
                    port=ollama_port,
                    interactive=False,
                    pull_if_missing=not skip_ollama_model_pull,
                    model_kind="embedding",
                )
            if llm.provider == "ollama" and llm.model != embedding.model:
                ensure_ollama_model(
                    llm.model,
                    host=ollama_host,
                    port=ollama_port,
                    interactive=False,
                    pull_if_missing=not skip_ollama_model_pull,
                    model_kind="llm",
                )
        else:
            if embedding.provider == "ollama":
                ensure_ollama_model(
                    embedding.model,
                    host=ollama_host,
                    port=ollama_port,
                    interactive=False,
                    pull_if_missing=not skip_ollama_model_pull,
                    model_kind="embedding",
                )
            if llm.provider == "ollama":
                ensure_ollama_model(
                    llm.model,
                    host=ollama_host,
                    port=ollama_port,
                    interactive=False,
                    pull_if_missing=not skip_ollama_model_pull,
                    model_kind="llm",
                )

    ollama_url = (
        _resolve_ollama_url(use_bundled=use_bundled, ollama_port=ollama_port)
        if embedding.provider == "ollama" or llm.provider == "ollama"
        else None
    )
    compose_env = {
        **base_env,
        **embedding.to_compose_env(ollama_runtime_url=ollama_url),
        **llm.to_compose_env(ollama_runtime_url=ollama_url, embedding=embedding),
    }

    if use_bundled:
        result = run_compose(
            ["--profile", "bundled-ollama", "up", "-d"],
            env={
                **compose_env,
                "OLLAMA_PORT": str(ollama_port),
            },
        )
    else:
        result = run_compose(
            ["up", "-d", "server"],
            env=compose_env,
        )
    return result, use_bundled, resolved_data_dir, embedding, llm


def down(*, include_ollama: bool | None = None) -> subprocess.CompletedProcess[str]:
    """
    Stop compose services. When include_ollama is False, only stops the server
    (leaves a bundled ollama container running if it was started separately).
    None = if saved config uses a cloud provider, stop server only; otherwise stop
    the full bundled-ollama profile (server + moorcheh-ollama if running).
    """
    env = {
        MOORCHEH_DATA_DIR_ENV: docker_bind_path(ensure_data_dir()),
        MOORCHEH_UPLOAD_DIR_ENV: docker_bind_path(ensure_upload_dir()),
    }
    if include_ollama is False:
        return run_compose(["stop", "server"], env=env)
    if include_ollama is None:
        saved = load_embedding_config()
        if saved and saved.provider != "ollama":
            return run_compose(["stop", "server"], env=env)
    return run_compose(["--profile", "bundled-ollama", "down"], env=env)
