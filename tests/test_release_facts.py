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
# number is supposed to describe.
CLAIMS = [
    (Path("README.md"), r"(\d+) under `make check`", "not ui"),
    (Path("README.md"), r"(\d+) driving a real browser", "ui"),
    (Path("docs/RELEASE-NOTES.md"), r"(\d+) under `make check`", "not ui"),
    (Path("docs/RELEASE-NOTES.md"), r"plus (\d+) browser-driven", "ui"),
    (Path("docs/USER-GUIDE.md"), r"a secret scan and (\d+)", "not ui"),
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
