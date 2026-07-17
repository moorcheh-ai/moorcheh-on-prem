from __future__ import annotations

from typing import Any

from moorcheh.client.client import MoorchehClient
from moorcheh.client.errors import MoorchehApiError

__all__ = ["MoorchehApiClient", "MoorchehApiError"]


class MoorchehApiClient:
    """
    Legacy flat API client. Prefer :class:`MoorchehClient` for resource-style calls.

    All methods delegate to :class:`MoorchehClient` and remain for backward compatibility.
    """

    def __init__(self, base_url: str, timeout: int = 30) -> None:
        self._client = MoorchehClient(base_url, timeout)

    @property
    def base_url(self) -> str:
        return self._client.base_url

    @property
    def timeout(self) -> int:
        return self._client.timeout

    def _raise_for_status(self, response: Any) -> None:
        self._client._http._raise_for_status(response)

    def health(self) -> dict[str, Any]:
        return self._client.health()

    def create_namespace(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._client.namespaces.create(
            payload["namespace_name"],
            type=payload["type"],
            vector_dimension=payload.get("vector_dimension"),
        )

    def list_namespaces(self) -> dict[str, Any]:
        return self._client.namespaces.list()

    def delete_namespace(
        self,
        namespace_name: str,
        *,
        wait: bool = True,
        poll_interval: float = 0.2,
        timeout: float = 120.0,
    ) -> dict[str, Any]:
        return self._client.namespaces.delete(
            namespace_name,
            wait=wait,
            poll_interval=poll_interval,
            timeout=timeout,
        )

    def delete_namespace_job_status(self, namespace_name: str, job_id: str) -> dict[str, Any]:
        return self._client.namespaces.delete_job_status(namespace_name, job_id)

    def upload_namespace_documents(self, namespace_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._client.documents.upload(
            namespace_name,
            documents=payload["documents"],
        )

    def upload_namespace_vectors(self, namespace_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._client.vectors.upload(
            namespace_name,
            vectors=payload["vectors"],
        )

    def get_namespace_items(self, namespace_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._client.documents.get(namespace_name, ids=payload["ids"])

    def fetch_text_data(
        self,
        namespace_name: str,
        *,
        limit: int | None = None,
        next_token: str | None = None,
    ) -> dict[str, Any]:
        return self._client.documents.fetch_text_data(
            namespace_name,
            limit=limit,
            next_token=next_token,
        )

    def delete_namespace_items(self, namespace_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._client.documents.delete(namespace_name, ids=payload["ids"])

    def upload_job_status(self, namespace_name: str, job_id: str) -> dict[str, Any]:
        return self._client.documents.upload_job_status(namespace_name, job_id)

    def upload_namespace_files(self, namespace_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._client.files.upload(namespace_name, files=payload["files"])

    def list_namespace_files(self, namespace_name: str) -> dict[str, Any]:
        return self._client.files.list(namespace_name)

    def get_namespace_file(self, namespace_name: str, file_id: str) -> dict[str, Any]:
        return self._client.files.get(namespace_name, file_id)

    def delete_namespace_files(self, namespace_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._client.files.delete(
            namespace_name,
            file_id=payload.get("file_id"),
            path=payload.get("path"),
        )

    def file_job_status(self, namespace_name: str, job_id: str) -> dict[str, Any]:
        return self._client.files.job_status(namespace_name, job_id)

    def upload_namespace_documents_job_status(self, namespace_name: str, job_id: str) -> dict[str, Any]:
        return self.upload_job_status(namespace_name, job_id)

    def search(self, payload: dict[str, Any]) -> dict[str, Any]:
        body = dict(payload)
        body.pop("metadata", None)
        return self._client.similarity_search.query(
            namespaces=body.pop("namespaces"),
            query=body.pop("query"),
            top_k=body.pop("top_k", 5),
            threshold=body.pop("threshold", 0.0),
            kiosk_mode=body.pop("kiosk_mode", False),
        )

    def answer(self, payload: dict[str, Any]) -> dict[str, Any]:
        body = dict(payload)
        return self._client.answer.generate(
            namespace=body.pop("namespace"),
            query=body.pop("query"),
            top_k=body.pop("top_k", None),
            threshold=body.pop("threshold", None),
            kiosk_mode=body.pop("kiosk_mode", False),
            temperature=body.pop("temperature", None),
            ai_model=body.pop("ai_model", None),
            header_prompt=body.pop("header_prompt", None),
            footer_prompt=body.pop("footer_prompt", None),
            chat_history=body.pop("chat_history", None),
            structured_response=body.pop("structured_response", None),
        )
