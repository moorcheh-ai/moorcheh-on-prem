from __future__ import annotations

from typing import Any

from moorcheh.client._http import HttpTransport
from moorcheh.client.resources import (
    AnswerResource,
    DocumentsResource,
    FilesResource,
    NamespacesResource,
    SimilaritySearchResource,
    VectorsResource,
)


class MoorchehClient:
    """
    Resource-based Python client for Moorcheh on-prem.

    Mirrors the cloud moorcheh-sdk layout (namespaces, documents, files, etc.).
    """

    def __init__(self, base_url: str = "http://localhost:8080", timeout: int = 30) -> None:
        self._http = HttpTransport(base_url, timeout)
        self.namespaces = NamespacesResource(self._http)
        self.documents = DocumentsResource(self._http)
        self.vectors = VectorsResource(self._http)
        self.files = FilesResource(self._http)
        self.similarity_search = SimilaritySearchResource(self._http)
        self.answer = AnswerResource(self._http)

    @property
    def base_url(self) -> str:
        return self._http.base_url

    @property
    def timeout(self) -> int:
        return self._http.timeout

    def health(self) -> dict[str, Any]:
        """GET /health — server status, quota, embedding and LLM provider info."""
        return self._http.get("/health")

    def __enter__(self) -> MoorchehClient:
        return self

    def __exit__(self, *_args: object) -> None:
        return None
