"""Checks that a submitted test targets behavior rather than markup.

The quest is about writing a test someone else can maintain, so the checks are about the
properties that make a test survive a refactor: it asserts on user-visible behavior, it
does not wait on the clock, and it leaves enough behind to diagnose a failure.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from quest_app.validator_runner import ValidatorOutput, Workspace

from quest_app.validator_runner import Check

# Selectors coupled to markup. A test built on these fails when someone renames a class.
BRITTLE_SELECTORS = re.compile(
    r"""(?:page|frame)\.(?:locator|query_selector|querySelector)\(\s*['"]"""
    r"""(?:\s*(?:div|span|table|tbody|tr|td)[\s>+~.#\[]|[.#][\w-]+\s*>)""",
    re.IGNORECASE,
)
ARBITRARY_WAIT = re.compile(
    r"wait_for_timeout\(|waitForTimeout\(|time\.sleep\(|sleep\(\s*\d", re.IGNORECASE
)
ROLE_QUERY = re.compile(
    r"get_by_(?:role|label|text|test_id|placeholder)|getBy(?:Role|Label|Text|TestId)"
)
ASSERTION = re.compile(r"\bexpect\(|\bassert\b")

# What failure evidence looks like on disk. Playwright writes `trace.zip` and
# `test-failed-1.png` by default, and a participant naming their own files follows the same
# habit, so the marker is in the name rather than in a path this validator dictates.
FAILURE_MARKERS = ("fail", "trace", "error")
RECORD_SUFFIXES = {".json", ".txt", ".log", ".xml", ".md", ".zip"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def run(workspace: Workspace, output: ValidatorOutput) -> None:
    tests = [
        path
        for path in workspace.iter_files("participant/tests")
        if path.suffix in {".py", ".ts", ".js"} and "test" in path.name.lower()
    ]
    if not tests:
        output.add(
            Check(
                id="test-exists",
                outcome="inconclusive",
                summary="No test file was found to evaluate.",
                evidence="participant/tests contains no test file.",
                suggested_action="Write the test, then run this again.",
            )
        )
        return

    sources = {path: workspace.read_text(str(path)) for path in tests}
    _check_assertions(workspace, sources, output)
    _check_selectors(workspace, sources, output)
    _check_waits(workspace, sources, output)
    _check_failure_evidence(workspace, output)


def _check_assertions(
    workspace: Workspace, sources: dict[Path, str], output: ValidatorOutput
) -> None:
    without = [
        workspace.relative(path) for path, text in sources.items() if not ASSERTION.search(text)
    ]
    if without:
        output.add(
            Check(
                id="test-asserts-something",
                outcome="fail",
                severity="blocking",
                summary="A test file contains no assertion.",
                evidence=", ".join(without[:5]),
                suggested_action="A test that cannot fail is not evidence of anything.",
            )
        )
    else:
        output.add(
            Check(
                id="test-asserts-something",
                outcome="pass",
                summary="Every test file asserts something.",
                evidence=f"{len(sources)} file(s) checked.",
            )
        )


def _check_selectors(
    workspace: Workspace, sources: dict[Path, str], output: ValidatorOutput
) -> None:
    brittle = [
        workspace.relative(path) for path, text in sources.items() if BRITTLE_SELECTORS.search(text)
    ]
    role_based = [path for path, text in sources.items() if ROLE_QUERY.search(text)]
    if brittle:
        output.add(
            Check(
                id="selectors-target-behavior",
                outcome="fail",
                severity="high",
                summary="The test selects elements by markup structure.",
                evidence=", ".join(brittle[:5]),
                suggested_action=(
                    "Query by role, label or visible text. A selector tied to a div renames itself "
                    "out of existence the next time someone touches the CSS."
                ),
            )
        )
    elif not role_based:
        output.add(
            Check(
                id="selectors-target-behavior",
                outcome="warning",
                severity="low",
                summary="No role, label or text query was found.",
                evidence="The test may still be sound; this is a hint, not a verdict.",
                suggested_action="Prefer queries a user could describe.",
            )
        )
    else:
        output.add(
            Check(
                id="selectors-target-behavior",
                outcome="pass",
                summary="The test queries by role, label or visible text.",
                evidence=f"{len(role_based)} file(s) use accessible queries.",
            )
        )


def _check_waits(workspace: Workspace, sources: dict[Path, str], output: ValidatorOutput) -> None:
    sleeping = [
        workspace.relative(path) for path, text in sources.items() if ARBITRARY_WAIT.search(text)
    ]
    if sleeping:
        output.add(
            Check(
                id="no-arbitrary-waits",
                outcome="fail",
                severity="medium",
                summary="The test waits on the clock rather than on a condition.",
                evidence=", ".join(sleeping[:5]),
                suggested_action=(
                    "Wait for the thing you actually need. A fixed sleep is slow when it works "
                    "and flaky when it does not."
                ),
            )
        )
    else:
        output.add(
            Check(
                id="no-arbitrary-waits",
                outcome="pass",
                summary="No arbitrary wait was found.",
                evidence="The test waits on conditions.",
            )
        )


def _check_failure_evidence(workspace: Workspace, output: ValidatorOutput) -> None:
    """Whether this attempt's evidence would let a reviewer diagnose a failing run.

    Criterion 9 asks for a trace, a screenshot and a reproduction summary from a failure.
    The older form accepted any `.json`, `.txt`, `.log` or `.xml` file anywhere under
    `participant/evidence`, so the successful run's own log satisfied it, and so did a file
    belonging to an entirely different quest.
    """
    artifacts = workspace.attempt_files()
    if not artifacts:
        output.add(
            Check(
                id="failure-is-diagnosable",
                outcome="warning",
                severity="low",
                summary="No run record was found in this attempt's evidence.",
                evidence="This attempt's evidence package is empty.",
                suggested_action=(
                    "Save the tagged run's output, and the trace and screenshot from a failing "
                    "run, so a reviewer can see what happened without re-running the test."
                ),
            )
        )
        return

    failure_records = [
        path for path in artifacts if _names_a_failure(path) and path.suffix in RECORD_SUFFIXES
    ]
    failure_images = [
        path for path in artifacts if _names_a_failure(path) and path.suffix in IMAGE_SUFFIXES
    ]

    missing = []
    if not failure_records:
        missing.append("a trace or log from the failing run")
    if not failure_images:
        missing.append("a screenshot of the failure")

    if missing:
        output.add(
            Check(
                id="failure-is-diagnosable",
                outcome="warning",
                severity="low",
                summary="The evidence does not show what a failure of this test looks like.",
                evidence=f"Missing: {', '.join(missing)}.",
                suggested_action=(
                    "Make the test fail once on purpose and keep what it produced. A test whose "
                    "failure nobody can read is a test nobody will trust."
                ),
            )
        )
    else:
        output.add(
            Check(
                id="failure-is-diagnosable",
                outcome="pass",
                summary="The evidence includes a record of the test failing.",
                evidence=", ".join(
                    workspace.relative(path) for path in (failure_records + failure_images)[:4]
                ),
            )
        )


def _names_a_failure(path: Path) -> bool:
    """Whether a file says in its own name that it came from a failure or a trace."""
    name = path.name.lower()
    return any(marker in name for marker in FAILURE_MARKERS)
