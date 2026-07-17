from __future__ import annotations

import json
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from moorcheh.cli.ollama_setup import (
    _model_matches,
    ensure_ollama_model,
    ollama_has_model,
    pull_ollama_model_http,
)


def test_model_matches_exact_and_tagged() -> None:
    installed = ["nomic-embed-text:latest", "mxbai-embed-large:abc"]
    assert _model_matches("nomic-embed-text", installed)
    assert _model_matches("mxbai-embed-large", installed)
    assert not _model_matches("all-minilm", installed)


@patch("moorcheh.cli.ollama_setup.list_ollama_models", return_value=["nomic-embed-text:latest"])
def test_ollama_has_model(_list: MagicMock) -> None:
    assert ollama_has_model("nomic-embed-text")
    assert not ollama_has_model("all-minilm")


@patch("moorcheh.cli.ollama_setup.wait_for_ollama", return_value=True)
@patch("moorcheh.cli.ollama_setup.ollama_has_model", return_value=True)
def test_ensure_ollama_model_already_installed(_has: MagicMock, _wait: MagicMock, capsys: pytest.CaptureFixture[str]) -> None:
    ensure_ollama_model("nomic-embed-text", interactive=False)
    out = capsys.readouterr().out
    assert "already available" in out


@patch("moorcheh.cli.ollama_setup.wait_for_ollama", return_value=True)
@patch("moorcheh.cli.ollama_setup.pull_ollama_model")
@patch("moorcheh.cli.ollama_setup.ollama_has_model", side_effect=[False, True])
def test_ensure_ollama_model_pulls_when_missing(
    _has: MagicMock, pull: MagicMock, _wait: MagicMock, capsys: pytest.CaptureFixture[str]
) -> None:
    ensure_ollama_model("all-minilm", interactive=False)
    pull.assert_called_once()
    assert "Pulling embedding model" in capsys.readouterr().out


@patch("moorcheh.cli.ollama_setup.wait_for_ollama", return_value=True)
@patch("moorcheh.cli.ollama_setup.ollama_has_model", return_value=False)
def test_ensure_ollama_model_skip_pull(_has: MagicMock, _wait: MagicMock, capsys: pytest.CaptureFixture[str]) -> None:
    ensure_ollama_model("all-minilm", interactive=False, pull_if_missing=False)
    assert "not installed" in capsys.readouterr().out


def test_pull_ollama_model_http_dedupes_status_lines(capsys: pytest.CaptureFixture[str]) -> None:
    events = [
        {"status": "pulling manifest"},
        {"status": "pulling abc", "completed": 10, "total": 100},
        {"status": "pulling abc", "completed": 10, "total": 100},
        {"status": "pulling abc", "completed": 50, "total": 100},
        {"status": "pulling abc", "completed": 50, "total": 100},
    ]
    body = b"".join(json.dumps(e).encode("utf-8") + b"\n" for e in events)
    response = MagicMock()
    response.readline.side_effect = [*body.splitlines(keepends=True), b""]
    response.__enter__.return_value = response
    response.__exit__.return_value = None

    request = MagicMock()
    with (
        patch("urllib.request.urlopen", return_value=response),
        patch("urllib.request.Request", return_value=request),
    ):
        pull_ollama_model_http("nomic-embed-text")

    out = capsys.readouterr().out
    assert out.count("pulling manifest") == 1
    assert out.count("(10%)") == 1
    assert out.count("(50%)") == 1
