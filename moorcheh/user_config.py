from __future__ import annotations

import json
import os
from dataclasses import dataclass
from getpass import getpass
from pathlib import Path
from typing import Any


CONFIG_DIR_NAME = ".moorcheh"
CONFIG_FILE_NAME = "config.json"

PROVIDER_CHOICES = ("ollama", "openai", "cohere")

# Curated models per provider (id, short label). Shown as a numbered menu during setup.
PROVIDER_MODELS: dict[str, list[tuple[str, str]]] = {
    "ollama": [
        ("nomic-embed-text", "Nomic Embed Text (recommended)"),
        ("mxbai-embed-large", "Mixedbread Embed Large"),
        ("all-minilm", "All-MiniLM"),
    ],
    "openai": [
        ("text-embedding-3-small", "Text Embedding 3 Small (recommended)"),
        ("text-embedding-3-large", "Text Embedding 3 Large"),
        ("text-embedding-ada-002", "Ada 002 (legacy)"),
    ],
    "cohere": [
        ("embed-v4.0", "Embed v4 — multimodal, 1536 dims (recommended)"),
        ("embed-english-v3.0", "Embed English v3 — 1024 dims, English"),
        ("embed-multilingual-v3.0", "Embed Multilingual v3 — 1024 dims, 100+ languages"),
    ],
}

# Canonical defaults (also written into config.json on save). Edit config.json to override
# without a new CLI release; re-run `moorcheh configure --force` to refresh from code defaults.
DEFAULT_PROVIDER_BASE_URLS: dict[str, str] = {
    "ollama": "http://host.docker.internal:11434",
    "openai": "https://api.openai.com/v1",
    "cohere": "https://api.cohere.com/v2",
}


def default_base_url(provider: str) -> str:
    return DEFAULT_PROVIDER_BASE_URLS[provider]


@dataclass
class EmbeddingConfig:
    provider: str
    model: str
    api_key: str | None = None
    base_url: str | None = None

    def requires_api_key(self) -> bool:
        return self.provider != "ollama"

    def default_model(self) -> str:
        return PROVIDER_MODELS[self.provider][0][0]

    def resolved_base_url(self, *, ollama_runtime_url: str | None = None) -> str:
        """
        URL passed to the server as EMBEDDING_BASE_URL.

        Ollama: runtime URL from `moorcheh up` (bundled vs host) wins; else config; else code default.
        OpenAI/Cohere: config override wins; else code default.
        """
        if self.provider == "ollama":
            if ollama_runtime_url:
                return ollama_runtime_url
            if self.base_url:
                return self.base_url
            return default_base_url("ollama")
        if self.base_url:
            return self.base_url
        return default_base_url(self.provider)

    def with_provider_defaults(self) -> EmbeddingConfig:
        """Return a copy with model/base_url filled from code defaults when missing."""
        return EmbeddingConfig(
            provider=self.provider,
            model=self.model or PROVIDER_MODELS[self.provider][0][0],
            api_key=self.api_key,
            base_url=self.base_url or default_base_url(self.provider),
        )

    def to_compose_env(self, *, ollama_runtime_url: str | None = None) -> dict[str, str]:
        """Env vars passed to the Moorcheh server container at `moorcheh up`."""
        base_url = self.resolved_base_url(ollama_runtime_url=ollama_runtime_url)
        env: dict[str, str] = {
            "EMBEDDING_PROVIDER": self.provider,
            "EMBEDDING_MODEL": self.model,
            "EMBEDDING_BASE_URL": base_url,
        }
        if self.api_key:
            env["EMBEDDING_API_KEY"] = self.api_key
        if self.provider == "ollama":
            env["OLLAMA_URL"] = base_url
            env["OLLAMA_MODEL"] = self.model
        return env

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EmbeddingConfig:
        provider = str(data.get("provider", "ollama")).strip().lower()
        if not provider:
            raise ValueError("config embedding.provider is empty; run 'moorcheh configure --force'")
        if provider not in PROVIDER_CHOICES:
            raise ValueError(f"unsupported provider '{provider}'")
        default_model = PROVIDER_MODELS[provider][0][0]
        model = str(data.get("model") or default_model).strip()
        api_key = data.get("api_key")
        if isinstance(api_key, str):
            api_key = api_key.strip() or None
        else:
            api_key = None
        base_url = data.get("base_url")
        if isinstance(base_url, str):
            base_url = base_url.strip() or None
        else:
            base_url = None
        return cls(provider=provider, model=model, api_key=api_key, base_url=base_url)


def config_dir() -> Path:
    return Path.home() / CONFIG_DIR_NAME


def config_file_path() -> Path:
    return config_dir() / CONFIG_FILE_NAME


