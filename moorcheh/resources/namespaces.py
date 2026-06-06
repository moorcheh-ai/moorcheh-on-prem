from __future__ import annotations

from typing import Any, Literal

from moorcheh._http import HttpTransport


class NamespacesResource:
    def __init__(self, http: HttpTransport) -> None:
        self._http = http

    def create(
        self,
        namespace_name: str,
        *,
        type: Literal["text", "vector"],
        vector_dimension: int | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "namespace_name": namespace_name,
            "type": type,
        }
        if vector_dimension is not None:
            payload["vector_dimension"] = vector_dimension
        return self._http.post("/namespaces", payload)

    def list(self) -> dict[str, Any]:
        return self._http.get("/namespaces")

    def delete(self, namespace_name: str) -> dict[str, Any]:
        return self._http.delete(f"/namespaces/{namespace_name}")

    def delete_job_status(self, namespace_name: str, job_id: str) -> dict[str, Any]:
        return self._http.get(f"/namespaces/{namespace_name}/delete-jobs/{job_id}")
