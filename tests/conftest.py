"""Shared fixtures.

Tests never touch `participant/`. Everything participant-shaped resolves against
`fixtures/participant` through the injected root from ADR-018.

The same now holds for `generated/` and `local-data/` (ADR-018, amended round 12, C2): a
test that shells out to the CLI sets `GTQ_GENERATED_ROOT`/`GTQ_LOCAL_DATA_ROOT`, and one that
builds in-process points `AppConfig.for_repo` at a private copy (`content_repo`/`config`
below). `_guard_repository_roots_are_untouched` is the backstop for a test that forgets.
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

# The three roots the application ever writes to (ADR-018) — never the repository's own
# copies while the test suite runs. `fixtures/participant` is a different, read-only path
# and is not one of these.
_GUARDED_DIRECTORY_NAMES = ("generated", "local-data", "participant")


def _directory_fingerprint(path: Path) -> tuple[str, ...] | None:
    """A cheap "did anything under here change" signature, or `None` if it does not exist.

    Full content hashing would make this expensive to run around the whole session; size
    and mtime catch a write without reading every generated page twice.
    """
    if not path.exists():
        return None
    fingerprint = []
    for entry in sorted(path.rglob("*")):
        try:
            stat = entry.stat()
        except OSError:
            continue
        fingerprint.append(f"{entry.relative_to(path)}:{stat.st_size}:{stat.st_mtime_ns}")
    return tuple(fingerprint)


@pytest.fixture(scope="session", autouse=True)
def _guard_repository_roots_are_untouched() -> object:
    """Fail the whole run if the suite wrote to the repository's own guarded directories.

    C2: a test that ran the CLI with `--participant-root <tmp>` but no generated/local-data
    override rebuilt the repository's real `generated/` on every mutating action — for
    example overwriting a checked-in `generated/index.html` with fixture data. Every such
    call site now isolates all three roots; this is what catches the next one that forgets.
    """
    before = {name: _directory_fingerprint(REPO_ROOT / name) for name in _GUARDED_DIRECTORY_NAMES}
    yield
    after = {name: _directory_fingerprint(REPO_ROOT / name) for name in _GUARDED_DIRECTORY_NAMES}
    changed = [name for name in _GUARDED_DIRECTORY_NAMES if before[name] != after[name]]
    assert not changed, (
        "the test suite wrote to the repository's own "
        + ", ".join(changed)
        + " — a test is missing --participant-root, GTQ_GENERATED_ROOT or "
        "GTQ_LOCAL_DATA_ROOT, or an in-process AppConfig is not pointed at a private copy"
    )


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
