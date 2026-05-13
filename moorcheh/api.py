from __future__ import annotations

from typing import Any

import requests


class MoorchehApiClient:
    def __init__(self, base_url: str, timeout: int = 30) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = requests.post(
            f"{self.base_url}{path}",
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def _get(self, path: str) -> dict[str, Any]:
        response = requests.get(
            f"{self.base_url}{path}",
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def health(self) -> dict[str, Any]:
        return self._get("/health")

    def create_namespace(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post("/namespaces", payload)

    def list_namespaces(self, user_id: str | None = None) -> dict[str, Any]:
        query = f"?user_id={user_id}" if user_id else ""
        return self._get(f"/namespaces{query}")

    def delete_namespace(self, namespace_name: str) -> dict[str, Any]:
        response = requests.delete(
            f"{self.base_url}/namespaces/{namespace_name}",
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def delete_namespace_job_status(self, namespace_name: str, job_id: str) -> dict[str, Any]:
        return self._get(f"/namespaces/{namespace_name}/delete-jobs/{job_id}")

    def upload_namespace_documents(self, namespace_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post(f"/namespaces/{namespace_name}/documents", payload)

    def upload_namespace_vectors(self, namespace_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post(f"/namespaces/{namespace_name}/vectors", payload)

    def get_namespace_items(self, namespace_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post(f"/namespaces/{namespace_name}/items/get", payload)

    def delete_namespace_items(self, namespace_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post(f"/namespaces/{namespace_name}/items/delete", payload)

    def upload_namespace_documents_job_status(self, namespace_name: str, job_id: str) -> dict[str, Any]:
        return self._get(f"/namespaces/{namespace_name}/upload-jobs/{job_id}")

    def search(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._post("/search", payload)
