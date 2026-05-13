from __future__ import annotations

import os
import subprocess
from importlib import resources


DEFAULT_SERVER_IMAGE = "moorcheh/server:latest"
DEFAULT_OLLAMA_IMAGE = "ollama/ollama:latest"
DEFAULT_OLLAMA_MODEL = "nomic-embed-text"


def compose_file_path() -> str:
    return str(resources.files("moorcheh").joinpath("compose/docker-compose.yml"))


def run_compose(command: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    full_env = os.environ.copy()
    if env:
        full_env.update(env)

    return subprocess.run(
        ["docker", "compose", "-f", compose_file_path(), *command],
        text=True,
        capture_output=True,
        check=True,
        env=full_env,
    )


def up(server_image: str, ollama_image: str, server_port: int, ollama_model: str) -> subprocess.CompletedProcess[str]:
    return run_compose(
        ["up", "-d"],
        env={
            "MOORCHEH_SERVER_IMAGE": server_image,
            "OLLAMA_IMAGE": ollama_image,
            "SERVER_PORT": str(server_port),
            "OLLAMA_MODEL": ollama_model,
        },
    )


def down() -> subprocess.CompletedProcess[str]:
    return run_compose(["down"])
