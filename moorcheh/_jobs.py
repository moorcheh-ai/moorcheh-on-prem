from __future__ import annotations

import time
from typing import Any, Callable

from moorcheh.errors import MoorchehApiError

_TERMINAL_DELETE_STATUSES = frozenset({"completed", "failed"})


def wait_for_namespace_delete_job(
    fetch_status: Callable[[], dict[str, Any]],
    *,
    poll_interval: float = 0.2,
    timeout: float = 120.0,
) -> dict[str, Any]:
    """
    Poll a namespace delete job until it reaches a terminal state.

    Raises MoorchehApiError when the job fails or the wait times out.
    """
    if poll_interval <= 0:
        raise ValueError("poll_interval must be > 0")
    if timeout <= 0:
        raise ValueError("timeout must be > 0")

    deadline = time.monotonic() + timeout
    last_job: dict[str, Any] | None = None

    while time.monotonic() < deadline:
        last_job = fetch_status()
        status = str(last_job.get("status", "")).lower()
        if status in _TERMINAL_DELETE_STATUSES:
            if status == "failed":
                message = last_job.get("last_error") or "Namespace delete job failed."
                raise MoorchehApiError(message, status_code=500, body=last_job)
            return last_job
        time.sleep(poll_interval)

    message = "Timed out waiting for namespace delete job to complete."
    raise MoorchehApiError(message, status_code=408, body=last_job)
