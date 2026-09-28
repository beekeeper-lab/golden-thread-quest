"""Round 14 web-lens findings: C1, C3, C4.

C1 — `ValidatorView.available` was hard-coded `False` in both `_quest_detail_context` and
`_evidence_context`, so a page built by the running service still told a participant to
"start the local service" beside a run control that was, in fact, live. It must track the
page's own `ServiceView`, exactly like the run button next to it already does.

C3 — the quest detail page called `build_proof_views(quest)` with no detection state
regardless of whether an attempt existed, so a submitted or verified quest's own page read
"Not detected" for every item while its evidence workspace correctly showed what had been
found. Once an attempt exists, the quest page must detect proof the same way the evidence
workspace does.

C4 — the reviewer page's "evidence changed" banner (and its silence) reflects the last
build, not a live filesystem read, and the guide claimed otherwise ("the page says so
plainly"). The fix is honest wording, not a live re-check (recording a decision already
re-checks live and correctly refuses an unacknowledged change).
"""

from __future__ import annotations

from quest_app.build import _evidence_context, _quest_detail_context, build_site
from quest_app.config import AppConfig
from quest_app.errors import ProblemReport
from quest_app.pipeline import load_world
from quest_app.progress_calc import compute_states
from quest_app.review import create_submission
from quest_app.store import ProgressStore
from quest_app.view_models import build_quest_summary, offline_service_view, online_service_view

# Has a registered validator and an attempt already on record (`evidence_ready`), so its
# `ValidatorView.latest_outcome` is not None either — the interesting case, not the one
# where nothing has run yet.
VALIDATED_QUEST = "jira-read-assigned-stories"
# Verified, with one required item (its validator) genuinely `validated` and the rest
# `missing` — the case C3 says a quest page must stop calling "Not detected".
VERIFIED_QUEST = "base-camp-repository-safety"
VALIDATOR_ITEM_ID = "repository-foundation-validation"


def _world_and_states(config: AppConfig):  # type: ignore[no-untyped-def]
    report = ProblemReport()
    world = load_world(config, report)
    assert world is not None, report.to_text()
    states = compute_states(world.content, world.participant)
    summaries = {qid: build_quest_summary(entry, world.content) for qid, entry in states.items()}
    return world, states, summaries


class TestC1ValidatorAvailabilityMatchesTheBuild:
    def test_quest_detail_validator_is_available_when_the_service_that_built_it_is(
        self, config: AppConfig
    ) -> None:
        world, states, summaries = _world_and_states(config)
        entry = states[VALIDATED_QUEST]

        online = _quest_detail_context(
            entry, world.content, summaries, world, online_service_view()
        )
        offline = _quest_detail_context(
            entry, world.content, summaries, world, offline_service_view()
        )

        assert online["validators"], "the fixture quest must declare a validator"
        assert all(v.available for v in online["validators"])
        assert all(v.unavailable_reason is None for v in online["validators"])
        assert not any(v.available for v in offline["validators"])
        assert all(v.unavailable_reason for v in offline["validators"])

    def test_evidence_workspace_validator_is_available_when_the_service_that_built_it_is(
        self, config: AppConfig
    ) -> None:
        world, states, summaries = _world_and_states(config)
        entry = states[VALIDATED_QUEST]

        online = _evidence_context(entry, summaries[VALIDATED_QUEST], world, online_service_view())
        offline = _evidence_context(
            entry, summaries[VALIDATED_QUEST], world, offline_service_view()
        )

        assert online["validators"], "the fixture quest must declare a validator"
        assert all(v.available for v in online["validators"])
        assert all(v.unavailable_reason is None for v in online["validators"])
        assert not any(v.available for v in offline["validators"])
        assert all(v.unavailable_reason for v in offline["validators"])

    def test_a_page_built_by_the_running_service_does_not_say_to_start_it(
        self, config: AppConfig
    ) -> None:
        """The visible symptom: the evidence workspace, built as `make serve` builds it."""
        report = ProblemReport()
        world = load_world(config, report)
        assert world is not None, report.to_text()
        build_site(world, service=online_service_view())
        html = (config.generated_root / "evidence" / VALIDATED_QUEST / "index.html").read_text(
            encoding="utf-8"
        )

        assert "Start the local service to run this check." not in html
        assert 'disabled aria-describedby="why-run-validate-jira-read-assigned"' not in html


