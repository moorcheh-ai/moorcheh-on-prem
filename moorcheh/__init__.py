"""Moorcheh Python client package."""

from importlib.metadata import PackageNotFoundError, version

from moorcheh.api import MoorchehApiClient, MoorchehApiError

__all__ = ["MoorchehApiClient", "MoorchehApiError", "__version__"]

try:
    __version__ = version("moorcheh-client")
except PackageNotFoundError:
    __version__ = "0.0.0"
