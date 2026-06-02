from __future__ import annotations

import argparse
import json
from unittest.mock import MagicMock, patch

import pytest

from moorcheh.api import MoorchehApiClient, MoorchehApiError
from moorcheh.cli import (
    _parse_json,
    _parse_json_array,
    build_parser,
    cmd_configure,
    cmd_down,
    cmd_items_delete,
    cmd_items_get,
    cmd_namespace_create,
    cmd_namespace_delete,
    cmd_namespace_delete_job_status,
    cmd_namespace_list,
    cmd_search,
    cmd_status,
    cmd_up,
    cmd_upload_documents,
    cmd_upload_job_status,
    cmd_upload_vectors,
    main,
)
from moorcheh.docker_runtime import ComposeCommandError
from moorcheh.user_config import EmbeddingConfig


ALL_COMMANDS = {
    "configure",
    "up",
    "down",
    "status",
    "namespace-create",
    "namespace-list",
    "namespace-delete",
    "namespace-delete-job-status",
    "upload-documents",
    "upload-vectors",
    "upload-job-status",
    "items-get",
    "items-delete",
    "search",
}


def _subcommand_choices(parser: argparse.ArgumentParser) -> set[str]:
    sub = next(a for a in parser._actions if getattr(a, "choices", None))
    return set(sub.choices.keys())


def test_parse_json_object() -> None:
    assert _parse_json('{"a": 1}', "payload") == {"a": 1}


def test_parse_json_rejects_invalid() -> None:
    with pytest.raises(ValueError, match="payload must be valid JSON"):
        _parse_json("{", "payload")
    with pytest.raises(ValueError, match="payload must be a JSON object"):
        _parse_json("[1]", "payload")


def test_parse_json_array() -> None:
    assert _parse_json_array('["a", "b"]', "ids") == ["a", "b"]


def test_parse_json_array_rejects_non_array() -> None:
    with pytest.raises(ValueError, match="ids must be a JSON array"):
        _parse_json_array('{"a": 1}', "ids")


def test_build_parser_includes_all_commands() -> None:
    assert _subcommand_choices(build_parser()) == ALL_COMMANDS


def test_parser_namespace_create_vector_dimension() -> None:
    args = build_parser().parse_args(
        ["namespace-create", "--name", "vec", "--type", "vector", "--vector-dimension", "768"]
    )
    assert args.vector_dimension == 768


@patch.object(MoorchehApiClient, "health", return_value={"items": 1, "max_items": 10, "remaining": 9, "model": "m"})
def test_cmd_status(_health: MagicMock, capsys: pytest.CaptureFixture[str]) -> None:
    args = argparse.Namespace(base_url="http://localhost:8080")
    assert cmd_status(args) == 0
    out = capsys.readouterr().out
    assert "items: 1 / 10" in out
    assert '"items": 1' in out
    _health.assert_called_once()


@patch.object(MoorchehApiClient, "create_namespace", return_value={"ok": True})
def test_cmd_namespace_create_text(create: MagicMock, capsys: pytest.CaptureFixture[str]) -> None:
    args = argparse.Namespace(
        base_url="http://localhost:8080",
        name="docs",
        type="text",
        vector_dimension=None,
    )
    assert cmd_namespace_create(args) == 0
    create.assert_called_once_with({"namespace_name": "docs", "type": "text"})
    assert '"ok": true' in capsys.readouterr().out.lower()


@patch.object(MoorchehApiClient, "create_namespace", return_value={"ok": True})
def test_cmd_namespace_create_vector(create: MagicMock) -> None:
    args = argparse.Namespace(
        base_url="http://localhost:8080",
        name="vec",
        type="vector",
        vector_dimension=768,
    )
    cmd_namespace_create(args)
    create.assert_called_once_with({"namespace_name": "vec", "type": "vector", "vector_dimension": 768})


@patch.object(MoorchehApiClient, "list_namespaces", return_value={"namespaces": []})
def test_cmd_namespace_list(list_ns: MagicMock) -> None:
    args = argparse.Namespace(base_url="http://localhost:8080")
    assert cmd_namespace_list(args) == 0
    list_ns.assert_called_once()


@patch.object(MoorchehApiClient, "delete_namespace", return_value={"job_id": "del-1"})
def test_cmd_namespace_delete(delete: MagicMock) -> None:
    args = argparse.Namespace(base_url="http://localhost:8080", namespace_name="docs")
    assert cmd_namespace_delete(args) == 0
    delete.assert_called_once_with("docs")


