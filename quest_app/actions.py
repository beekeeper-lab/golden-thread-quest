"""Performing a quest action, independent of how it was asked for.

Every mutating action lives here rather than in the HTTP handler, so the same guards run
whichever way a participant reaches them. `quest_app.serve` calls this over HTTP for the
browser; `quest_app.cli action` calls it directly from a terminal, which is the only path
available on surfaces that cannot reach a loopback server — an agent sandbox, a remote
shell, CI.

The guards are the reason this is shared rather than reimplemented. A second copy of
"refuse to mark evidence ready if the secret scan finds something" is a second copy that
can drift, and the product's whole claim is that those rules cannot be gone around.
"""

from __future__ import annotations

from typing import Any

from quest_app.build import build_site
from quest_app.errors import ProblemReport
from quest_app.state_machine import BY_ACTION
from quest_app.store import ProgressStore, StoreError, start_attempt, transition_attempt
from quest_app.view_models import online_service_view


def _default_display_name() -> str:
    """A name for a brand-new participant's record.

    The local account name is a better first guess than "Participant", and it is theirs to
    change: `participant/progress.yaml` is an ordinary file in their repository.
    """
    import getpass

    try:
        return getpass.getuser()[:100] or "Participant"
    except Exception:
        return "Participant"


def quest_id_of(payload: dict[str, Any]) -> str:
    value = payload.get("quest_id")
    if not isinstance(value, str):
        raise ValueError("A quest ID is required.")
    return value


# Every action this application will perform. Anything else is refused before it is looked
# at, whichever caller asked. Kept here rather than in the HTTP layer because the CLI needs
# the same allowlist and a second copy is a second thing to drift.
MUTATING_ACTIONS = frozenset(BY_ACTION) | {"rebuild", "run-validator", "record-review"}
READ_ACTIONS = frozenset({"health", "git-status", "actions"})


