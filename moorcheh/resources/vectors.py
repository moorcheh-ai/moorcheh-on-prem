from __future__ import annotations

from typing import Any

from moorcheh._http import HttpTransport


class VectorsResource:
    def __init__(self, http: HttpTransport) -> None:
        self._http = http

    def upload(
        self,
        namespace_name: str,
        *,
        vectors: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """POST vectors (async job). May raise MoorchehApiError with status 409."""
        return self._http.post(
            f"/namespaces/{namespace_name}/vectors",
            {"vectors": vectors},
        )

    def delete(
        self,
        namespace_name: str,
        *,
        ids: list[str],
    ) -> dict[str, Any]:
        return self._http.post(
            f"/namespaces/{namespace_name}/items/delete",
            {"ids": ids},
        )

    def upload_job_status(self, namespace_name: str, job_id: str) -> dict[str, Any]:
        return self._http.get(f"/namespaces/{namespace_name}/upload-jobs/{job_id}")
