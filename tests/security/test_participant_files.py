"""Reading and writing inside `participant/` without following it somewhere else.

Round 12 found every write below the participant root following links: the activity line
appended through a link to wherever it led and blocked forever on a FIFO while both locks
were held, validation results went into a `validation/` directory that was a link out of the
tree and were read back as evidence, and the review archive was a plain `write_text` (E1).
Validation results were read with no bound (E2). The reviewer page read review records the
loader never checked, unbounded and unguarded (E3). And no evidence file had a size ceiling,
so a large log made every build slow while it held the locks, and hashing held every file in
memory (E8).

A FIFO that a broken implementation would block on is exercised only in a subprocess with a
timeout, or where the fix is what keeps the call from blocking, so a regression fails here
rather than hanging the suite forever.
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
import yaml
from quest_app.actions import CONFIRMATIONS
from quest_app.config import AppConfig
from quest_app.content_loader import SchemaSet
from quest_app.errors import ProblemReport
from quest_app.pipeline import load_world
from quest_app.safe_io import MAX_EVIDENCE_FILE_BYTES, MAX_STATE_BYTES, MAX_VALIDATION_RESULT_BYTES
from quest_app.store import StoreError

ROOT = Path(__file__).resolve().parent.parent.parent
QUEST = "base-camp-repository-safety"
VERIFIED = "participant/evidence/base-camp-repository-safety/base-camp-attempt-001"
READY = "participant/evidence/jira-read-assigned-stories/jira-attempt-001"
RESULT = "validation/repository-foundation-run-001.json"
# A subprocess that is still running after this has blocked. Generous: every action here
# rebuilds the site, which takes a few seconds on a slow machine.
HANG = 90


def action(participant: Path, *args: str) -> subprocess.CompletedProcess[str]:
    confirm = ["--confirm"] if args and args[0] in CONFIRMATIONS else []
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
        # The participant root alone does not move the rebuild: without these the action
        # rebuilt the repository's own `generated/` (round 12 C2).
        env={
            **os.environ,
            "GTQ_GENERATED_ROOT": str(participant.parent / "generated"),
            "GTQ_LOCAL_DATA_ROOT": str(participant.parent / "local-data"),
        },
        capture_output=True,
        text=True,
        check=False,
        timeout=HANG,
    )


def state_of(participant: Path) -> str:
    data = yaml.safe_load((participant / "progress.yaml").read_text())
    return str(data["attempts"][-1]["state"])


def problems(report: ProblemReport, code: str) -> list[Any]:
    return [problem for problem in report.problems if problem.code == code]


def make(target: Path, kind: str, outside: Path) -> None:
    """Put something that is not an ordinary file (or directory) at `target`."""
    if target.is_dir() and not target.is_symlink():
        import shutil

        shutil.rmtree(target)
    elif target.exists() or target.is_symlink():
        target.unlink()
    if kind == "fifo":
        os.mkfifo(target)
    elif kind == "device":
        target.symlink_to("/dev/zero")
    elif kind == "link_outside":
        target.symlink_to(outside)
    elif kind == "dangling":
        target.symlink_to(outside.parent / "nothing-here")
    elif kind == "directory":
        target.mkdir()
    else:  # pragma: no cover - a typo in a parameter list
        raise AssertionError(kind)


# --- E1: the activity line -------------------------------------------------------------


@pytest.mark.parametrize("kind", ["fifo", "link_outside", "dangling", "directory"])
def test_an_unusable_activity_file_skips_the_line_and_the_change_completes(
    tmp_path: Path, kind: str
) -> None:
    """The change stands, the line is skipped with a warning, and the locks are released.

    A FIFO `ACTIVITY.md` blocked the action forever while it held the progress lock, after
    `progress.yaml` had already changed; a link was appended through to whatever it led to.
    The second action proves the lock was released: it takes the same lock.
    """
    participant = tmp_path / "participant"
    assert action(participant, "start-quest", "--quest", QUEST).returncode == 0
    outside = tmp_path / "outside.md"
    outside.write_text("not the participant's\n")
    make(participant / "ACTIVITY.md", kind, outside)

    result = action(participant, "mark-evidence-ready", "--quest", QUEST)

    assert result.returncode == 0, result.stderr
    assert state_of(participant) == "evidence_ready"
    assert "activity line was not written" in result.stderr
    assert "Traceback" not in result.stderr
    assert outside.read_text() == "not the participant's\n"
    assert not (tmp_path / "nothing-here").exists()
    again = action(participant, "reopen-evidence", "--quest", QUEST)
    assert again.returncode == 0, again.stderr
    assert state_of(participant) == "in_progress"


def test_a_lock_file_that_is_a_link_is_not_created_through(tmp_path: Path) -> None:
    """`open("a+")` created the lock wherever a planted link pointed; now it runs unlocked."""
    participant = tmp_path / "participant"
    assert action(participant, "start-quest", "--quest", QUEST).returncode == 0
    lock = participant / ".progress.lock"
    lock.unlink()
    lock.symlink_to(tmp_path / "planted.lock")

    result = action(participant, "mark-evidence-ready", "--quest", QUEST)

    assert result.returncode == 0, result.stderr
    assert not (tmp_path / "planted.lock").exists()


@pytest.mark.parametrize("where", ["outside", "inside"])
def test_an_evidence_package_is_not_created_through_a_link(tmp_path: Path, where: str) -> None:
    """A linked `participant/evidence` put the new package wherever the link led."""
    participant = tmp_path / "participant"
    participant.mkdir()
    target = tmp_path / "elsewhere" if where == "outside" else participant / "elsewhere"
    target.mkdir()
    (participant / "evidence").symlink_to(target)

    result = action(participant, "start-quest", "--quest", QUEST)

    assert result.returncode != 0
    assert "Traceback" not in result.stderr
    assert str(tmp_path) not in result.stderr, "a refusal must not print an absolute path"
    assert list(target.iterdir()) == []


# --- E1: validation results ------------------------------------------------------------


@pytest.mark.parametrize("where", ["validation_outside", "validation_inside", "package_parent"])
def test_a_validation_result_is_not_written_through_a_link(
    config: AppConfig, tmp_path: Path, where: str
) -> None:
    """The result is refused, and nothing appears where the link leads."""
    from quest_app.evidence import store_result

    package = config.participant_root / VERIFIED.removeprefix("participant/")
    elsewhere = (
        config.participant_root / "elsewhere"
        if where == "validation_inside"
        else tmp_path / "elsewhere"
    )
    elsewhere.mkdir()
    if where == "package_parent":
        # The quest's evidence area itself is the link; the package lies beyond it.
        area = package.parent
        (elsewhere / package.name).mkdir()
        import shutil

        shutil.rmtree(area)
        area.symlink_to(elsewhere)
        before = sorted(p.name for p in (elsewhere / package.name).iterdir())
    else:
        import shutil

        shutil.rmtree(package / "validation")
        (package / "validation").symlink_to(elsewhere)
        before = []

    with pytest.raises(StoreError, match="link"):
        store_result(config, VERIFIED, {"run_id": "repository-foundation-run-999"})

    if where == "package_parent":
        assert sorted(p.name for p in (elsewhere / package.name).iterdir()) == before
    else:
        assert list(elsewhere.iterdir()) == []


def test_the_loader_does_not_read_results_through_a_linked_validation_directory(
    config: AppConfig, tmp_path: Path
) -> None:
    """Results are what `locally_validated` is derived from; a linked folder is reported."""
    from quest_app.progress import load_participant_state

    package = config.participant_root / VERIFIED.removeprefix("participant/")
    moved = tmp_path / "validation-elsewhere"
    (package / "validation").rename(moved)
    (package / "validation").symlink_to(moved)

    report = ProblemReport()
    state = load_participant_state(config, SchemaSet(config.schemas_root), report)

    assert state is not None
    assert state.validations.get("base-camp-attempt-001", ()) == ()
    assert problems(report, "validation.directory_not_a_directory"), report.to_text()


def test_a_result_over_the_stored_ceiling_is_refused_before_it_is_written(
    config: AppConfig,
) -> None:
    from quest_app.evidence import ResultRejectedError, store_result

    document = {"run_id": "big-run", "output_excerpt": "x" * (MAX_VALIDATION_RESULT_BYTES + 1)}
    with pytest.raises(ResultRejectedError, match="byte limit"):
        store_result(config, VERIFIED, document)
    package = config.participant_root / VERIFIED.removeprefix("participant/")
    assert not (package / "validation" / "big-run.json").exists()


# --- E1: the review archive ------------------------------------------------------------


@pytest.mark.parametrize("kind", ["link_outside", "dangling", "directory"])
def test_the_review_archive_is_not_written_through_a_link(
    config: AppConfig, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    """The archive of a superseded decision was a plain `write_text` to a predictable name."""
    from quest_app import review

    class Frozen(datetime):
        @classmethod
        def now(cls, tz: Any = None) -> Frozen:  # type: ignore[override]
            return cls(2026, 9, 24, 12, 0, 0, tzinfo=timezone.utc)

    monkeypatch.setattr(review, "datetime", Frozen)
    package = config.participant_write_path(VERIFIED)
    current = package / "review.yaml"
    original = current.read_bytes()
    outside = tmp_path / "outside.yaml"
    outside.write_text("not the participant's\n")
    make(package / "review-20260924120000.yaml", kind, outside)

    document = yaml.safe_load(original)
    with pytest.raises(StoreError, match="link or special file"):
        review._write_yaml(config, current, document, SchemaSet(config.schemas_root), "review")

    assert outside.read_text() == "not the participant's\n"
    assert not (tmp_path / "nothing-here").exists()
    assert current.read_bytes() == original, "a refused archive must not replace the decision"


# --- E2: validation results are read bounded -------------------------------------------


@pytest.mark.parametrize("kind", ["fifo", "device", "too_large", "link_outside"])
def test_a_validation_result_that_is_not_a_small_ordinary_file_is_reported_not_read(
    config: AppConfig, tmp_path: Path, kind: str
) -> None:
    """A FIFO hung `validate`, `build` and the service; `/dev/zero` got the process killed.

    A link to an ordinary file is refused too: the runner writes these itself, never as links.
    """
    package = config.participant_root / VERIFIED.removeprefix("participant/")
    target = package / RESULT
    outside = tmp_path / "result.json"
    outside.write_bytes(target.read_bytes())
    if kind == "too_large":
        target.write_text('{"pad": "' + "x" * MAX_VALIDATION_RESULT_BYTES + '"}')
    else:
        make(target, kind, outside)

    report = ProblemReport()
    assert load_world(config, report) is None
    assert problems(report, "validation.not_a_regular_file"), report.to_text()


# --- E3: review records ----------------------------------------------------------------


@pytest.mark.parametrize("name", ["reviewer-notes.yaml", "review-notes.yaml", "reviews.yaml"])
def test_a_file_that_is_not_a_review_record_is_read_by_neither_the_loader_nor_the_page(
    config: AppConfig, name: str
) -> None:
    """`review_history` read `review*.yaml` and the loader checked `review-*.yaml`, so a
    broken `reviewer-notes.yaml` passed `validate` and then crashed `build`."""
    from quest_app.cli import main
    from quest_app.progress import load_participant_state
    from quest_app.review import review_history

    package = config.participant_root / VERIFIED.removeprefix("participant/")
    (package / name).write_text("a: [unclosed\n")

    report = ProblemReport()
    state = load_participant_state(config, SchemaSet(config.schemas_root), report)
    assert state is not None
    attempt = state.progress.attempt_for(QUEST)
    assert attempt is not None
    history = review_history(config, attempt)
    assert [item["review_id"] for item in history] == ["base-camp-review-001"]
    assert main(["build", "--repo-root", str(config.repo_root)]) == 0


@pytest.mark.parametrize("kind", ["bad_yaml", "fifo", "device", "too_large"])
@pytest.mark.parametrize(
    "name", ["review-20260101000000.yaml", "review-20260101000000-abcdef.yaml", "review.yaml"]
)
def test_a_damaged_review_record_is_a_load_problem_and_never_stops_the_page(
    config: AppConfig, tmp_path: Path, name: str, kind: str
) -> None:
    """The same files, read the same bounded way: reported at load, left out of the page."""
    from quest_app.progress import load_participant_state
    from quest_app.review import review_history

    package = config.participant_root / VERIFIED.removeprefix("participant/")
    target = package / name
    state = load_participant_state(config, SchemaSet(config.schemas_root), ProblemReport())
    assert state is not None
    attempt = state.progress.attempt_for(QUEST)
    assert attempt is not None
    if kind == "bad_yaml":
        target.write_text("a: [unclosed\n")
    elif kind == "too_large":
        target.write_text("x: 1\n" + "# pad\n" * (MAX_STATE_BYTES // 6 + 10))
    else:
        make(target, kind, tmp_path / "x")

    history = review_history(config, attempt)
    assert all(item.get("review_id") for item in history)
    report = ProblemReport()
    assert load_world(config, report) is None
    assert any(problem.source.endswith(name) for problem in report.errors), report.to_text()


@pytest.mark.parametrize("kind", ["bad_yaml", "fifo", "device", "too_large"])
def test_a_damaged_submission_is_none_for_a_page_and_an_error_for_a_decision(
    config: AppConfig, tmp_path: Path, kind: str
) -> None:
    """`read_submission` read unbounded and parsed unguarded. A page gets `None`; a decision
    gets a refusal, because "could not read it" must not pass as "nothing changed"."""
    from quest_app.progress import load_participant_state
    from quest_app.review import DamagedRecordError, changes_since_submission, read_submission

    state = load_participant_state(config, SchemaSet(config.schemas_root), ProblemReport())
    assert state is not None
    attempt = state.progress.attempt_for(QUEST)
    assert attempt is not None
    target = config.participant_root / VERIFIED.removeprefix("participant/") / "submission.yaml"
    if kind == "bad_yaml":
        target.write_text("a: [unclosed\n")
    elif kind == "too_large":
        target.write_text("x: 1\n" + "# pad\n" * (MAX_STATE_BYTES // 6 + 10))
    else:
        make(target, kind, tmp_path / "x")

    assert read_submission(config, attempt) is None
    assert changes_since_submission(config, attempt) == []
    with pytest.raises(DamagedRecordError):
        read_submission(config, attempt, strict=True)
    with pytest.raises(DamagedRecordError):
        changes_since_submission(config, attempt, strict=True)


# --- E8: evidence size and hashing -----------------------------------------------------


def _old_digest(chunks: list[bytes]) -> str:
    """The digest as it was computed before files were streamed, for compatibility."""
    import hashlib

    hasher = hashlib.sha256()
    for chunk in chunks:
        hasher.update(str(len(chunk)).encode("ascii"))
        hasher.update(b"\0")
        hasher.update(chunk)
    return "sha256:" + hasher.hexdigest()


def test_hashing_streams_files_and_keeps_every_recorded_digest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No file is held whole in memory, and a digest recorded before still matches."""
    from quest_app import hashing
    from quest_app.hashing import hash_directory, hash_file

    (tmp_path / "logs").mkdir()
    big = os.urandom(3 * 1024 * 1024 + 17)
    (tmp_path / "logs" / "run.log").write_bytes(big)
    (tmp_path / "PROOF.md").write_text("# Proof\n")
    expected_tree = _old_digest([b"PROOF.md", b"# Proof\n", b"logs", b"dir", b"logs/run.log", big])
    expected_file = _old_digest([big])

    def refuse(self: Path) -> bytes:
        raise AssertionError(f"{self.name} was read whole")

    monkeypatch.setattr(Path, "read_bytes", refuse)
    reads: list[int] = []
    real_open = os.fdopen

    def spy(fd: int, *args: Any, **kwargs: Any) -> Any:
        stream = real_open(fd, *args, **kwargs)
        real_read = stream.read

        def read(size: int = -1) -> bytes:
            reads.append(size)
            return real_read(size)

        stream.read = read  # type: ignore[method-assign]
        return stream

    monkeypatch.setattr(hashing.os, "fdopen", spy)
    assert hash_directory(tmp_path) == expected_tree
    assert hash_file(tmp_path / "logs" / "run.log") == expected_file
    assert reads and max(reads) <= 1024 * 1024 and -1 not in reads