def load_config() -> dict[str, Any] | None:
    path = config_file_path()
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_embedding_config() -> EmbeddingConfig | None:
    raw = load_config()
    if not raw:
        return None
    embedding = raw.get("embedding")
    if not isinstance(embedding, dict):
        return None
    return EmbeddingConfig.from_dict(embedding)


def save_embedding_config(config: EmbeddingConfig) -> Path:
    config = config.with_provider_defaults()
    path = config_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "embedding": {
            "provider": config.provider,
            "model": config.model,
            "base_url": config.base_url,
        }
    }
    if config.api_key:
        payload["embedding"]["api_key"] = config.api_key
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return path


def _prompt_choice(prompt: str, choices: tuple[str, ...], default: str) -> str:
    options = "/".join(choices)
    while True:
        value = input(f"{prompt} [{options}] (default: {default}): ").strip().lower()
        if not value:
            return default
        if value in choices:
            return value
        print(f"Choose one of: {', '.join(choices)}")


def _prompt_model_for_provider(provider: str) -> str:
    models = PROVIDER_MODELS[provider]
    print(f"\nSelect an embedding model for {provider}:")
    for index, (model_id, label) in enumerate(models, start=1):
        print(f"  {index}. {label}  ({model_id})")
    default_model = models[0][0]
    while True:
        raw = input(f"Choice [1-{len(models)}] (default: 1): ").strip()
        if not raw:
            return default_model
        if raw.isdigit():
            choice = int(raw)
            if 1 <= choice <= len(models):
                return models[choice - 1][0]
        print(f"Enter a number from 1 to {len(models)}, or press Enter for the default.")


def configure_embedding_interactive(*, force: bool = False) -> EmbeddingConfig:
    existing = None if force else load_embedding_config()
    if existing and not force:
        reuse = input(
            f"Use saved embedding config ({existing.provider}, model={existing.model})? [Y/n]: "
        ).strip().lower()
        if reuse in ("", "y", "yes"):
            resolved = existing.with_provider_defaults()
            if resolved.provider == "ollama":
                from moorcheh.ollama_setup import prepare_ollama_at_configure

                prepare_ollama_at_configure(resolved.model)
            return resolved

    print("Configure text embeddings for Moorcheh (used for text namespaces and text search).")
    provider = _prompt_choice("Embedding provider", PROVIDER_CHOICES, "openai")
    model = _prompt_model_for_provider(provider)

    api_key: str | None = None
    if provider != "ollama":
        while True:
            api_key = getpass(f"API key for {provider} (input hidden): ").strip()
            if api_key:
                break
            print("API key is required for cloud embedding providers.")

    if provider == "ollama":
        from moorcheh.ollama_setup import prepare_ollama_at_configure

        prepare_ollama_at_configure(model)

    config = EmbeddingConfig(
        provider=provider,
        model=model,
        api_key=api_key,
        base_url=default_base_url(provider),
    )
    saved = save_embedding_config(config)
    print(f"Saved to {saved}")
    print("API base URL is stored in config (defaults from this release). Edit base_url there to override.")
    return config


def ensure_embedding_config(
    *,
    provider: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    interactive: bool = True,
) -> EmbeddingConfig:
    if provider or model or api_key:
        resolved_provider = (provider or "ollama").strip().lower()
        if resolved_provider not in PROVIDER_CHOICES:
            raise ValueError(f"unsupported provider '{resolved_provider}'")
        resolved_model = (model or PROVIDER_MODELS[resolved_provider][0][0]).strip()
        saved = load_embedding_config()
        resolved_api_key = api_key.strip() if api_key else None
        if not resolved_api_key and saved and saved.provider == resolved_provider:
            resolved_api_key = saved.api_key
        if not resolved_api_key and resolved_provider != "ollama":
            raise ValueError(
                f"API key required for '{resolved_provider}'. "
                "Run 'moorcheh configure' or pass --embedding-api-key."
            )
        if saved and saved.provider == resolved_provider and saved.base_url:
            resolved_base_url = saved.base_url
        else:
            resolved_base_url = default_base_url(resolved_provider)
        config = EmbeddingConfig(
            provider=resolved_provider,
            model=resolved_model,
            api_key=resolved_api_key,
            base_url=resolved_base_url,
        )
        save_embedding_config(config)
        return config

    saved = load_embedding_config()
    if saved:
        return saved.with_provider_defaults()
    if interactive:
        return configure_embedding_interactive()
    raise ValueError(
        "No embedding configuration found. Run 'moorcheh configure' or pass "
        "--embedding-provider (and --embedding-api-key for cloud providers) to 'moorcheh up'."
    )
