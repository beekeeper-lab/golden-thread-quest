"""Derived progress: what state each quest is in, and what has actually been earned.

Three rules shape everything here.

* `locked` and `available` are computed from prerequisites and never stored, so a
  participant cannot write them (Stage 0 finding F3).
* A validation run never changes state (ADR-017). `locally_validated` is a state the
  participant reaches, having run the validators; a failing run leaves the attempt alone.
* Verified completion and verified XP come only from an approved review that matches the
  attempt (ADR-011). Claimed and verified are computed separately and never added together.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from quest_app.models import (
    STATE_AUTHORITY,
    STATE_EXPLANATIONS,
    STATE_LABELS,
    Authority,
    Badge,
    ContentBundle,
    Quest,
    QuestState,
)
from quest_app.progress import Attempt, ParticipantState, ReviewDecision


@dataclass(frozen=True, slots=True)
class StateView:
    """A state together with who put the quest in it, which the UI must always show."""

    id: QuestState
    label: str
    authority: Authority
    explanation: str
    occurred_at: str | None = None

    @classmethod
    def of(cls, state: QuestState, occurred_at: str | None = None) -> StateView:
        return cls(
            id=state,
            label=STATE_LABELS[state],
            authority=STATE_AUTHORITY[state],
            explanation=STATE_EXPLANATIONS[state],
            occurred_at=occurred_at,
        )


@dataclass(frozen=True, slots=True)
class QuestProgress:
    quest: Quest
    state: StateView
    attempt: Attempt | None
    review: ReviewDecision | None
    unmet_prerequisites: tuple[str, ...]

    @property
    def is_verified(self) -> bool:
        return self.state.id is QuestState.VERIFIED

    @property
    def is_started(self) -> bool:
        return self.attempt is not None

    @property
    def claimed_xp(self) -> int:
        """XP the participant has claimed by their own record.

        Anything from `evidence_ready` onward counts as claimed: the participant has
        asserted the work is done. Nothing below that does, because starting is not doing.
        """
        claimed_states = {
            QuestState.EVIDENCE_READY,
            QuestState.LOCALLY_VALIDATED,
            QuestState.SUBMITTED,
            QuestState.NEEDS_CHANGES,
            QuestState.VERIFIED,
        }
        return self.quest.xp if self.state.id in claimed_states else 0

    @property
    def verified_xp(self) -> int:
        return self.quest.xp if self.is_verified else 0


@dataclass(frozen=True, slots=True)
class RegionProgress:
    region_id: str
    total: int
    verified: int
    claimed: int
    started: int
    by_state: dict[QuestState, int] = field(default_factory=dict)

    @property
    def verified_fraction(self) -> float:
        return self.verified / self.total if self.total else 0.0


@dataclass(frozen=True, slots=True)
class BadgeProgress:
    badge: Badge
    earned: bool
    pending_review: bool
    satisfied: int
    required: int
    reason: str

    @property
    def state_id(self) -> str:
        if self.earned:
            return "earned"
        if self.pending_review:
            return "pending"
        return "in-progress" if self.satisfied else "locked"


def compute_states(
    bundle: ContentBundle, participant: ParticipantState | None
) -> dict[str, QuestProgress]:
    """The current state of every quest, in one pass.

    Prerequisite satisfaction is defined as *verified*, not merely attempted: a quest whose
    prerequisite is only claimed would let a participant build on work nobody has confirmed.
    """
    progress: dict[str, QuestProgress] = {}
    recorded: dict[str, tuple[Attempt, ReviewDecision | None]] = {}

    if participant is not None:
        for quest_id in bundle.quests:
            attempt = participant.progress.attempt_for(quest_id)
            if attempt is not None:
                recorded[quest_id] = (attempt, participant.latest_review_for(attempt))

    verified_ids = {
        quest_id
        for quest_id, (attempt, review) in recorded.items()
        if attempt.recorded_state.value == "verified" and review is not None and review.is_approval
    }

    for quest in bundle.ordered_quests():
        unmet = tuple(p for p in quest.prerequisites if p not in verified_ids)
        entry = recorded.get(quest.id)
        if entry is None:
            state = StateView.of(QuestState.LOCKED if unmet else QuestState.AVAILABLE)
            progress[quest.id] = QuestProgress(quest, state, None, None, unmet)
            continue

        attempt, review = entry
        if attempt.recorded_state.value == "verified":
            # Re-derived, never believed. An attempt reaching here without a valid approval
            # was already refused as an integrity error during loading.
            state = StateView.of(QuestState.VERIFIED, review.reviewed_at if review else None)
        else:
            state = StateView.of(QuestState(attempt.recorded_state.value), attempt.updated_at)
        progress[quest.id] = QuestProgress(quest, state, attempt, review, unmet)

    return progress


def region_progress(
    bundle: ContentBundle, states: dict[str, QuestProgress]
) -> dict[str, RegionProgress]:
    result: dict[str, RegionProgress] = {}
    for region in bundle.ordered_regions():
        quests = bundle.quests_in_region(region.id)
        by_state: dict[QuestState, int] = {}
        verified = claimed = started = 0
        for quest in quests:
            entry = states[quest.id]
            by_state[entry.state.id] = by_state.get(entry.state.id, 0) + 1
            verified += 1 if entry.is_verified else 0
            claimed += 1 if entry.claimed_xp else 0
            started += 1 if entry.is_started else 0
        result[region.id] = RegionProgress(
            region_id=region.id,
            total=len(quests),
            verified=verified,
            claimed=claimed,
            started=started,
            by_state=by_state,
        )
    return result


def totals(states: dict[str, QuestProgress]) -> dict[str, int]:
    """Claimed and verified totals, kept separate on purpose (C02)."""
    return {
        "claimed_xp": sum(p.claimed_xp for p in states.values()),
        "verified_xp": sum(p.verified_xp for p in states.values()),
        "claimed_quests": sum(1 for p in states.values() if p.claimed_xp),
        "verified_quests": sum(1 for p in states.values() if p.is_verified),
        "total_quests": len(states),
        "available_xp": sum(p.quest.xp for p in states.values()),
    }


def badge_progress(
    bundle: ContentBundle, states: dict[str, QuestProgress], participant: ParticipantState | None
) -> list[BadgeProgress]:
    """Badge status, evaluated from verified work only.

    Every criterion counts verified quests. A badge awarded for claimed work would make the
    passport a record of assertions rather than of demonstrated capability.
    """
    verified_ids = {quest_id for quest_id, entry in states.items() if entry.is_verified}
    verified_xp = sum(entry.verified_xp for entry in states.values())
    verified_tags = {tag for quest_id in verified_ids for tag in bundle.quests[quest_id].tags}

    results: list[BadgeProgress] = []
    for badge in bundle.ordered_badges():
        criteria = badge.criteria
        satisfied = 0
        required = 0
        reasons: list[str] = []

        if criteria.all_quests:
            required += len(criteria.all_quests)
            done = [q for q in criteria.all_quests if q in verified_ids]
            satisfied += len(done)
            reasons.append(f"{len(done)} of {len(criteria.all_quests)} named quests verified")
        if criteria.any_quests:
            required += 1
            done = [q for q in criteria.any_quests if q in verified_ids]
            satisfied += 1 if done else 0
            reasons.append(f"{len(done)} of {len(criteria.any_quests)} alternatives verified")
        if criteria.verified_quest_count is not None:
            required += 1
            count = len(verified_ids)
            satisfied += 1 if count >= criteria.verified_quest_count else 0
            reasons.append(f"{count} of {criteria.verified_quest_count} verified quests")
        if criteria.verified_xp is not None:
            required += 1
            satisfied += 1 if verified_xp >= criteria.verified_xp else 0
            reasons.append(f"{verified_xp} of {criteria.verified_xp} verified XP")
        if criteria.region is not None:
            required += 1
            region_quests = {q.id for q in bundle.quests_in_region(criteria.region)}
            complete = bool(region_quests) and region_quests <= verified_ids
            satisfied += 1 if complete else 0
            reasons.append(
                f"{len(region_quests & verified_ids)} of {len(region_quests)} quests in "
                f"{criteria.region} verified"
            )
        if criteria.required_tags:
            required += len(criteria.required_tags)
            have = [t for t in criteria.required_tags if t in verified_tags]
            satisfied += len(have)
            reasons.append(
                f"{len(have)} of {len(criteria.required_tags)} required tags demonstrated"
            )

        machine_criteria_met = required > 0 and satisfied >= required
        awarded_by_reviewer = _badge_awarded_by_reviewer(badge, participant)

        if badge.award_type == "automatic":
            earned = machine_criteria_met
            pending = False
        else:
            # A reviewer-awarded or program-awarded badge is never granted by arithmetic.
            # Meeting the criteria only makes it eligible.
            earned = awarded_by_reviewer
            pending = machine_criteria_met and not awarded_by_reviewer

        results.append(
            BadgeProgress(
                badge=badge,
                earned=earned,
                pending_review=pending,
                satisfied=satisfied,
                required=max(required, 1),
                reason="; ".join(reasons) or "No machine-evaluable criteria",
            )
        )
    return results


def _badge_awarded_by_reviewer(badge: Badge, participant: ParticipantState | None) -> bool:
    """Whether a reviewer actually awarded this badge.

    Release one has no badge-award record type, so nothing can be awarded this way yet. The
    honest answer is therefore `False`, and the passport says "pending" rather than showing
    a badge nobody granted. The alternative — treating criteria as an award — is exactly the
    blurring of authority that ADR-011 exists to prevent.
    """
    del badge, participant
    return False
