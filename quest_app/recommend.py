"""Which quest to do next, and why.

`docs/CONTENT-MODEL.md` requires an explainable deterministic score rather than AI
inference, and `docs/ui/UI-SPECIFICATION.md` requires at least three concrete reasons shown
to the participant. Both constraints point the same way: the score is a small table of
weighted signals, each of which can state its own reason in a sentence.

Determinism matters beyond reproducibility. A participant who is told "because this
finishes this region" and then sees a different answer on reload stops trusting the
recommendation, and a recommendation nobody trusts is worse than a list.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from quest_app.models import ContentBundle, Quest, QuestState
from quest_app.progress import ParticipantProgress
from quest_app.progress_calc import QuestProgress, RegionProgress


@dataclass(frozen=True, slots=True)
class Signal:
    """One weighted reason. `reason` is participant-facing text, not a debug string."""

    weight: int
    reason: str


@dataclass(frozen=True, slots=True)
class Recommendation:
    quest: Quest
    score: int
    reasons: tuple[str, ...]

    @property
    def top_reasons(self) -> tuple[str, ...]:
        return self.reasons[:3]


# Weights are small integers on purpose: the ordering they produce should be arguable from
# the table alone, without running anything.
W_IN_PROGRESS = 100
W_NEEDS_CHANGES = 120
W_TRACK = 40
W_UNBLOCKS = 15
W_FOCUS_TAG = 20
W_FITS_SESSION = 12
W_COMPLETES_REGION = 25
W_BOOKEND_BALANCE = 18
W_ORDER_BONUS = 6


def recommend(
    bundle: ContentBundle,
    states: dict[str, QuestProgress],
    regions: dict[str, RegionProgress],
    progress: ParticipantProgress | None,
    *,
    limit: int = 4,
) -> list[Recommendation]:
    """Eligible quests, best first. Ties break on region order then ID, so the list is stable."""
    focus_tags = set(progress.focus_tags) if progress else set()
    capacity = progress.session_capacity_minutes if progress else None
    track = bundle.tracks.get(progress.selected_track) if progress else None
    track_quests = set(track.quest_ids) if track else set()

    # How many quests each quest would unlock, so finishing a bottleneck ranks above a leaf.
    unlocks: dict[str, int] = {}
    for quest in bundle.quests.values():
        for prerequisite in quest.prerequisites:
            unlocks[prerequisite] = unlocks.get(prerequisite, 0) + 1

    verified_bookends = [
        entry.quest.bookend
        for entry in states.values()
        if entry.is_verified and entry.quest.bookend
    ]
    weakest_bookend = _weakest_bookend(verified_bookends)

    scored: list[Recommendation] = []
    for quest in bundle.ordered_quests():
        entry = states[quest.id]
        if not _is_eligible(entry):
            continue
        signals = _signals(
            quest=quest,
            entry=entry,
            regions=regions,
            track_quests=track_quests,
            track_title=track.title if track else None,
            focus_tags=focus_tags,
            capacity=capacity,
            unlocks=unlocks.get(quest.id, 0),
            weakest_bookend=weakest_bookend,
        )
        score = sum(signal.weight for signal in signals)
        reasons = tuple(signal.reason for signal in sorted(signals, key=lambda s: -s.weight))
        scored.append(Recommendation(quest=quest, score=score, reasons=reasons))

    region_order = {region.id: region.order for region in bundle.regions.values()}
    scored.sort(key=lambda r: (-r.score, region_order.get(r.quest.region, 10_000), r.quest.id))
    return scored[:limit]


def _is_eligible(entry: QuestProgress) -> bool:
    """A quest worth recommending: not locked, not finished, not withdrawn."""
    if entry.quest.deprecated:
        return False
    return entry.state.id not in (
        QuestState.LOCKED,
        QuestState.VERIFIED,
        QuestState.SUBMITTED,
    )


def _weakest_bookend(verified: Sequence[str | None]) -> str | None:
    """The bookend the participant has demonstrated least, for balanced development.

    With nothing verified yet there is no weakest side, so no balance reason is offered
    rather than an arbitrary one.
    """
    if not verified:
        return None
    counts = {"intent": 0, "validation": 0}
    for bookend in verified:
        if bookend in counts:
            counts[bookend] += 1
    if counts["intent"] == counts["validation"]:
        return None
    return "intent" if counts["intent"] < counts["validation"] else "validation"


def _signals(
    *,
    quest: Quest,
    entry: QuestProgress,
    regions: dict[str, RegionProgress],
    track_quests: set[str],
    track_title: str | None,
    focus_tags: set[str],
    capacity: int | None,
    unlocks: int,
    weakest_bookend: str | None,
) -> list[Signal]:
    signals: list[Signal] = []

    if entry.state.id is QuestState.NEEDS_CHANGES:
        signals.append(
            Signal(
                W_NEEDS_CHANGES, "A reviewer asked for changes here, and your evidence is preserved"
            )
        )
    elif entry.state.id in (
        QuestState.IN_PROGRESS,
        QuestState.EVIDENCE_READY,
        QuestState.LOCALLY_VALIDATED,
    ):
        signals.append(Signal(W_IN_PROGRESS, "You already started this quest"))

    if quest.id in track_quests and track_title:
        signals.append(Signal(W_TRACK, f"It is part of your current track, {track_title}"))

    overlap = focus_tags & set(quest.tags)
    if overlap:
        signals.append(
            Signal(W_FOCUS_TAG, f"It matches your focus on {', '.join(sorted(overlap))}")
        )

    if capacity is not None and quest.estimated_minutes <= capacity:
        signals.append(
            Signal(
                W_FITS_SESSION,
                f"It fits a {capacity}-minute session at about {quest.estimated_minutes} minutes",
            )
        )

    if unlocks:
        signals.append(
            Signal(
                W_UNBLOCKS,
                f"Finishing it unlocks {unlocks} further quest{'s' if unlocks > 1 else ''}",
            )
        )

    region = regions.get(quest.region)
    if region and region.total > 1 and region.verified == region.total - 1:
        signals.append(Signal(W_COMPLETES_REGION, "It is the last unverified quest in its region"))

    if weakest_bookend and quest.bookend == weakest_bookend:
        side = (
            "turning intent into structured work"
            if weakest_bookend == "intent"
            else "validating delivered behavior"
        )
        signals.append(
            Signal(W_BOOKEND_BALANCE, f"It builds the side you have demonstrated least: {side}")
        )

    if quest.order is not None:
        signals.append(Signal(W_ORDER_BONUS, "The curriculum places it next in its region"))

    # Guarantee the three reasons the UI specification requires. These are true of every
    # eligible quest, so they are stated last and only used to fill.
    signals.append(Signal(1, f"Its prerequisites are satisfied, and it is worth {quest.xp} XP"))
    signals.append(
        Signal(0, f"It takes about {quest.estimated_minutes} minutes at {quest.level_label} level")
    )
    if quest.bookend:
        signals.append(Signal(0, f"It develops the {quest.bookend.replace('-', ' ')} bookend"))
    return signals
