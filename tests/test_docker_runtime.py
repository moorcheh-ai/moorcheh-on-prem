from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from moorcheh import docker_runtime
from moorcheh.user_config import EmbeddingConfig


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


def test_up_openai_starts_server_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    embedding = EmbeddingConfig(
        provider="openai",
        model="text-embedding-3-small",
        api_key="sk-test",
        base_url="https://api.openai.com/v1",
    )
    compose_result = MagicMock(stdout="", stderr="", returncode=0)

    with (
        patch("moorcheh.docker_runtime.ensure_embedding_config", return_value=embedding),
        patch("moorcheh.docker_runtime.remove_stale_compose_containers") as remove_stale,
        patch("moorcheh.docker_runtime.ensure_data_dir", return_value=tmp_path),
        patch("moorcheh.docker_runtime.run_compose", return_value=compose_result) as run_compose,
        patch("moorcheh.docker_runtime.ensure_ollama_model") as ensure_model,
    ):
        result, bundled, data_dir, returned = docker_runtime.up(
            "moorcheh/server:latest",
            "ollama/ollama:latest",
            8080,
            11434,
            no_configure=True,
        )

    assert result is compose_result
    assert bundled is False
    assert data_dir == tmp_path
    assert returned.provider == "openai"
    remove_stale.assert_called_once_with(include_ollama=False)
    ensure_model.assert_not_called()
    run_compose.assert_called_once()
    assert run_compose.call_args[0][0] == ["up", "-d", "server"]
    env = run_compose.call_args[1]["env"]
    assert env["EMBEDDING_PROVIDER"] == "openai"
    assert env["EMBEDDING_API_KEY"] == "sk-test"


def test_up_ollama_host_skips_bundled_container(tmp_path: Path) -> None:
    embedding = EmbeddingConfig(provider="ollama", model="nomic-embed-text")
    compose_result = MagicMock(stdout="", stderr="", returncode=0)

    with (
        patch("moorcheh.docker_runtime.ensure_embedding_config", return_value=embedding),
        patch("moorcheh.docker_runtime.should_use_bundled_ollama", return_value=False),
        patch("moorcheh.docker_runtime.remove_stale_compose_containers"),
        patch("moorcheh.docker_runtime.ensure_data_dir", return_value=tmp_path),
        patch("moorcheh.docker_runtime.ensure_ollama_model"),
        patch("moorcheh.docker_runtime.run_compose", return_value=compose_result) as run_compose,
    ):
        _, bundled, _, _ = docker_runtime.up(
            "moorcheh/server:latest",
            "ollama/ollama:latest",
            8080,
            11434,
            no_configure=True,
        )

    assert bundled is False
    assert run_compose.call_args[0][0] == ["up", "-d", "server"]
    env = run_compose.call_args[1]["env"]
    assert env["EMBEDDING_BASE_URL"] == "http://host.docker.internal:11434"


def test_down_stops_server_only_for_cloud_provider() -> None:
    embedding = EmbeddingConfig(provider="openai", model="text-embedding-3-small", api_key="sk")
    compose_result = MagicMock(returncode=0)

    with (
        patch("moorcheh.docker_runtime.load_embedding_config", return_value=embedding),
        patch("moorcheh.docker_runtime.ensure_data_dir", return_value=Path("/data")),
        patch("moorcheh.docker_runtime.run_compose", return_value=compose_result) as run_compose,
    ):
        docker_runtime.down(include_ollama=None)

    assert run_compose.call_args[0][0] == ["stop", "server"]