def test_an_evidence_file_over_the_ceiling_is_a_finding_that_blocks_submission(
    config: AppConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A 135 MB log made every build take a minute; now it is not scanned, and says so."""
    from quest_app import evidence
    from quest_app.review import blocking, readiness_problems

    package = config.participant_root / READY.removeprefix("participant/")
    (package / "logs").mkdir(exist_ok=True)
    (package / "logs" / "huge.log").write_bytes(b"x" * (MAX_EVIDENCE_FILE_BYTES + 1))
    (package / "logs" / "at-the-limit.log").write_bytes(b"y" * MAX_EVIDENCE_FILE_BYTES)

    scanned: list[int] = []
    real_scan = evidence.scan_text

    def spy(text: str) -> Any:
        scanned.append(len(text))
        return real_scan(text)

    monkeypatch.setattr(evidence, "scan_text", spy)
    findings = evidence.scan_evidence(config, READY)
    assert [f.path for f in findings] == [f"{READY}/logs/huge.log"]
    assert findings[0].description == evidence.OVERSIZE_DESCRIPTION
    assert max(scanned) == MAX_EVIDENCE_FILE_BYTES, "a file at the ceiling is still scanned"

    report = ProblemReport()
    world = load_world(config, report)
    assert world is not None and world.participant is not None, report.to_text()
    attempt = world.participant.progress.attempt_for("jira-read-assigned-stories")
    assert attempt is not None
    quest = world.content.quests["jira-read-assigned-stories"]
    blockers = blocking(readiness_problems(quest, attempt, world.participant, config))
    assert any("huge.log" in b and "Trim it" in b for b in blockers), blockers
    assert not any("secret-like" in b for b in blockers), "a big file is not a secret"


def test_a_proof_document_over_the_ceiling_is_not_rendered(config: AppConfig) -> None:
    from quest_app.build import _proof_document

    package = config.participant_root / READY.removeprefix("participant/")
    report = ProblemReport()
    world = load_world(config, report)
    assert world is not None, report.to_text()
    assert _proof_document(world, READY) is not None
    (package / "PROOF.md").write_text("# Proof\n" + "x" * MAX_EVIDENCE_FILE_BYTES)
    assert _proof_document(world, READY) is None


@pytest.mark.parametrize("kind", ["fifo", "directory"])
def test_a_validator_cannot_write_into_a_special_file(tmp_path: Path, kind: str) -> None:
    """`Workspace.write_text` resolved links but opened a FIFO for writing, which blocks."""
    from quest_app.validator_runner import Workspace, WorkspaceError

    root = tmp_path / "participant"
    root.mkdir()
    make(root / "out.txt", kind, tmp_path / "x")
    workspace = Workspace(
        read_roots=(root,),
        write_roots=(root,),
        repo_root=tmp_path,
        participant_root=root,
        parameters={},
    )
    with pytest.raises(WorkspaceError, match="ordinary file"):
        workspace.write_text("participant/out.txt", "result\n")


def test_a_validator_still_writes_and_replaces_an_ordinary_file(tmp_path: Path) -> None:
    from quest_app.validator_runner import Workspace

    root = tmp_path / "participant"
    (root / "logs").mkdir(parents=True)
    (root / "logs" / "out.txt").write_text("a much longer earlier result\n")
    workspace = Workspace(
        read_roots=(root,),
        write_roots=(root,),
        repo_root=tmp_path,
        participant_root=root,
        parameters={},
    )
    workspace.write_text("participant/logs/out.txt", "short\n")
    workspace.write_text("participant/logs/new/made.txt", "made\n")
    assert (root / "logs" / "out.txt").read_text() == "short\n"
    assert (root / "logs" / "new" / "made.txt").read_text() == "made\n"
