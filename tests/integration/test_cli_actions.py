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
from quest_app.actions import CONFIRMATIONS, MUTATING_ACTIONS

ROOT = Path(__file__).resolve().parent.parent.parent
QUEST = "base-camp-repository-safety"


def run(participant: Path, *args: str, confirm: bool = True) -> subprocess.CompletedProcess[str]:
    # An action that carries a confirmation is refused without one, on every surface
    # (ADR-033). A test about something else says it means it, exactly as the browser form
    # does. `confirm=False` is the gate itself, tested below.
    needs = bool(args) and args[0] in CONFIRMATIONS and "--confirm" not in args
    confirmation = ["--confirm"] if confirm and needs else []
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "quest_app.cli",
            "action",
            *args,
            *confirmation,
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
    assert state_of(participant, QUEST) != "verified", (
        "a participant reached verified without a reviewer"
    )


def _front_matter() -> dict[str, dict[str, object]]:
    """Every quest in the catalogue, by id, with the front matter this module reasons about.

    Derived from the content tree rather than a hand-written list, so a quest authored
    tomorrow is covered by the tests below without anyone remembering to add it.
    """
    quests: dict[str, dict[str, object]] = {}
    for path in sorted((ROOT / "content" / "quests").glob("*/*.md")):
        text = path.read_text()
        if not text.startswith("---\n"):
            continue
        front = yaml.safe_load(text.split("\n---\n", 1)[0].removeprefix("---\n"))
        quests[front["id"]] = front
    return quests


FRONT_MATTER = _front_matter()
QUESTS = {q: tuple(f.get("validators") or ()) for q, f in FRONT_MATTER.items()}
PREREQUISITES = {q: tuple(f.get("prerequisites") or ()) for q, f in FRONT_MATTER.items()}
WITHOUT_VALIDATORS = sorted(q for q, v in QUESTS.items() if not v)
WITH_VALIDATORS = sorted(q for q, v in QUESTS.items() if v)


def state_of(participant: Path, quest: str) -> str | None:
    """The recorded state of one quest, not of the whole file.

    `unlock` carries prerequisites to verified through the reviewer, so asserting on the
    word "verified" anywhere in `progress.yaml` would now pass or fail for the wrong quest.
    """
    path = participant / "progress.yaml"
    if not path.exists():
        return None
    data = yaml.safe_load(path.read_text()) or {}
    for attempt in data.get("attempts", []):
        if attempt.get("quest_id") == quest:
            return str(attempt.get("state"))
    return None


def unlock(participant: Path, quest: str) -> None:
    """Carry every prerequisite of `quest` to verified, the only way that is possible.

    A locked quest is refused on every surface since round 4, so a test that starts a quest
    three links down the chain has to walk the chain. It walks it through the product's own
    commands, reviewer approval included: there is no test-only door into `verified`, and
    adding one would delete the guarantee these tests exist to hold.
    """
    for prerequisite in PREREQUISITES.get(quest, ()):
        unlock(participant, prerequisite)
        for action in ("start-quest", "mark-evidence-ready", "submit-for-review"):
            result = run(participant, action, "--quest", prerequisite)
            assert result.returncode == 0, f"{prerequisite} {action}: {result.stderr}"
        result = run(
            participant,
            "record-review",
            "--quest",
            prerequisite,
            "--decision",
            "approved",
            "--reviewer",
            "A Reviewer",
            "--statement",
            "Read the evidence and confirmed it.",
        )
        assert result.returncode == 0, f"{prerequisite} record-review: {result.stderr}"


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
    unlock(participant, quest)
    for action in ("start-quest", "mark-evidence-ready", "mark-locally-validated"):
        result = run(participant, action, "--quest", quest)
        assert result.returncode == 0, f"{action} on {quest}: {result.stderr}"
    result = run(participant, "submit-for-review", "--quest", quest)
    assert result.returncode == 0, result.stderr
    assert "submitted" in (participant / "progress.yaml").read_text()


def test_four_processes_starting_the_same_quest_produce_one_attempt(participant: Path) -> None:
    """The service's lock is held inside one process; a second process cannot see it.

    Run concurrently, four `start-quest` calls each read the same progress file, each
    decided it was the first, and three attempts and four activity lines survived. The
    outcome was not deterministic — it reproduced in three runs out of six — which is what
    a race looks like from the outside.
    """
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(
            pool.map(lambda _: run(participant, "start-quest", "--quest", QUEST), range(4))
        )

    data = yaml.safe_load((participant / "progress.yaml").read_text())
    attempts = [a for a in data["attempts"] if a["quest_id"] == QUEST]
    activity = (participant / "ACTIVITY.md").read_text()

    assert len(attempts) == 1, f"{len(attempts)} attempts from four concurrent starts"
    assert activity.count("Started") == 1, "one start, one line"
    assert sum(r.returncode == 0 for r in results) == 1, "only the first start can succeed"


LOCKED = sorted(q for q, prerequisites in PREREQUISITES.items() if prerequisites)


def test_the_catalogue_contains_a_locked_quest() -> None:
    """The test below is vacuous if every quest is available from a standing start."""
    assert LOCKED, "no quest declares a prerequisite; the lock guard is never exercised"