class ActionRunner:
    """Performs actions against one participant's progress, with every guard applied.

    Holds no request state. The caller supplies configuration, the schema set, and a
    callable that loads the world, so an HTTP handler and a CLI command can share it
    without either knowing about the other.
    """

    def __init__(self, config: Any, schemas: Any, load: Any, service: Any = None) -> None:
        self.config = config
        self.schemas = schemas
        self.load = load
        # How the rebuilt site should describe the local service. A browser reaches actions
        # through a running server, so pages say so; a CLI caller has no server, and a page
        # claiming one is running would send the reader to a dead address.
        self.service = service if service is not None else online_service_view

    def perform(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        """One mutation at a time, across processes as well as within one.

        The service serialises requests with a lock its own process holds. Since the CLI
        landed, a second process performs the same read-modify-write against the same file,
        and that lock cannot see it. The file lock is held across the load as well as the
        write, because reading state that another process is about to replace is the race.
        """
        if action not in MUTATING_ACTIONS:
            return self._perform(action, payload)
        with ProgressStore(self.config).exclusive():
            return self._perform(action, payload)

    def _perform(self, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        world = self.load()
        store = ProgressStore(self.config)

        if action == "rebuild":
            result = build_site(world, service=self.service())
            return {"ok": True, "action": action, "pages": result.page_count}

        quest_id = payload.get("quest_id")
        if not isinstance(quest_id, str) or quest_id not in world.content.quests:
            # A quest ID is matched against loaded content, so it can only ever name
            # something the build already knows about. No path reaches the filesystem.
            raise ValueError("That quest does not exist.")
        quest = world.content.quests[quest_id]

        if action == "record-review":
            return self._record_review(world, quest_id_of(payload), payload)

        if action == "run-validator":
            # Not a transition (ADR-017). It appends a result and changes nothing else.
            return self._run_validator(world, quest_id, payload)

        if action == "start-quest":
            self._require_met_prerequisites(world, quest_id)
            # A participant with no progress file gets one here, seeded from the site's own
            # configuration. Without this the very first action of the pilot failed.
            attempt_id = start_attempt(
                store,
                quest_id=quest_id,
                quest_version=quest.version,
                content_hash=quest.content_hash,
                schemas=self.schemas,
                display_name=_default_display_name(),
                track_id=world.content.site.default_track,
            )
            state = "in_progress"
        else:
            if action == "submit-for-review":
                return self._submit(world, quest, store)
            if action == "mark-evidence-ready":
                self._require_clean_secret_scan(world, quest_id)

            def guard(requested: str) -> None:
                if requested == "mark-locally-validated":
                    self._require_qualifying_validation(world, quest_id)

            new_state = transition_attempt(
                store,
                quest_id=quest_id,
                action=action,
                schemas=self.schemas,
                guard=guard,
            )
            state = new_state.value
            attempt_id = None

        # The change is already on disk. A rebuild that fails afterwards is bad news about
        # the generated site, not about the participant's work, and reporting it as a failed
        # action told them their change had not happened while `progress.yaml` said it had.
        # Generated output is disposable and rebuildable; their record is neither.
        advisories: list[str] = []
        try:
            build_site(self.load(), service=self.service())
        except OSError as exc:
            reason = exc.strerror or type(exc).__name__
            advisories.append(
                f"Your change was recorded. The site could not be rebuilt ({reason}); "
                "run `quest-app build` once that is fixed."
            )
        return {
            "ok": True,
            "action": action,
            "quest_id": quest_id,
            "state": state,
            "attempt_id": attempt_id,
            "advisories": tuple(advisories),
        }

    def _submit(self, world: Any, quest: Any, store: ProgressStore) -> dict[str, Any]:
        """Submission is a record, not just a state change.

        The record captures the evidence hash at this moment, which is the only thing that
        later makes "has this changed since I reviewed it?" answerable.
        """
        from quest_app.review import ReviewError, create_submission, submission_instructions

        participant = world.participant
        attempt = participant.progress.attempt_for(quest.id) if participant else None
        if attempt is None:
            raise StoreError("There is nothing to submit.")
        try:
            record = create_submission(
                self.config,
                store,
                quest=quest,
                attempt=attempt,
                participant=participant,
                schemas=self.schemas,
            )
        except ReviewError as exc:
            raise StoreError(str(exc)) from exc

        build_site(self.load(), service=self.service())
        return {
            "ok": True,
            "action": "submit-for-review",
            "quest_id": quest.id,
            "state": "submitted",
            "submission_id": record.submission_id,
            # Not blockers, or the submission would have been refused. A participant who is
            # never told a declared check went unrun learns it from a reviewer instead.
            "advisories": list(record.advisories),
            # The application never pushes and never opens a pull request. Those are claims
            # on the participant's behalf that the work is finished.
            "next_steps": submission_instructions(quest.id, attempt.attempt_id, None),
        }

    def _record_review(self, world: Any, quest_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        from quest_app.review import ReviewError, record_decision

        if quest_id not in world.content.quests:
            raise ValueError("That quest does not exist.")
        participant = world.participant
        attempt = participant.progress.attempt_for(quest_id) if participant else None
        if attempt is None:
            raise StoreError("There is nothing to review.")

        reviewer = payload.get("reviewer_name")
        if not isinstance(reviewer, str) or not reviewer.strip():
            raise ValueError("A reviewer name is required.")
        findings = payload.get("findings") or []
        if not isinstance(findings, list):
            raise ValueError("Findings must be a list.")

        try:
            decision = record_decision(
                self.config,
                ProgressStore(self.config),
                quest=world.content.quests[quest_id],
                attempt=attempt,
                participant=participant,
                decision=str(payload.get("decision", "")),
                reviewer_name=reviewer.strip()[:100],
                verification_statement=payload.get("verification_statement"),
                findings=findings,
                schemas=self.schemas,
                acknowledge_changed_evidence=bool(payload.get("acknowledge_changed_evidence")),
            )
        except ReviewError as exc:
            raise StoreError(str(exc)) from exc

        build_site(self.load(), service=self.service())
        return {
            "ok": True,
            "action": "record-review",
            "quest_id": quest_id,
            "decision": decision.decision,
            "review_id": decision.review_id,
        }

    def _run_validator(self, world: Any, quest_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        from quest_app.evidence import new_run_id, store_result
        from quest_app.validator_registry import ValidatorError, load_registry
        from quest_app.validator_runner import run_validator

        validator_id = payload.get("validator_id")
        if not isinstance(validator_id, str):
            raise ValueError("A validator ID is required.")
        quest = world.content.quests[quest_id]
        if validator_id not in quest.validators:
            # The quest decides which validators apply to it, so a caller cannot run an
            # arbitrary registered validator against arbitrary work.
            raise ValueError("That validator is not declared by this quest.")

        report = ProblemReport()
        registry = load_registry(self.config, report)
        if registry is None:
            raise StoreError("The validator registry could not be loaded.")

        participant = world.participant
        attempt = participant.progress.attempt_for(quest_id) if participant else None
        if attempt is None:
            raise StoreError("Start the quest before running its checks.")

        try:
            definition = registry.get(validator_id)
            result = run_validator(
                definition,
                self.config,
                quest_id=quest_id,
                attempt_id=attempt.attempt_id,
                run_id=new_run_id(validator_id),
                parameters=payload.get("parameters"),
            )
        except ValidatorError as exc:
            raise ValueError(str(exc)) from exc

        from quest_app.evidence import ResultRejectedError

        try:
            stored = store_result(
                self.config,
                attempt.evidence_path,
                result.to_document(),
                self.schemas,
            )
        except ResultRejectedError as exc:
            raise StoreError(str(exc)) from exc
        build_site(self.load(), service=self.service())
        return {
            "ok": True,
            "action": "run-validator",
            "quest_id": quest_id,
            "validator_id": validator_id,
            "outcome": result.outcome,
            "run_id": result.run_id,
            "result_path": stored,
            "note": "A validation run never changes quest state.",
        }

    def _require_clean_secret_scan(self, world: Any, quest_id: str) -> None:
        """Refuse to prepare a submission that carries a credential.

        The asymmetry is the argument: a false positive costs a minute, and a missed
        credential costs a rotation and an awkward conversation.
        """
        from quest_app.evidence import scan_evidence

        participant = world.participant
        attempt = participant.progress.attempt_for(quest_id) if participant else None
        if attempt is None:
            return
        findings = scan_evidence(self.config, attempt.evidence_path)
        if findings:
            locations = ", ".join(f"{f.path}:{f.line}" for f in findings[:3])
            raise StoreError(
                f"Something secret-like is in your evidence ({locations}). "
                "Remove it before submitting; the scan never reports the value itself."
            )

    def _require_met_prerequisites(self, world: Any, quest_id: str) -> None:
        """A locked quest is locked on every surface, not only where a button can be greyed.

        Prerequisites were computed for display and enforced nowhere. The browser disabled
        Start on a locked quest and the CLI started it, so a participant with nothing verified
        could take a quest three links down the chain and carry it to `verified`. The rule
        that makes prerequisites mean anything is the same one `compute_states` uses:
        satisfied means *verified*, not merely attempted.
        """
        from quest_app.progress_calc import compute_states

        progress = compute_states(world.content, world.participant).get(quest_id)
        if progress is None or not progress.unmet_prerequisites:
            return
        titles = [
            world.content.quests[p].title if p in world.content.quests else p
            for p in progress.unmet_prerequisites
        ]
        raise StoreError("This quest is locked until a reviewer has verified: " + ", ".join(titles))

    def _require_qualifying_validation(self, world: Any, quest_id: str) -> None:
        """`locally_validated` is a claim about validator results, so the results decide.

        Without this the state would be a participant's assertion wearing a validator's
        authority, which is exactly the blurring the progress model exists to prevent.
        """
        quest = world.content.quests[quest_id]
        if not quest.validators:
            return
        participant = world.participant
        attempt = participant.progress.attempt_for(quest_id) if participant else None
        if attempt is None:
            raise StoreError("There is no attempt to validate.")
        results = participant.results_for(attempt) if participant else ()
        latest = {result.validator_id: result for result in results}
        missing = [
            validator
            for validator in quest.validators
            if validator not in latest or not latest[validator].qualifies
        ]
        if missing:
            raise StoreError(
                "These checks have not returned a qualifying result yet: " + ", ".join(missing)
            )
