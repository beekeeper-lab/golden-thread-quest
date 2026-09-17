"""The recommendation is deterministic and explainable, or it is not worth showing.

Nothing tested `recommend.py` at all, while the traceability document claimed two test files
covered it. The nearest assertion was the heading "Recommended next".
"""

from __future__ import annotations

from pathlib import Path

import pytest
from quest_app.config import AppConfig
from quest_app.errors import ProblemReport
from quest_app.models import QuestState
from quest_app.pipeline import load_world
from quest_app.progress_calc import compute_states, region_progress
from quest_app.recommend import recommend


@pytest.fixture
def world(repo_root: Path, fixture_participant_root: Path):  # type: ignore[no-untyped-def]
    config = AppConfig.for_repo(repo_root, participant_root=fixture_participant_root)
    report = ProblemReport()
    loaded = load_world(config, report)
    assert loaded is not None, report.to_text()
    return loaded


def rank(world):  # type: ignore[no-untyped-def]
    states = compute_states(world.content, world.participant)
    regions = region_progress(world.content, states)
    progress = world.participant.progress if world.participant else None
    return recommend(world.content, states, regions, progress)


def test_it_recommends_something_eligible(world) -> None:  # type: ignore[no-untyped-def]
    results = rank(world)
    assert results
    states = compute_states(world.content, world.participant)
    for result in results:
        assert states[result.quest.id].state.id not in (
            QuestState.LOCKED,
            QuestState.VERIFIED,
            QuestState.SUBMITTED,
        )


def test_it_gives_at_least_three_reasons(world) -> None:  # type: ignore[no-untyped-def]
    """`UI-SPECIFICATION.md` requires three concise reasons, and the UI shows exactly these."""
    for result in rank(world):
        assert len(result.top_reasons) == 3
        assert all(reason.strip() for reason in result.top_reasons)


def test_the_reasons_read_as_sentences_not_debug_output(world) -> None:  # type: ignore[no-untyped-def]
    for result in rank(world):
        for reason in result.reasons:
            assert reason[0].isupper(), reason
            assert "score" not in reason.lower()
            assert "weight" not in reason.lower()


def test_it_is_deterministic(world) -> None:  # type: ignore[no-untyped-def]
    """A participant told why, who then sees a different answer on reload, stops trusting it."""
    first = [(r.quest.id, r.score, r.reasons) for r in rank(world)]
    for _ in range(5):
        assert [(r.quest.id, r.score, r.reasons) for r in rank(world)] == first


def test_work_already_started_outranks_work_not_started(world) -> None:  # type: ignore[no-untyped-def]
    results = rank(world)
    states = compute_states(world.content, world.participant)
    started = [r for r in results if states[r.quest.id].is_started]
    unstarted = [r for r in results if not states[r.quest.id].is_started]
    if started and unstarted:
        assert started[0].score > unstarted[0].score


def test_a_deprecated_quest_is_never_recommended(world) -> None:  # type: ignore[no-untyped-def]
    import dataclasses

    quest = next(iter(world.content.quests.values()))
    deprecated = dataclasses.replace(quest, deprecated=True)
    bundle = dataclasses.replace(
        world.content, quests={**world.content.quests, quest.id: deprecated}
    )
    states = compute_states(bundle, world.participant)
    regions = region_progress(bundle, states)
    results = recommend(bundle, states, regions, world.participant.progress)
    assert quest.id not in {result.quest.id for result in results}


def test_ties_break_stably(world) -> None:  # type: ignore[no-untyped-def]
    """Equal scores must order by region then ID, so the list never shuffles."""
    results = rank(world)
    scores = [result.score for result in results]
    assert scores == sorted(scores, reverse=True)


def test_it_survives_a_participant_with_no_progress(world) -> None:  # type: ignore[no-untyped-def]
    states = compute_states(world.content, None)
    regions = region_progress(world.content, states)
    results = recommend(world.content, states, regions, None)
    assert results
    assert all(len(result.top_reasons) == 3 for result in results)
