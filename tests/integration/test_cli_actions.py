"""Every state transition must work with no browser anywhere in the picture.

Participants on the installed Cowork app have no terminal they type into and no way to
reach a loopback server inside the sandbox VM. The CLI action layer is the only path to
changing state there, so it is tested as a first-class caller rather than a convenience:
the same guards, the same refusals, the same messages.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from quest_app.actions import MUTATING_ACTIONS

ROOT = Path(__file__).resolve().parent.parent.parent
QUEST = "base-camp-repository-safety"


def run(participant: Path, *args: str) -> subprocess.CompletedProcess[str]:
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
def participant(tmp_path: Path) -> Path:
    """A participant who has never run anything. The state most defects hide in."""
    return tmp_path / "participant"


def test_a_participant_with_nothing_can_start(participant: Path) -> None:
    result = run(participant, "start-quest", "--quest", QUEST)
    assert result.returncode == 0, result.stderr
    progress = yaml.safe_load((participant / "progress.yaml").read_text())
    states = (
        [a["state"] for q in progress["quests"] for a in q.get("attempts", [])]
        if isinstance(progress.get("quests"), list)
        else []
    )
    assert "in_progress" in str(progress) or "in_progress" in states
    assert (participant / "ACTIVITY.md").exists(), "the change must be recorded for the reader"


def test_an_illegal_transition_is_refused_with_the_legal_states_named(participant: Path) -> None:
    run(participant, "start-quest", "--quest", QUEST)
    result = run(participant, "mark-locally-validated", "--quest", QUEST)
    assert result.returncode != 0
    assert "evidence_ready" in result.stderr, "the refusal must name where it is legal from"


def test_an_unknown_action_is_refused_before_anything_is_loaded(participant: Path) -> None:
    result = run(participant, "delete-everything", "--quest", QUEST)
    assert result.returncode != 0
    assert "not an action" in result.stderr
    assert not participant.exists(), "a refused action must not create participant state"


def test_the_cli_and_the_service_share_one_allowlist() -> None:
    """A second copy of the allowlist is a second thing to drift."""
    from quest_app import serve

    assert serve.MUTATING_ACTIONS is MUTATING_ACTIONS


def test_listing_actions_names_every_transition(participant: Path) -> None:
    result = run(participant, "--list")
    assert result.returncode == 0
    listed = set(result.stdout.split())
    assert listed == set(MUTATING_ACTIONS)


def test_no_cli_action_can_produce_verified(participant: Path) -> None:
    """The product's central rule, asserted against the surface that bypasses the browser."""
    run(participant, "start-quest", "--quest", QUEST)
    for action in sorted(MUTATING_ACTIONS - {"record-review", "rebuild"}):
        run(participant, action, "--quest", QUEST)
    written = (
        (participant / "progress.yaml").read_text()
        if (participant / "progress.yaml").exists()
        else ""
    )
    assert "verified" not in written, "a participant reached verified without a reviewer"
