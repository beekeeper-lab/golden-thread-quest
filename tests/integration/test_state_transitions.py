"""Participant state changes: what is allowed, what is refused, and what survives a crash.

The transitions a participant may make are a small table (`quest_app/state_machine.py`).
What matters is the two things absent from it — nothing produces `verified`, and running a
validator is not a transition — and that a write either lands completely or not at all.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from quest_app.config import AppConfig
from quest_app.content_loader import SchemaSet
from quest_app.errors import ProblemReport
from quest_app.models import AttemptState
from quest_app.pipeline import load_world
from quest_app.state_machine import BY_ACTION, TransitionError, allowed_actions, check
from quest_app.store import (
    ProgressStore,
    StoreError,
    atomic_write_text,
    no_guard,
    start_attempt,
    transition_attempt,
)

UNSTARTED = "playwright-first-independent-test"
IN_PROGRESS = "jira-read-assigned-stories"
VERIFIED = "base-camp-repository-safety"


@pytest.fixture
def store(config: AppConfig) -> ProgressStore:
    return ProgressStore(config)


@pytest.fixture
def schemas(config: AppConfig) -> SchemaSet:
    return SchemaSet(config.schemas_root)


class TestTheTable:
    def test_no_transition_can_produce_verified(self) -> None:
        """Verified completion is the shadow of an approval, never a move a participant makes."""
        assert all(t.target is not AttemptState.VERIFIED for t in BY_ACTION.values())

    def test_no_transition_can_produce_needs_changes(self) -> None:
        """Only a reviewer asks for changes."""
        assert all(t.target is not AttemptState.NEEDS_CHANGES for t in BY_ACTION.values())

    def test_running_a_validator_is_not_an_action(self) -> None:
        """ADR-017: a validation run appends a result and changes no state."""
        assert "run-validator" not in BY_ACTION
        assert not any("valid" in name and "mark" not in name for name in BY_ACTION)

    @pytest.mark.parametrize("action", ["rm", "verify", "approve", "delete-attempt", ""])
    def test_an_unknown_action_is_refused(self, action: str) -> None:
        with pytest.raises(TransitionError):
            check(action, AttemptState.IN_PROGRESS)

    def test_starting_twice_is_refused(self) -> None:
        with pytest.raises(TransitionError, match="already has an attempt"):
            check("start-quest", AttemptState.IN_PROGRESS)

    def test_submitting_from_in_progress_is_refused(self) -> None:
        """Evidence has to be assembled before it can be reviewed."""
        with pytest.raises(TransitionError, match="only possible from"):
            check("submit-for-review", AttemptState.IN_PROGRESS)

    def test_a_refusal_says_what_would_be_allowed(self) -> None:
        with pytest.raises(TransitionError) as error:
            check("mark-locally-validated", AttemptState.IN_PROGRESS)
        assert "evidence_ready" in str(error.value)

    def test_allowed_actions_from_nothing_is_only_starting(self) -> None:
        assert [t.action for t in allowed_actions(None)] == ["start-quest"]


class TestWritingProgress:
    def test_starting_a_quest_creates_an_attempt_and_its_evidence_package(
        self, store: ProgressStore, schemas: SchemaSet, config: AppConfig
    ) -> None:
        report = ProblemReport()
        world = load_world(config, report)
        assert world is not None
        quest = world.content.quests[UNSTARTED]

        attempt_id = start_attempt(
            store,
            quest_id=UNSTARTED,
            quest_version=quest.version,
            content_hash=quest.content_hash,
            schemas=schemas,
        )

        directory = config.participant_root / "evidence" / UNSTARTED / attempt_id
        assert (directory / "PROOF.md").exists()
        assert (directory / "manifest.yaml").exists()
        assert (directory / "validation").is_dir()

        data = yaml.safe_load(store.path.read_text())
        recorded = next(a for a in data["attempts"] if a["quest_id"] == UNSTARTED)
        assert recorded["state"] == "in_progress"
        assert recorded["content_hash"] == quest.content_hash

    def test_the_new_attempt_loads_cleanly(
        self, store: ProgressStore, schemas: SchemaSet, config: AppConfig
    ) -> None:
        """A write the loader would later refuse would lock a participant out of their work."""
        world = load_world(config, ProblemReport())
        assert world is not None
        start_attempt(
            store,
            quest_id=UNSTARTED,
            quest_version=world.content.quests[UNSTARTED].version,
            content_hash=world.content.quests[UNSTARTED].content_hash,
            schemas=schemas,
        )
        report = ProblemReport()
        assert load_world(config, report) is not None, report.to_text()

    def test_a_transition_is_recorded_and_survives_a_reload(
        self, store: ProgressStore, schemas: SchemaSet, config: AppConfig
    ) -> None:
        """State lives in a file, not in a browser, so restarting restores it.

        `mark-locally-validated` rather than `submit-for-review`: the latter is only ever
        legitimate alongside a `submission.yaml` `create_submission` writes (E4), and this
        test's subject is the state-machine layer's own persistence, not that record.
        """
        transition_attempt(
            store,
            quest_id=IN_PROGRESS,
            action="mark-locally-validated",
            schemas=schemas,
            guard=no_guard,
        )

        report = ProblemReport()
        world = load_world(config, report)
        assert world is not None, report.to_text()
        attempt = world.participant.progress.attempt_for(IN_PROGRESS)
        assert attempt is not None
        assert attempt.recorded_state is AttemptState.LOCALLY_VALIDATED

    def test_an_invalid_transition_leaves_the_file_untouched(
        self, store: ProgressStore, schemas: SchemaSet
    ) -> None:
        before = store.path.read_text()
        with pytest.raises(StoreError):
            transition_attempt(
                store,
                quest_id=IN_PROGRESS,
                action="withdraw-submission",
                schemas=schemas,
                guard=no_guard,
            )
        assert store.path.read_text() == before

    def test_a_transition_on_a_quest_with_no_attempt_is_refused(
        self, store: ProgressStore, schemas: SchemaSet
    ) -> None:
        with pytest.raises(StoreError, match="no attempt"):
            transition_attempt(
                store,
                quest_id=UNSTARTED,
                action="mark-evidence-ready",
                schemas=schemas,
                guard=no_guard,
            )

    def test_every_change_is_recorded_where_the_participant_can_read_it(
        self, store: ProgressStore, schemas: SchemaSet, config: AppConfig
    ) -> None:
        transition_attempt(
            store, quest_id=IN_PROGRESS, action="submit-for-review", schemas=schemas, guard=no_guard
        )
        activity = (config.participant_root / "ACTIVITY.md").read_text()
        assert IN_PROGRESS in activity
        assert "submitted" in activity


class TestAtomicWrites:
    def test_a_write_replaces_the_file_completely(self, tmp_path: Path) -> None:
        target = tmp_path / "progress.yaml"
        target.write_text("old contents\n")
        atomic_write_text(target, "new contents\n")
        assert target.read_text() == "new contents\n"

    def test_a_failed_write_leaves_the_original_and_no_debris(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An interrupted save must not leave a half-written file or a stray temporary.

        The interruption is simulated at `fsync`, which is the last moment before the
        rename — the point at which a real power loss is most likely to be noticed.
        """
        import os

        target = tmp_path / "progress.yaml"
        target.write_text("original\n")

        def explode(_: int) -> None:
            raise OSError("no space left on device")

        monkeypatch.setattr(os, "fsync", explode)
        with pytest.raises(OSError, match="no space"):
            atomic_write_text(target, "new contents\n")

        assert target.read_text() == "original\n"
        assert [entry.name for entry in tmp_path.iterdir()] == ["progress.yaml"]

    def test_writing_creates_missing_parent_directories(self, tmp_path: Path) -> None:
        target = tmp_path / "a" / "b" / "c.md"
        atomic_write_text(target, "x")
        assert target.read_text() == "x"


def test_a_participant_cannot_write_verified_through_the_store(
    store: ProgressStore, schemas: SchemaSet
) -> None:
    """The last line of defense: even a direct call cannot reach the reviewer's state."""
    with pytest.raises(StoreError):
        transition_attempt(
            store, quest_id=VERIFIED, action="start-quest", schemas=schemas, guard=no_guard
        )
