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
DEFAULT_PROVIDER = "ollama"

DATA_SUBDIR_NAME = "data"
DATA_STORE_FILENAME = "moorcheh_data_store.json"
NAMESPACE_REGISTRY_FILENAME = "namespace_registry.json"

# Curated models per provider (id, short label). Shown as a numbered menu during setup.
PROVIDER_MODELS: dict[str, list[tuple[str, str]]] = {
    "ollama": [
        ("mxbai-embed-large", "Mixedbread Embed Large (recommended)"),
        ("nomic-embed-text", "Nomic Embed Text"),
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

LLM_PROVIDER_MODELS: dict[str, list[tuple[str, str]]] = {
    "ollama": [
        ("qwen2.5", "Qwen 2.5 (recommended)"),
        ("llama3.2", "Llama 3.2"),
        ("mistral", "Mistral"),
    ],
    "openai": [
        ("gpt-5.5", "GPT-5.5 (recommended)"),
        ("gpt-5", "GPT-5"),
        ("gpt-4o-mini", "GPT-4o Mini"),
    ],
    "cohere": [
        ("command-a-plus-05-2026", "Command A+ (recommended)"),
        ("command-r-plus-08-2024", "Command R+"),
        ("command-r-08-2024", "Command R"),
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


def default_data_dir() -> Path:
    return Path.home() / CONFIG_DIR_NAME / DATA_SUBDIR_NAME


def _recommended_model_index(_provider: str) -> int:
    """Recommended model is always the first entry in each provider list."""
    return 0


def recommended_embedding_model(provider: str) -> str:
    models = PROVIDER_MODELS[provider]
    return models[_recommended_model_index(provider)][0]


def recommended_llm_model(provider: str) -> str:
    models = LLM_PROVIDER_MODELS[provider]
    return models[_recommended_model_index(provider)][0]


def has_existing_stored_data(data_dir: Path | None = None) -> bool:
    """True when ~/.moorcheh/data already contains namespaces or indexed items."""
    root = data_dir or default_data_dir()
    store_path = root / DATA_STORE_FILENAME
    registry_path = root / NAMESPACE_REGISTRY_FILENAME

    if store_path.is_file():
        try:
            payload = json.loads(store_path.read_text(encoding="utf-8"))
            items: list[Any] | None = None
            if isinstance(payload, dict):
                # Server persists items under "moorcheh_data_store" (see store.rs).
                raw = payload.get("moorcheh_data_store")
                if isinstance(raw, list):
                    items = raw
                else:
                    legacy = payload.get("items")
                    if isinstance(legacy, list):
                        items = legacy
            if items:
                return True
        except (json.JSONDecodeError, OSError):
            pass

    if registry_path.is_file():
        try:
            payload = json.loads(registry_path.read_text(encoding="utf-8"))
            # Server persists namespaces as a top-level JSON array.
            if isinstance(payload, list) and payload:
                return True
            if isinstance(payload, dict):
                namespaces = payload.get("namespaces")
                if isinstance(namespaces, list) and namespaces:
                    return True
        except (json.JSONDecodeError, OSError):
            pass

    return False


def _print_existing_data_warning() -> None:
    """Inform the user before they change embedding settings (no confirmation)."""
    if not has_existing_stored_data():
        return
    print("\n*** WARNING: existing Moorcheh data detected ***")
    print(f"Data directory: {default_data_dir()}")
    print(
        "You already have namespaces and/or documents stored locally. "
        "Changing the embedding provider or model will break semantic search and "
        "/answer for existing text namespaces — those vectors were built with your "
        "previous embedding model and dimensions."
    )
    print("Keep your current embedding settings, or re-upload all text documents after changing.")


def _confirm_embedding_change_if_data_exists(
    *,
    existing: EmbeddingConfig | None,
    new_provider: str,
    new_model: str,
) -> None:
    if not has_existing_stored_data():
        return
    if (
        existing is not None
        and existing.provider == new_provider
        and existing.model == new_model
    ):
        return

    _print_existing_data_warning()
    confirm = input("Continue with new embedding settings anyway? [y/N]: ").strip().lower()
    if confirm not in ("y", "yes"):
        raise SystemExit("Configure cancelled; existing data kept with previous settings.")


@dataclass
class EmbeddingConfig:
    provider: str
    model: str
    api_key: str | None = None
    base_url: str | None = None

    def requires_api_key(self) -> bool:
        return self.provider != "ollama"

    def default_model(self) -> str:
        return recommended_embedding_model(self.provider)

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
            model=self.model or recommended_embedding_model(self.provider),
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
        default_model = recommended_embedding_model(provider)
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


@dataclass
class LlmConfig:
    provider: str
    model: str
    api_key: str | None = None
    base_url: str | None = None

    def requires_api_key(self) -> bool:
        return self.provider != "ollama"

    def default_model(self) -> str:
        return recommended_llm_model(self.provider)

    def resolved_base_url(
        self,
        *,
        ollama_runtime_url: str | None = None,
        embedding: EmbeddingConfig | None = None,
    ) -> str:
        if self.provider == "ollama":
            if ollama_runtime_url:
                return ollama_runtime_url
            if self.base_url:
                return self.base_url
            return default_base_url("ollama")
        if self.base_url:
            return self.base_url
        if embedding and embedding.provider == self.provider and embedding.base_url:
            return embedding.resolved_base_url(ollama_runtime_url=ollama_runtime_url)
        return default_base_url(self.provider)

    def with_provider_defaults(self) -> LlmConfig:
        return LlmConfig(
            provider=self.provider,
            model=self.model or recommended_llm_model(self.provider),
            api_key=self.api_key,
            base_url=self.base_url or default_base_url(self.provider),
        )

    def to_compose_env(
        self,
        *,
        ollama_runtime_url: str | None = None,
        embedding: EmbeddingConfig | None = None,
    ) -> dict[str, str]:
        base_url = self.resolved_base_url(
            ollama_runtime_url=ollama_runtime_url,
            embedding=embedding,
        )
        env: dict[str, str] = {
            "LLM_PROVIDER": self.provider,
            "LLM_MODEL": self.model,
            "LLM_BASE_URL": base_url,
        }
        if self.api_key:
            env["LLM_API_KEY"] = self.api_key
        elif embedding and embedding.api_key and embedding.provider == self.provider:
            env["LLM_API_KEY"] = embedding.api_key
        return env

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LlmConfig:
        provider = str(data.get("provider", "ollama")).strip().lower()
        if provider not in PROVIDER_CHOICES:
            raise ValueError(f"unsupported LLM provider '{provider}'")
        default_model = recommended_llm_model(provider)
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

    @classmethod
    def default_for_embedding(cls, embedding: EmbeddingConfig) -> LlmConfig:
        return cls(
            provider=embedding.provider,
            model=recommended_llm_model(embedding.provider),
            api_key=embedding.api_key,
            base_url=embedding.base_url or default_base_url(embedding.provider),
        )


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


def load_llm_config(*, embedding: EmbeddingConfig | None = None) -> LlmConfig | None:
    raw = load_config()
    if not raw:
        return None
    llm = raw.get("llm")
    if isinstance(llm, dict):
        return LlmConfig.from_dict(llm)
    if embedding:
        return LlmConfig.default_for_embedding(embedding)
    return None


def save_runtime_config(embedding: EmbeddingConfig, llm: LlmConfig) -> Path:
    embedding = embedding.with_provider_defaults()
    llm = llm.with_provider_defaults()
    path = config_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "embedding": {
            "provider": embedding.provider,
            "model": embedding.model,
            "base_url": embedding.base_url,
        },
        "llm": {
            "provider": llm.provider,
            "model": llm.model,
            "base_url": llm.base_url,
        },
    }
    if embedding.api_key:
        payload["embedding"]["api_key"] = embedding.api_key
    if llm.api_key:
        payload["llm"]["api_key"] = llm.api_key
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return path


def save_embedding_config(config: EmbeddingConfig) -> Path:
    llm = load_llm_config(embedding=config) or LlmConfig.default_for_embedding(config)
    return save_runtime_config(config, llm)


def _prompt_choice(prompt: str, choices: tuple[str, ...], default: str) -> str:
    options = "/".join(choices)
    while True:
        value = input(f"{prompt} [{options}] (default: {default}): ").strip().lower()
        if not value:
            return default
        if value in choices:
            return value
        print(f"Choose one of: {', '.join(choices)}")


def _prompt_model_for_provider(
    provider: str,
    *,
    models: dict[str, list[tuple[str, str]]] | None = None,
    label: str = "embedding",
) -> str:
    catalog = models or PROVIDER_MODELS
    choices = catalog[provider]
    default_choice = _recommended_model_index(provider) + 1
    default_model = choices[_recommended_model_index(provider)][0]
    print(f"\nSelect an {label} model for {provider}:")
    for index, (model_id, model_label) in enumerate(choices, start=1):
        print(f"  {index}. {model_label}  ({model_id})")
    while True:
        raw = input(f"Choice [1-{len(choices)}] (default: {default_choice}): ").strip()
        if not raw:
            return default_model
        if raw.isdigit():
            choice = int(raw)
            if 1 <= choice <= len(choices):
                return choices[choice - 1][0]
        print(f"Enter a number from 1 to {len(choices)}, or press Enter for the default.")


def _prompt_llm_model_for_provider(provider: str) -> str:
    return _prompt_model_for_provider(
        provider,
        models=LLM_PROVIDER_MODELS,
        label="LLM",
    )


def _configure_llm_interactive(embedding: EmbeddingConfig) -> LlmConfig:
    print("\nConfigure the LLM for /answer (AI generation).")
    same = input(
        f"Use the same provider as embeddings ({embedding.provider})? [Y/n]: "
    ).strip().lower()
    if same in ("", "y", "yes"):
        provider = embedding.provider
    else:
        provider = _prompt_choice("LLM provider", PROVIDER_CHOICES, embedding.provider)

    model = _prompt_llm_model_for_provider(provider)

    api_key: str | None = None
    if provider != "ollama":
        if embedding.provider == provider and embedding.api_key:
            reuse = input(f"Reuse saved API key for {provider}? [Y/n]: ").strip().lower()
            if reuse in ("", "y", "yes"):
                api_key = embedding.api_key
        if not api_key:
            while True:
                api_key = getpass(f"API key for {provider} LLM (input hidden): ").strip()
                if api_key:
                    break
                print("API key is required for cloud LLM providers.")

    if provider == "ollama":
        from moorcheh.cli.ollama_setup import prepare_ollama_at_configure

        prepare_ollama_at_configure(model)

    return LlmConfig(
        provider=provider,
        model=model,
        api_key=api_key,
        base_url=default_base_url(provider),
    )


def configure_embedding_interactive(*, force: bool = False) -> EmbeddingConfig:
    saved = load_embedding_config()
    existing = None if force else saved

    _print_existing_data_warning()

    if existing and not force:
        reuse = input(
            f"Use saved embedding config ({existing.provider}, model={existing.model})? [Y/n]: "
        ).strip().lower()
        if reuse in ("", "y", "yes"):
            resolved = existing.with_provider_defaults()
            if resolved.provider == "ollama":
                from moorcheh.cli.ollama_setup import prepare_ollama_at_configure

                prepare_ollama_at_configure(resolved.model)
            return resolved
        print(
            "\nYou chose to change embedding settings. "
            "You will be asked to confirm again before anything is saved."
        )

    print("Configure text embeddings for Moorcheh (used for text namespaces and text search).")
    provider = _prompt_choice("Embedding provider", PROVIDER_CHOICES, DEFAULT_PROVIDER)
    model = _prompt_model_for_provider(provider)

    _confirm_embedding_change_if_data_exists(
        existing=saved,
        new_provider=provider,
        new_model=model,
    )

    api_key: str | None = None
    if provider != "ollama":
        while True:
            api_key = getpass(f"API key for {provider} (input hidden): ").strip()
            if api_key:
                break
            print("API key is required for cloud embedding providers.")

    if provider == "ollama":
        from moorcheh.cli.ollama_setup import prepare_ollama_at_configure

        prepare_ollama_at_configure(model)

    config = EmbeddingConfig(
        provider=provider,
        model=model,
        api_key=api_key,
        base_url=default_base_url(provider),
    )
    llm = _configure_llm_interactive(config)
    save_runtime_config(config, llm)
    print(f"Saved to {config_file_path()}")
    print("API base URL is stored in config (defaults from this release). Edit base_url there to override.")
    print(
        "\nRestart the server to apply: moorcheh down  then  moorcheh up"
    )
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
        resolved_model = (model or recommended_embedding_model(resolved_provider)).strip()
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
        llm = load_llm_config(embedding=config) or LlmConfig.default_for_embedding(config)
        save_runtime_config(config, llm)
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
