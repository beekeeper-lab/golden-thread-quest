"""The numbers the project claims about itself must be the numbers it produces.

An external audit found the README, the release notes and the user guide all quoting a
test count that was five short, because each was hand-maintained. For a product whose
whole argument is that claims must be backed by evidence, a stale claim about its own
evidence is the wrong kind of defect. This makes the documents fail when they drift.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

# Every place a suite size is asserted in prose, and the pytest marker expression the
# number is supposed to describe. The user guide is deliberately absent: it now says what
# `make check` does without quoting a total, which is one fewer number to drift.
CLAIMS = [
    (Path("README.md"), r"(\d+) under `make check`", "not ui"),
    (Path("README.md"), r"(\d+) driving a real browser", "ui"),
    (Path("docs/RELEASE-NOTES.md"), r"(\d+) under `make check`", "not ui"),
    (Path("docs/RELEASE-NOTES.md"), r"plus (\d+) browser-driven", "ui"),
]


def collected(marker: str) -> int:
    """How many tests pytest actually collects for a marker expression."""
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-p", "no:cacheprovider", "-m", marker],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    # pytest prints either "N tests collected" or "N/M tests collected (K deselected)".
    match = re.search(r"(\d+)(?:/\d+)?\s+tests? collected", result.stdout)
    if match is None:
        # Collection can fail outright rather than report zero, which is what happens in a
        # virtualenv without the browser extra installed. Treat that as "none here" and let
        # the caller decide; asserting would turn a missing optional dependency into a
        # documentation failure.
        return 0
    return int(match.group(1))


@pytest.mark.slow
@pytest.mark.parametrize(("document", "pattern", "marker"), CLAIMS)
def test_documented_test_counts_are_true(document: Path, pattern: str, marker: str) -> None:
    text = (ROOT / document).read_text()
    found = re.search(pattern, text)
    assert found, f"{document} no longer states a count matching {pattern!r}"
    claimed = int(found.group(1))
    actual = collected(marker)
    if actual == 0 and marker == "ui":
        pytest.skip("browser tests are not installed here; make setup-ui installs them")
    assert claimed == actual, (
        f"{document} claims {claimed} tests for -m {marker!r}, but pytest collects "
        f"{actual}. Update the document, or explain the difference."
    )


# --- Which diagram each page ships -------------------------------------------------

GUIDE = Path("docs/USER-GUIDE.md")
IMAGE_PLAN = Path("IMAGE-PLAN.md")
_GUIDE_IMAGE = re.compile(r"!\[[^\]]*\]\(media/(images/[^)]+)\)")
_PLAN_ROW = re.compile(r"^\|[^|]+\|\s*\**`(images?/[^`]+|[^`|]+\.png)`\**\s*\|", re.MULTILINE)


def _guide_images() -> list[str]:
    return _GUIDE_IMAGE.findall((ROOT / GUIDE).read_text())


def _planned_images() -> list[str]:
    """The files the 'Which take each page ships' table says the guide renders."""
    text = (ROOT / IMAGE_PLAN).read_text()
    table = text.split("## Which take each page ships", 1)
    assert len(table) == 2, f"{IMAGE_PLAN} no longer records which take each page ships"
    rows = re.findall(r"^\|[^|]+\|\s*`([^`]+\.png)`\s*\|", table[1], re.MULTILINE)
    return [f"images/{name}" for name in rows]


def test_every_diagram_the_guide_references_exists() -> None:
    """A broken image in the onboarding document is invisible to every other check."""
    missing = [ref for ref in _guide_images() if not (ROOT / "docs" / "media" / ref).exists()]
    assert not missing, f"{GUIDE} references files that are not on disk: {missing}"


def test_the_guide_ships_the_take_the_plan_says_it_ships() -> None:
    """Generating a correction and wiring it in are two acts, and round 2 did only the first.

    Three superseded diagrams stayed in the guide for a release because nothing compared
    the two lists. One of them put `locally validated` in the reviewer column, which is the
    opposite of the rule the image exists to state.
    """
    assert _guide_images() == _planned_images(), (
        f"{GUIDE} and the 'Which take each page ships' table in {IMAGE_PLAN} disagree. "
        "Update whichever is wrong; a correction that is generated but not referenced is "
        "not shipped."
    )


# --- What the curriculum contains --------------------------------------------------


def test_the_readme_states_the_curriculum_it_actually_has() -> None:
    """The README said "3 quests" for a release after five more were authored.

    Test counts were already enforced here; nothing enforced the counts that describe the
    content, which is the first thing a reader of the front page looks at.
    """
    counted = {
        "regions": len(list((ROOT / "content" / "regions").glob("*.yaml"))),
        "quests": len(list((ROOT / "content" / "quests").glob("*/*.md"))),
        "badges": len(list((ROOT / "content" / "badges").glob("*.yaml"))),
        "tracks": len(list((ROOT / "content" / "tracks").glob("*.yaml"))),
    }
    row = re.search(r"\| Sample curriculum \| ([^|]+) \|", (ROOT / "README.md").read_text())
    assert row, "README.md no longer states what the sample curriculum contains"
    claimed = {
        noun: int(number)
        for number, noun in re.findall(r"(\d+) (regions?|quests?|badges?|tracks?)", row.group(1))
    }
    normalised = {noun.rstrip("s") + "s": n for noun, n in claimed.items()}
    assert normalised == counted, (
        f"README.md claims {normalised}, the content tree holds {counted}."
    )


def test_the_readme_says_the_project_is_not_released() -> None:
    """It is public and unfinished, and a reader must not have to infer the second part."""
    head = (ROOT / "README.md").read_text().split("## ", 1)[0].lower()
    assert "work in progress" in head
    assert "not released" in head
