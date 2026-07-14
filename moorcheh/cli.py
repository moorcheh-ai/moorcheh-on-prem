from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from moorcheh.api import MoorchehApiClient, MoorchehApiError
from moorcheh.docker_runtime import (
    DEFAULT_OLLAMA_IMAGE,
    DEFAULT_SERVER_IMAGE,
    ComposeCommandError,
    default_upload_dir,
    down,
    ensure_upload_dir,
    host_path_to_container_upload_path,
    up,
)
from moorcheh.user_config import configure_embedding_interactive, config_file_path, load_llm_config


def _print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2))


def _parse_json(text: str, field_name: str) -> dict[str, Any]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{field_name} must be valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{field_name} must be a JSON object")
    return data


def _parse_json_array(text: str, field_name: str) -> list[Any]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{field_name} must be valid JSON: {exc}") from exc
    if not isinstance(data, list):
        raise ValueError(f"{field_name} must be a JSON array")
    return data


def _api_client(base_url: str) -> MoorchehApiClient:
    return MoorchehApiClient(base_url=base_url)


def cmd_up(args: argparse.Namespace) -> int:
    bundled_ollama: bool | None
    if args.bundled_ollama and args.use_host_ollama:
        raise ValueError("Use only one of --bundled-ollama or --use-host-ollama")
    if args.bundled_ollama:
        bundled_ollama = True
    elif args.use_host_ollama:
        bundled_ollama = False
    else:
        bundled_ollama = None

    result, started_bundled_ollama, data_dir, embedding, llm = up(
        server_image=args.server_image,
        ollama_image=args.ollama_image,
        server_port=args.server_port,
        ollama_port=args.ollama_port,
        bundled_ollama=bundled_ollama,
        ollama_host=args.ollama_host,
        embedding_provider=args.embedding_provider,
        embedding_model=args.embedding_model,
        embedding_api_key=args.embedding_api_key,
        configure=args.configure,
        no_configure=args.no_configure,
        skip_ollama_model_pull=args.skip_ollama_model_pull,
    )
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip(), file=sys.stderr)
    print(f"Server image: {args.server_image}")
    print(f"Data directory: {data_dir}")
    print(f"Upload directory: {ensure_upload_dir()}")
    print(f"Embedding provider: {embedding.provider}  |  model: {embedding.model}")
    print(f"LLM provider: {llm.provider}  |  model: {llm.model}")
    if embedding.provider == "ollama" or llm.provider == "ollama":
        if started_bundled_ollama:
            print(
                f"Started Moorcheh server + Ollama container (Ollama on host port {args.ollama_port})"
            )
        else:
            print(
                f"Using Ollama already running at http://{args.ollama_host}:{args.ollama_port} "
                "(moorcheh-ollama container not started)"
            )
    else:
        print("Moorcheh server started (cloud embedding provider; Ollama not required).")
    print(f"Moorcheh API: http://localhost:{args.server_port}")
    return 0


def cmd_down(args: argparse.Namespace) -> int:
    bundled_ollama: bool | None
    if args.bundled_ollama and args.use_host_ollama:
        raise ValueError("Use only one of --bundled-ollama or --use-host-ollama")
    if args.bundled_ollama:
        bundled_ollama = True
    elif args.use_host_ollama:
        bundled_ollama = False
    else:
        bundled_ollama = None

    include_ollama: bool | None
    if bundled_ollama is True:
        include_ollama = True
    elif bundled_ollama is False:
        include_ollama = False
    else:
        include_ollama = None

    result = down(include_ollama=include_ollama)
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip(), file=sys.stderr)
    return 0


