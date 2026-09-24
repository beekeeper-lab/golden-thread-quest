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
"""

from __future__ import annotations

import re
from pathlib import Path

from quest_app.actions import CONFIRMATIONS

REPO_ROOT = Path(__file__).resolve().parents[2]

# The living instructions a participant or reviewer actually copies commands from.
# docs/audits/** and docs/DECISIONS.md are historical/narrative record, not instructions, and
# are deliberately not held to this rule.
DOC_FILES = (
    "README.md",
    "CONTRIBUTING.md",
    "docs/USER-GUIDE.md",
    "docs/guides/REVIEWER.md",
    "docs/guides/UPDATING.md",
)

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


def test_every_confirmed_action_example_carries_confirm() -> None:
    missing: list[str] = []
    for relative in DOC_FILES:
        path = REPO_ROOT / relative
        if not path.exists():
            continue
        for command in _commands(path.read_text(encoding="utf-8")):
            match = ACTION_NAME.search(command)
            if not match:
                continue
            action = match.group(1).strip("`")
            # A bare mention with no flags at all is a reference to the other guide, not a
            # command meant to be copied and run — real examples always carry at least
            # `--quest`.
            if action in CONFIRMATIONS and "--" in command and "--confirm" not in command:
                missing.append(f"{relative}: {command.splitlines()[0]!r} has no --confirm")
    assert not missing, "\n".join(missing)


def test_the_action_confirmations_this_test_checks_are_not_empty() -> None:
    """A guard against the check silently checking nothing if `CONFIRMATIONS` were emptied."""
    assert CONFIRMATIONS