@patch.object(MoorchehApiClient, "delete_namespace_job_status", return_value={"status": "completed"})
def test_cmd_namespace_delete_job_status(job: MagicMock) -> None:
    args = argparse.Namespace(base_url="http://localhost:8080", namespace_name="docs", job_id="del-1")
    assert cmd_namespace_delete_job_status(args) == 0
    job.assert_called_once_with("docs", "del-1")


def test_cmd_upload_documents(tmp_path, capsys: pytest.CaptureFixture[str]) -> None:
    doc_file = tmp_path / "docs.json"
    doc_file.write_text(json.dumps({"documents": [{"id": "d1", "text": "hi"}]}), encoding="utf-8")
    args = argparse.Namespace(
        base_url="http://localhost:8080",
        namespace_name="docs",
        documents_file=str(doc_file),
    )
    with patch.object(MoorchehApiClient, "upload_namespace_documents", return_value={"job_id": "j1"}) as upload:
        assert cmd_upload_documents(args) == 0
    upload.assert_called_once_with("docs", {"documents": [{"id": "d1", "text": "hi"}]})


def test_cmd_upload_vectors(tmp_path) -> None:
    vec_file = tmp_path / "vec.json"
    vec_file.write_text(json.dumps({"vectors": [{"id": "v1", "vector": [0.1]}]}), encoding="utf-8")
    args = argparse.Namespace(
        base_url="http://localhost:8080",
        namespace_name="vecns",
        vectors_file=str(vec_file),
    )
    with patch.object(MoorchehApiClient, "upload_namespace_vectors", return_value={"job_id": "j2"}) as upload:
        assert cmd_upload_vectors(args) == 0
    upload.assert_called_once_with("vecns", {"vectors": [{"id": "v1", "vector": [0.1]}]})


@patch.object(MoorchehApiClient, "upload_job_status", return_value={"status": "completed"})
def test_cmd_upload_job_status(job: MagicMock) -> None:
    args = argparse.Namespace(base_url="http://localhost:8080", namespace_name="docs", job_id="j1")
    assert cmd_upload_job_status(args) == 0
    job.assert_called_once_with("docs", "j1")


@patch.object(MoorchehApiClient, "get_namespace_items", return_value={"items": []})
def test_cmd_items_get(get_items: MagicMock) -> None:
    args = argparse.Namespace(
        base_url="http://localhost:8080",
        namespace_name="docs",
        ids_json='["a","b"]',
    )
    assert cmd_items_get(args) == 0
    get_items.assert_called_once_with("docs", {"ids": ["a", "b"]})


def test_cmd_items_get_rejects_non_string_ids() -> None:
    args = argparse.Namespace(
        base_url="http://localhost:8080",
        namespace_name="docs",
        ids_json="[1]",
    )
    with pytest.raises(ValueError, match="ids_json must be an array of strings"):
        cmd_items_get(args)


@patch.object(MoorchehApiClient, "delete_namespace_items", return_value={"deleted": 1})
def test_cmd_items_delete(delete_items: MagicMock) -> None:
    args = argparse.Namespace(
        base_url="http://localhost:8080",
        namespace_name="docs",
        ids_json='["a"]',
    )
    assert cmd_items_delete(args) == 0
    delete_items.assert_called_once_with("docs", {"ids": ["a"]})


@patch.object(MoorchehApiClient, "search", return_value={"results": []})
def test_cmd_search_text(search: MagicMock) -> None:
    args = argparse.Namespace(
        base_url="http://localhost:8080",
        query="hello",
        query_vector_json=None,
        namespaces="docs, products ",
        top_k=10,
        threshold=0.5,
        metadata_json='{"team":"ai"}',
    )
    assert cmd_search(args) == 0
    search.assert_called_once_with(
        {
            "query": "hello",
            "top_k": 10,
            "threshold": 0.5,
            "metadata": {"team": "ai"},
            "namespaces": ["docs", "products"],
        }
    )


@patch.object(MoorchehApiClient, "search", return_value={"results": []})
def test_cmd_search_vector(search: MagicMock) -> None:
    args = argparse.Namespace(
        base_url="http://localhost:8080",
        query=None,
        query_vector_json="[0.1, 0.2]",
        namespaces="vecns",
        top_k=5,
        threshold=0.0,
        metadata_json="{}",
    )
    assert cmd_search(args) == 0
    search.assert_called_once_with(
        {
            "query": [0.1, 0.2],
            "top_k": 5,
            "threshold": 0.0,
            "metadata": {},
            "namespaces": ["vecns"],
        }
    )


def test_cmd_search_requires_query_or_vector() -> None:
    args = argparse.Namespace(
        base_url="http://localhost:8080",
        query=None,
        query_vector_json=None,
        namespaces="",
        top_k=5,
        threshold=0.0,
        metadata_json="{}",
    )
    with pytest.raises(ValueError, match="query is required"):
        cmd_search(args)


