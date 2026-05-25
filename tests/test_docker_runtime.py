from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from moorcheh import docker_runtime


def test_compose_file_path_is_packaged() -> None:
    path = docker_runtime.compose_file_path()
    assert path.endswith("docker-compose.yml")
    assert Path(path).is_file()


def test_docker_bind_path_uses_posix_slashes(tmp_path: Path) -> None:
    assert docker_runtime.docker_bind_path(tmp_path) == tmp_path.resolve().as_posix()


def test_should_use_bundled_ollama_forced_flags() -> None:
    with patch.object(docker_runtime, "ollama_is_reachable", return_value=True):
        assert docker_runtime.should_use_bundled_ollama(bundled_ollama=True, ollama_host="127.0.0.1", ollama_port=11434)
        assert not docker_runtime.should_use_bundled_ollama(
            bundled_ollama=False, ollama_host="127.0.0.1", ollama_port=11434
        )


def test_should_use_bundled_ollama_auto_detect() -> None:
    with patch.object(docker_runtime, "ollama_is_reachable", return_value=False):
        assert docker_runtime.should_use_bundled_ollama(bundled_ollama=None, ollama_host="127.0.0.1", ollama_port=11434)
    with patch.object(docker_runtime, "ollama_is_reachable", return_value=True):
        assert not docker_runtime.should_use_bundled_ollama(
            bundled_ollama=None, ollama_host="127.0.0.1", ollama_port=11434
        )


def test_ollama_is_reachable_on_success() -> None:
    from unittest.mock import MagicMock

    response = MagicMock()
    response.status = 200
    response.__enter__.return_value = response
    response.__exit__.return_value = None

    with patch("urllib.request.urlopen", return_value=response):
        assert docker_runtime.ollama_is_reachable()


def test_ollama_is_reachable_on_failure() -> None:
    import urllib.error

    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("down")):
        assert not docker_runtime.ollama_is_reachable()