def cmd_configure(args: argparse.Namespace) -> int:
    embedding = configure_embedding_interactive(force=args.force)
    llm = load_llm_config(embedding=embedding)
    print(f"Embedding: {embedding.provider}  |  model: {embedding.model}")
    if llm:
        print(f"LLM:       {llm.provider}  |  model: {llm.model}")
    print(f"Config file: {config_file_path()}")
    print(
        "\nConfig is saved on disk only. To apply it to the running server, recreate the container:\n"
        "  moorcheh down\n"
        "  moorcheh up"
    )
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    client = _api_client(args.base_url)
    health = client.health()
    items = health.get("items")
    max_items = health.get("max_items")
    remaining = health.get("remaining")
    if items is not None and max_items is not None:
        provider = health.get("embedding_provider", "ollama")
        print(
            f"items: {items} / {max_items}  |  remaining: {remaining}  |  "
            f"embedding: {provider} / {health.get('model')}  |  "
            f"llm: {health.get('llm_provider')} / {health.get('llm_model')}"
        )
    _print_json(health)
    return 0


def cmd_namespace_create(args: argparse.Namespace) -> int:
    client = _api_client(args.base_url)
    payload: dict[str, Any] = {
        "namespace_name": args.name,
        "type": args.type,
    }
    if args.vector_dimension is not None:
        payload["vector_dimension"] = args.vector_dimension
    _print_json(client.create_namespace(payload))
    return 0


def cmd_namespace_list(args: argparse.Namespace) -> int:
    client = _api_client(args.base_url)
    _print_json(client.list_namespaces())
    return 0


def cmd_namespace_delete(args: argparse.Namespace) -> int:
    client = _api_client(args.base_url)
    _print_json(
        client.delete_namespace(
            args.namespace_name,
            wait=not args.no_wait,
            poll_interval=args.poll_interval,
            timeout=args.wait_timeout,
        )
    )
    return 0


def cmd_namespace_delete_job_status(args: argparse.Namespace) -> int:
    client = _api_client(args.base_url)
    _print_json(client.delete_namespace_job_status(args.namespace_name, args.job_id))
    return 0


