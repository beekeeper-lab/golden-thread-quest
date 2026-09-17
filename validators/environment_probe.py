"""Reports the environment it was actually given. Used only to test the allowlist.

The allowlist is a documented security control, and the only way to know it holds is to ask
the child what it can see — inspecting the registry strings, which is what the first test
did, cannot tell you that the parent applied them.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from quest_app.validator_runner import ValidatorOutput, Workspace

from quest_app.validator_runner import Check

WATCHED = ("JIRA_BASE_URL", "GTQ_TEST_SECRET", "PATH")


def run(workspace: Workspace, output: ValidatorOutput) -> None:
    del workspace
    for name in WATCHED:
        value = os.environ.get(name)
        output.add(
            Check(
                id=f"env-{name.lower().replace('_', '-')}",
                outcome="pass" if value is not None else "skipped",
                summary=f"{name} is {'present' if value is not None else 'absent'}",
                evidence=f"{name}={value if value is not None else '<ABSENT>'}",
            )
        )
