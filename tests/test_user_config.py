from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from moorcheh.user_config import (
    EmbeddingConfig,
    ensure_embedding_config,
    load_embedding_config,
    save_embedding_config,
)


def test_embedding_config_requires_api_key() -> None:
    assert EmbeddingConfig(provider="ollama", model="nomic-embed-text").requires_api_key() is False
    assert EmbeddingConfig(provider="openai", model="text-embedding-3-small").requires_api_key() is True


def test_embedding_config_resolved_base_url_ollama_runtime_wins() -> None:
    config = EmbeddingConfig(provider="ollama", model="nomic-embed-text", base_url="http://old:11434")
    assert config.resolved_base_url(ollama_runtime_url="http://ollama:11434") == "http://ollama:11434"


def test_embedding_config_resolved_base_url_openai_default() -> None:
    config = EmbeddingConfig(provider="openai", model="text-embedding-3-small")
    assert config.resolved_base_url() == "https://api.openai.com/v1"


def test_embedding_config_to_compose_env_openai() -> None:
    config = EmbeddingConfig(
        provider="openai",
        model="text-embedding-3-small",
        api_key="sk-test",
        base_url="https://api.openai.com/v1",
    )
    env = config.to_compose_env()
    assert env["EMBEDDING_PROVIDER"] == "openai"
    assert env["EMBEDDING_MODEL"] == "text-embedding-3-small"
    assert env["EMBEDDING_API_KEY"] == "sk-test"
    assert env["EMBEDDING_BASE_URL"] == "https://api.openai.com/v1"
    assert "OLLAMA_URL" not in env


def test_embedding_config_to_compose_env_ollama() -> None:
    config = EmbeddingConfig(provider="ollama", model="nomic-embed-text")
    env = config.to_compose_env(ollama_runtime_url="http://ollama:11434")
    assert env["EMBEDDING_PROVIDER"] == "ollama"
    assert env["EMBEDDING_BASE_URL"] == "http://ollama:11434"
    assert env["OLLAMA_URL"] == "http://ollama:11434"
    assert env["OLLAMA_MODEL"] == "nomic-embed-text"
    assert "EMBEDDING_API_KEY" not in env


def test_embedding_config_from_dict_rejects_empty_provider() -> None:
    with pytest.raises(ValueError, match="provider is empty"):
        EmbeddingConfig.from_dict({"provider": "", "model": "m"})


def test_embedding_config_from_dict_rejects_unknown_provider() -> None:
    with pytest.raises(ValueError, match="unsupported provider"):
        EmbeddingConfig.from_dict({"provider": "gemini", "model": "m"})


def test_save_and_load_embedding_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("moorcheh.user_config.config_file_path", lambda: tmp_path / "config.json")
    saved = save_embedding_config(
        EmbeddingConfig(
            provider="cohere",
            model="embed-v4.0",
            api_key="cohere-secret",
            base_url="https://api.cohere.com/v2",
        )
    )
    assert saved == tmp_path / "config.json"
    raw = json.loads(saved.read_text(encoding="utf-8"))
    assert raw["embedding"]["provider"] == "cohere"
    assert raw["embedding"]["api_key"] == "cohere-secret"

    loaded = load_embedding_config()
    assert loaded is not None
    assert loaded.provider == "cohere"
    assert loaded.model == "embed-v4.0"
    assert loaded.api_key == "cohere-secret"


def test_load_embedding_config_missing_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("moorcheh.user_config.config_file_path", lambda: tmp_path / "missing.json")
    assert load_embedding_config() is None


def test_load_embedding_config_missing_embedding_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"other": 1}), encoding="utf-8")
    monkeypatch.setattr("moorcheh.user_config.config_file_path", lambda: path)
    assert load_embedding_config() is None


def test_ensure_embedding_config_from_flags(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("moorcheh.user_config.config_file_path", lambda: tmp_path / "config.json")
    config = ensure_embedding_config(
        provider="openai",
        model="text-embedding-3-small",
        api_key="sk-flag",
        interactive=False,
    )
    assert config.provider == "openai"
    assert config.api_key == "sk-flag"
    reloaded = load_embedding_config()
    assert reloaded is not None
    assert reloaded.api_key == "sk-flag"


def test_ensure_embedding_config_cloud_requires_api_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("moorcheh.user_config.config_file_path", lambda: tmp_path / "config.json")
    with pytest.raises(ValueError, match="API key required"):
        ensure_embedding_config(provider="openai", interactive=False)


def test_ensure_embedding_config_reuses_saved_api_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("moorcheh.user_config.config_file_path", lambda: tmp_path / "config.json")
    save_embedding_config(
        EmbeddingConfig(
            provider="openai",
            model="text-embedding-3-small",
            api_key="sk-saved",
            base_url="https://api.openai.com/v1",
        )
    )
    config = ensure_embedding_config(provider="openai", model="text-embedding-3-large", interactive=False)
    assert config.api_key == "sk-saved"
    assert config.model == "text-embedding-3-large"


def test_ensure_embedding_config_no_configure_without_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("moorcheh.user_config.config_file_path", lambda: tmp_path / "config.json")
    with pytest.raises(ValueError, match="No embedding configuration"):
        ensure_embedding_config(interactive=False)


def test_ensure_embedding_config_loads_saved(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("moorcheh.user_config.config_file_path", lambda: tmp_path / "config.json")
    save_embedding_config(EmbeddingConfig(provider="ollama", model="all-minilm", base_url="http://host.docker.internal:11434"))
    config = ensure_embedding_config(interactive=False)
    assert config.provider == "ollama"
    assert config.model == "all-minilm"
