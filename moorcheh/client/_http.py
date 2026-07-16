from __future__ import annotations

from typing import Any

import requests

from moorcheh.client.errors import MoorchehApiError


class HttpTransport:
    """Low-level HTTP transport for the Moorcheh on-prem API."""

    def __init__(self, base_url: str, timeout: int = 30) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def get(self, path: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        response = requests.get(
            f"{self.base_url}{path}",
            params=params,
            timeout=self.timeout,
        )
        self._raise_for_status(response)
        return response.json()

    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = requests.post(
            f"{self.base_url}{path}",
            json=payload,
            timeout=self.timeout,
        )
        self._raise_for_status(response)
        return response.json()

    def delete(self, path: str) -> dict[str, Any]:
        response = requests.delete(
            f"{self.base_url}{path}",
            timeout=self.timeout,
        )
        self._raise_for_status(response)
        return response.json()

    def _raise_for_status(self, response: requests.Response) -> None:
        if response.ok:
            return
        body: dict[str, Any] | None = None
        try:
            parsed = response.json()
            if isinstance(parsed, dict):
                body = parsed
        except requests.JSONDecodeError:
            body = None
        message = (
            str(body.get("message"))
            if body and body.get("message") is not None
            else response.text or response.reason
        )
        raise MoorchehApiError(message, response.status_code, body)
