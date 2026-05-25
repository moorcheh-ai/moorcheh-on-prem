from __future__ import annotations

import re

from moorcheh import __version__


def test_version_is_non_empty_string() -> None:
    assert isinstance(__version__, str)
    assert __version__
    assert re.match(r"^\d+\.\d+\.\d+", __version__) or __version__.endswith("+unknown")
