"""The process a validator actually runs in.

Started by `validator_runner.CHILD_BOOTSTRAP`, which runs it as `__main__` with a JSON
specification on stdin. It imports the registered entrypoint, runs it against a
`Workspace`, and writes the result as JSON on stdout.

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


def _safe_reason(error: BaseException) -> str:
    """An exception described without the paths it mentions.

    `OSError.strerror` is the description; `filename` is the path. Using `str(error)` joins
    them, which puts an absolute path into an evidence package a reviewer will read.
    """
    if isinstance(error, OSError):
        return f"{type(error).__name__}: {error.strerror or 'operation failed'}"
    message = str(error)[:200]
    # Anything path-shaped is replaced rather than trimmed, so a message that embeds one in
    # the middle is still usable.
    import re as _re

    message = _re.sub(r"(?:/[^/\s'\"]+){2,}/?", "<path>", message)
    return f"{type(error).__name__}: {message}" if message else type(error).__name__


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
        evidence_root=(
            Path(specification["evidence_root"]) if specification.get("evidence_root") else None
        ),
    )

    # The process group is created by the parent's `start_new_session=True`. Calling
    # `os.setsid()` here as well raises PermissionError, because this process is already the
    # session leader — which is exactly how the first version of this failed.
    # The result travels on the original stdout; everything the validator itself writes there,
    # by `print()` or from a process it starts, is moved to stderr. A stray print used to be
    # spliced into the JSON and turned a finished run into "could not be read".
    import os

    result_channel = os.fdopen(os.dup(1), "w", encoding="utf-8")
    sys.stdout.flush()
    os.dup2(2, 1)

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
    sys.stdout.flush()
    result_channel.write(json.dumps(payload))
    result_channel.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