def cmd_upload_documents(args: argparse.Namespace) -> int:
    client = _api_client(args.base_url)
    documents_path = Path(args.documents_file)
    payload = json.loads(documents_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("documents file must contain a JSON object with a 'documents' array")
    _print_json(client.upload_namespace_documents(args.namespace_name, payload))
    return 0


def cmd_upload_vectors(args: argparse.Namespace) -> int:
    client = _api_client(args.base_url)
    vectors_path = Path(args.vectors_file)
    payload = json.loads(vectors_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("vectors file must contain a JSON object with a 'vectors' array")
    _print_json(client.upload_namespace_vectors(args.namespace_name, payload))
    return 0


def cmd_upload_job_status(args: argparse.Namespace) -> int:
    client = _api_client(args.base_url)
    _print_json(client.upload_job_status(args.namespace_name, args.job_id))
    return 0


def cmd_upload_file(args: argparse.Namespace) -> int:
    client = _api_client(args.base_url)
    upload_root = default_upload_dir()
    host_file = Path(args.file).resolve()
    if not host_file.is_file():
        raise ValueError(f"File not found: {host_file}")
    container_path = host_path_to_container_upload_path(host_file, upload_root)
    file_entry: dict[str, Any] = {"path": container_path}
    if args.force_reindex:
        file_entry["force_reindex"] = True
    if args.metadata_json:
        metadata = _parse_json(args.metadata_json, "metadata_json")
        file_entry.update(metadata)
    _print_json(
        client.upload_namespace_files(
            args.namespace_name,
            {"files": [file_entry]},
        )
    )
    return 0


def cmd_upload_files(args: argparse.Namespace) -> int:
    client = _api_client(args.base_url)
    files_path = Path(args.files_file)
    payload = json.loads(files_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("files file must contain a JSON object with a 'files' array")
    _print_json(client.upload_namespace_files(args.namespace_name, payload))
    return 0


def cmd_list_files(args: argparse.Namespace) -> int:
    client = _api_client(args.base_url)
    _print_json(client.list_namespace_files(args.namespace_name))
    return 0


def cmd_file_get(args: argparse.Namespace) -> int:
    client = _api_client(args.base_url)
    _print_json(client.get_namespace_file(args.namespace_name, args.file_id))
    return 0


def cmd_delete_file(args: argparse.Namespace) -> int:
    client = _api_client(args.base_url)
    has_path = bool(args.path and args.path.strip())
    has_file_id = bool(args.file_id and args.file_id.strip())
    if has_path == has_file_id:
        raise ValueError("Provide exactly one of --path or --file-id")
    payload: dict[str, Any] = {}
    if has_path:
        upload_root = default_upload_dir()
        host_file = Path(args.path).resolve()
        payload["path"] = host_path_to_container_upload_path(host_file, upload_root)
    else:
        payload["file_id"] = args.file_id
    _print_json(client.delete_namespace_files(args.namespace_name, payload))
    return 0


def cmd_file_job_status(args: argparse.Namespace) -> int:
    client = _api_client(args.base_url)
    _print_json(client.file_job_status(args.namespace_name, args.job_id))
    return 0


def cmd_fetch_text_data(args: argparse.Namespace) -> int:
    client = _api_client(args.base_url)
    _print_json(
        client.fetch_text_data(
            args.namespace_name,
            limit=args.limit,
            next_token=args.next_token or None,
        )
    )
    return 0


def cmd_items_get(args: argparse.Namespace) -> int:
    client = _api_client(args.base_url)
    ids = _parse_json_array(args.ids_json, "ids_json")
    if any(not isinstance(item, str) for item in ids):
        raise ValueError("ids_json must be an array of strings")
    payload = {"ids": ids}
    _print_json(client.get_namespace_items(args.namespace_name, payload))
    return 0


def cmd_items_delete(args: argparse.Namespace) -> int:
    client = _api_client(args.base_url)
    ids = _parse_json_array(args.ids_json, "ids_json")
    if any(not isinstance(item, str) for item in ids):
        raise ValueError("ids_json must be an array of strings")
    payload = {"ids": ids}
    _print_json(client.delete_namespace_items(args.namespace_name, payload))
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    client = _api_client(args.base_url)
    query: Any
    if args.query_vector_json is not None:
        query = json.loads(args.query_vector_json)
        if not isinstance(query, list):
            raise ValueError("query_vector_json must be a JSON array")
    else:
        if not args.query:
            raise ValueError("query is required when query_vector_json is not provided")
        query = args.query
    namespaces = [n.strip() for n in args.namespaces.split(",") if n.strip()]
    payload: dict[str, Any] = {
        "query": query,
        "top_k": args.top_k,
        "threshold": args.threshold,
        "namespaces": namespaces,
    }
    _print_json(
        client.search(payload)
    )
    return 0


def cmd_answer(args: argparse.Namespace) -> int:
    client = _api_client(args.base_url)
    payload: dict[str, Any] = {
        "query": args.query,
        "namespace": args.namespace,
    }
    if args.top_k is not None:
        payload["top_k"] = args.top_k
    if args.temperature is not None:
        payload["temperature"] = args.temperature
    if args.ai_model:
        payload["ai_model"] = args.ai_model
    if args.header_prompt:
        payload["header_prompt"] = args.header_prompt
    if args.footer_prompt:
        payload["footer_prompt"] = args.footer_prompt
    if args.kiosk_mode:
        payload["kiosk_mode"] = True
    if args.threshold is not None:
        payload["threshold"] = args.threshold
    if args.chat_history_json:
        payload["chat_history"] = _parse_json_array(args.chat_history_json, "chat_history_json")
    if args.structured:
        payload["structured_response"] = {"enabled": True}
    _print_json(client.answer(payload))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="moorcheh", description="Moorcheh on-prem client and runtime CLI.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_configure = sub.add_parser(
        "configure",
        help="Save embedding provider, model, and API key to ~/.moorcheh/config.json.",
    )
    p_configure.add_argument(
        "--force",
        action="store_true",
        help="Re-run interactive setup even if config already exists.",
    )
    p_configure.set_defaults(func=cmd_configure)

    p_up = sub.add_parser("up", help="Start Moorcheh server (and Ollama only when configured).")
    p_up.add_argument("--server-image", default=DEFAULT_SERVER_IMAGE)
    p_up.add_argument("--ollama-image", default=DEFAULT_OLLAMA_IMAGE)
    p_up.add_argument("--server-port", type=int, default=8080)
    p_up.add_argument(
        "--ollama-port",
        type=int,
        default=11434,
        help="Host port to probe for existing Ollama, or to publish bundled Ollama on.",
    )
    p_up.add_argument(
        "--ollama-host",
        default="127.0.0.1",
        help="Host to probe for existing Ollama (default: 127.0.0.1).",
    )
    p_up.add_argument(
        "--bundled-ollama",
        action="store_true",
        help="Always start the moorcheh-ollama Docker container.",
    )
    p_up.add_argument(
        "--use-host-ollama",
        action="store_true",
        help="Never start moorcheh-ollama; server uses Ollama on the host (port 11434).",
    )
    p_up.add_argument(
        "--embedding-provider",
        choices=["ollama", "openai", "cohere"],
        help="Embedding provider (saved to ~/.moorcheh/config.json when set).",
    )
    p_up.add_argument("--embedding-model", help="Embedding model name for the chosen provider.")
    p_up.add_argument(
        "--ollama-model",
        dest="embedding_model",
        help="Deprecated alias for --embedding-model when provider is ollama.",
    )
    p_up.add_argument("--embedding-api-key", help="API key for openai/cohere (avoid in shell history).")
    p_up.add_argument(
        "--configure",
        action="store_true",
        help="Run interactive embedding setup before starting.",
    )
    p_up.add_argument(
        "--no-configure",
        action="store_true",
        help="Do not prompt; fail if ~/.moorcheh/config.json is missing.",
    )
    p_up.add_argument(
        "--skip-ollama-model-pull",
        action="store_true",
        help="When embedding provider is ollama, do not pull the model if missing (default: pull automatically).",
    )
    p_up.set_defaults(func=cmd_up)

    p_down = sub.add_parser("down", help="Stop and remove runtime containers.")
    p_down.add_argument("--bundled-ollama", action="store_true")
    p_down.add_argument("--use-host-ollama", action="store_true")
    p_down.set_defaults(func=cmd_down)

    p_status = sub.add_parser("status", help="Check server health endpoint.")
    p_status.add_argument("--base-url", default="http://localhost:8080")
    p_status.set_defaults(func=cmd_status)

    p_namespace_create = sub.add_parser("namespace-create", help="Create a namespace.")
    p_namespace_create.add_argument("--base-url", default="http://localhost:8080")
    p_namespace_create.add_argument("--name", required=True)
    p_namespace_create.add_argument("--type", choices=["text", "vector"], required=True)
    p_namespace_create.add_argument("--vector-dimension", type=int)
    p_namespace_create.set_defaults(func=cmd_namespace_create)

    p_namespace_list = sub.add_parser("namespace-list", help="List namespaces.")
    p_namespace_list.add_argument("--base-url", default="http://localhost:8080")
    p_namespace_list.set_defaults(func=cmd_namespace_list)

    p_namespace_delete = sub.add_parser(
        "namespace-delete",
        help="Delete a namespace. Waits for the async delete job by default.",
    )
    p_namespace_delete.add_argument("--base-url", default="http://localhost:8080")
    p_namespace_delete.add_argument("--namespace-name", required=True)
    p_namespace_delete.add_argument(
        "--no-wait",
        action="store_true",
        help="Return immediately with job_id instead of polling until completed.",
    )
    p_namespace_delete.add_argument(
        "--poll-interval",
        type=float,
        default=0.2,
        help="Seconds between delete-job status polls (default: 0.2).",
    )
    p_namespace_delete.add_argument(
        "--wait-timeout",
        type=float,
        default=120.0,
        help="Max seconds to wait for delete job completion (default: 120).",
    )
    p_namespace_delete.set_defaults(func=cmd_namespace_delete)

    p_namespace_delete_job_status = sub.add_parser(
        "namespace-delete-job-status",
        help="Call GET /namespaces/{namespace_name}/delete-jobs/{job_id}.",
    )
    p_namespace_delete_job_status.add_argument("--base-url", default="http://localhost:8080")
    p_namespace_delete_job_status.add_argument("--namespace-name", required=True)
    p_namespace_delete_job_status.add_argument("--job-id", required=True)
    p_namespace_delete_job_status.set_defaults(func=cmd_namespace_delete_job_status)

    p_upload_documents = sub.add_parser("upload-documents", help="Call POST /namespaces/{namespace_name}/documents.")
    p_upload_documents.add_argument("--base-url", default="http://localhost:8080")
    p_upload_documents.add_argument("--namespace-name", required=True)
    p_upload_documents.add_argument("--documents-file", required=True, help="Path to JSON body with {'documents': [...]} payload.")
    p_upload_documents.set_defaults(func=cmd_upload_documents)

    p_upload_vectors = sub.add_parser("upload-vectors", help="Call POST /namespaces/{namespace_name}/vectors.")
    p_upload_vectors.add_argument("--base-url", default="http://localhost:8080")
    p_upload_vectors.add_argument("--namespace-name", required=True)
    p_upload_vectors.add_argument("--vectors-file", required=True, help="Path to JSON body with {'vectors': [...]} payload.")
    p_upload_vectors.set_defaults(func=cmd_upload_vectors)

    p_upload_job_status = sub.add_parser(
        "upload-job-status",
        help="Poll document or vector upload job (GET .../upload-jobs/{job_id}).",
    )
    p_upload_job_status.add_argument("--base-url", default="http://localhost:8080")
    p_upload_job_status.add_argument("--namespace-name", required=True)
    p_upload_job_status.add_argument("--job-id", required=True)
    p_upload_job_status.set_defaults(func=cmd_upload_job_status)

    p_upload_file = sub.add_parser(
        "upload-file",
        help="Upload one file from ~/.moorcheh/uploads (POST /namespaces/{namespace_name}/files).",
    )
    p_upload_file.add_argument("--base-url", default="http://localhost:8080")
    p_upload_file.add_argument("--namespace-name", required=True)
    p_upload_file.add_argument("--file", required=True, help="Host path to a file under ~/.moorcheh/uploads")
    p_upload_file.add_argument("--force-reindex", action="store_true")
    p_upload_file.add_argument("--metadata-json", default="", help='Optional JSON object merged into file metadata.')
    p_upload_file.set_defaults(func=cmd_upload_file)

    p_upload_files = sub.add_parser(
        "upload-files",
        help="Upload files from a JSON payload (POST /namespaces/{namespace_name}/files).",
    )
    p_upload_files.add_argument("--base-url", default="http://localhost:8080")
    p_upload_files.add_argument("--namespace-name", required=True)
    p_upload_files.add_argument("--files-file", required=True, help="JSON body with {'files': [...]} using container paths.")
    p_upload_files.set_defaults(func=cmd_upload_files)

    p_list_files = sub.add_parser("list-files", help="List indexed files in a namespace.")
    p_list_files.add_argument("--base-url", default="http://localhost:8080")
    p_list_files.add_argument("--namespace-name", required=True)
    p_list_files.set_defaults(func=cmd_list_files)

    p_file_get = sub.add_parser("file-get", help="Get one indexed file record by file_id.")
    p_file_get.add_argument("--base-url", default="http://localhost:8080")
    p_file_get.add_argument("--namespace-name", required=True)
    p_file_get.add_argument("--file-id", required=True)
    p_file_get.set_defaults(func=cmd_file_get)

    p_delete_file = sub.add_parser(
        "delete-file",
        help="Remove a file from the Moorcheh index only (disk file is kept).",
    )
    p_delete_file.add_argument("--base-url", default="http://localhost:8080")
    p_delete_file.add_argument("--namespace-name", required=True)
    p_delete_file.add_argument("--path", help="Host path under ~/.moorcheh/uploads")
    p_delete_file.add_argument("--file-id", help="Indexed file_id from list-files")
    p_delete_file.set_defaults(func=cmd_delete_file)

    p_file_job_status = sub.add_parser(
        "file-job-status",
        help="Poll file upload or delete job (GET .../file-jobs/{job_id}).",
    )
    p_file_job_status.add_argument("--base-url", default="http://localhost:8080")
    p_file_job_status.add_argument("--namespace-name", required=True)
    p_file_job_status.add_argument("--job-id", required=True)
    p_file_job_status.set_defaults(func=cmd_file_job_status)

    p_fetch_text_data = sub.add_parser(
        "fetch-text-data",
        help="List text chunks with cursor pagination (GET .../documents/fetch-text-data).",
    )
    p_fetch_text_data.add_argument("--base-url", default="http://localhost:8080")
    p_fetch_text_data.add_argument("--namespace-name", required=True)
    p_fetch_text_data.add_argument("--limit", type=int, help="Page size (default 100, max 100).")
    p_fetch_text_data.add_argument("--next-token", help="Opaque cursor from a previous page.")
    p_fetch_text_data.set_defaults(func=cmd_fetch_text_data)

    p_items_get = sub.add_parser("items-get", help="Call POST /namespaces/{namespace_name}/items/get.")
    p_items_get.add_argument("--base-url", default="http://localhost:8080")
    p_items_get.add_argument("--namespace-name", required=True)
    p_items_get.add_argument("--ids-json", required=True, help='JSON array string, e.g. ["id1","id2"].')
    p_items_get.set_defaults(func=cmd_items_get)

    p_items_delete = sub.add_parser("items-delete", help="Call POST /namespaces/{namespace_name}/items/delete.")
    p_items_delete.add_argument("--base-url", default="http://localhost:8080")
    p_items_delete.add_argument("--namespace-name", required=True)
    p_items_delete.add_argument("--ids-json", required=True, help='JSON array string, e.g. ["id1","id2"].')
    p_items_delete.set_defaults(func=cmd_items_delete)

    p_search = sub.add_parser("search", help="Call /search endpoint.")
    p_search.add_argument("--base-url", default="http://localhost:8080")
    p_search.add_argument("--query", help="Text query.")
    p_search.add_argument("--query-vector-json", help="JSON array string vector query.")
    p_search.add_argument("--namespaces", default="", help="Comma-separated namespace list.")
    p_search.add_argument("--top-k", type=int, default=5)
    p_search.add_argument("--threshold", type=float, default=0.0)
    p_search.set_defaults(func=cmd_search)

    p_answer = sub.add_parser("answer", help="Call /answer endpoint.")
    p_answer.add_argument("--base-url", default="http://localhost:8080")
    p_answer.add_argument("--query", required=True)
    p_answer.add_argument(
        "--namespace",
        default="",
        help='Namespace for RAG search mode, or "" (default) for direct LLM.',
    )
    p_answer.add_argument("--top-k", type=int)
    p_answer.add_argument("--temperature", type=float)
    p_answer.add_argument("--ai-model", help="Override configured LLM model.")
    p_answer.add_argument("--header-prompt")
    p_answer.add_argument("--footer-prompt")
    p_answer.add_argument("--threshold", type=float)
    p_answer.add_argument("--kiosk-mode", action="store_true")
    p_answer.add_argument(
        "--chat-history-json",
        help='JSON array of {"role":"user"|"assistant","content":"..."} turns.',
    )
    p_answer.add_argument(
        "--structured",
        action="store_true",
        help="Enable structured_response with the default schema.",
    )
    p_answer.set_defaults(func=cmd_answer)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        code = args.func(args)
    except ComposeCommandError as exc:
        if exc.stdout.strip():
            print(exc.stdout.strip())
        if exc.stderr.strip():
            print(exc.stderr.strip(), file=sys.stderr)
        print(f"Error: docker compose failed (exit {exc.returncode})", file=sys.stderr)
        raise SystemExit(1) from exc
    except MoorchehApiError as exc:
        if exc.body:
            _print_json(exc.body)
        print(f"Error ({exc.status_code}): {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    except Exception as exc:  # pragma: no cover - surfaced to CLI user
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    raise SystemExit(code)


if __name__ == "__main__":
    main()
