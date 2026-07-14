from __future__ import annotations

from typing import Any, Literal

from moorcheh._http import HttpTransport
from moorcheh._jobs import wait_for_namespace_delete_job


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

    def delete(
        self,
        namespace_name: str,
        *,
        wait: bool = True,
        poll_interval: float = 0.2,
        timeout: float = 120.0,
    ) -> dict[str, Any]:
        """
        Delete a namespace and all of its items.

        By default waits for the async delete job to finish so callers can safely
        recreate the same namespace name immediately afterward. Set ``wait=False``
        to return as soon as the server accepts the delete (202 + job_id).
        """
        resp = self._http.delete(f"/namespaces/{namespace_name}")
        job_id = resp.get("job_id")
        if wait and job_id:
            job = wait_for_namespace_delete_job(
                lambda: self.delete_job_status(namespace_name, job_id),
                poll_interval=poll_interval,
                timeout=timeout,
            )
            resp = {**resp, "delete_job": job}
        return resp

    def delete_job_status(self, namespace_name: str, job_id: str) -> dict[str, Any]:
        return self._http.get(f"/namespaces/{namespace_name}/delete-jobs/{job_id}")