class TestC3QuestPageDetectsProofOnceAnAttemptExists:
    def test_a_verified_quests_own_page_shows_what_the_evidence_workspace_shows(
        self, config: AppConfig
    ) -> None:
        world, states, summaries = _world_and_states(config)
        entry = states[VERIFIED_QUEST]
        assert entry.attempt is not None, "fixture must have an attempt to make this meaningful"

        quest_ctx = _quest_detail_context(
            entry, world.content, summaries, world, offline_service_view()
        )
        evidence_ctx = _evidence_context(
            entry, summaries[VERIFIED_QUEST], world, offline_service_view()
        )

        def status_of(items: tuple, item_id: str) -> str:
            (match,) = (item.status for item in items if item.id == item_id)
            return match

        quest_status = status_of(quest_ctx["required_proof"], VALIDATOR_ITEM_ID)
        evidence_status = status_of(evidence_ctx["required_proof"], VALIDATOR_ITEM_ID)

        assert evidence_status == "validated", "the evidence workspace must show its own truth"
        assert quest_status == evidence_status, (
            "the quest page must agree with the evidence workspace once an attempt exists"
        )

    def test_before_any_attempt_the_quest_page_still_says_not_detected(
        self, config: AppConfig
    ) -> None:
        """C3's fix must not claim detection for a quest nobody has started."""
        world, states, summaries = _world_and_states(config)
        untouched = next(
            (qid, e) for qid, e in states.items() if e.attempt is None and e.quest.required_proof
        )
        quest_id, entry = untouched

        quest_ctx = _quest_detail_context(
            entry, world.content, summaries, world, offline_service_view()
        )

        assert all(item.status == "missing" for item in quest_ctx["required_proof"])
        del quest_id


class TestC4ReviewPageStatesWhenItsComparisonWasMade:
    def _submit_and_render(self, config: AppConfig) -> str:
        from quest_app.content_loader import SchemaSet

        report = ProblemReport()
        world = load_world(config, report)
        assert world is not None, report.to_text()
        quest = world.content.quests[VALIDATED_QUEST]
        attempt = world.participant.progress.attempt_for(VALIDATED_QUEST)
        create_submission(
            config,
            ProgressStore(config),
            quest=quest,
            attempt=attempt,
            participant=world.participant,
            schemas=SchemaSet(config.schemas_root),
        )

        report = ProblemReport()
        world = load_world(config, report)
        assert world is not None, report.to_text()
        build_site(world, built_at="2026-09-20T00:00:00+00:00", service=online_service_view())
        page = config.generated_root / "review" / VALIDATED_QUEST / "index.html"
        return page.read_text(encoding="utf-8")

    def test_the_page_states_its_silence_is_as_of_the_build_not_live(
        self, config: AppConfig
    ) -> None:
        html = self._submit_and_render(config)

        assert "The evidence changed since it was submitted" not in html, (
            "nothing changed after this submission, so no warning banner is expected"
        )
        assert "not a live read" in html
        assert "2026-09-20T00:00:00+00:00" in html, (
            "the honest statement must name the build it reflects"
        )

    def test_reviewer_guide_no_longer_claims_a_live_read(self, repo_root) -> None:  # type: ignore[no-untyped-def]
        text = (repo_root / "docs" / "guides" / "REVIEWER.md").read_text(encoding="utf-8")
        assert "The page says so plainly" not in text
        assert "says what a build found" in text
        assert "your working tree holds right now" in text
        assert "re-checks the files at that moment" in text