@pytest.mark.parametrize("quest", LOCKED)
def test_a_locked_quest_is_refused_here_too(participant: Path, quest: str) -> None:
    """The browser greys out Start on a locked quest. Nothing stopped this surface.

    Prerequisites were computed for display and enforced nowhere, so a participant with
    nothing verified could start a quest three links down the chain and carry it to
    `verified`. Enforcement belongs in the action layer both callers share, which is why
    this test and the service's own are the same assertion from two directions.
    """
    result = run(participant, "start-quest", "--quest", quest)

    assert result.returncode != 0, "a locked quest started with no prerequisite verified"
    assert "locked" in result.stderr
    assert state_of(participant, quest) is None, "a refused start must record nothing"

    unlock(participant, quest)
    assert run(participant, "start-quest", "--quest", quest).returncode == 0, (
        "the same quest must start once its prerequisites are verified"
    )


@pytest.mark.parametrize("quest", WITH_VALIDATORS)
def test_a_quest_declaring_a_validator_is_refused_without_a_qualifying_run(
    participant: Path, quest: str
) -> None:
    """The other half of the same guard: the early exit must not have widened into a hole."""
    unlock(participant, quest)
    run(participant, "start-quest", "--quest", quest)
    run(participant, "mark-evidence-ready", "--quest", quest)
    result = run(participant, "mark-locally-validated", "--quest", quest)
    assert result.returncode != 0, "a validator quest reached locally_validated with no result"
    for validator in QUESTS[quest]:
        assert validator in result.stderr, "the refusal must name the check that is missing"


def test_an_unrun_declared_check_is_told_to_the_participant_and_the_reviewer(
    participant: Path,
) -> None:
    """The advisory existed and reached nobody.

    `readiness_problems` built it on every submission, `create_submission` kept only the
    blocking half, and nothing else called it. The participant was not told before
    submitting and the reviewer was not told after; a reviewer could infer it from an empty
    result list, which reads the same as a quest that declares no checks at all.
    """
    quest = WITH_VALIDATORS[0]
    unlock(participant, quest)
    for action in ("start-quest", "mark-evidence-ready"):
        assert run(participant, action, "--quest", quest).returncode == 0

    result = run(participant, "submit-for-review", "--quest", quest)
    assert result.returncode == 0, result.stderr
    assert "advisory:" in result.stdout, "the participant submitted without being told"
    for validator in QUESTS[quest]:
        assert validator in result.stdout

    data = yaml.safe_load((participant / "progress.yaml").read_text())
    evidence = next(a["evidence_path"] for a in data["attempts"] if a["quest_id"] == quest)
    submission = yaml.safe_load((participant.parent / evidence / "submission.yaml").read_text())
    assert submission["advisories"], "the record the reviewer reads carries nothing"
    assert any(v in " ".join(submission["advisories"]) for v in QUESTS[quest])


# --- The reviewer's path, which on a browserless surface is the only one -------------

REVIEWED = "trello-read-board"
STATEMENT = "I read the board export and both runs against every numbered criterion."


def submitted(participant: Path, quest: str = REVIEWED) -> None:
    unlock(participant, quest)
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
    assert state_of(participant, REVIEWED) == "verified"


def test_approval_without_a_statement_is_refused(participant: Path) -> None:
    submitted(participant)
    result = run(participant, "record-review", "--quest", REVIEWED, "--decision", "approved")
    assert result.returncode != 0
    assert "verification statement" in result.stderr
    assert state_of(participant, REVIEWED) != "verified"


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
    assert state_of(participant, REVIEWED) == "verified"


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


# --- The confirmation, on the surface that has no checkbox ---------------------------


@pytest.mark.parametrize("action", sorted(CONFIRMATIONS))
def test_a_confirmed_action_is_refused_without_the_confirmation(
    participant: Path, action: str
) -> None:
    """C21 on the CLI. The checkbox is the browser's rule; this is the application's.

    Until round 8 the gate lived in the form handler alone, so this command performed the
    action with nothing saying the caller meant it — `record-review` included, which is the
    one action that produces verified completion and verified XP.
    """
    unlock(participant, QUEST)
    result = run(participant, action, "--quest", QUEST, confirm=False)

    assert result.returncode != 0
    assert CONFIRMATIONS[action].split(".")[0][:24] in result.stderr, result.stderr
    progress = participant / "progress.yaml"
    assert not progress.exists() or "verified" not in progress.read_text()


def test_an_approval_without_the_confirmation_records_nothing(participant: Path) -> None:
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
        confirm=False,
    )

    assert result.returncode != 0
    assert "confirm it" in result.stderr
    assert state_of(participant, REVIEWED) != "verified"


def test_a_broken_template_after_the_change_is_an_advisory_not_a_traceback(
    config,  # type: ignore[no-untyped-def]
) -> None:
    """The rebuild runs after the state is written, so its failure cannot undo anything.

    `_rebuild` caught `OSError`. A broken template raises `TemplateSyntaxError`, which went
    through the CLI as a traceback carrying absolute paths — after the transition had
    landed. The participant read a crash and their retry was refused, because the attempt
    had in fact moved.
    """
    template = config.repo_root / "templates" / "pages" / "evidence.html.j2"
    template.write_text(template.read_text() + "\n{% for x in %}\n")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "quest_app.cli",
            "action",
            "start-quest",
            "--quest",
            "trello-read-board",
            "--confirm",
            "--repo-root",
            str(config.repo_root),
            "--participant-root",
            str(config.participant_root),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert "Traceback" not in result.stderr, result.stderr
    assert str(config.repo_root) not in result.stdout + result.stderr, "an absolute path leaked"
    assert result.returncode == 0, result.stderr
    assert "advisory:" in result.stdout, result.stdout
    assert "could not be rebuilt" in result.stdout, result.stdout

    progress = yaml.safe_load((config.participant_root / "progress.yaml").read_text())
    started = [a for a in progress["attempts"] if a["quest_id"] == "trello-read-board"]
    assert started, "the change the advisory says was recorded must actually be recorded"
