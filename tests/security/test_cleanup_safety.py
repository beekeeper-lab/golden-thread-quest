"""`make clean` must remove generated output and nothing a participant owns.

This is the test the plan asks for by name: a cleanup that quietly eats
`participant/evidence` would destroy work no rebuild can recreate.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

import clean

PARTICIPANT_SHAPED = [
    "participant",
    "participant/evidence",
    "participant/progress.yaml",
    "fixtures",
    "fixtures/participant/evidence",
]

OUTSIDE_REPO = ["..", "../..", "/etc", "/", "~", "../other-project"]

REPOSITORY_SOURCE = [
    "content",
    "schemas",
    "templates",
    "docs",
    "quest_app",
    "validators",
    "tests",
    ".git",
]


@pytest.mark.parametrize("name", PARTICIPANT_SHAPED)
def test_participant_paths_are_refused(name: str) -> None:
    with pytest.raises(clean.UnsafeTargetError):
        clean.resolve_target(name)


@pytest.mark.parametrize("name", OUTSIDE_REPO)
def test_paths_outside_the_repository_are_refused(name: str) -> None:
    with pytest.raises(clean.UnsafeTargetError):
        clean.resolve_target(name)


@pytest.mark.parametrize("name", REPOSITORY_SOURCE)
def test_program_owned_source_is_refused(name: str) -> None:
    with pytest.raises(clean.UnsafeTargetError):
        clean.resolve_target(name)


def test_every_declared_removable_target_is_safe() -> None:
    """The allowlist itself is checked, so adding an unsafe entry fails here."""
    for name in clean.REMOVABLE:
        resolved = clean.resolve_target(name)
        assert clean.REPO_ROOT in resolved.parents


def test_removable_and_protected_lists_do_not_overlap() -> None:
    first_parts = {Path(name).parts[0] for name in clean.REMOVABLE}
    assert first_parts.isdisjoint(clean.PROTECTED)


def test_plan_lists_only_existing_removable_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A dry-run plan never names something that is not there, so the output is trustworthy."""
    monkeypatch.setattr(clean, "REPO_ROOT", tmp_path)
    (tmp_path / "generated").mkdir()
    (tmp_path / "participant" / "evidence").mkdir(parents=True)
    (tmp_path / "participant" / "progress.yaml").write_text("schema_version: 1\n")

    targets = clean.plan()

    assert targets == [tmp_path / "generated"]
    assert (tmp_path / "participant" / "progress.yaml").exists()


def test_apply_removes_generated_and_leaves_participant_intact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(clean, "REPO_ROOT", tmp_path)
    generated = tmp_path / "generated" / "quests" / "x"
    generated.mkdir(parents=True)
    (generated / "index.html").write_text("<!doctype html>")
    evidence = tmp_path / "participant" / "evidence" / "quest" / "attempt-001"
    evidence.mkdir(parents=True)
    (evidence / "PROOF.md").write_text("# Proof\n")

    assert clean.main(["--apply"]) == 0

    assert not (tmp_path / "generated").exists()
    assert (evidence / "PROOF.md").read_text() == "# Proof\n"


def test_symlinked_generated_directory_is_unlinked_not_followed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A symlink named `generated` must not become a path to delete someone else's files."""
    monkeypatch.setattr(clean, "REPO_ROOT", tmp_path)
    outside = tmp_path.parent / "outside-target"
    outside.mkdir()
    (outside / "keep.txt").write_text("keep me")
    (tmp_path / "generated").symlink_to(outside, target_is_directory=True)

    # resolve_target() resolves symlinks, so a link pointing outside the repository is refused
    # outright rather than followed.
    with pytest.raises(clean.UnsafeTargetError):
        clean.resolve_target("generated")
    assert (outside / "keep.txt").exists()
