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
from quest_app.actions import CONFIRMATIONS
from quest_app.config import AppConfig
from quest_app.store import ProgressStore

ROOT = Path(__file__).resolve().parent.parent.parent
QUEST = "base-camp-repository-safety"
LOCKED_QUEST = "scrum-standup-digest"


def _isolated_env(base: Path) -> dict[str, str]:
    """Every root a mutating CLI action can rebuild into, pointed away from `ROOT` (C2).

    `--participant-root` is the only root the CLI itself lets a caller move; `generated/`
    and `local-data/` still default to whatever `--repo-root` resolves to, which here is
    `ROOT` (no `--repo-root` is passed). Without this, every action below rebuilt the
    repository's own `generated/` and could write `local-data/`.
    """
    return {
        **os.environ,
        "GTQ_GENERATED_ROOT": str(base / "generated"),
        "GTQ_LOCAL_DATA_ROOT": str(base / "local-data"),
    }


def action(participant: Path, *args: str) -> subprocess.CompletedProcess[str]:
    # An action that carries a confirmation is refused without one, on every surface
    # (ADR-033). A test about something else says it means it, exactly as the browser form
    # does; the gate itself is tested in tests/integration/test_confirmations.py.
    confirm = ["--confirm"] if args and args[0] in CONFIRMATIONS and "--confirm" not in args else []
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "quest_app.cli",
            "action",
            *args,
            *confirm,
            "--participant-root",
            str(participant),
        ],
        cwd=ROOT,
        env=_isolated_env(participant.parent),
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


def test_a_refused_action_records_no_state(tmp_path: Path) -> None:
    """A refusal writes nothing a participant or a reviewer would ever read.

    Round 5 went further and deleted the lock file and the directory around it, so that a
    refusal left no trace at all. Round 6 showed what that cost: another process holding
    `flock` on that inode was left holding a lock on an orphan, the next process created a
    fresh file and entered immediately, and two writers were in the critical section at once.
    A hidden, ignored file in a directory the participant owns is the cheaper of the two, so
    what this asserts is that no *state* was recorded, not that no byte was written.
    """
    participant = tmp_path / "participant"
    result = action(participant, "start-quest", "--quest", LOCKED_QUEST)

    assert result.returncode != 0
    assert "locked" in result.stderr
    assert not (participant / "progress.yaml").exists(), "a refused action recorded state"
    assert not (participant / "ACTIVITY.md").exists(), "a refused action told a story"
    leftovers = sorted(p.name for p in participant.iterdir()) if participant.exists() else []
    assert leftovers in ([], [".progress.lock"]), leftovers


def _start_quest(barrier: Any, participant: str) -> int:
    """Perform one start, released at the same instant as its siblings."""
    from quest_app.actions import ActionRunner
    from quest_app.content_loader import SchemaSet
    from quest_app.errors import ProblemReport
    from quest_app.pipeline import load_world

    # `start-quest` rebuilds the site (C2): without `generated_root` here too, four
    # in-process workers would each rebuild the repository's own `generated/`.
    base = Path(participant).parent
    config = AppConfig.for_repo(
        ROOT,
        participant_root=Path(participant),
        generated_root=base / "generated",
        local_data_root=base / "local-data",
    )

    def load() -> Any:
        world = load_world(config, ProblemReport())
        assert world is not None
        return world

    runner = ActionRunner(config, SchemaSet(config.schemas_root), load)
    barrier.wait(timeout=60)
    try:
        runner.perform("start-quest", {"quest_id": QUEST, "confirm": True})
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


