from __future__ import annotations

from typing import Any

from moorcheh.client._http import HttpTransport


class AnswerResource:
    def __init__(self, http: HttpTransport) -> None:
        self._http = http

    def generate(
        self,
        *,
        namespace: str,
        query: str,
        top_k: int | None = None,
        threshold: float | None = None,
        kiosk_mode: bool = False,
        temperature: float | None = None,
        ai_model: str | None = None,
        header_prompt: str | None = None,
        footer_prompt: str | None = None,
        chat_history: list[dict[str, str]] | None = None,
        structured_response: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "query": query,
            "namespace": namespace,
        }
        if top_k is not None:
            payload["top_k"] = top_k
        if threshold is not None:
            payload["threshold"] = threshold
        if kiosk_mode:
            payload["kiosk_mode"] = True
        if temperature is not None:
            payload["temperature"] = temperature
        if ai_model:
            payload["ai_model"] = ai_model
        if header_prompt:
            payload["header_prompt"] = header_prompt
        if footer_prompt:
            payload["footer_prompt"] = footer_prompt
        if chat_history is not None:
            payload["chat_history"] = chat_history
        if structured_response is not None:
            payload["structured_response"] = structured_response
        return self._http.post("/answer", payload)
