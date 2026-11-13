"""The version the application reports is the version the release carries."""

from __future__ import annotations

import re
from pathlib import Path

from quest_app.config import APPLICATION_VERSION

ROOT = Path(__file__).resolve().parents[2]


def test_the_application_version_matches_pyproject() -> None:
    text = (Path(ROOT) / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version = "([^"]+)"', text, re.MULTILINE)
    assert match is not None
    assert match.group(1) == APPLICATION_VERSION