def test_a_build_whose_lock_cannot_be_opened_still_publishes(tmp_path: Path) -> None:
    """The build lock was given the store's shape without the store's fall-through.

    ADR-035 and ADR-036 both say that not being able to lock is never a reason to refuse the
    work, and the build handled a missing `fcntl` module and nothing else: an unwritable
    `generated.lock`, or a filesystem answering `ENOLCK`, crashed every publisher on exactly
    the filesystem the fall-through was written for.

    The lock lives beside `generated_root` (`generated_root.with_suffix(".lock")`), so
    pointing `GTQ_GENERATED_ROOT` at `tmp_path` (C2) exercises the same lock-file mechanics
    without touching `ROOT/generated.lock`.
    """
    generated_root = tmp_path / "generated"
    lock = generated_root.with_suffix(".lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.touch()
    lock.chmod(0o444)
    try:
        result = subprocess.run(
            [sys.executable, "-m", "quest_app.cli", "build"],
            cwd=ROOT,
            env=_isolated_env(tmp_path),
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        lock.chmod(0o644)

    assert "Traceback" not in result.stderr, result.stderr
    assert result.returncode == 0, result.stderr


def test_a_build_that_cannot_lock_at_all_still_publishes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`ENOLCK` is what a filesystem with no lock manager answers."""
    import fcntl

    from quest_app.build import _exclusive_output

    def refuse(*_: Any, **__: Any) -> None:
        raise OSError(37, "No locks available")

    monkeypatch.setattr(fcntl, "flock", refuse)
    config = AppConfig.for_repo(ROOT, generated_root=tmp_path / "generated")

    with _exclusive_output(config):
        pass  # the point is that this block is reached at all


def _hold_then_report(participant: str, seconds: float, out: Any) -> None:
    """Hold the progress lock, then say how long entering it took."""
    import time

    config = AppConfig.for_repo(ROOT, participant_root=Path(participant))
    started = time.monotonic()
    with ProgressStore(config).exclusive():
        out.put(time.monotonic() - started)
        time.sleep(seconds)


@pytest.mark.skipif(
    "fork" not in multiprocessing.get_all_start_methods(), reason="needs fork for the queue"
)
def test_the_progress_lock_excludes_rather_than_merely_existing(tmp_path: Path) -> None:
    """A shared lock passes every other test in this file.

    `LOCK_EX` changed to `LOCK_SH` left the whole suite green while two processes sat in the
    critical section together, because each one writes `progress.yaml` whole and the last
    writer is what the assertions see. Waiting is the only observable difference between a
    lock that excludes and a lock that does not.
    """
    participant = tmp_path / "participant"
    participant.mkdir(parents=True)
    ctx = multiprocessing.get_context("fork")
    out = ctx.Queue()

    # The hold is long and the margins are wide on purpose. The distinction being asserted
    # is "waited for the other process" against "did not wait at all", and a tight bound
    # turns that into a measurement of how loaded the machine is: this test failed once
    # while a second suite was running beside it.
    hold = 3.0
    first = ctx.Process(target=_hold_then_report, args=(str(participant), hold, out))
    first.start()
    assert out.get(timeout=60) < hold / 2, "the first process should not have waited"

    second = ctx.Process(target=_hold_then_report, args=(str(participant), 0.0, out))
    second.start()
    waited = out.get(timeout=60)
    first.join(timeout=60)
    second.join(timeout=60)

    assert waited > 1.0, f"the second process entered after {waited:.2f}s; the lock is shared"


def test_a_rebuild_that_fails_does_not_deny_a_change_that_happened(
    content_repo: Path,
) -> None:
    """The state change is on disk before the rebuild runs.

    An `OSError` from the rebuild was caught as though the participant's own directory could
    not be written, so the CLI said the change had not happened, pointed at the wrong
    directory, and exited non-zero — while `progress.yaml` said `in_progress`. Generated
    output is disposable and rebuildable; the participant's record is neither.
    """
    participant = content_repo.parent / "participant-new"  # outside the read-only tree
    generated = content_repo / "generated"
    generated.mkdir(parents=True, exist_ok=True)
    content_repo.chmod(0o555)  # nothing new can be created beside the output
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "quest_app.cli",
                "action",
                "start-quest",
                "--confirm",
                "--quest",
                QUEST,
                "--repo-root",
                str(content_repo),
                "--participant-root",
                str(participant),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        content_repo.chmod(0o755)

    if result.returncode == 0 and "could not be rebuilt" not in (result.stdout + result.stderr):
        pytest.skip("the build succeeded here, so there is no failed rebuild to judge")
    assert "Traceback" not in result.stderr, result.stderr
    assert result.returncode == 0, result.stderr
    assert "was recorded" in result.stdout + result.stderr
    assert "in_progress" in (participant / "progress.yaml").read_text()
