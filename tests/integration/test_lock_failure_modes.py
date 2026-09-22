"""What the lock does when it cannot lock, and what it leaves behind when it refuses.

Round 4 added a cross-process lock on `participant/progress.yaml` and wrote in its docstring
that a local-first application must not refuse to work because it cannot lock. It delivered
that for a missing `fcntl` module and for nothing else. Round 5 found three ways the lock
itself became the failure:

* a `.progress.lock` the participant cannot open, which took every CLI action down with a
  traceback carrying absolute paths;
* `flock` answering `ENOLCK`, which is what a filesystem with no lock manager returns, and
  which killed every mutation on both surfaces;
* a refused action creating the participant directory and a lock file inside it before any
  guard had run.

The fourth test here is the one round 4's own lock test could not be: four processes released
from a barrier rather than four processes started in a loop. The loop version detected the
lock's removal one run in twelve, because each process paid a second of interpreter start
before reaching the critical section.
"""

from __future__ import annotations

import multiprocessing
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml
from quest_app.config import AppConfig
from quest_app.store import ProgressStore

ROOT = Path(__file__).resolve().parent.parent.parent
QUEST = "base-camp-repository-safety"
LOCKED_QUEST = "scrum-standup-digest"


def action(participant: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "quest_app.cli",
            "action",
            *args,
            "--participant-root",
            str(participant),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture
def started(tmp_path: Path) -> Path:
    participant = tmp_path / "participant"
    result = action(participant, "start-quest", "--quest", QUEST)
    assert result.returncode == 0, result.stderr
    return participant


def test_an_unwritable_lock_file_does_not_stop_the_change(started: Path) -> None:
    """The lock is an optimisation. The work is the point."""
    lock = started / ".progress.lock"
    lock.chmod(0o444)
    try:
        result = action(started, "mark-evidence-ready", "--quest", QUEST)
    finally:
        lock.chmod(0o644)

    assert "Traceback" not in result.stderr, result.stderr
    assert str(started) not in result.stderr, "a refusal must not print an absolute path"
    assert result.returncode == 0, result.stderr
    assert "evidence_ready" in (started / "progress.yaml").read_text()


def test_a_filesystem_that_cannot_lock_does_not_stop_the_change(
    started: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`ENOLCK` is what an NFS or 9p home directory answers when it has no lock manager."""
    import fcntl

    def refuse(*_: Any, **__: Any) -> None:
        raise OSError(37, "No locks available")

    monkeypatch.setattr(fcntl, "flock", refuse)
    config = AppConfig.for_repo(ROOT, participant_root=started)

    with ProgressStore(config).exclusive():
        pass  # the point is that this block is reached at all


def test_waiting_for_another_change_says_so(started: Path) -> None:
    """Correct but silent is indistinguishable from a hang.

    `run-validator` holds this lock across a validator subprocess, and the registry allows
    one 120 seconds.
    """
    holder = subprocess.Popen(
        [
            sys.executable,
            "-c",
            "import fcntl,sys,time\n"
            "h=open(sys.argv[1],'a+')\n"
            "fcntl.flock(h.fileno(), fcntl.LOCK_EX)\n"
            "print('held', flush=True)\n"
            "time.sleep(2)\n",
            str(started / ".progress.lock"),
        ],
        stdout=subprocess.PIPE,
        text=True,
    )
    assert holder.stdout is not None
    assert holder.stdout.readline().strip() == "held"
    try:
        result = action(started, "mark-evidence-ready", "--quest", QUEST)
    finally:
        holder.wait(timeout=30)

    assert result.returncode == 0, result.stderr
    assert "Another change is in progress" in result.stderr


def test_a_refused_action_leaves_no_participant_directory(tmp_path: Path) -> None:
    """The lock is taken before the guards, so a refusal used to create state anyway."""
    participant = tmp_path / "participant"
    result = action(participant, "start-quest", "--quest", LOCKED_QUEST)

    assert result.returncode != 0
    assert "locked" in result.stderr
    assert not participant.exists(), sorted(p.name for p in participant.iterdir())


def _start_quest(barrier: Any, participant: str) -> int:
    """Perform one start, released at the same instant as its siblings."""
    from quest_app.actions import ActionRunner
    from quest_app.content_loader import SchemaSet
    from quest_app.errors import ProblemReport
    from quest_app.pipeline import load_world

    config = AppConfig.for_repo(ROOT, participant_root=Path(participant))

    def load() -> Any:
        world = load_world(config, ProblemReport())
        assert world is not None
        return world

    runner = ActionRunner(config, SchemaSet(config.schemas_root), load)
    barrier.wait(timeout=60)
    try:
        runner.perform("start-quest", {"quest_id": QUEST})
    except Exception:
        return 1
    return 0


@pytest.mark.skipif(
    "fork" not in multiprocessing.get_all_start_methods(), reason="needs fork to share a barrier"
)
def test_four_processes_released_together_produce_one_attempt(tmp_path: Path) -> None:
    """Round 4's version of this test caught the lock's removal one run in twelve.

    Four `subprocess.run` calls each paid about a second of interpreter start and content
    load, so their read-modify-write windows almost never overlapped: the test that existed
    to guard the lock reported on process startup timing instead. Loading the world first
    and releasing all four at a barrier puts every process inside the critical section at
    once, which is what the lock is for.
    """
    participant = tmp_path / "participant"
    participant.mkdir(parents=True)
    ctx = multiprocessing.get_context("fork")
    barrier = ctx.Barrier(4)

    workers = [ctx.Process(target=_start_quest, args=(barrier, str(participant))) for _ in range(4)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=120)

    progress = yaml.safe_load((participant / "progress.yaml").read_text())
    attempts = [a for a in progress.get("attempts", []) if a["quest_id"] == QUEST]
    activity = (participant / "ACTIVITY.md").read_text()

    assert len(attempts) == 1, f"{len(attempts)} attempts from four simultaneous starts"
    assert activity.count("Started") == 1, "one start, one line"


def test_the_lock_never_runs_as_root() -> None:
    """A guard on the test above: as root, an unwritable file is still writable."""
    if os.geteuid() == 0:
        pytest.skip("the permission test cannot mean anything as root")
