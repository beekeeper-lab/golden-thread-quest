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


def test_symlink_inside_the_repository_is_refused_not_followed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`generated` as a link to a program-owned directory must not delete that directory.

    The Stage 1 audit did exactly this: `ln -s prototype generated && clean.py --apply`
    removed `prototype/` and everything in it, because the target was resolved before it was
    screened and `is_symlink()` was then asked of the already-resolved path.
    """
    monkeypatch.setattr(clean, "REPO_ROOT", tmp_path)
    real = tmp_path / "prototype"
    real.mkdir()
    (real / "index.html").write_text("<!doctype html>")
    (tmp_path / "generated").symlink_to(real, target_is_directory=True)

    with pytest.raises(clean.UnsafeTargetError, match="symbolic link"):
        clean.resolve_target("generated")

    assert clean.main(["--apply"]) == 0
    assert (real / "index.html").exists()
    assert (tmp_path / "generated").is_symlink(), "the link itself is left alone, not followed"


def test_symlink_pointing_outside_the_repository_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(clean, "REPO_ROOT", tmp_path)
    outside = tmp_path.parent / "outside-target"
    outside.mkdir(exist_ok=True)
    (outside / "keep.txt").write_text("keep me")
    (tmp_path / "generated").symlink_to(outside, target_is_directory=True)

    with pytest.raises(clean.UnsafeTargetError):
        clean.resolve_target("generated")
    assert (outside / "keep.txt").exists()


@pytest.mark.parametrize(
    "escape",
    [
        "generated/../README.md",
        "local-data/../.github",
        ".coverage/../Makefile",
        "generated/../../etc",
    ],
)
def test_parent_directory_escapes_are_refused(escape: str) -> None:
    """Resolving first and screening the result let these through; they are rejected now."""
    with pytest.raises(clean.UnsafeTargetError):
        clean.resolve_target(escape)


def test_protected_names_are_compared_case_insensitively() -> None:
    """A case-sensitive check is a hole on macOS, where `Participant/` is `participant/`."""
    with pytest.raises(clean.UnsafeTargetError):
        clean.resolve_target("Participant/evidence")


def test_an_unsafe_entry_added_to_removable_is_still_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`REMOVABLE` is data, so the guard must not depend on it being written correctly."""
    monkeypatch.setattr(clean, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(clean, "REMOVABLE", ("generated", "participant", "generated/../docs"))
    (tmp_path / "participant" / "evidence").mkdir(parents=True)
    (tmp_path / "participant" / "evidence" / "PROOF.md").write_text("# Proof\n")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "keep.md").write_text("keep")

    assert clean.main(["--apply"]) == 0

    assert (tmp_path / "participant" / "evidence" / "PROOF.md").exists()
    assert (tmp_path / "docs" / "keep.md").exists()
