from __future__ import annotations

from typing import Any

from moorcheh.client._http import HttpTransport


class DocumentsResource:
    def __init__(self, http: HttpTransport) -> None:
        self._http = http

    def upload(
        self,
        namespace_name: str,
        *,
        documents: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """POST documents (async job). May raise MoorchehApiError with status 409."""
        return self._http.post(
            f"/namespaces/{namespace_name}/documents",
            {"documents": documents},
        )

    def get(
        self,
        namespace_name: str,
        *,
        ids: list[str],
    ) -> dict[str, Any]:
        return self._http.post(
            f"/namespaces/{namespace_name}/items/get",
            {"ids": ids},
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

    def fetch_text_data(
        self,
        namespace_name: str,
        *,
        limit: int | None = None,
        next_token: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, str] = {}
        if limit is not None:
            params["limit"] = str(limit)
        if next_token:
            params["next_token"] = next_token
        return self._http.get(
            f"/namespaces/{namespace_name}/documents/fetch-text-data",
            params=params or None,
        )

    def upload_job_status(self, namespace_name: str, job_id: str) -> dict[str, Any]:
        return self._http.get(f"/namespaces/{namespace_name}/upload-jobs/{job_id}")
