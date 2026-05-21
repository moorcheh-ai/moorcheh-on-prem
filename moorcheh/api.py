from __future__ import annotations

from typing import Any

import requests


class MoorchehApiError(Exception):
    """HTTP error from the Moorcheh API (includes parsed JSON body when available)."""

    def __init__(
        self,
        message: str,
        status_code: int,
        body: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.body = body

    @property
    def is_item_limit_exceeded(self) -> bool:
        return self.status_code == 409 and bool(self.body)


class MoorchehApiClient:
    def __init__(self, base_url: str, timeout: int = 30) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _raise_for_status(self, response: requests.Response) -> None:
        if response.ok:
            return
        body: dict[str, Any] | None = None
        try:
            parsed = response.json()
            if isinstance(parsed, dict):
                body = parsed
        except requests.JSONDecodeError:
            body = None
        message = (
            str(body.get("message"))
            if body and body.get("message") is not None
            else response.text or response.reason
        )
        raise MoorchehApiError(message, response.status_code, body)

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = requests.post(
            f"{self.base_url}{path}",
            json=payload,
            timeout=self.timeout,
        )
        self._raise_for_status(response)
        return response.json()

    def _get(self, path: str) -> dict[str, Any]:
        response = requests.get(f"{self.base_url}{path}", timeout=self.timeout)
        self._raise_for_status(response)
        return response.json()

    def health(self) -> dict[str, Any]:
        """
        GET /health — includes global item quota:
        items, max_items, remaining, model, status.
        """
        return self._get("/health")

    def create_namespace(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post("/namespaces", payload)

    def list_namespaces(self) -> dict[str, Any]:
        return self._get("/namespaces")

    def delete_namespace(self, namespace_name: str) -> dict[str, Any]:
        response = requests.delete(
            f"{self.base_url}/namespaces/{namespace_name}",
            timeout=self.timeout,
        )
        self._raise_for_status(response)
        return response.json()

    def delete_namespace_job_status(self, namespace_name: str, job_id: str) -> dict[str, Any]:
        return self._get(f"/namespaces/{namespace_name}/delete-jobs/{job_id}")

    def upload_namespace_documents(self, namespace_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        """POST documents (async job). May raise MoorchehApiError with status 409 if global item cap exceeded."""
        return self._post(f"/namespaces/{namespace_name}/documents", payload)

    def upload_namespace_vectors(self, namespace_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        """POST vectors (async job). May raise MoorchehApiError with status 409 if global item cap exceeded."""
        return self._post(f"/namespaces/{namespace_name}/vectors", payload)

    def get_namespace_items(self, namespace_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post(f"/namespaces/{namespace_name}/items/get", payload)

    def delete_namespace_items(self, namespace_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Delete by item id within namespace (ids are unique per namespace, not globally)."""
        return self._post(f"/namespaces/{namespace_name}/items/delete", payload)

    def upload_job_status(self, namespace_name: str, job_id: str) -> dict[str, Any]:
        """Poll document or vector upload job status."""
        return self._get(f"/namespaces/{namespace_name}/upload-jobs/{job_id}")

    def upload_namespace_documents_job_status(self, namespace_name: str, job_id: str) -> dict[str, Any]:
        return self.upload_job_status(namespace_name, job_id)

    def search(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post("/search", payload)
