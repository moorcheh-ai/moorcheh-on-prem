from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from moorcheh.api import MoorchehApiClient
from moorcheh.errors import MoorchehApiError


def _mock_response(
    *,
    ok: bool,
    status_code: int,
    json_data: dict | None = None,
    text: str = "",
    reason: str = "Error",
) -> MagicMock:
    response = MagicMock(spec=requests.Response)
    response.ok = ok
    response.status_code = status_code
    response.text = text
    response.reason = reason
    if json_data is None:
        response.json.side_effect = requests.JSONDecodeError("msg", "doc", 0)
    else:
        response.json.return_value = json_data
    return response


@pytest.fixture
def client() -> MoorchehApiClient:
    return MoorchehApiClient("http://localhost:8080/", timeout=15)


def test_client_strips_trailing_slash_and_uses_timeout() -> None:
    c = MoorchehApiClient("http://example.com/api/", timeout=99)
    assert c.base_url == "http://example.com/api"
    assert c.timeout == 99


def test_raise_for_status_ok_does_not_raise(client: MoorchehApiClient) -> None:
    client._raise_for_status(_mock_response(ok=True, status_code=200, json_data={}))


def test_health_calls_get_health(client: MoorchehApiClient) -> None:
    payload = {"status": "ok", "items": 1, "max_items": 100000, "remaining": 99999}
    with patch("moorcheh._http.requests.get", return_value=_mock_response(ok=True, status_code=200, json_data=payload)) as get:
        assert client.health() == payload
    get.assert_called_once_with("http://localhost:8080/health", params=None, timeout=15)


def test_list_namespaces(client: MoorchehApiClient) -> None:
    payload = {"namespaces": [{"namespace_name": "docs"}]}
    with patch("moorcheh._http.requests.get", return_value=_mock_response(ok=True, status_code=200, json_data=payload)) as get:
        assert client.list_namespaces() == payload
    get.assert_called_once_with("http://localhost:8080/namespaces", params=None, timeout=15)


def test_create_namespace_posts_json(client: MoorchehApiClient) -> None:
    body = {"namespace_name": "docs", "type": "text"}
    with patch(
        "moorcheh._http.requests.post",
        return_value=_mock_response(ok=True, status_code=200, json_data={"ok": True}),
    ) as post:
        result = client.create_namespace(body)
    assert result == {"ok": True}
    post.assert_called_once_with("http://localhost:8080/namespaces", json=body, timeout=15)


def test_delete_namespace(client: MoorchehApiClient) -> None:
    with patch(
        "moorcheh._http.requests.delete",
        return_value=_mock_response(ok=True, status_code=200, json_data={"job_id": "job-1"}),
    ) as delete:
        result = client.delete_namespace("docs")
    assert result == {"job_id": "job-1"}
    delete.assert_called_once_with("http://localhost:8080/namespaces/docs", timeout=15)


def test_delete_namespace_job_status(client: MoorchehApiClient) -> None:
    payload = {"status": "completed"}
    with patch("moorcheh._http.requests.get", return_value=_mock_response(ok=True, status_code=200, json_data=payload)) as get:
        assert client.delete_namespace_job_status("docs", "job-del-1") == payload
    get.assert_called_once_with(
        "http://localhost:8080/namespaces/docs/delete-jobs/job-del-1",
        params=None,
        timeout=15,
    )


def test_upload_namespace_documents(client: MoorchehApiClient) -> None:
    body = {"documents": [{"id": "d1", "text": "hello"}]}
    with patch(
        "moorcheh._http.requests.post",
        return_value=_mock_response(ok=True, status_code=200, json_data={"job_id": "up-1"}),
    ) as post:
        assert client.upload_namespace_documents("docs", body) == {"job_id": "up-1"}
    post.assert_called_once_with("http://localhost:8080/namespaces/docs/documents", json=body, timeout=15)


def test_upload_namespace_vectors(client: MoorchehApiClient) -> None:
    body = {"vectors": [{"id": "v1", "vector": [0.1, 0.2]}]}
    with patch(
        "moorcheh._http.requests.post",
        return_value=_mock_response(ok=True, status_code=200, json_data={"job_id": "up-2"}),
    ) as post:
        assert client.upload_namespace_vectors("vecns", body) == {"job_id": "up-2"}
    post.assert_called_once_with("http://localhost:8080/namespaces/vecns/vectors", json=body, timeout=15)


