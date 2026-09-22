"""Which state transitions a participant may make, and which nothing may make.

The table is small and explicit because the alternative — deciding at each call site whether
a change is allowed — is how `verified` eventually gets written by something that is not a
reviewer.

Two rules are absolute:

* nothing in this module can produce `verified`. Verified completion is the shadow of an
  approved review (ADR-011), so it is derived at load time and never written as a
  transition;
* a validation run is not a transition (ADR-017). Running validators appends a result; the
  participant then asks for `locally_validated`, and that request is refused unless the
  results actually support it. That condition cannot be expressed in the table below, so it
  is passed to `store.transition_attempt` as a guard — in the store rather than in the
  service, so no other caller can reach the transition without it.
"""

from __future__ import annotations

from dataclasses import dataclass

from quest_app.models import AttemptState

# The actions a participant confirms before they happen (C21), and the words they confirm.
# One definition: the quest page renders it as a required checkbox and the service refuses a
# submission without it, so the rule the page states is the rule the service keeps (ADR-033).
CONFIRMATIONS: dict[str, str] = {
    "start-quest": "Start this quest and create an evidence package in my repository",
    "submit-for-review": "Submit this evidence for review. A reviewer will read it",
    # The one action that produces verified completion and verified XP, and the last one
    # this list reached. Until round 8 the reviewer's decision was confirmed by a
    # `window.confirm` in the page's script and by nothing else, so a browser with
    # scripting off, the JSON endpoint and the CLI all recorded an approval unguarded.
    "record-review": (
        "Record this decision. Approving produces verified completion and verified XP"
    ),
}


@dataclass(frozen=True, slots=True)
class Transition:
    """One allowed move, and who is allowed to ask for it."""

    action: str
    source: frozenset[AttemptState] | None
    target: AttemptState
    actor: str
    description: str


# `source=None` means "no attempt exists yet".
TRANSITIONS: tuple[Transition, ...] = (
    Transition(
        action="start-quest",
        source=None,
        target=AttemptState.IN_PROGRESS,
        actor="participant",
        description="Start work and create an evidence package.",
    ),
    Transition(
        action="resume-quest",
        source=frozenset({AttemptState.NEEDS_CHANGES}),
        target=AttemptState.IN_PROGRESS,
        actor="participant",
        description="Resume after a reviewer asked for changes.",
    ),
    Transition(
        action="mark-evidence-ready",
        source=frozenset({AttemptState.IN_PROGRESS}),
        target=AttemptState.EVIDENCE_READY,
        actor="participant",
        description="Assert that the required proof is assembled.",
    ),
    Transition(
        action="reopen-evidence",
        source=frozenset({AttemptState.EVIDENCE_READY, AttemptState.LOCALLY_VALIDATED}),
        target=AttemptState.IN_PROGRESS,
        actor="participant",
        description="Go back to working on the evidence.",
    ),
    Transition(
        action="mark-locally-validated",
        source=frozenset({AttemptState.EVIDENCE_READY}),
        target=AttemptState.LOCALLY_VALIDATED,
        actor="participant",
        description="Record that every required validator returned a qualifying result.",
    ),
    Transition(
        action="submit-for-review",
        source=frozenset({AttemptState.EVIDENCE_READY, AttemptState.LOCALLY_VALIDATED}),
        target=AttemptState.SUBMITTED,
        actor="participant",
        description="Ask a reviewer to decide.",
    ),
    Transition(
        action="withdraw-submission",
        source=frozenset({AttemptState.SUBMITTED}),
        target=AttemptState.IN_PROGRESS,
        actor="participant",
        description="Withdraw a submission before a reviewer has decided.",
    ),
)

BY_ACTION = {transition.action: transition for transition in TRANSITIONS}

# Written only by the reviewer workflow, from an approved review. Listed here so that a
# reader of this module can see what is deliberately absent from the table above.
REVIEWER_ONLY_STATES = frozenset({AttemptState.VERIFIED, AttemptState.NEEDS_CHANGES})


class TransitionError(ValueError):
    """A transition that is not allowed, with a reason a participant can act on."""


def check(action: str, current: AttemptState | None) -> Transition:
    """The transition for `action`, if it is legal from `current`."""
    transition = BY_ACTION.get(action)
    if transition is None:
        raise TransitionError(f"{action!r} is not an action this application performs")
    if transition.source is None:
        if current is not None:
            raise TransitionError(
                f"This quest already has an attempt in state {current.value!r}, "
                "so it cannot be started again."
            )
        return transition
    if current is None:
        raise TransitionError(f"{action!r} needs an attempt in progress; none has been started.")
    if current not in transition.source:
        allowed = ", ".join(sorted(state.value for state in transition.source))
        raise TransitionError(
            f"{action!r} is only possible from {allowed}; this attempt is {current.value!r}."
        )
    return transition


def allowed_actions(current: AttemptState | None) -> list[Transition]:
    """Every action a participant may take from here, for building a UI without guessing."""
    return [
        transition
        for transition in TRANSITIONS
        if (transition.source is None and current is None)
        or (transition.source is not None and current is not None and current in transition.source)
    ]
