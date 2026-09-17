"""Generate the site.

Two properties matter more than anything else here.

**Determinism.** Two builds from the same inputs must produce the same bytes, so a diff of
`generated/` means content changed and nothing else. Every traversal is sorted, every
mapping is written with sorted keys, and the one genuinely varying value — the build time —
is confined to the manifest and the footer, where it is labelled.

**Atomicity.** A failed build must leave the last good site intact. The whole site is
rendered into a sibling directory and swapped in at the end, so a participant reading a page
while a build fails keeps reading the page that was there.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from quest_app import routes
from quest_app.markdown_render import strip_markdown
from quest_app.models import QuestState
from quest_app.pipeline import LoadedWorld
from quest_app.progress_calc import (
    QuestProgress,
    badge_progress,
    compute_states,
    region_progress,
    totals,
)
from quest_app.recommend import recommend
from quest_app.view_models import (
    ActionView,
    ActivityEvent,
    EnvironmentCheck,
    PageView,
    PrerequisiteView,
    ValidatorView,
    build_badge_views,
    build_filter_options,
    build_legend,
    build_participant_view,
    build_proof_views,
    build_quest_summary,
    build_recommendation_view,
    build_region_cards,
    build_site_view,
    default_build_view,
    offline_service_view,
)

OUTPUT_SUFFIX_NEW = ".building"
OUTPUT_SUFFIX_OLD = ".previous"


@dataclass(frozen=True, slots=True)
class BuildResult:
    output_root: Path
    page_count: int
    manifest: dict[str, Any]


def make_environment(templates_root: Path) -> Environment:
    """Jinja2 configured so a template mistake is loud rather than silent.

    `StrictUndefined` turns a typo in a field name into an error at build time instead of an
    empty string on a page. Autoescaping is on for every HTML template — the only
    pre-rendered HTML that reaches a template is the sanitized Markdown in
    `safe_rendered_html`, and that name is the whole warning system.
    """
    return Environment(
        loader=FileSystemLoader(str(templates_root)),
        autoescape=select_autoescape(default_for_string=True, default=True),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
        auto_reload=False,
    )


def url_for(current_route: str) -> Any:
    """A `url()` helper bound to the page being rendered.

    Links are emitted relative to the current page so the generated site works both served
    from the local service and opened straight from `generated/` in a browser, where a
    leading slash would mean the filesystem root.
    """

    def url(target: str) -> str:
        return routes.relative_to(target, current_route)

    return url


def build_site(world: LoadedWorld, *, built_at: str | None = None) -> BuildResult:
    """Render every page and swap the result into place atomically."""
    config = world.config
    bundle = world.content
    participant = world.participant

    states = compute_states(bundle, participant)
    regions = region_progress(bundle, states)
    totals_map = totals(states)
    badges = badge_progress(bundle, states, participant)
    recommendations = recommend(
        bundle, states, regions, participant.progress if participant else None
    )

    stamp = built_at or datetime.now(UTC).isoformat(timespec="seconds")
    build_view = default_build_view(bundle, stamp)
    service = offline_service_view()
    environment = make_environment(config.templates_root)

    staging = config.generated_root.with_suffix(OUTPUT_SUFFIX_NEW)
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)

    pages: list[tuple[str, str, dict[str, Any]]] = []

    def shared(nav_id: str, page: PageView) -> dict[str, Any]:
        return {
            "site": build_site_view(bundle.site, nav_id),
            "page": page,
            "participant": build_participant_view(participant, bundle, totals_map),
            "service": service,
            "build": build_view,
            "flash": (),
        }

    region_cards = build_region_cards(bundle, states, regions)
    summaries = {qid: build_quest_summary(entry, bundle) for qid, entry in states.items()}
    ordered_summaries = tuple(summaries[q.id] for q in bundle.ordered_quests())

    # ---- Home
    primary = (
        build_recommendation_view(recommendations[0], states, bundle) if recommendations else None
    )
    alternatives = tuple(build_recommendation_view(r, states, bundle) for r in recommendations[1:4])
    pages.append(
        (
            routes.HOME,
            "pages/home.html.j2",
            shared(
                "home",
                PageView(
                    title="Home",
                    description="Where you are, and the most useful thing to do next.",
                    route=routes.HOME,
                    nav_id="home",
                    heading=f"Welcome back, {participant.progress.display_name}"
                    if participant
                    else bundle.site.title,
                ),
            )
            | {
                "primary": primary,
                "alternatives": alternatives,
                "regions": region_cards,
                "totals": totals_map,
                "activity": _recent_activity(world, states),
                "environment_warning": None,
                "is_new_participant": participant is None or not participant.progress.attempts,
                "first_region": region_cards[0] if region_cards else None,
            },
        )
    )

    # ---- Map
    pages.append(
        (
            routes.MAP,
            "pages/map.html.j2",
            shared(
                "quest-map",
                PageView(
                    title="Quest map",
                    description="The whole journey, and how far you have travelled.",
                    route=routes.MAP,
                    nav_id="quest-map",
                    heading="Quest map",
                ),
            )
            | {"regions": region_cards, "totals": totals_map, "legend": build_legend()},
        )
    )

    # ---- Catalog
    filters = build_filter_options(ordered_summaries, bundle)
    pages.append(
        (
            routes.CATALOG,
            "pages/catalog.html.j2",
            shared(
                "catalog",
                PageView(
                    title="Catalog",
                    description="Find a quest by capability, tool, risk, difficulty or time.",
                    route=routes.CATALOG,
                    nav_id="catalog",
                    heading="Catalog",
                ),
            )
            | {"quests": ordered_summaries, "selected": {}, **filters},
        )
    )

    # ---- Regions
    for card in region_cards:
        region_quests = tuple(summaries[q.id] for q in bundle.quests_in_region(card.region.id))
        pages.append(
            (
                card.route,
                "pages/region.html.j2",
                shared(
                    "quest-map",
                    PageView(
                        title=card.region.title,
                        description=card.region.summary,
                        route=card.route,
                        nav_id="quest-map",
                        heading=card.region.title,
                    ),
                )
                | {
                    "region": card.region,
                    "region_progress": card.progress,
                    "sequence": region_quests,
                    "quests": region_quests,
                    "badges": tuple(b for b in badges if b.badge.criteria.region == card.region.id),
                    "selected": {},
                    "region_route": card.route,
                    **build_filter_options(region_quests, bundle),
                },
            )
        )

    # ---- Tag pages. A tag link has to lead somewhere without JavaScript.
    for tag_name in bundle.all_tags():
        tagged = tuple(summary for summary in ordered_summaries if tag_name in summary.tags)
        pages.append(
            (
                routes.tag(tag_name),
                "pages/tag.html.j2",
                shared(
                    "catalog",
                    PageView(
                        title=f"Tag · {tag_name}",
                        description=f"Every quest carrying the {tag_name} tag.",
                        route=routes.tag(tag_name),
                        nav_id="catalog",
                        heading=tag_name,
                    ),
                )
                | {"tag": tag_name, "quests": tagged},
            )
        )

    # ---- Quest detail
    for quest in bundle.ordered_quests():
        entry = states[quest.id]
        pages.append(
            (
                routes.quest(quest.id),
                "pages/quest_detail.html.j2",
                shared(
                    "catalog",
                    PageView(
                        title=quest.title,
                        description=quest.summary,
                        route=routes.quest(quest.id),
                        nav_id="catalog",
                        heading=quest.title,
                    ),
                )
                | _quest_detail_context(entry, bundle, summaries, world),
            )
        )

    # ---- Evidence, validation results, review
    for quest in bundle.ordered_quests():
        entry = states[quest.id]
        pages.append(
            (
                routes.evidence(quest.id),
                "pages/evidence.html.j2",
                shared(
                    "evidence",
                    PageView(
                        title=f"Evidence · {quest.title}",
                        description="What you have assembled, and what remains.",
                        route=routes.evidence(quest.id),
                        nav_id="evidence",
                        heading=quest.title,
                    ),
                )
                | _evidence_context(entry, summaries[quest.id], world),
            )
        )
        for result in _results_for(entry, world):
            route = routes.validation(quest.id, result.run_id)
            from quest_app.view_models import OUTCOME_EXPLANATIONS, OUTCOME_LABELS

            pages.append(
                (
                    route,
                    "pages/validation_result.html.j2",
                    shared(
                        "evidence",
                        PageView(
                            title=f"Validation · {result.run_id}",
                            description="What passed, what failed, and how to reproduce it.",
                            route=route,
                            nav_id="evidence",
                            heading=OUTCOME_LABELS.get(result.outcome, result.outcome),
                        ),
                    )
                    | {
                        "quest": summaries[quest.id],
                        "result": result,
                        "evidence_route": routes.evidence(quest.id),
                        "outcome_label": OUTCOME_LABELS.get(result.outcome, result.outcome),
                        "outcome_explanation": OUTCOME_EXPLANATIONS.get(result.outcome, ""),
                    },
                )
            )

    attempt_rows = tuple(
        {
            "quest": summaries[quest_id],
            "attempt_id": entry.attempt.attempt_id,
            "evidence_path": entry.attempt.evidence_path,
            "evidence_route": routes.evidence(quest_id),
            "updated_at": entry.attempt.updated_at,
        }
        for quest_id, entry in sorted(states.items())
        if entry.attempt is not None
    )
    pages.append(
        (
            routes.EVIDENCE_INDEX,
            "pages/evidence_index.html.j2",
            shared(
                "evidence",
                PageView(
                    title="Evidence",
                    description=(
                        "Every evidence package you have started, and where each one lives."
                    ),
                    route=routes.EVIDENCE_INDEX,
                    nav_id="evidence",
                    heading="Evidence",
                ),
            )
            | {"attempts": attempt_rows},
        )
    )

    pages.append(
        (
            routes.REVIEW_INDEX,
            "pages/review.html.j2",
            shared(
                "reviewer",
                PageView(
                    title="Reviewer",
                    description="Evidence waiting for a decision.",
                    route=routes.REVIEW_INDEX,
                    nav_id="reviewer",
                    heading="Reviewer",
                ),
            )
            | _review_queue_context(states, summaries, world),
        )
    )

    # ---- Passport, environment
    pages.append(
        (
            routes.PASSPORT,
            "pages/passport.html.j2",
            shared(
                "passport",
                PageView(
                    title="Passport",
                    description="What you have credibly demonstrated.",
                    route=routes.PASSPORT,
                    nav_id="passport",
                    heading="Passport",
                ),
            )
            | {
                "totals": totals_map,
                "regions": region_cards,
                "badges": build_badge_views(badges),
                "timeline": _verified_timeline(states),
                "capability_gaps": _capability_gaps(bundle, states),
                "public_preview": _public_preview(world, totals_map),
            },
        )
    )
    pages.append(
        (
            routes.HEALTH,
            "pages/health.html.j2",
            shared(
                "environment",
                PageView(
                    title="Environment health",
                    description="Whether your machine is ready, safe and connected enough.",
                    route=routes.HEALTH,
                    nav_id="environment",
                    heading="Environment health",
                ),
            )
            | {"checks": _environment_checks(world, stamp)},
        )
    )

    for route, template_name, context in pages:
        _write(
            staging,
            route,
            environment.get_template(template_name).render(**context, url=url_for(route)),
        )

    _copy_assets(config.assets_root, staging / "assets")
    manifest = _write_indexes(staging, world, states, ordered_summaries, stamp)
    _swap(config.generated_root, staging)

    return BuildResult(output_root=config.generated_root, page_count=len(pages), manifest=manifest)


# --------------------------------------------------------------------------------------
# Page contexts
# --------------------------------------------------------------------------------------


def _results_for(entry: QuestProgress, world: LoadedWorld) -> tuple[Any, ...]:
    if world.participant is None or entry.attempt is None:
        return ()
    return world.participant.results_for(entry.attempt)


def _quest_detail_context(
    entry: QuestProgress, bundle: Any, summaries: dict[str, Any], world: LoadedWorld
) -> dict[str, Any]:
    quest = entry.quest
    required, optional = build_proof_views(quest)
    prerequisites = tuple(
        PrerequisiteView(
            id=pid,
            title=bundle.quests[pid].title,
            route=routes.quest(pid),
            state=summaries[pid].state,
            satisfied=pid not in entry.unmet_prerequisites,
        )
        for pid in quest.prerequisites
        if pid in bundle.quests
    )
    results = _results_for(entry, world)
    latest: dict[str, Any] = {}
    for result in results:
        latest[result.validator_id] = result

    validators = tuple(
        ValidatorView(
            id=vid,
            display_name=vid.replace("-", " ").capitalize(),
            latest_outcome=latest[vid].outcome if vid in latest else None,
            latest_run_id=latest[vid].run_id if vid in latest else None,
            latest_completed_at=latest[vid].completed_at if vid in latest else None,
            result_route=routes.validation(quest.id, latest[vid].run_id) if vid in latest else None,
            available=False,
            unavailable_reason="Start the local service to run checks from this page.",
        )
        for vid in quest.validators
    )

    if entry.state.id is QuestState.LOCKED:
        action = ActionView(
            id="start-quest",
            label="Start quest",
            enabled=False,
            reason=(
                f"{len(entry.unmet_prerequisites)} prerequisite(s) are not verified yet. "
                "They are listed above with links."
            ),
        )
    elif entry.attempt is None:
        action = ActionView(
            id="start-quest",
            label="Start quest",
            enabled=False,
            route=routes.evidence(quest.id),
            reason="Start the local service to record progress.",
        )
    else:
        action = ActionView(
            id="continue-quest",
            label="Open evidence workspace",
            enabled=True,
            route=routes.evidence(quest.id),
            method="get",
        )

    version_notice = None
    if entry.attempt is not None and entry.attempt.quest_version < quest.version:
        version_notice = (
            f"You are working against version {entry.attempt.quest_version}; version "
            f"{quest.version} is published. Your attempt is not migrated automatically, and "
            "your evidence is untouched."
        )

    return {
        "quest": summaries[quest.id],
        "version": quest.version,
        "content_hash": quest.content_hash,
        "sections": quest.sections,
        "outcomes": quest.outcomes,
        "acceptance_criteria": quest.acceptance_criteria,
        "required_proof": required,
        "optional_proof": optional,
        "prerequisites": prerequisites,
        "related": tuple(summaries[r] for r in quest.related_quests if r in summaries),
        "validators": validators,
        "tools": quest.tools,
        "primary_action": action,
        "evidence_route": routes.evidence(quest.id) if entry.attempt else None,
        "version_notice": version_notice,
        "lock_notice": (
            "Verify its prerequisites first. You can read everything below meanwhile."
            if entry.state.id is QuestState.LOCKED
            else None
        ),
        "risk_notice": (
            quest.risk.notes
            or "Every external write is previewed and confirmed immediately before it happens."
            if quest.risk.external_write
            else None
        ),
        "attempt_version": entry.attempt.quest_version if entry.attempt else None,
    }


def _evidence_context(entry: QuestProgress, summary: Any, world: LoadedWorld) -> dict[str, Any]:
    from quest_app.evidence import detect_proof, scan_evidence

    quest = entry.quest
    results = _results_for(entry, world)
    evidence_path = entry.attempt.evidence_path if entry.attempt else None
    detected = detect_proof(quest, world.config, evidence_path, results)
    required, optional = build_proof_views(quest, detected)
    latest: dict[str, Any] = {r.validator_id: r for r in results}
    validators = tuple(
        ValidatorView(
            id=vid,
            display_name=vid.replace("-", " ").capitalize(),
            latest_outcome=latest[vid].outcome if vid in latest else None,
            latest_run_id=latest[vid].run_id if vid in latest else None,
            latest_completed_at=latest[vid].completed_at if vid in latest else None,
            result_route=routes.validation(quest.id, latest[vid].run_id) if vid in latest else None,
            available=False,
            unavailable_reason="Start the local service to run this check.",
        )
        for vid in quest.validators
    )
    actions = (
        ActionView(
            id="mark-evidence-ready",
            label="Mark evidence ready",
            enabled=False,
            reason="Start the local service to change state.",
        ),
        ActionView(
            id="submit-for-review",
            label="Submit for review",
            enabled=False,
            reason="Start the local service to submit.",
            consequential=True,
        ),
    )
    return {
        "quest": summary,
        "attempt_id": entry.attempt.attempt_id if entry.attempt else None,
        "evidence_path": entry.attempt.evidence_path if entry.attempt else None,
        "required_proof": required,
        "optional_proof": optional,
        "validators": validators,
        "results": results,
        "proof_document": None,
        # The scan runs at build time so the page can say something true about the evidence
        # as it stands. It is also enforced at the moment of submission, which is the check
        # that actually matters.
        "secret_scan_clean": (
            not scan_evidence(world.config, evidence_path) if evidence_path else None
        ),
        "actions": actions if entry.attempt else (),
        "git_summary": git_summary_for(world, evidence_path),
    }


def git_summary_for(world: LoadedWorld, evidence_path: str | None) -> dict[str, Any]:
    """Repository status for the evidence page. Reports and advises; never acts."""
    from quest_app.git_status import summary_for

    return summary_for(world.config.repo_root, evidence_path)


def _review_queue_context(
    states: dict[str, QuestProgress], summaries: dict[str, Any], world: LoadedWorld
) -> dict[str, Any]:
    from quest_app.view_models import ReviewQueueEntry

    queue = tuple(
        ReviewQueueEntry(
            quest=summaries[quest_id],
            attempt_id=entry.attempt.attempt_id,
            submitted_at=entry.attempt.updated_at,
            route=routes.review(quest_id),
        )
        for quest_id, entry in sorted(states.items())
        if entry.attempt is not None and entry.state.id is QuestState.SUBMITTED
    )
    del world
    return {
        "quest": None,
        "attempt_id": None,
        "quest_version": 1,
        "evidence_hash": None,
        "evidence_changed": False,
        "outcomes": (),
        "acceptance_criteria": (),
        "required_proof": (),
        "results": (),
        "history": (),
        "queue": queue,
        "reproduction": None,
        "can_decide": False,
        "blocked_reason": (
            "Recording a decision needs the local service. Until Stage 7 lands the reviewer "
            "workflow, this page reports what is waiting."
        ),
    }


def _recent_activity(
    world: LoadedWorld, states: dict[str, QuestProgress]
) -> tuple[ActivityEvent, ...]:
    if world.participant is None:
        return ()
    events: list[ActivityEvent] = []
    for quest_id, entry in states.items():
        if entry.attempt is None:
            continue
        for result in world.participant.results_for(entry.attempt):
            events.append(
                ActivityEvent(
                    kind="validation",
                    label="Validation",
                    authority="registered_validator",
                    occurred_at=result.completed_at,
                    summary=f"{result.validator_id} · {result.outcome.replace('_', ' ')}",
                    route=routes.validation(quest_id, result.run_id),
                )
            )
        review = entry.review
        if review is not None:
            events.append(
                ActivityEvent(
                    kind="review",
                    label="Review",
                    authority="reviewer",
                    occurred_at=review.reviewed_at,
                    summary=f"{entry.quest.title} · {review.decision.replace('_', ' ')}",
                    route=routes.quest(quest_id),
                )
            )
    return tuple(sorted(events, key=lambda e: (e.occurred_at, e.summary), reverse=True)[:8])


def _verified_timeline(states: dict[str, QuestProgress]) -> tuple[ActivityEvent, ...]:
    events = [
        ActivityEvent(
            kind="verified",
            label="Verified",
            authority="reviewer",
            occurred_at=entry.review.reviewed_at,
            summary=f"{entry.quest.title} · {entry.quest.xp} XP",
            route=routes.quest(entry.quest.id),
        )
        for entry in states.values()
        if entry.is_verified and entry.review is not None
    ]
    return tuple(sorted(events, key=lambda e: (e.occurred_at, e.summary), reverse=True))


def _capability_gaps(bundle: Any, states: dict[str, QuestProgress]) -> tuple[str, ...]:
    """Where breadth is missing, named by region and bookend rather than scored."""
    gaps: list[str] = []
    for region in bundle.ordered_regions():
        quests = bundle.quests_in_region(region.id)
        if quests and not any(states[q.id].is_verified for q in quests):
            gaps.append(f"Nothing verified yet in {region.title}.")
    verified = [entry.quest for entry in states.values() if entry.is_verified]
    for bookend, label in (
        ("intent", "turning intent into structured work"),
        ("validation", "validating delivered behaviour"),
    ):
        if not any(q.bookend == bookend for q in verified):
            gaps.append(f"No verified work yet on {label}.")
    return tuple(gaps)


def _public_preview(world: LoadedWorld, totals_map: dict[str, int]) -> dict[str, Any]:
    """Exactly what an opt-in share would contain, and nothing else.

    No evidence paths, repository URLs, ticket contents, credentials or email addresses —
    the page shows this so a participant can check before choosing to share it.
    """
    participant = world.participant
    return {
        "display_name": participant.progress.display_name if participant else "—",
        "verified_quests": totals_map["verified_quests"],
        "verified_xp": totals_map["verified_xp"],
        "track": participant.progress.selected_track if participant else "—",
        "curriculum": world.content.site.curriculum,
    }


def _environment_checks(world: LoadedWorld, stamp: str) -> tuple[EnvironmentCheck, ...]:
    """What a static page can honestly say about the environment.

    A generated page cannot inspect the machine at the moment it is read, so every check
    here reports what was true at build time and says so. Live checks arrive with the local
    service; claiming them now would be the page pretending.
    """
    import sys

    config = world.config
    checks = [
        EnvironmentCheck(
            id="python",
            name="Python",
            importance="required",
            status="pass",
            detail=(
                f"{sys.version_info.major}.{sys.version_info.minor}."
                f"{sys.version_info.micro} at build time"
            ),
        ),
        EnvironmentCheck(
            id="content",
            name="Curriculum content",
            importance="required",
            status="pass",
            detail=f"{len(world.content.quests)} quest(s) validated at {stamp}",
        ),
        EnvironmentCheck(
            id="participant-root",
            name="Participant directory",
            importance="required",
            status="pass" if config.participant_root.exists() else "fail",
            detail=f"{config.relative(config.participant_root)}",
            remediation=None if config.participant_root.exists() else "make serve",
        ),
        EnvironmentCheck(
            id="progress",
            name="Participant progress",
            importance="optional",
            status="pass" if world.participant else "warning",
            detail="loaded" if world.participant else "no progress file yet — start a quest",
        ),
        EnvironmentCheck(
            id="service",
            name="Local action service",
            importance="required",
            status="unknown",
            detail="A generated page cannot tell whether it is running.",
            remediation="make serve",
        ),
    ]
    return tuple(checks)


# --------------------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------------------


def _write(root: Path, route: str, html: str) -> None:
    target = root / routes.output_path(route)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html, encoding="utf-8")


def _copy_assets(source: Path, destination: Path) -> None:
    if not source.exists():
        return
    shutil.copytree(source, destination)


def _write_indexes(
    root: Path,
    world: LoadedWorld,
    states: dict[str, QuestProgress],
    summaries: tuple[Any, ...],
    stamp: str,
) -> dict[str, Any]:
    """Search, tag, region, relationship and build indexes.

    All generated from normalized content, all written with sorted keys. The search index
    deliberately contains published quest text only: a catalog page must not become a search
    index over someone's private evidence.
    """
    bundle = world.content

    search = [
        {
            "id": summary.id,
            "title": summary.title,
            "route": summary.route,
            "region": summary.region.id,
            "level": summary.level_id,
            "tags": list(summary.tags),
            "text": strip_markdown(f"{summary.title} {summary.summary}"),
        }
        for summary in summaries
    ]
    tags: dict[str, list[str]] = {}
    for summary in summaries:
        for tag in summary.tags:
            tags.setdefault(tag, []).append(summary.id)

    relationships = {
        quest.id: {
            "prerequisites": list(quest.prerequisites),
            "related": list(quest.related_quests),
            "unlocks": sorted(
                other.id for other in bundle.quests.values() if quest.id in other.prerequisites
            ),
        }
        for quest in bundle.ordered_quests()
    }

    manifest = {
        "application_version": world.config
        and __import__("quest_app.config", fromlist=["x"]).APPLICATION_VERSION,
        "content_hash": bundle.content_hash,
        "built_at": stamp,
        "quests": len(bundle.quests),
        "regions": len(bundle.regions),
        "badges": len(bundle.badges),
        "tracks": len(bundle.tracks),
        "has_participant_state": world.participant is not None,
        "quest_hashes": {q.id: q.content_hash for q in bundle.ordered_quests()},
    }

    index_root = root / "indexes"
    index_root.mkdir(parents=True, exist_ok=True)
    for name, payload in (
        ("search", search),
        ("tags", {tag: sorted(ids) for tag, ids in sorted(tags.items())}),
        (
            "regions",
            {r.id: [q.id for q in bundle.quests_in_region(r.id)] for r in bundle.ordered_regions()},
        ),
        ("relationships", relationships),
        ("states", {qid: str(entry.state.id) for qid, entry in sorted(states.items())}),
    ):
        (index_root / f"{name}.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    (root / "build-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def _swap(target: Path, staging: Path) -> None:
    """Replace the published site with the staged one, keeping the old until it is safe.

    The rename is the publish. Everything before it can fail without a participant ever
    seeing a half-built site.
    """
    previous = target.with_suffix(OUTPUT_SUFFIX_OLD)
    if previous.exists():
        shutil.rmtree(previous)
    if target.exists():
        target.rename(previous)
    staging.rename(target)
    if previous.exists():
        shutil.rmtree(previous)
