from __future__ import annotations

from typing import Any


class MoorchehApiError(Exception):
    """HTTP error from the Moorcheh API (includes parsed JSON body when available)."""

    def __init__(
        self,
        message: str,
        status_code: int,
        body: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.body = body

    @property
    def is_item_limit_exceeded(self) -> bool:
        return self.status_code == 409 and bool(self.body)

    @property
    def is_conflict(self) -> bool:
        return self.status_code == 409
