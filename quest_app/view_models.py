"""Display-ready models, one per page.

Templates receive these and nothing else (`docs/VIEW-MODEL-CONTRACT.md`). They do not open
files, parse front matter, calculate progress, resolve prerequisites, inspect Git, decide
authority, run validators or infer routes — all of that has happened by the time a template
is handed one of these objects.

Rendered Markdown travels in fields named `safe_rendered_html`, so a template author cannot
mistake it for text that still needs escaping and a reviewer grepping for `| safe` lands on
a name that says why.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from quest_app import routes
from quest_app.config import APPLICATION_VERSION
from quest_app.models import (
    AcceptanceCriterion,
    Badge,
    ContentBundle,
    NarrativeSection,
    ProofRequirement,
    Quest,
    QuestState,
    Region,
    SiteConfig,
)
from quest_app.progress import ParticipantState, ReviewDecision, ValidationResult
from quest_app.progress_calc import (
    BadgeProgress,
    QuestProgress,
    RegionProgress,
    StateView,
)
from quest_app.recommend import Recommendation


@dataclass(frozen=True, slots=True)
class NavItemView:
    id: str
    label: str
    route: str
    current: bool


@dataclass(frozen=True, slots=True)
class SiteView:
    title: str
    curriculum: str
    tagline: str
    professional_role: str | None
    navigation: tuple[NavItemView, ...]


@dataclass(frozen=True, slots=True)
class PageView:
    title: str
    description: str
    route: str
    nav_id: str
    heading: str
    eyebrow: str | None = None


@dataclass(frozen=True, slots=True)
class ParticipantView:
    """The display-safe participant summary. No paths, no evidence, no identifiers."""

    display_name: str
    track_title: str | None
    claimed_xp: int
    verified_xp: int
    claimed_quests: int
    verified_quests: int
    total_quests: int
    available_xp: int


@dataclass(frozen=True, slots=True)
class ServiceView:
    """What the page may say about the local service.

    A generated page is static, so it cannot know whether the service is running when the
    page is read. It says what it knows — whether the build had one — and the script leaves
    the honest default in place: controls are disabled with an explanation, never shown as
    working.
    """

    available: bool
    reason: str
    cli_alternative: str | None = None


@dataclass(frozen=True, slots=True)
class BuildView:
    application_version: str
    content_version: str
    built_at: str
    deterministic: bool


@dataclass(frozen=True, slots=True)
class BaseView:
    """What every page receives (`docs/VIEW-MODEL-CONTRACT.md`, "Shared page model")."""

    site: SiteView
    page: PageView
    participant: ParticipantView | None
    service: ServiceView
    build: BuildView
    flash: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RegionRefView:
    id: str
    title: str
    route: str
    accent: str


@dataclass(frozen=True, slots=True)
class QuestSummaryView:
    """The reusable quest card (C05). One record, many pages, no duplication."""

    id: str
    title: str
    summary: str
    route: str
    region: RegionRefView
    state: StateView
    level_id: str
    level_label: str
    xp: int
    estimated_minutes: int
    tags: tuple[str, ...]
    prerequisites_satisfied: int
    prerequisites_total: int
    recommendation_reasons: tuple[str, ...] = ()
    bookend: str | None = None
    external_write: bool = False
    deprecated: bool = False

    @property
    def search_text(self) -> str:
        """What client-side filtering matches against.

        Title, summary, tags, region and level only. Never participant evidence — a public
        catalog page must not become a search index over someone's private work.
        """
        parts = [self.title, self.summary, self.region.title, self.level_label, *self.tags]
        if self.bookend:
            parts.append(self.bookend)
        return " ".join(parts).lower()

    @property
    def risk_id(self) -> str:
        return "external-write" if self.external_write else "read-only"


@dataclass(frozen=True, slots=True)
class PrerequisiteView:
    id: str
    title: str
    route: str
    state: StateView
    satisfied: bool


@dataclass(frozen=True, slots=True)
class ProofView:
    id: str
    type: str
    description: str
    required: bool
    path: str | None
    validator: str | None
    status: str
    status_label: str
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class ValidatorView:
    id: str
    display_name: str
    latest_outcome: str | None
    latest_run_id: str | None
    latest_completed_at: str | None
    result_route: str | None
    available: bool
    unavailable_reason: str | None = None


@dataclass(frozen=True, slots=True)
class ActionView:
    """The one action a page offers, with an explicit reason when it is not available."""

    id: str
    label: str
    enabled: bool
    route: str | None = None
    method: str = "post"
    reason: str | None = None
    consequential: bool = False
    confirm: str | None = None


@dataclass(frozen=True, slots=True)
class QuestDetailView(BaseView):
    quest: QuestSummaryView = field(default=None)  # type: ignore[assignment]
    version: int = 1
    content_hash: str = ""
    sections: tuple[NarrativeSection, ...] = ()
    outcomes: tuple[str, ...] = ()
    acceptance_criteria: tuple[AcceptanceCriterion, ...] = ()
    required_proof: tuple[ProofView, ...] = ()
    optional_proof: tuple[ProofView, ...] = ()
    prerequisites: tuple[PrerequisiteView, ...] = ()
    related: tuple[QuestSummaryView, ...] = ()
    validators: tuple[ValidatorView, ...] = ()
    tools: tuple[str, ...] = ()
    primary_action: ActionView = field(default=None)  # type: ignore[assignment]
    evidence_route: str | None = None
    version_notice: str | None = None
    lock_notice: str | None = None
    risk_notice: str | None = None
    attempt_version: int | None = None


@dataclass(frozen=True, slots=True)
class RegionCardView:
    region: Region
    route: str
    progress: RegionProgress
    state_counts: tuple[tuple[StateView, int], ...]


@dataclass(frozen=True, slots=True)
class MapView(BaseView):
    regions: tuple[RegionCardView, ...] = ()
    totals: dict[str, int] = field(default_factory=dict)
    legend: tuple[StateView, ...] = ()


@dataclass(frozen=True, slots=True)
class FilterOption:
    value: str
    label: str
    count: int


@dataclass(frozen=True, slots=True)
class CatalogView(BaseView):
    quests: tuple[QuestSummaryView, ...] = ()
    times: tuple[FilterOption, ...] = ()
    regions: tuple[FilterOption, ...] = ()
    states: tuple[FilterOption, ...] = ()
    levels: tuple[FilterOption, ...] = ()
    tags: tuple[FilterOption, ...] = ()
    bookends: tuple[FilterOption, ...] = ()
    risks: tuple[FilterOption, ...] = ()


@dataclass(frozen=True, slots=True)
class RegionPageView(CatalogView):
    region: Region = field(default=None)  # type: ignore[assignment]
    region_progress: RegionProgress = field(default=None)  # type: ignore[assignment]
    badges: tuple[BadgeProgress, ...] = ()
    sequence: tuple[QuestSummaryView, ...] = ()


@dataclass(frozen=True, slots=True)
class RecommendationView:
    quest: QuestSummaryView
    reasons: tuple[str, ...]
    action: ActionView


@dataclass(frozen=True, slots=True)
class ActivityEvent:
    kind: str
    label: str
    authority: str
    occurred_at: str
    summary: str
    route: str | None = None


@dataclass(frozen=True, slots=True)
class HomeView(BaseView):
    primary: RecommendationView | None = None
    alternatives: tuple[RecommendationView, ...] = ()
    regions: tuple[RegionCardView, ...] = ()
    totals: dict[str, int] = field(default_factory=dict)
    activity: tuple[ActivityEvent, ...] = ()
    environment_warning: str | None = None
    is_new_participant: bool = False


@dataclass(frozen=True, slots=True)
class EvidenceView(BaseView):
    quest: QuestSummaryView = field(default=None)  # type: ignore[assignment]
    attempt_id: str | None = None
    evidence_path: str | None = None
    required_proof: tuple[ProofView, ...] = ()
    optional_proof: tuple[ProofView, ...] = ()
    validators: tuple[ValidatorView, ...] = ()
    results: tuple[ValidationResult, ...] = ()
    proof_document: str | None = None
    secret_scan_clean: bool | None = None
    actions: tuple[ActionView, ...] = ()
    git_summary: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ValidationResultView(BaseView):
    quest: QuestSummaryView = field(default=None)  # type: ignore[assignment]
    result: ValidationResult = field(default=None)  # type: ignore[assignment]
    evidence_route: str = ""
    outcome_label: str = ""
    outcome_explanation: str = ""


@dataclass(frozen=True, slots=True)
class PassportView(BaseView):
    totals: dict[str, int] = field(default_factory=dict)
    regions: tuple[RegionCardView, ...] = ()
    badges: tuple[BadgeProgress, ...] = ()
    timeline: tuple[ActivityEvent, ...] = ()
    capability_gaps: tuple[str, ...] = ()
    public_preview: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EnvironmentCheck:
    id: str
    name: str
    importance: str
    status: str
    detail: str
    remediation: str | None = None


@dataclass(frozen=True, slots=True)
class HealthView(BaseView):
    checks: tuple[EnvironmentCheck, ...] = ()


@dataclass(frozen=True, slots=True)
class ReviewQueueEntry:
    quest: QuestSummaryView
    attempt_id: str
    submitted_at: str
    route: str


@dataclass(frozen=True, slots=True)
class ReviewView(BaseView):
    quest: QuestSummaryView = field(default=None)  # type: ignore[assignment]
    attempt_id: str | None = None
    quest_version: int = 1
    evidence_hash: str | None = None
    evidence_changed: bool = False
    outcomes: tuple[str, ...] = ()
    acceptance_criteria: tuple[AcceptanceCriterion, ...] = ()
    required_proof: tuple[ProofView, ...] = ()
    results: tuple[ValidationResult, ...] = ()
    history: tuple[ReviewDecision, ...] = ()
    queue: tuple[ReviewQueueEntry, ...] = ()
    reproduction: str | None = None
    can_decide: bool = False
    blocked_reason: str | None = None


@dataclass(frozen=True, slots=True)
class ErrorPageView(BaseView):
    problems: tuple[dict[str, object], ...] = ()
    error_count: int = 0
    warning_count: int = 0


# --------------------------------------------------------------------------------------
# Builders
# --------------------------------------------------------------------------------------

PROOF_STATUS_LABELS = {
    "missing": "Not detected",
    "detected": "Detected",
    "warning": "Needs attention",
    "validated": "Validated",
    "reviewer_confirmed": "Confirmed by reviewer",
    "stale": "Changed since review",
}

OUTCOME_LABELS = {
    "pass": "Passed",
    "fail": "Failed",
    "warning": "Passed with advisories",
    "environment_failure": "Could not run",
    "inconclusive": "Inconclusive",
    "interrupted": "Interrupted",
}

OUTCOME_EXPLANATIONS = {
    "pass": "Every required check passed. Reviewer approval remains required.",
    "fail": "A required check failed. Your evidence is preserved and the quest is unchanged.",
    "warning": "The core checks passed and there are advisories worth reading.",
    "environment_failure": (
        "The validator could not evaluate your work because of the environment, "
        "not the work itself."
    ),
    "inconclusive": "There was not enough evidence to decide. This is not a failure.",
    "interrupted": "The run did not finish, so it says nothing either way.",
}


def build_site_view(site: SiteConfig, current_nav: str) -> SiteView:
    return SiteView(
        title=site.title,
        curriculum=site.curriculum,
        tagline=site.tagline,
        professional_role=site.professional_role,
        navigation=tuple(
            NavItemView(
                id=item.id,
                label=item.label,
                route=item.route,
                current=item.id == current_nav,
            )
            for item in site.navigation
        ),
    )


def build_participant_view(
    participant: ParticipantState | None, bundle: ContentBundle, totals: dict[str, int]
) -> ParticipantView | None:
    if participant is None:
        return None
    track = bundle.tracks.get(participant.progress.selected_track)
    return ParticipantView(
        display_name=participant.progress.display_name,
        track_title=track.title if track else None,
        claimed_xp=totals["claimed_xp"],
        verified_xp=totals["verified_xp"],
        claimed_quests=totals["claimed_quests"],
        verified_quests=totals["verified_quests"],
        total_quests=totals["total_quests"],
        available_xp=totals["available_xp"],
    )


def build_quest_summary(
    entry: QuestProgress, bundle: ContentBundle, reasons: tuple[str, ...] = ()
) -> QuestSummaryView:
    quest = entry.quest
    region = bundle.regions[quest.region]
    return QuestSummaryView(
        id=quest.id,
        title=quest.title,
        summary=quest.summary,
        route=routes.quest(quest.id),
        region=RegionRefView(
            id=region.id, title=region.title, route=routes.region(region.id), accent=region.accent
        ),
        state=entry.state,
        level_id=quest.level,
        level_label=quest.level_label,
        xp=quest.xp,
        estimated_minutes=quest.estimated_minutes,
        tags=quest.tags,
        prerequisites_satisfied=len(quest.prerequisites) - len(entry.unmet_prerequisites),
        prerequisites_total=len(quest.prerequisites),
        recommendation_reasons=reasons,
        bookend=quest.bookend,
        external_write=quest.risk.external_write,
        deprecated=quest.deprecated,
    )


def build_recommendation_view(
    recommendation: Recommendation, states: dict[str, QuestProgress], bundle: ContentBundle
) -> RecommendationView:
    entry = states[recommendation.quest.id]
    summary = build_quest_summary(entry, bundle, recommendation.top_reasons)
    label = "Continue quest" if entry.is_started else "View quest"
    return RecommendationView(
        quest=summary,
        reasons=recommendation.top_reasons,
        action=ActionView(
            id="open-quest",
            label=label,
            enabled=True,
            route=routes.quest(entry.quest.id),
            method="get",
        ),
    )


def build_proof_views(
    quest: Quest, detected: dict[str, str] | None = None
) -> tuple[tuple[ProofView, ...], tuple[ProofView, ...]]:
    """Proof requirements with whatever detection state the caller has established.

    With no detection information — on a quest page, before an attempt exists — every item
    reads "Not detected", which is accurate rather than pessimistic.
    """
    detected = detected or {}

    def view(item: ProofRequirement) -> ProofView:
        status = detected.get(item.id, "missing")
        return ProofView(
            id=item.id,
            type=item.type,
            description=item.description,
            required=item.required,
            path=item.path,
            validator=item.validator,
            status=status,
            status_label=PROOF_STATUS_LABELS.get(status, status),
        )

    return (
        tuple(view(item) for item in quest.required_proof),
        tuple(view(item) for item in quest.optional_proof),
    )


def build_legend() -> tuple[StateView, ...]:
    """Every state a map or catalog can show, in the order the lifecycle runs."""
    return tuple(
        StateView.of(state)
        for state in (
            QuestState.LOCKED,
            QuestState.AVAILABLE,
            QuestState.IN_PROGRESS,
            QuestState.EVIDENCE_READY,
            QuestState.LOCALLY_VALIDATED,
            QuestState.SUBMITTED,
            QuestState.NEEDS_CHANGES,
            QuestState.VERIFIED,
        )
    )


def build_region_cards(
    bundle: ContentBundle, states: dict[str, QuestProgress], regions: dict[str, RegionProgress]
) -> tuple[RegionCardView, ...]:
    cards = []
    for region in bundle.ordered_regions():
        progress = regions[region.id]
        counts = tuple(
            (StateView.of(state), count)
            for state, count in sorted(progress.by_state.items(), key=lambda pair: pair[0].value)
        )
        cards.append(
            RegionCardView(
                region=region,
                route=routes.region(region.id),
                progress=progress,
                state_counts=counts,
            )
        )
    return tuple(cards)


def build_filter_options(
    quests: tuple[QuestSummaryView, ...], bundle: ContentBundle
) -> dict[str, tuple[FilterOption, ...]]:
    """Catalog filters, derived entirely from the content that is present.

    Adding a quest with a new tag adds a filter. Nothing here enumerates a tag, a region or
    a level by name, which is what makes that true.
    """

    def count_by(key: Any) -> dict[str, int]:
        counts: dict[str, int] = {}
        for quest in quests:
            for value in key(quest):
                counts[value] = counts.get(value, 0) + 1
        return counts

    region_counts = count_by(lambda q: [q.region.id])
    state_counts = count_by(lambda q: [str(q.state.id)])
    level_counts = count_by(lambda q: [q.level_id])
    tag_counts = count_by(lambda q: list(q.tags))
    bookend_counts = count_by(lambda q: [q.bookend] if q.bookend else [])
    risk_counts = count_by(lambda q: [q.risk_id])

    from quest_app.models import BOOKEND_LABELS, LEVEL_LABELS, STATE_LABELS

    # Time buckets rather than raw minutes: a participant asks "have I got half an hour?",
    # not "is this quest under 47 minutes?". Only buckets that would match something are
    # offered, so no filter can empty the page on its own.
    buckets = ((30, "30 minutes or less"), (60, "An hour or less"), (120, "Two hours or less"))
    time_options = tuple(
        FilterOption(
            value=str(limit),
            label=label,
            count=sum(1 for q in quests if q.estimated_minutes <= limit),
        )
        for limit, label in buckets
        if any(q.estimated_minutes <= limit for q in quests)
    )

    return {
        "times": time_options,
        "regions": tuple(
            FilterOption(value=r.id, label=r.title, count=region_counts.get(r.id, 0))
            for r in bundle.ordered_regions()
            if region_counts.get(r.id)
        ),
        "states": tuple(
            FilterOption(
                value=str(state), label=STATE_LABELS[state], count=state_counts[str(state)]
            )
            for state in QuestState
            if state_counts.get(str(state))
        ),
        "levels": tuple(
            FilterOption(value=level, label=label, count=level_counts[level])
            for level, label in LEVEL_LABELS.items()
            if level_counts.get(level)
        ),
        "tags": tuple(
            FilterOption(value=tag, label=tag, count=count)
            for tag, count in sorted(tag_counts.items())
        ),
        "bookends": tuple(
            FilterOption(value=key, label=label, count=bookend_counts[key])
            for key, label in BOOKEND_LABELS.items()
            if bookend_counts.get(key)
        ),
        "risks": tuple(
            FilterOption(value=key, label=label, count=risk_counts[key])
            for key, label in (
                ("read-only", "Read-only"),
                ("external-write", "Writes to an external system"),
            )
            if risk_counts.get(key)
        ),
    }


def build_view_context(
    bundle: ContentBundle,
    participant: ParticipantState | None,
    totals_map: dict[str, int],
    *,
    nav_id: str,
    service: ServiceView,
    build: BuildView,
) -> dict[str, Any]:
    """The shared half of every page's view model."""
    return {
        "site": build_site_view(bundle.site, nav_id),
        "participant": build_participant_view(participant, bundle, totals_map),
        "service": service,
        "build": build,
    }


def default_build_view(bundle: ContentBundle, built_at: str) -> BuildView:
    return BuildView(
        application_version=APPLICATION_VERSION,
        content_version=bundle.content_hash[:19],
        built_at=built_at,
        deterministic=True,
    )


def offline_service_view() -> ServiceView:
    return ServiceView(
        available=False,
        reason="The local action service is not running, so nothing here can change state.",
        cli_alternative="make serve",
    )


def build_badge_views(badges: list[BadgeProgress]) -> tuple[BadgeProgress, ...]:
    return tuple(badges)


def summarize_quest_for_badge(badge: Badge) -> str:
    return badge.summary
