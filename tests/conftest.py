"""Shared fixtures.

Tests never touch `participant/`. Everything participant-shaped resolves against
`fixtures/participant` through the injected root from ADR-018.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from quest_app.config import AppConfig
    from quest_app.errors import ProblemReport

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


@pytest.fixture
def content_repo(tmp_path: Path) -> Path:
    """A writable copy of the real content tree, for tests that need to break something.

    Invalid content is built by mutating a copy rather than shipped as broken files in
    `content/`, so the repository always validates and a maintainer opening `content/` never
    finds a deliberately corrupt quest next to a real one.
    """
    import shutil

    for name in ("content", "schemas", "templates", "assets", "validators", "quest_app"):
        shutil.copytree(
            REPO_ROOT / name,
            tmp_path / name,
            ignore=shutil.ignore_patterns("__pycache__"),
        )
    # The repository ignore rules are a narrow read root for one validator, so a copy needs
    # them or that check has nothing to look at.
    shutil.copy2(REPO_ROOT / ".gitignore", tmp_path / ".gitignore")
    shutil.copytree(REPO_ROOT / "fixtures" / "participant", tmp_path / "participant")
    return tmp_path


@pytest.fixture
def config(content_repo: Path) -> AppConfig:
    from quest_app.config import AppConfig

    return AppConfig.for_repo(content_repo, participant_root=content_repo / "participant")


@pytest.fixture
def report() -> ProblemReport:
    from quest_app.errors import ProblemReport

    return ProblemReport()
