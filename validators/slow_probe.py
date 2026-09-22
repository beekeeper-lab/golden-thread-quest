"""A validator that never finishes, used only to prove the timeout kills its process tree.

It spawns a child of its own, because a timeout that kills only the direct child leaves the
grandchild running — and a "stopped" run that keeps writing files is worse than one that
never stopped.
"""

from __future__ import annotations

import subprocess
import sys
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from quest_app.validator_runner import ValidatorOutput, Workspace


# In the grandchild's argv, so a test can find it by name and prove it died with its
# parent. Without a marker the only way to look for it was to guess at `sleep`, which is
# why the process-group kill could be downgraded to killing the child alone and no test
# noticed.
GRANDCHILD_MARKER = "gtq-slow-probe-grandchild"


def run(workspace: Workspace, output: ValidatorOutput) -> None:
    del workspace, output
    subprocess.Popen(  # noqa: S603 - fixed argv, no shell, test fixture only
        [sys.executable, "-c", f"import time\ntime.sleep(120)  # {GRANDCHILD_MARKER}"]
    )
    while True:
        time.sleep(1)
