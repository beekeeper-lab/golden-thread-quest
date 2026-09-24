"""Every printed `quest-app action <mutating-action>` example carries `--confirm` when the
action needs it (T2).

`ActionRunner.perform` refuses `start-quest`, `submit-for-review` and `record-review` without
a confirmation (ADR-033). A participant or reviewer who copies a printed command exactly and
sees it refused has to notice, on their own, that the printed command was missing a flag the
refusal message never names. docs/USER-GUIDE.md and docs/guides/REVIEWER.md shipped several
such examples. This does not check the whole file, only the shape a copy-paste example takes:
a mention with no flags at all (`docs/DECISIONS.md`, "a reviewer records a decision with
`quest-app action record-review`") is a reference, not an instruction to run, so it is left
alone.

A hand-kept list of five documents used to name what gets checked (T1). It skipped
`docs/guides/PARTICIPANT.md`, `docs/SETUP.md`, `docs/guides/VALIDATOR-AUTHORING.md` and
`docs/CONTENT-AUTHORING-GUIDE.md` — none printed an action command the day the list was
written, which said nothing about the next edit to any of them. Every living Markdown
document is checked now: every `*.md` at the repository root and under `docs/`, except a
short, justified list of files that are historical record rather than current instructions.
"""

from __future__ import annotations

import re
from pathlib import Path

from quest_app.actions import CONFIRMATIONS

REPO_ROOT = Path(__file__).resolve().parents[2]

# Historical record, not living instructions a participant or reviewer copies commands from.
# Each one predates or stands outside the day-to-day USER-GUIDE/REVIEWER-guide flow this test
# actually protects:
#   - docs/audits/** and docs/DECISIONS.md — round-by-round audit and decision history.
#   - docs/RELEASE-NOTES.md is deliberately NOT here: README.md points at it as the current
#     list of known limitations, so it is live and stays checked.
#   - HANDOFF-PROMPT.md, PACKAGE-MANIFEST.md, VALIDATION-REPORT.md — the pre-Stage-1 planning
#     package handed to the implementation agent. VALIDATION-REPORT.md says so of itself
#     ("Preserved as written on the validation date, before Stage 1"); the other two describe
#     that same one-time handoff and are not read by a participant or reviewer using the
#     running application.
#   - IMAGE-PLAN.md — a diagram-generation log for docs/USER-GUIDE.md's illustrations, not
#     application usage instructions.
_HISTORICAL_FILES = frozenset(
    {
        "docs/DECISIONS.md",
        "HANDOFF-PROMPT.md",
        "IMAGE-PLAN.md",
        "PACKAGE-MANIFEST.md",
        "VALIDATION-REPORT.md",
    }
)


def _doc_files() -> tuple[Path, ...]:
    """Every living Markdown document: repo-root `*.md` and `docs/**/*.md`."""
    candidates = sorted((REPO_ROOT).glob("*.md")) + sorted((REPO_ROOT / "docs").rglob("*.md"))
    return tuple(
        path
        for path in candidates
        if path.relative_to(REPO_ROOT).parts[:2] != ("docs", "audits")
        and path.relative_to(REPO_ROOT).as_posix() not in _HISTORICAL_FILES
    )


DOC_FILES = tuple(path.relative_to(REPO_ROOT).as_posix() for path in _doc_files())

ACTION_NAME = re.compile(r"quest-app action (\S+)")


def _commands(text: str) -> list[str]:
    """`quest-app action ...` invocations, backslash-continuation lines joined into one."""
    lines = text.splitlines()
    commands: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if "quest-app action" in line:
            group = [line]
            while group[-1].rstrip().endswith("\\") and index + 1 < len(lines):
                index += 1
                group.append(lines[index])
            commands.append("\n".join(group))
        index += 1
    return commands


def _missing_confirmations(label: str, text: str) -> list[str]:
    missing: list[str] = []
    for command in _commands(text):
        match = ACTION_NAME.search(command)
        if not match:
            continue
        action = match.group(1).strip("`")
        # A bare mention with no flags at all is a reference to the other guide, not a
        # command meant to be copied and run — real examples always carry at least
        # `--quest`.
        if action in CONFIRMATIONS and "--" in command and "--confirm" not in command:
            missing.append(f"{label}: {command.splitlines()[0]!r} has no --confirm")
    return missing


def test_every_confirmed_action_example_carries_confirm() -> None:
    missing: list[str] = []
    for relative in DOC_FILES:
        path = REPO_ROOT / relative
        if not path.exists():
            continue
        missing.extend(_missing_confirmations(relative, path.read_text(encoding="utf-8")))
    assert not missing, "\n".join(missing)


def test_the_action_confirmations_this_test_checks_are_not_empty() -> None:
    """A guard against the check silently checking nothing if `CONFIRMATIONS` were emptied."""
    assert CONFIRMATIONS


def test_setup_md_is_in_scope_and_a_planted_bad_example_is_caught() -> None:
    """T1: the hand-kept list this test used to check skipped `docs/SETUP.md` (among others).

    It is not skipped now. Rather than land a permanently broken example in a real guide to
    prove it, a planted one is appended to a copy of the current text and run through the
    same detection the main test above uses.
    """
    relative = "docs/SETUP.md"
    assert relative in DOC_FILES, f"{relative} is skipped; it should be in scope"

    real_text = (REPO_ROOT / relative).read_text(encoding="utf-8")
    assert not _missing_confirmations(relative, real_text), (
        "the real document already has an unconfirmed example; fix it directly"
    )

    planted = real_text + "\n\n    quest-app action start-quest --quest demo-quest\n"
    assert _missing_confirmations(relative, planted), (
        "a planted --confirm-less example in docs/SETUP.md was not caught"
    )