def test_fetch_text_data(client: MoorchehApiClient) -> None:
    with patch(
        "moorcheh._http.requests.get",
        return_value=_mock_response(ok=True, status_code=200, json_data={"items": []}),
    ) as get:
        assert client.fetch_text_data("docs", limit=2, next_token="tok") == {"items": []}
    get.assert_called_once_with(
        "http://localhost:8080/namespaces/docs/documents/fetch-text-data",
        params={"limit": "2", "next_token": "tok"},
        timeout=15,
    )


def test_get_namespace_items(client: MoorchehApiClient) -> None:
    body = {"ids": ["a", "b"]}
    with patch(
        "moorcheh._http.requests.post",
        return_value=_mock_response(ok=True, status_code=200, json_data={"items": []}),
    ) as post:
        assert client.get_namespace_items("docs", body) == {"items": []}
    post.assert_called_once_with("http://localhost:8080/namespaces/docs/items/get", json=body, timeout=15)


def test_delete_namespace_items(client: MoorchehApiClient) -> None:
    body = {"ids": ["a"]}
    with patch(
        "moorcheh._http.requests.post",
        return_value=_mock_response(ok=True, status_code=200, json_data={"deleted": 1}),
    ) as post:
        assert client.delete_namespace_items("docs", body) == {"deleted": 1}
    post.assert_called_once_with("http://localhost:8080/namespaces/docs/items/delete", json=body, timeout=15)


def test_upload_job_status(client: MoorchehApiClient) -> None:
    payload = {"status": "completed"}
    with patch("moorcheh._http.requests.get", return_value=_mock_response(ok=True, status_code=200, json_data=payload)) as get:
        assert client.upload_job_status("docs", "job-up-1") == payload
    get.assert_called_once_with(
        "http://localhost:8080/namespaces/docs/upload-jobs/job-up-1",
        params=None,
        timeout=15,
    )


def test_upload_namespace_documents_job_status_alias(client: MoorchehApiClient) -> None:
    with patch.object(client, "upload_job_status", return_value={"status": "running"}) as upload_job_status:
        assert client.upload_namespace_documents_job_status("docs", "job-up-2") == {"status": "running"}
    upload_job_status.assert_called_once_with("docs", "job-up-2")


def test_search(client: MoorchehApiClient) -> None:
    body = {"query": "hello", "namespaces": ["docs"], "top_k": 3}
    with patch(
        "moorcheh._http.requests.post",
        return_value=_mock_response(ok=True, status_code=200, json_data={"results": []}),
    ) as post:
        assert client.search(body) == {"results": []}
    post.assert_called_once_with(
        "http://localhost:8080/search",
        json={**body, "threshold": 0.0},
        timeout=15,
    )


def test_answer(client: MoorchehApiClient) -> None:
    body = {"query": "hello", "namespace": ""}
    with patch(
        "moorcheh._http.requests.post",
        return_value=_mock_response(ok=True, status_code=200, json_data={"answer": "hi"}),
    ) as post:
        assert client.answer(body) == {"answer": "hi"}
    post.assert_called_once_with("http://localhost:8080/answer", json=body, timeout=15)


def test_api_error_uses_message_from_body(client: MoorchehApiClient) -> None:
    response = _mock_response(
        ok=False,
        status_code=409,
        json_data={
            "message": "item limit exceeded",
            "items": 100000,
            "max_items": 100000,
        },
    )
    with pytest.raises(MoorchehApiError) as exc_info:
        client._raise_for_status(response)
    err = exc_info.value
    assert err.status_code == 409
    assert err.is_item_limit_exceeded
    assert err.body["items"] == 100000


def test_api_error_not_item_limit_on_other_status(client: MoorchehApiClient) -> None:
    response = _mock_response(ok=False, status_code=409, json_data=None)
    with pytest.raises(MoorchehApiError) as exc_info:
        client._raise_for_status(response)
    assert not exc_info.value.is_item_limit_exceeded


def test_api_error_falls_back_to_response_text(client: MoorchehApiClient) -> None:
    response = _mock_response(ok=False, status_code=500, text="internal error", reason="Server Error")
    with pytest.raises(MoorchehApiError) as exc_info:
        client._raise_for_status(response)
    assert str(exc_info.value) == "internal error"
    assert exc_info.value.body is None


def test_post_raises_on_error(client: MoorchehApiClient) -> None:
    with patch(
        "moorcheh._http.requests.post",
        return_value=_mock_response(ok=False, status_code=400, json_data={"message": "bad request"}),
    ):
        with pytest.raises(MoorchehApiError, match="bad request"):
            client.search({"query": "x", "namespaces": []})
