from __future__ import annotations

from typing import Any

from moorcheh._http import HttpTransport


class SimilaritySearchResource:
    def __init__(self, http: HttpTransport) -> None:
        self._http = http

    def query(
        self,
        *,
        namespaces: list[str],
        query: str | list[float],
        top_k: int = 5,
        threshold: float = 0.0,
        kiosk_mode: bool = False,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "query": query,
            "namespaces": namespaces,
            "top_k": top_k,
            "threshold": threshold,
        }
        if kiosk_mode:
            payload["kiosk_mode"] = True
        return self._http.post("/search", payload)
