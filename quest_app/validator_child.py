"""The process a validator actually runs in.

Invoked as `python -m quest_app.validator_child` with a JSON specification on stdin, it
imports the registered entrypoint, runs it against a `Workspace`, and writes the result as
JSON on stdout.

A separate process invoked by `subprocess` rather than `multiprocessing`, for two reasons
that both turned out to matter:

* **The environment is per-run by construction.** `subprocess` takes `env=`, so each
  validator gets exactly its registered allowlist. The `multiprocessing` version set
  `os.environ` around `process.start()`, and `forkserver` captures its helper's environment
  once — so the second validator of a session inherited the first one's allowlist, in both
  directions, and in a running service the order is whatever the participant clicks first.
* **It does not re-import the parent's `__main__`.** Both `spawn` and `forkserver` do, which
  made running a validator depend on how the parent process happened to be started.

Nothing here trusts its input beyond the shape: the entrypoint is checked against the
allowlisted package before it is imported, exactly as it is in the parent.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any


def main() -> int:
    specification = json.loads(sys.stdin.read())

    from quest_app.validator_runner import (
        ValidatorOutput,
        Workspace,
        WorkspaceError,
        _import_entrypoint,
    )

    workspace = Workspace(
        read_roots=tuple(Path(p) for p in specification["read_roots"]),
        write_roots=tuple(Path(p) for p in specification["write_roots"]),
        repo_root=Path(specification["repo_root"]),
        participant_root=Path(specification["participant_root"]),
        parameters=specification["parameters"],
    )

    # The process group is created by the parent's `start_new_session=True`. Calling
    # `os.setsid()` here as well raises PermissionError, because this process is already the
    # session leader — which is exactly how the first version of this failed.
    output = ValidatorOutput()
    try:
        _import_entrypoint(specification["entrypoint"])(workspace, output)
    except WorkspaceError as exc:
        output.fail_environment(f"the validator tried to leave its permitted paths: {exc}")
    except Exception as exc:
        # The type and message, never the traceback: a traceback carries absolute paths and
        # this text is shown to a participant.
        output.fail_environment(f"the validator raised {type(exc).__name__}: {exc!s:.200}")

    payload: dict[str, Any] = {
        "checks": [asdict(check) for check in output.checks],
        "notes": output.notes,
        "environment_failure": output.environment_failure,
    }
    sys.stdout.write(json.dumps(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
