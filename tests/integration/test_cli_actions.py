"""Every state transition must work with no browser anywhere in the picture.

Participants on the installed Cowork app have no terminal they type into and no way to
reach a loopback server inside the sandbox VM. The CLI action layer is the only path to
changing state there, so it is tested as a first-class caller rather than a convenience:
the same guards, the same refusals, the same messages.
"""

from __future__ import annotations

import re
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


def _declared_validators() -> dict[str, tuple[str, ...]]:
    """Every quest in the catalogue and the validators it declares.

    Derived from the content tree rather than a hand-written list, so a quest authored
    tomorrow is covered by the two tests below without anyone remembering to add it.
    """
    quests: dict[str, tuple[str, ...]] = {}
    for path in sorted((ROOT / "content" / "quests").glob("*/*.md")):
        text = path.read_text()
        if not text.startswith("---\n"):
            continue
        front = yaml.safe_load(text.split("\n---\n", 1)[0].removeprefix("---\n"))
        quests[front["id"]] = tuple(front.get("validators") or ())
    return quests


QUESTS = _declared_validators()
WITHOUT_VALIDATORS = sorted(q for q, v in QUESTS.items() if not v)
WITH_VALIDATORS = sorted(q for q, v in QUESTS.items() if v)


def test_the_catalogue_contains_both_kinds_of_quest() -> None:
    """Both tests below are vacuous if the content tree stops exercising a branch."""
    assert WITHOUT_VALIDATORS, "no quest declares zero validators; the guard's early exit is dead"
    assert WITH_VALIDATORS, "no quest declares a validator; the guard is never exercised"


@pytest.mark.parametrize("quest", WITHOUT_VALIDATORS)
def test_a_quest_declaring_no_validators_can_still_reach_submitted(
    participant: Path, quest: str
) -> None:
    """The guard on `mark-locally-validated` must not strand a quest that asks for nothing.

    `validators/registry.yaml` is program-owned, so a quest authored under a content-only
    scope has no way to declare one. If the guard demanded a qualifying run regardless,
    every such quest would be a dead end at `evidence_ready`.
    """
    for action in ("start-quest", "mark-evidence-ready", "mark-locally-validated"):
        result = run(participant, action, "--quest", quest)
        assert result.returncode == 0, f"{action} on {quest}: {result.stderr}"
    result = run(participant, "submit-for-review", "--quest", quest)
    assert result.returncode == 0, result.stderr
    assert "submitted" in (participant / "progress.yaml").read_text()


@pytest.mark.parametrize("quest", WITH_VALIDATORS)
def test_a_quest_declaring_a_validator_is_refused_without_a_qualifying_run(
    participant: Path, quest: str
) -> None:
    """The other half of the same guard: the early exit must not have widened into a hole."""
    run(participant, "start-quest", "--quest", quest)
    run(participant, "mark-evidence-ready", "--quest", quest)
    result = run(participant, "mark-locally-validated", "--quest", quest)
    assert result.returncode != 0, "a validator quest reached locally_validated with no result"
    for validator in QUESTS[quest]:
        assert validator in result.stderr, "the refusal must name the check that is missing"


# --- The reviewer's path, which on a browserless surface is the only one -------------

REVIEWED = "trello-read-board"
STATEMENT = "I read the board export and both runs against every numbered criterion."


def submitted(participant: Path, quest: str = REVIEWED) -> None:
    for action in (
        "start-quest",
        "mark-evidence-ready",
        "mark-locally-validated",
        "submit-for-review",
    ):
        result = run(participant, action, "--quest", quest)
        assert result.returncode == 0, f"{action}: {result.stderr}"


def test_the_cli_and_the_reviewer_module_share_one_decision_vocabulary() -> None:
    """A second copy of the vocabulary is a second thing to drift, and it did drift.

    The CLI shipped accepting `approve` and `request-changes`; `record_decision` accepts
    `approved`, `needs_changes` and `rejected`. Nothing translated, so every value argparse
    allowed was refused one layer down and no decision could be recorded without a browser.
    """
    from quest_app.models import Decision

    listed = run(Path("/nonexistent"), "--help").stdout
    for member in Decision:
        assert member.value in listed, f"argparse does not offer {member.value!r}"
    for retired in ("approve", "request-changes"):
        rejected = run(
            Path("/nonexistent"), "record-review", "--quest", REVIEWED, "--decision", retired
        )
        assert rejected.returncode != 0, f"{retired!r} is accepted and nothing acts on it"
        assert "invalid choice" in rejected.stderr


