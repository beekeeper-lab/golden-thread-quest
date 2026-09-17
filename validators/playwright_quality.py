"""Checks that a submitted test targets behaviour rather than markup.

The quest is about writing a test someone else can maintain, so the checks are about the
properties that make a test survive a refactor: it asserts on user-visible behaviour, it
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
                id="selectors-target-behaviour",
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
                id="selectors-target-behaviour",
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
                id="selectors-target-behaviour",
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
    artifacts = workspace.iter_files("participant/evidence")
    has_run_record = any(
        path.suffix in {".json", ".txt", ".log", ".xml"} or "trace" in path.name.lower()
        for path in artifacts
    )
    if has_run_record:
        output.add(
            Check(
                id="failure-is-diagnosable",
                outcome="pass",
                summary="The evidence includes a run record.",
                evidence="A reviewer can see what happened without re-running the test.",
            )
        )
    else:
        output.add(
            Check(
                id="failure-is-diagnosable",
                outcome="warning",
                severity="low",
                summary="No run record was found in the evidence.",
                evidence="Only source files are present.",
                suggested_action=(
                    "Keep the run output or a trace so a failure can be diagnosed later."
                ),
            )
        )
