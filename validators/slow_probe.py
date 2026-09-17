"""A validator that never finishes, used only to prove the timeout kills its process tree.

It spawns a child of its own, because a timeout that kills only the direct child leaves the
grandchild running — and a "stopped" run that keeps writing files is worse than one that
never stopped.
"""

from __future__ import annotations

import subprocess
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from quest_app.validator_runner import ValidatorOutput, Workspace


def run(workspace: Workspace, output: ValidatorOutput) -> None:
    del workspace, output
    subprocess.Popen(["sleep", "120"])  # noqa: S607 - fixed argv, no shell, test fixture only
    while True:
        time.sleep(1)
