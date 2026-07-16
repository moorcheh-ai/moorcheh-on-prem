from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from moorcheh.client.client import MoorchehClient


def _mock_response(
    *,
    ok: bool,
    status_code: int,
    json_data: dict | None = None,
) -> MagicMock:
    response = MagicMock(spec=requests.Response)
    response.ok = ok
    response.status_code = status_code
    response.text = ""
    response.reason = "Error"
    if json_data is None:
        response.json.side_effect = requests.JSONDecodeError("msg", "doc", 0)
    else:
        response.json.return_value = json_data
    return response


@pytest.fixture
def client() -> MoorchehClient:
    return MoorchehClient("http://localhost:8080/", timeout=15)


def test_client_context_manager() -> None:
    with MoorchehClient("http://localhost:8080") as client:
        assert client.base_url == "http://localhost:8080"


def test_namespaces_create(client: MoorchehClient) -> None:
    with patch(
        "moorcheh._http.requests.post",
        return_value=_mock_response(ok=True, status_code=200, json_data={"status": "success"}),
    ) as post:
        result = client.namespaces.create("docs", type="text")
    assert result["status"] == "success"
    post.assert_called_once_with(
        "http://localhost:8080/namespaces",
        json={"namespace_name": "docs", "type": "text"},
        timeout=15,
    )


def test_documents_upload(client: MoorchehClient) -> None:
    docs = [{"id": "d1", "text": "hello"}]
    with patch(
        "moorcheh._http.requests.post",
        return_value=_mock_response(ok=True, status_code=200, json_data={"job_id": "j1"}),
    ) as post:
        result = client.documents.upload("docs", documents=docs)
    assert result["job_id"] == "j1"
    post.assert_called_once_with(
        "http://localhost:8080/namespaces/docs/documents",
        json={"documents": docs},
        timeout=15,
    )


def test_documents_fetch_text_data(client: MoorchehClient) -> None:
    with patch(
        "moorcheh._http.requests.get",
        return_value=_mock_response(ok=True, status_code=200, json_data={"items": []}),
    ) as get:
        result = client.documents.fetch_text_data("docs", limit=2, next_token="tok")
    assert result["items"] == []
    get.assert_called_once_with(
        "http://localhost:8080/namespaces/docs/documents/fetch-text-data",
        params={"limit": "2", "next_token": "tok"},
        timeout=15,
    )


def test_files_upload(client: MoorchehClient) -> None:
    files = [{"path": "/uploads/doc.pdf"}]
    with patch(
        "moorcheh._http.requests.post",
        return_value=_mock_response(ok=True, status_code=200, json_data={"job_id": "fj1"}),
    ) as post:
        result = client.files.upload("docs", files=files)
    assert result["job_id"] == "fj1"
    post.assert_called_once_with(
        "http://localhost:8080/namespaces/docs/files",
        json={"files": files},
        timeout=15,
    )


def test_similarity_search_query(client: MoorchehClient) -> None:
    with patch(
        "moorcheh._http.requests.post",
        return_value=_mock_response(ok=True, status_code=200, json_data={"results": []}),
    ) as post:
        result = client.similarity_search.query(
            namespaces=["docs"],
            query="hello",
            top_k=3,
            threshold=0.5,
        )
    assert result["results"] == []
    post.assert_called_once_with(
        "http://localhost:8080/search",
        json={
            "query": "hello",
            "namespaces": ["docs"],
            "top_k": 3,
            "threshold": 0.5,
        },
        timeout=15,
    )


def test_answer_generate(client: MoorchehClient) -> None:
    with patch(
        "moorcheh._http.requests.post",
        return_value=_mock_response(ok=True, status_code=200, json_data={"answer": "hi"}),
    ) as post:
        result = client.answer.generate(namespace="docs", query="hello", top_k=2)
    assert result["answer"] == "hi"
    post.assert_called_once_with(
        "http://localhost:8080/answer",
        json={"namespace": "docs", "query": "hello", "top_k": 2},
        timeout=15,
    )
