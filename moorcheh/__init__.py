"""Moorcheh Python client package."""

from importlib.metadata import PackageNotFoundError, version

from moorcheh.client import MoorchehApiClient, MoorchehClient, MoorchehApiError

__all__ = ["MoorchehApiClient", "MoorchehClient", "MoorchehApiError", "__version__"]

try:
    __version__ = version("moorcheh-client")
except PackageNotFoundError:
    __version__ = "0.0.0"