def test_cmd_search_rejects_invalid_vector_json() -> None:
    args = argparse.Namespace(
        base_url="http://localhost:8080",
        query=None,
        query_vector_json='{"not": "array"}',
        namespaces="",
        top_k=5,
        threshold=0.0,
        metadata_json="{}",
    )
    with pytest.raises(ValueError, match="query_vector_json must be a JSON array"):
        cmd_search(args)


def _up_args(**overrides: object) -> argparse.Namespace:
    defaults = {
        "server_image": "moorcheh/server:latest",
        "ollama_image": "ollama/ollama:latest",
        "server_port": 8080,
        "ollama_port": 11434,
        "ollama_host": "127.0.0.1",
        "bundled_ollama": False,
        "use_host_ollama": False,
        "embedding_provider": None,
        "embedding_model": None,
        "embedding_api_key": None,
        "configure": False,
        "no_configure": False,
        "skip_ollama_model_pull": False,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


@patch(
    "moorcheh.cli.up",
    return_value=(
        MagicMock(stdout="started\n", stderr=""),
        True,
        MagicMock(),
        EmbeddingConfig(provider="ollama", model="nomic-embed-text"),
    ),
)
def test_cmd_up_bundled_ollama(up: MagicMock, capsys: pytest.CaptureFixture[str]) -> None:
    assert cmd_up(_up_args(bundled_ollama=True)) == 0
    up.assert_called_once()
    out = capsys.readouterr().out
    assert "Started Moorcheh server + Ollama" in out
    assert "Embedding provider: ollama" in out


@patch(
    "moorcheh.cli.up",
    return_value=(
        MagicMock(stdout="", stderr=""),
        False,
        MagicMock(),
        EmbeddingConfig(provider="openai", model="text-embedding-3-small", api_key="sk"),
    ),
)
def test_cmd_up_cloud_provider(up: MagicMock, capsys: pytest.CaptureFixture[str]) -> None:
    assert cmd_up(_up_args()) == 0
    out = capsys.readouterr().out
    assert "cloud embedding provider" in out
    assert "Embedding provider: openai" in out
    assert "Ollama not required" in out


def test_cmd_up_rejects_conflicting_ollama_flags() -> None:
    with pytest.raises(ValueError, match="only one of"):
        cmd_up(_up_args(bundled_ollama=True, use_host_ollama=True))


@patch(
    "moorcheh.cli.configure_embedding_interactive",
    return_value=EmbeddingConfig(provider="cohere", model="embed-v4.0", api_key="key"),
)
def test_cmd_configure(configure: MagicMock, capsys: pytest.CaptureFixture[str]) -> None:
    args = argparse.Namespace(force=False)
    assert cmd_configure(args) == 0
    configure.assert_called_once_with(force=False)
    out = capsys.readouterr().out
    assert "Provider: cohere" in out
    assert "Model: embed-v4.0" in out


@patch("moorcheh.cli.down", return_value=MagicMock(stdout="", stderr=""))
def test_cmd_down_bundled_ollama(down: MagicMock) -> None:
    args = argparse.Namespace(bundled_ollama=True, use_host_ollama=False)
    assert cmd_down(args) == 0
    down.assert_called_once_with(include_ollama=True)


def test_main_exits_on_moorcheh_api_error(capsys: pytest.CaptureFixture[str]) -> None:
    parser = build_parser()
    args = parser.parse_args(["namespace-list"])
    with (
        patch.object(parser, "parse_args", return_value=args),
        patch("moorcheh.cli.build_parser", return_value=parser),
        patch.object(MoorchehApiClient, "list_namespaces", side_effect=MoorchehApiError("fail", 503, {"message": "down"})),
        pytest.raises(SystemExit) as exc,
    ):
        main()
    assert exc.value.code == 1
    captured = capsys.readouterr()
    assert "Error (503)" in captured.err
    assert '"message": "down"' in captured.out


def test_main_exits_on_compose_error(capsys: pytest.CaptureFixture[str]) -> None:
    parser = build_parser()
    args = parser.parse_args(["up", "--bundled-ollama"])
    compose_err = ComposeCommandError(["docker"], 1, "out", "compose failed")
    with (
        patch.object(parser, "parse_args", return_value=args),
        patch("moorcheh.cli.build_parser", return_value=parser),
        patch("moorcheh.cli.up", side_effect=compose_err),
        pytest.raises(SystemExit) as exc,
    ):
        main()
    assert exc.value.code == 1
    assert "docker compose failed" in capsys.readouterr().err
