"""Shared fixtures.

Tests never touch `participant/`. Everything participant-shaped resolves against
`fixtures/participant` through the injected root from ADR-018.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture(scope="session")
def fixture_participant_root() -> Path:
    """The participant root used by tests (ADR-018) — never the live `participant/`."""
    return REPO_ROOT / "fixtures" / "participant"


@pytest.fixture(scope="session")
def schemas() -> dict[str, dict[str, object]]:
    return {
        path.name.removesuffix(".schema.json"): json.loads(path.read_text())
        for path in sorted((REPO_ROOT / "schemas").glob("*.schema.json"))
    }
