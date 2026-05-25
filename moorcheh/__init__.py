"""Moorcheh Python client package."""

from __future__ import annotations

from moorcheh.api import MoorchehApiClient, MoorchehApiError


def _resolve_version() -> str:
    try:
        from importlib.metadata import version

        return version("moorcheh-client")
    except Exception:
        pass

    try:
        from setuptools_scm import get_version

        return get_version(root="..", relative_to=__file__)
    except Exception:
        pass

    try:
        from moorcheh._version import version

        return version
    except ImportError:
        return "0.0.0+unknown"


__all__ = ["MoorchehApiClient", "MoorchehApiError", "__version__"]
__version__ = _resolve_version()
