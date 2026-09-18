"""Normalized content models.

Everything downstream — semantic validation, progress calculation, view models, templates —
reads these, never raw dictionaries and never the files themselves
(`docs/VIEW-MODEL-CONTRACT.md`). They are frozen because content is immutable once loaded:
a build that could mutate a quest halfway through rendering could not be deterministic.

Each model carries `source`, the repository-relative path it came from, so any problem
found later can name the file an author has to open.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

from quest_app.compat import StrEnum

# CONTENT-MODEL.md difficulty table. The typical XP is advisory: an unusual value produces a
# warning, never an error, because a maintainer may weight a quest deliberately.
LEVEL_LABELS: Final[dict[str, str]] = {
    "scout": "Scout",
    "explorer": "Explorer",
    "builder": "Builder",
    "navigator": "Navigator",
    "boss": "Boss",
}
TYPICAL_XP: Final[dict[str, int]] = {
    "scout": 10,
    "explorer": 20,
    "builder": 30,
    "navigator": 50,
    "boss": 100,
}
BOOKEND_LABELS: Final[dict[str, str]] = {
    "intent": "Intent",
    "validation": "Validation",
    "cross-bookend": "Cross-bookend",
    "foundation": "Foundation",
}


class AttemptState(StrEnum):
    """The six states a participant record can hold.

    `locked` and `available` are deliberately absent: they are computed from prerequisites
    and must never be writable (Stage 0 finding F3). `QuestState` is the display union.
    """

    IN_PROGRESS = "in_progress"
    EVIDENCE_READY = "evidence_ready"
    LOCALLY_VALIDATED = "locally_validated"
    SUBMITTED = "submitted"
    NEEDS_CHANGES = "needs_changes"
    VERIFIED = "verified"


class Decision(StrEnum):
    """The three decisions a reviewer may record.

    One vocabulary, in one place, because the browser form and the CLI both name these
    values. The CLI shipped with `approve` and `request-changes`, which nothing accepted, so
    every decision it would let a reviewer type was refused — and the CLI is the only
    reviewer path on a surface with no browser.
    """

    APPROVED = "approved"
    NEEDS_CHANGES = "needs_changes"
    REJECTED = "rejected"


class QuestState(StrEnum):
    """Every state a quest can be shown in, stored or derived."""

    LOCKED = "locked"
    AVAILABLE = "available"
    IN_PROGRESS = "in_progress"
    EVIDENCE_READY = "evidence_ready"
    LOCALLY_VALIDATED = "locally_validated"
    SUBMITTED = "submitted"
    NEEDS_CHANGES = "needs_changes"
    VERIFIED = "verified"


class Authority(StrEnum):
    """Who put a quest in its current state.

    This is the field that stops the interface implying a validator verified something.
    `UI-SPECIFICATION.md` requires the authority beside every state.
    """

    SYSTEM = "system"
    PARTICIPANT = "participant"
    REGISTERED_VALIDATOR = "registered_validator"
    REVIEWER = "reviewer"


STATE_LABELS: Final[dict[QuestState, str]] = {
    QuestState.LOCKED: "Locked",
    QuestState.AVAILABLE: "Available",
    QuestState.IN_PROGRESS: "In progress",
    QuestState.EVIDENCE_READY: "Evidence ready",
    QuestState.LOCALLY_VALIDATED: "Locally validated",
    QuestState.SUBMITTED: "Submitted for review",
    QuestState.NEEDS_CHANGES: "Needs changes",
    QuestState.VERIFIED: "Verified",
}

STATE_AUTHORITY: Final[dict[QuestState, Authority]] = {
    QuestState.LOCKED: Authority.SYSTEM,
    QuestState.AVAILABLE: Authority.SYSTEM,
    QuestState.IN_PROGRESS: Authority.PARTICIPANT,
    QuestState.EVIDENCE_READY: Authority.PARTICIPANT,
    QuestState.LOCALLY_VALIDATED: Authority.REGISTERED_VALIDATOR,
    QuestState.SUBMITTED: Authority.PARTICIPANT,
    QuestState.NEEDS_CHANGES: Authority.REVIEWER,
    QuestState.VERIFIED: Authority.REVIEWER,
}

STATE_EXPLANATIONS: Final[dict[QuestState, str]] = {
    QuestState.LOCKED: "Prerequisites are not satisfied yet.",
    QuestState.AVAILABLE: "Prerequisites are satisfied. Work has not started.",
    QuestState.IN_PROGRESS: "You started this quest.",
    QuestState.EVIDENCE_READY: "You assembled the required proof. Nothing has checked it yet.",
    QuestState.LOCALLY_VALIDATED: (
        "Required automated checks passed. Reviewer approval remains required."
    ),
    QuestState.SUBMITTED: "You requested review. A reviewer has not decided yet.",
    QuestState.NEEDS_CHANGES: "A reviewer asked for corrections. Your evidence is preserved.",
    QuestState.VERIFIED: "A reviewer approved this evidence.",
}

# `locally_validated` normally means validators returned qualifying results. A quest that
# declares none reaches the same state on the participant's word alone, and saying "required
# automated checks passed" there would be the interface asserting a check that does not
# exist — the one thing the authority field is in the model to prevent.
UNVALIDATED_LOCALLY_VALIDATED: Final[str] = (
    "This quest declares no automated checks, so this is your own assertion. "
    "Reviewer approval remains required."
)


@dataclass(frozen=True, slots=True)
class AcceptanceCriterion:
    """One numbered expectation, parsed from the quest body (ADR-016).

    `id` is positional and stable across edits to the wording; `text_hash` is what changes
    when the wording does, which is how a reviewer finding pinned to `ac-3` can be shown as
    possibly stale rather than silently re-pointed at different text.
    """

    id: str
    number: int
    text: str
    text_hash: str
    # The criterion with its inline Markdown rendered and sanitized. `text` stays the plain
    # source, because that is what the hash covers and what a plain-text export needs.
    safe_rendered_html: str = ""

    @property
    def dom_id(self) -> str:
        return f"criterion-{self.id}"


@dataclass(frozen=True, slots=True)
class ProofRequirement:
    id: str
    type: str
    description: str
    path: str | None = None
    validator: str | None = None
    required: bool = True


@dataclass(frozen=True, slots=True)
class NarrativeSection:
    """One `## heading` of the quest body, already rendered and sanitized.

    The field is named `safe_rendered_html` so a template author cannot mistake it for text
    that still needs escaping, and so a search for `| safe` lands on a name that says why
    (ADR-021).
    """

    key: str
    title: str
    heading_id: str
    safe_rendered_html: str


@dataclass(frozen=True, slots=True)
class Risk:
    external_write: bool = False
    sensitive_data: bool = False
    notes: str | None = None


@dataclass(frozen=True, slots=True)
class Quest:
    id: str
    version: int
    title: str
    summary: str
    region: str
    level: str
    xp: int
    estimated_minutes: int
    tags: tuple[str, ...]
    outcomes: tuple[str, ...]
    proof: tuple[ProofRequirement, ...]
    acceptance_criteria: tuple[AcceptanceCriterion, ...]
    sections: tuple[NarrativeSection, ...]
    content_hash: str
    source: str
    order: int | None = None
    tools: tuple[str, ...] = ()
    bookend: str | None = None
    risk: Risk = field(default_factory=Risk)
    prerequisites: tuple[str, ...] = ()
    related_quests: tuple[str, ...] = ()
    validators: tuple[str, ...] = ()
    author: str | None = None
    last_reviewed: str | None = None
    deprecated: bool = False

    @property
    def level_label(self) -> str:
        return LEVEL_LABELS[self.level]

    @property
    def bookend_label(self) -> str | None:
        return BOOKEND_LABELS.get(self.bookend) if self.bookend else None

    @property
    def required_proof(self) -> tuple[ProofRequirement, ...]:
        return tuple(p for p in self.proof if p.required)

    @property
    def optional_proof(self) -> tuple[ProofRequirement, ...]:
        return tuple(p for p in self.proof if not p.required)


@dataclass(frozen=True, slots=True)
class Region:
    id: str
    version: int
    title: str
    summary: str
    order: int
    accent: str
    outcomes: tuple[str, ...]
    source: str
    short_title: str | None = None
    icon: str | None = None
    tags: tuple[str, ...] = ()

    @property
    def display_title(self) -> str:
        return self.short_title or self.title


@dataclass(frozen=True, slots=True)
class BadgeCriteria:
    all_quests: tuple[str, ...] = ()
    any_quests: tuple[str, ...] = ()
    verified_quest_count: int | None = None
    verified_xp: int | None = None
    region: str | None = None
    required_tags: tuple[str, ...] = ()
    reviewer_statement: str | None = None


@dataclass(frozen=True, slots=True)
class Badge:
    id: str
    version: int
    title: str
    summary: str
    award_type: str
    icon: str
    criteria: BadgeCriteria
    source: str

    @property
    def award_label(self) -> str:
        return {
            "automatic": "Awarded automatically",
            "reviewer": "Awarded by a reviewer",
            "program": "Awarded by the program",
        }[self.award_type]


@dataclass(frozen=True, slots=True)
class TrackBalance:
    intent_minimum: int = 0
    validation_minimum: int = 0
    cross_bookend_minimum: int = 0


@dataclass(frozen=True, slots=True)
class Track:
    id: str
    version: int
    title: str
    summary: str
    quest_ids: tuple[str, ...]
    source: str
    focus_tags: tuple[str, ...] = ()
    balance: TrackBalance = field(default_factory=TrackBalance)


@dataclass(frozen=True, slots=True)
class NavigationItem:
    id: str
    label: str
    route: str
    icon: str | None = None


@dataclass(frozen=True, slots=True)
class SiteConfig:
    schema_version: int
    title: str
    curriculum: str
    tagline: str
    default_track: str
    navigation: tuple[NavigationItem, ...]
    source: str
    professional_role: str | None = None


@dataclass(frozen=True, slots=True)
class ContentBundle:
    """Everything authored, loaded and validated, indexed by stable ID."""

    site: SiteConfig
    quests: dict[str, Quest]
    regions: dict[str, Region]
    badges: dict[str, Badge]
    tracks: dict[str, Track]
    content_hash: str

    def quests_in_region(self, region_id: str) -> list[Quest]:
        return [q for q in self.ordered_quests() if q.region == region_id]

    def ordered_quests(self) -> list[Quest]:
        """Explicit `order` first, then a documented stable fallback.

        The fallback is region order, then title, then ID. Title before ID keeps a catalog
        readable; ID last guarantees the sort is total, so two builds never disagree.
        """
        region_order = {r.id: r.order for r in self.regions.values()}
        return sorted(
            self.quests.values(),
            key=lambda q: (
                region_order.get(q.region, 10_000),
                0 if q.order is not None else 1,
                q.order if q.order is not None else 0,
                q.title.casefold(),
                q.id,
            ),
        )

    def ordered_regions(self) -> list[Region]:
        return sorted(self.regions.values(), key=lambda r: (r.order, r.id))

    def ordered_badges(self) -> list[Badge]:
        return sorted(self.badges.values(), key=lambda b: (b.title.casefold(), b.id))

    def all_tags(self) -> list[str]:
        return sorted({tag for quest in self.quests.values() for tag in quest.tags})
