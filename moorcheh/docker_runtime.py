from __future__ import annotations

import os
import subprocess
import urllib.error
import urllib.request
from importlib import resources
from pathlib import Path


DEFAULT_SERVER_IMAGE = "moorcheh/server:latest"
DEFAULT_OLLAMA_IMAGE = "ollama/ollama:latest"
DEFAULT_OLLAMA_MODEL = "nomic-embed-text"
DEFAULT_OLLAMA_HOST = "127.0.0.1"
DEFAULT_OLLAMA_PORT = 11434
HOST_OLLAMA_URL = "http://host.docker.internal:11434"

# Must match container_name in compose/docker-compose.yml
COMPOSE_CONTAINER_NAMES = ("moorcheh-ollama", "moorcheh-onprem-server")

MOORCHEH_DATA_DIR_ENV = "MOORCHEH_DATA_DIR"


def default_data_dir() -> Path:
    """Per-user data directory: ~/.moorcheh/data (e.g. C:\\Users\\you\\.moorcheh\\data on Windows)."""
    return Path.home() / ".moorcheh" / "data"


def ensure_data_dir() -> Path:
    """Create and return ~/.moorcheh/data for the current user."""
    path = default_data_dir().resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


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
    return str(resources.files("moorcheh").joinpath("compose/docker-compose.yml"))


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


def up(
    server_image: str,
    ollama_image: str,
    server_port: int,
    ollama_port: int,
    ollama_model: str,
    *,
    bundled_ollama: bool | None = None,
    ollama_host: str = DEFAULT_OLLAMA_HOST,
) -> tuple[subprocess.CompletedProcess[str], bool, Path]:
    """
    Start the Moorcheh stack. Returns (compose result, whether bundled Ollama was started, data_dir).

    When host Ollama is already running on ollama_host:ollama_port, only the server
    container is started and OLLAMA_URL points at host.docker.internal:11434.
    """
    use_bundled = should_use_bundled_ollama(
        bundled_ollama=bundled_ollama,
        ollama_host=ollama_host,
        ollama_port=ollama_port,
    )
    remove_stale_compose_containers(include_ollama=use_bundled)

    resolved_data_dir = ensure_data_dir()
    base_env = {
        "MOORCHEH_SERVER_IMAGE": server_image,
        "OLLAMA_IMAGE": ollama_image,
        "SERVER_PORT": str(server_port),
        "OLLAMA_MODEL": ollama_model,
        MOORCHEH_DATA_DIR_ENV: docker_bind_path(resolved_data_dir),
    }

    if use_bundled:
        result = run_compose(
            ["--profile", "bundled-ollama", "up", "-d"],
            env={
                **base_env,
                "OLLAMA_PORT": str(ollama_port),
                "OLLAMA_URL": "http://ollama:11434",
            },
        )
    else:
        result = run_compose(
            ["up", "-d", "server"],
            env={
                **base_env,
                "OLLAMA_URL": HOST_OLLAMA_URL,
            },
        )
    return result, use_bundled, resolved_data_dir


def down(*, include_ollama: bool | None = None) -> subprocess.CompletedProcess[str]:
    """
    Stop compose services. When include_ollama is False, only stops the server
    (leaves a bundled ollama container running if it was started separately).
    None = stop all services defined in the compose file (including profile services
    that were started).
    """
    env = {MOORCHEH_DATA_DIR_ENV: docker_bind_path(ensure_data_dir())}
    if include_ollama is False:
        return run_compose(["stop", "server"], env=env)
    return run_compose(["--profile", "bundled-ollama", "down"], env=env)
