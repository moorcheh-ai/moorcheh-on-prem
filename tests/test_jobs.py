from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from moorcheh.client._jobs import wait_for_namespace_delete_job
from moorcheh.client.client import MoorchehClient
from moorcheh.client.errors import MoorchehApiError


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


def test_wait_for_namespace_delete_job_completes() -> None:
    calls = {"n": 0}

    def fetch() -> dict:
        calls["n"] += 1
        if calls["n"] < 2:
            return {"status": "running"}
        return {"status": "completed", "deleted_items": 3}

    with patch("moorcheh._jobs.time.sleep"):
        job = wait_for_namespace_delete_job(fetch, poll_interval=0.01, timeout=1.0)
    assert job["status"] == "completed"


def test_wait_for_namespace_delete_job_raises_on_failed() -> None:
    with patch("moorcheh._jobs.time.sleep"):
        with pytest.raises(MoorchehApiError, match="disk error"):
            wait_for_namespace_delete_job(
                lambda: {"status": "failed", "last_error": "disk error"},
                poll_interval=0.01,
                timeout=1.0,
            )


def test_namespaces_delete_waits_for_job_by_default() -> None:
    client = MoorchehClient("http://localhost:8080", timeout=15)
    delete_resp = {
        "status": "success",
        "job_id": "job-del-1",
        "namespace_name": "docs",
    }
    completed_job = {"status": "completed", "deleted_items": 0}

    with patch(
        "moorcheh._http.requests.delete",
        return_value=_mock_response(ok=True, status_code=202, json_data=delete_resp),
    ) as delete:
        with patch(
            "moorcheh._http.requests.get",
            return_value=_mock_response(ok=True, status_code=200, json_data=completed_job),
        ) as get:
            with patch("moorcheh._jobs.time.sleep"):
                result = client.namespaces.delete("docs")

    delete.assert_called_once()
    get.assert_called_once_with(
        "http://localhost:8080/namespaces/docs/delete-jobs/job-del-1",
        params=None,
        timeout=15,
    )
    assert result["job_id"] == "job-del-1"
    assert result["delete_job"]["status"] == "completed"


def test_namespaces_delete_no_wait_skips_polling() -> None:
    client = MoorchehClient("http://localhost:8080", timeout=15)
    delete_resp = {"status": "success", "job_id": "job-del-1"}

    with patch(
        "moorcheh._http.requests.delete",
        return_value=_mock_response(ok=True, status_code=202, json_data=delete_resp),
    ) as delete:
        with patch("moorcheh._http.requests.get") as get:
            result = client.namespaces.delete("docs", wait=False)

    delete.assert_called_once()
    get.assert_not_called()
    assert result == delete_resp
