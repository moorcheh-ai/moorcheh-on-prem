from __future__ import annotations

from typing import Any

from moorcheh._http import HttpTransport


class FilesResource:
    def __init__(self, http: HttpTransport) -> None:
        self._http = http

    def upload(
        self,
        namespace_name: str,
        *,
        files: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """POST files from server-visible paths (async file upload job)."""
        return self._http.post(
            f"/namespaces/{namespace_name}/files",
            {"files": files},
        )

    def list(self, namespace_name: str) -> dict[str, Any]:
        return self._http.get(f"/namespaces/{namespace_name}/files")

    def get(self, namespace_name: str, file_id: str) -> dict[str, Any]:
        return self._http.get(f"/namespaces/{namespace_name}/files/{file_id}")

    def delete(
        self,
        namespace_name: str,
        *,
        file_id: str | None = None,
        path: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {}
        if file_id is not None:
            payload["file_id"] = file_id
        if path is not None:
            payload["path"] = path
        return self._http.post(
            f"/namespaces/{namespace_name}/files/delete",
            payload,
        )

    def job_status(self, namespace_name: str, job_id: str) -> dict[str, Any]:
        return self._http.get(f"/namespaces/{namespace_name}/file-jobs/{job_id}")