def test_the_review_form_posts_the_same_decision_values() -> None:
    """The browser is the other caller of the same vocabulary."""
    import re

    from quest_app.models import Decision

    template = (ROOT / "templates" / "pages" / "review.html.j2").read_text()
    form = template.split('name="decision"', 1)[1].split("</select>", 1)[0]
    posted = set(re.findall(r'<option value="([^"]+)"', form))
    assert posted == {member.value for member in Decision}


def test_a_reviewer_can_approve_without_a_browser(participant: Path) -> None:
    """The flow the Cowork surface depends on, asserted end to end."""
    submitted(participant)
    result = run(
        participant,
        "record-review",
        "--quest",
        REVIEWED,
        "--decision",
        "approved",
        "--reviewer",
        "A Reviewer",
        "--statement",
        STATEMENT,
    )
    assert result.returncode == 0, result.stderr
    assert "verified" in (participant / "progress.yaml").read_text()


def test_approval_without_a_statement_is_refused(participant: Path) -> None:
    submitted(participant)
    result = run(participant, "record-review", "--quest", REVIEWED, "--decision", "approved")
    assert result.returncode != 0
    assert "verification statement" in result.stderr
    assert "verified" not in (participant / "progress.yaml").read_text()


def test_requesting_changes_needs_a_finding_and_takes_a_well_formed_one(
    participant: Path,
) -> None:
    submitted(participant)
    bare = run(participant, "record-review", "--quest", REVIEWED, "--decision", "needs_changes")
    assert bare.returncode != 0
    assert "at least one finding" in bare.stderr

    result = run(
        participant,
        "record-review",
        "--quest",
        REVIEWED,
        "--decision",
        "needs_changes",
        "--finding",
        "high:The second run is missing:logs/second-run.txt is absent",
    )
    assert result.returncode == 0, result.stderr
    assert "needs_changes" in (participant / "progress.yaml").read_text()


def test_a_malformed_finding_is_refused_rather_than_dropped(participant: Path) -> None:
    """Dropping it in silence made the next refusal name the wrong problem."""
    submitted(participant)
    result = run(
        participant,
        "record-review",
        "--quest",
        REVIEWED,
        "--decision",
        "needs_changes",
        "--finding",
        "high:no evidence",
    )
    assert result.returncode != 0
    assert "severity:summary:evidence" in result.stderr
    assert "at least one finding" not in result.stderr


def test_approving_changed_evidence_needs_the_acknowledgement(participant: Path) -> None:
    """The browser form has this checkbox; without the flag the CLI reviewer was stuck."""
    submitted(participant)
    proof = next((participant / "evidence" / REVIEWED).glob("*/PROOF.md"))
    proof.write_text(proof.read_text() + "\nAdded after submitting.\n")

    refused = run(
        participant,
        "record-review",
        "--quest",
        REVIEWED,
        "--decision",
        "approved",
        "--statement",
        STATEMENT,
    )
    assert refused.returncode != 0
    assert "changed" in refused.stderr

    result = run(
        participant,
        "record-review",
        "--quest",
        REVIEWED,
        "--decision",
        "approved",
        "--statement",
        STATEMENT,
        "--acknowledge-changed-evidence",
    )
    assert result.returncode == 0, result.stderr
    assert "verified" in (participant / "progress.yaml").read_text()


# --- The installed commands, not the module path ------------------------------------


def test_the_commands_the_guides_name_are_actually_installed() -> None:
    """Every test here runs `python -m quest_app.cli`, so none of them can catch this.

    `quest-app` went unregistered for a release while the user guide and the reviewer guide
    named it thirteen times, including the whole browserless flow the Cowork surface
    depends on. A participant following the guide would find the command did not exist.
    """
    try:
        import tomllib
    except ModuleNotFoundError:  # Python 3.10, the declared floor, has no tomllib.
        import tomli as tomllib  # type: ignore[no-redef]

    named = set()
    for document in ("docs/USER-GUIDE.md", "docs/guides/REVIEWER.md"):
        # A command, not a placeholder: `quest-app action …` counts, `<quest-id>` does not.
        named |= set(re.findall(r"(?<![<\w-])(quest-[a-z]+)(?=\s)", (ROOT / document).read_text()))

    registered = set(tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["scripts"])
    assert named <= registered, f"the guides name commands nothing installs: {named - registered}"


def test_the_installed_command_runs(tmp_path: Path) -> None:
    """A console script can be registered and still be broken on its entry point."""
    executable = Path(sys.executable).parent / "quest-app"
    if not executable.exists():
        pytest.skip("run `uv pip install -e .` to test the installed command")
    result = subprocess.run(
        [str(executable), "action", "--list"], cwd=ROOT, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert set(result.stdout.split()) == set(MUTATING_ACTIONS)
