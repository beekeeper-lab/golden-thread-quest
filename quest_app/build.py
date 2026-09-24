"""Generate the site.

Two properties matter more than anything else here.

**Determinism.** Two builds from the same inputs must produce the same bytes, so a diff of
`generated/` means content changed and nothing else. Every traversal is sorted, every
mapping is written with sorted keys, and the one genuinely varying value — the build time —
is confined to the manifest and the footer, where it is labeled.

**Atomicity.** A failed build must leave the last good site intact. The whole site is
rendered into a sibling directory and swapped in at the end, so a participant reading a page
while a build fails keeps reading the page that was there.
"""

from __future__ import annotations

import contextlib
import json
import os
import shutil
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from quest_app import routes
from quest_app.config import APPLICATION_VERSION, AppConfig
from quest_app.errors import ProblemReport
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
from quest_app.state_machine import CONFIRMATIONS, DECISION_CONFIRMATIONS, allowed_actions
from quest_app.view_models import (
    ActionView,
    ActivityEvent,
    EnvironmentCheck,
    PageView,
    PrerequisiteView,
    ServiceView,
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
OUTPUT_SUFFIX_LOCK = ".lock"


@dataclass(frozen=True, slots=True)
class BuildResult:
    output_root: Path
    page_count: int
    manifest: dict[str, Any]


def build_stamp() -> str:
    """The build timestamp, honouring `SOURCE_DATE_EPOCH`.

    Everything else about a build is a function of its inputs, so this stamp is the only
    thing that changes between two builds of the same content — which made the documented
    claim that two builds are byte-identical false for the command a reader actually runs.
    Setting `SOURCE_DATE_EPOCH` to a fixed value now makes it true, by the same convention
    the rest of the reproducible-builds world uses.
    """
    raw = os.environ.get("SOURCE_DATE_EPOCH")
    if raw:
        try:
            moment = datetime.fromtimestamp(int(raw.strip()), tz=timezone.utc)
        except (ValueError, OverflowError, OSError):
            # An unusable value is not worth failing a build over, and silently ignoring it
            # is better than pretending the output is reproducible when it is not.
            return datetime.now(timezone.utc).isoformat(timespec="seconds")
        return moment.isoformat(timespec="seconds")
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def render_error_page(config: AppConfig, report: ProblemReport) -> Path:
    """Render the authoring-error screen (U11) somewhere safe to look at it.

    Deliberately not into `generated/`: a failed build must leave the last good site
    standing, so writing a page of errors over it would trade one requirement for another.
    It goes to the gitignored local-data directory and the CLI prints the path.
    """
    from quest_app.config import APPLICATION_VERSION
    from quest_app.view_models import (
        BuildView,
        NavItemView,
        PageView,
        ServiceView,
        SiteView,
    )

    target: Path = config.local_data_root / "build-errors" / "index.html"
    environment = make_environment(config.templates_root)
    route = "/errors/"
    problems = tuple(problem.to_dict() for problem in report.sorted_problems())
    html = environment.get_template("pages/content_error.html.j2").render(
        url=url_for(route),
        site=SiteView(
            title="Golden Thread Quest",
            curriculum="The AI Context Engineer Journey",
            tagline="Content that does not validate is never published.",
            professional_role=None,
            navigation=(NavItemView(id="home", label="Home", route="/", current=False),),
        ),
        page=PageView(
            title="Content errors",
            description="Why the build refused to publish.",
            route=route,
            nav_id="home",
            heading="This content was not published",
        ),
        participant=None,
        service=ServiceView(available=False, reason="A failed build is not served."),
        build=BuildView(
            application_version=APPLICATION_VERSION,
            content_version="unpublished",
            built_at=build_stamp(),
            deterministic=False,
        ),
        flash=(),
        problems=problems,
        error_count=len(report.errors),
        warning_count=len(report.warnings),
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html, encoding="utf-8")
    return target


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


@contextmanager
def _exclusive_output(config: AppConfig) -> Iterator[None]:
    """Hold an exclusive lock on the output directory for the whole build.

    Every build stages into one directory and publishes it by rename. Two builds in the same
    repository therefore share one staging directory, and the second one's first act is to
    delete it: `shutil.rmtree` on a tree the first build is still writing. Round 5 reproduced
    it three times out of three and the crash was the good case. Twice, both processes exited
    zero and published a site holding 3 and 20 pages out of 53, because the loser's rename
    landed on a staging directory the winner had already half-removed.

    Round 4 put the same kind of lock on `participant/progress.yaml`, which serialises action
    against action. Nothing covered build against build: `quest-app build` and `make build`
    take no lock at all, and the service rebuilds on every action.

    The lock is advisory and POSIX-only, and **not being able to lock is never a reason to
    refuse to publish**. Round 5 wrote that sentence here, gave this function the store's
    shape, and gave it only the store's `ImportError` branch: an unwritable `generated.lock`
    or a filesystem answering `ENOLCK` crashed every publisher with a traceback carrying
    absolute paths, on exactly the filesystem the fall-through was written for. Round 6 found
    it twice, from two lenses. The parity the ADR claims is now in the code.
    """
    try:
        import fcntl
    except ImportError:  # pragma: no cover - POSIX everywhere this is tested
        yield
        return

    lock_path = config.generated_root.with_suffix(OUTPUT_SUFFIX_LOCK)
    try:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        handle = lock_path.open("a+", encoding="utf-8")
    except OSError:
        yield
        return

    try:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            # A build queued behind a service rebuild that is itself inside a 120-second
            # validator looks hung. The store says this for the same reason.
            print("Another build is in progress; waiting for it to finish.", file=sys.stderr)
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            except OSError:
                yield
                return
        except OSError:
            yield
            return
        try:
            yield
        finally:
            with contextlib.suppress(OSError):  # unlocking a lock we hold
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    finally:
        handle.close()


def build_site(
    world: LoadedWorld, *, built_at: str | None = None, service: ServiceView | None = None
) -> BuildResult:
    """Render every page and swap the result into place atomically.

    One build at a time per output directory. See `_exclusive_output`.
    """
    with _exclusive_output(world.config):
        return _render_and_publish(world, built_at=built_at, service=service)


def _render_and_publish(
    world: LoadedWorld, *, built_at: str | None = None, service: ServiceView | None = None
) -> BuildResult:
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

    stamp = built_at or build_stamp()
    build_view = default_build_view(bundle, stamp)
    # A build from the CLI produces pages that say state cannot change; a build from the
    # running service produces pages whose actions work. Same templates, different truth.
    service = service or offline_service_view()
    environment = make_environment(config.templates_root)

    staging = config.generated_root.with_suffix(OUTPUT_SUFFIX_NEW)
    if staging.is_symlink() or (staging.exists() and not staging.is_dir()):
        # Debris in the shape of a file, which `rmtree` answers with `NotADirectoryError` —
        # permanently, for every build, until someone deletes it by hand. `make clean` did
        # not remove it either, because it was not on the list.
        staging.unlink()
    elif staging.exists():
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
                    description="The whole journey, and how far you have traveled.",
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
            | {
                "quests": ordered_summaries,
                "selected": {},
                # Pre-filtered links built by the route helper, so the query string is
                # encoded once and in one place rather than assembled in a template.
                "filter_links": {
                    "by_region": {
                        option.value: routes.catalog_filtered(region=option.value)
                        for option in filters["regions"]
                    }
                },
                **filters,
            },
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
                | _quest_detail_context(entry, bundle, summaries, world, service),
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
                | _evidence_context(entry, summaries[quest.id], world, service),
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
                        "ordered_checks": _checks_by_severity(result),
                        "rerun_action": ActionView(
                            id=f"rerun-{result.validator_id}",
                            label=f"Run {result.validator_id.replace('-', ' ')} again",
                            enabled=False,
                            reason="Start the local service to run checks from this page.",
                        ),
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

    # ---- One reviewer page per attempt. The queue linked to these and they were never
    # generated, so every entry in it was a 404 (final audit B3).
    for quest_id, entry in sorted(states.items()):
        if entry.attempt is None:
            continue
        route = routes.review(quest_id)
        pages.append(
            (
                route,
                "pages/review.html.j2",
                shared(
                    "reviewer",
                    PageView(
                        title=f"Review · {entry.quest.title}",
                        description="Evidence, and the decision only you can make.",
                        route=route,
                        nav_id="reviewer",
                        heading=entry.quest.title,
                    ),
                )
                | _review_context(entry, summaries[quest_id], world, service),
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


# Blocking first, information last. A reviewer and a participant both read this list
# top-down, so the order is the advice (SCREEN-SPECS U07).
_SEVERITY_ORDER = {"blocking": 0, "high": 1, "medium": 2, "low": 3, "information": 4}
_OUTCOME_ORDER = {"fail": 0, "warning": 1, "inconclusive": 2, "skipped": 3, "pass": 4}


def _checks_by_severity(result: Any) -> tuple[Any, ...]:
    """Findings ordered by severity, then by outcome, then by ID so the sort is total."""
    return tuple(
        sorted(
            result.checks,
            key=lambda check: (
                _SEVERITY_ORDER.get(check.severity or "information", 4),
                _OUTCOME_ORDER.get(check.outcome, 5),
                check.id,
            ),
        )
    )


def _results_for(entry: QuestProgress, world: LoadedWorld) -> tuple[Any, ...]:
    if world.participant is None or entry.attempt is None:
        return ()
    return world.participant.results_for(entry.attempt)


def _reviewer_findings(entry: QuestProgress) -> dict[str, Any] | None:
    """What a reviewer said when they did not approve, shaped for the participant's pages.

    The findings were stored faithfully and rendered only on the reviewer's own page, so a
    participant was told "a reviewer asked for corrections" and never what the corrections
    were. The one place the reason existed was `review.yaml` in their own repository, which
    is not a user interface. Shown here for every decision that is not an approval, and not
    after a later approval supersedes it, because the attempt then names the approval.
    """
    review = entry.review
    if review is None or review.is_approval or not review.findings:
        return None
    return {
        "decision": review.decision.replace("_", " "),
        "reviewer_display_name": review.reviewer_display_name,
        "reviewed_at": review.reviewed_at,
        "findings": review.findings,
    }


def _quest_detail_context(
    entry: QuestProgress,
    bundle: Any,
    summaries: dict[str, Any],
    world: LoadedWorld,
    service: ServiceView,
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
            enabled=service.available,
            route=routes.action("start-quest", quest.id),
            reason=None if service.available else "Start the local service to record progress.",
            confirm=CONFIRMATIONS["start-quest"],
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
            # What the application can promise is what it does. It performs no external
            # write and has no mechanism for one, so a page saying every external write is
            # previewed and confirmed would be describing something that does not exist.
            or (
                "This quest writes to a system outside your machine. That write is yours to "
                "make: preview it, confirm it, and record what happened. Nothing in this "
                "application performs one for you."
            )
            if quest.risk.external_write
            else None
        ),
        "attempt_version": entry.attempt.quest_version if entry.attempt else None,
        "reviewer_findings": _reviewer_findings(entry),
    }


def _evidence_context(
    entry: QuestProgress, summary: Any, world: LoadedWorld, service: ServiceView
) -> dict[str, Any]:
    from quest_app.evidence import detect_proof, scan_evidence, scan_kinds

    quest = entry.quest
    results = _results_for(entry, world)
    evidence_path = entry.attempt.evidence_path if entry.attempt else None
    # The scan runs at build time so the page can say something true about the evidence as
    # it stands. It is also enforced at the moment of submission, which is the check that
    # actually matters.
    scan_findings = scan_evidence(world.config, evidence_path) if evidence_path else []
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
    run_actions = tuple(
        ActionView(
            id=f"run-{validator.id}",
            label=f"Run {validator.display_name.lower()}",
            enabled=service.available,
            route=routes.action("run-validator", quest.id, validator.id),
            reason=None if service.available else "Start the local service to run this check.",
        )
        for validator in validators
    )
    # Round 12 C4: `locally_validated` is earned once (ADR-017 — a failing re-run never
    # unwinds it), so nothing here changes that state. But the same page also shows each
    # validator's *latest* result, and a reviewer or participant reading "Required automated
    # checks passed" beside "Last run: fail" for the same check needs to be told those are
    # two different moments, not a contradiction.
    stale_local_validation = (
        tuple(vid for vid in quest.validators if vid in latest and not latest[vid].qualifies)
        if entry.state.id is QuestState.LOCALLY_VALIDATED
        else ()
    )
    allowed = {
        transition.action
        for transition in allowed_actions(entry.attempt.recorded_state if entry.attempt else None)
    }
    actions = tuple(
        ActionView(
            id=action_id,
            label=label,
            enabled=service.available and action_id in allowed,
            route=routes.action(action_id, quest.id),
            reason=(
                "Start the local service to change state."
                if not service.available
                else f"Not possible from {entry.state.label.lower()}."
            ),
            consequential=consequential,
            confirm=confirm,
        )
        for action_id, label, consequential, confirm in (
            ("mark-evidence-ready", "Mark evidence ready", False, None),
            ("mark-locally-validated", "Record local validation", False, None),
            ("submit-for-review", "Submit for review", True, CONFIRMATIONS["submit-for-review"]),
            ("reopen-evidence", "Go back to working on it", False, None),
            ("withdraw-submission", "Withdraw the submission", False, None),
            ("resume-quest", "Resume after review", False, None),
        )
    )
    return {
        "quest": summary,
        "attempt_id": entry.attempt.attempt_id if entry.attempt else None,
        "evidence_path": entry.attempt.evidence_path if entry.attempt else None,
        "required_proof": required,
        "optional_proof": optional,
        "validators": validators,
        "run_actions": run_actions,
        "results": results,
        "stale_local_validation": stale_local_validation,
        "proof_document": _proof_document(world, evidence_path),
        "secret_scan_clean": not scan_findings if evidence_path else None,
        "scan_kinds": scan_kinds(scan_findings),
        "actions": tuple(a for a in actions if a.enabled or a.id in allowed)
        if entry.attempt
        else (),
        "git_summary": git_summary_for(world, evidence_path),
        "reviewer_findings": _reviewer_findings(entry),
    }


def _proof_document(world: LoadedWorld, evidence_path: str | None) -> str | None:
    """The participant's own PROOF.md, rendered and sanitized.

    It was hard-coded to `None`, so the preview the evidence workspace promises never
    appeared on any page (Stage 3 audit S3-M6).
    """
    if not evidence_path:
        return None
    from quest_app.evidence import package_file
    from quest_app.markdown_render import render_markdown
    from quest_app.safe_io import MAX_EVIDENCE_FILE_BYTES, UnsafeStateFileError, read_bounded_bytes
    from quest_app.secret_patterns import redact_text

    # Only the directory used to be resolved, so a PROOF.md that was a link to any file the
    # build could read was rendered into the site. A link out of the package is refused
    # here, reported by the loader, and blocks submission through the secret scan.
    path = package_file(world.config, evidence_path, "PROOF.md")
    if path is None:
        return None

    # Redacted before rendering. It is the participant's own file and they can already read
    # it, but the guarantee "generated output contains no secrets" has to hold for the
    # generated directory as a whole — it can be served, and it is what a screenshot catches.
    # Bounded like the scan: a PROOF.md over the ceiling is a scan finding that blocks
    # submission, and rendering it would cost every build what the scan no longer does.
    try:
        raw = read_bounded_bytes(path, max_bytes=MAX_EVIDENCE_FILE_BYTES)
    except (UnsafeStateFileError, OSError):
        return None
    text, _ = redact_text(raw.decode("utf-8", errors="replace"))
    return render_markdown(text)


def git_summary_for(world: LoadedWorld, evidence_path: str | None) -> dict[str, Any]:
    """Repository status for the evidence page. Reports and advises; never acts."""
    from quest_app.git_status import summary_for

    return summary_for(world.config.repo_root, evidence_path)


def _review_context(
    entry: QuestProgress, summary: Any, world: LoadedWorld, service: ServiceView
) -> dict[str, Any]:
    """Everything U10 requires about one attempt."""
    from quest_app.evidence import detect_proof, scan_evidence, scan_kinds
    from quest_app.review import changes_since_submission, read_submission, review_history

    attempt = entry.attempt
    if attempt is None:
        # `assert` is removed under `python -O`, and the next line would then raise an
        # AttributeError from inside a page render. Every other invariant here is explicit.
        raise ValueError(f"{entry.quest.id} has no attempt, so it has no reviewer page")
    config = world.config
    results = _results_for(entry, world)
    submission = read_submission(config, attempt) or {}
    required, _ = build_proof_views(
        entry.quest, detect_proof(entry.quest, config, attempt.evidence_path, results)
    )
    if attempt.quest_version != entry.quest.version:
        # Round 12 C5: the checklist above is the *published* quest's required evidence,
        # detected against paths that version currently declares. An attempt on a different
        # version may have been written and submitted against proof paths the curriculum has
        # since renamed, so "Not detected" here does not mean the evidence is missing — it
        # may mean the path moved. Only missing items get the note; a path that still
        # resolves needs no caveat.
        version_note = (
            f"This checklist reflects version {entry.quest.version}, the published one. "
            f"The attempt was made against version {attempt.quest_version}, so a missing "
            "item here may be a proof path that has since been renamed rather than evidence "
            "that was never produced."
        )
        required = tuple(
            replace(item, detail=version_note) if item.status == "missing" else item
            for item in required
        )
    history = review_history(config, attempt)
    changed = changes_since_submission(config, attempt)

    return {
        "quest": summary,
        "attempt_id": attempt.attempt_id,
        "quest_version": attempt.quest_version,
        # Said on the page, not only in CLI output: a reviewer judging an attempt on an older
        # version is reading the published version's criteria, which may differ.
        "published_version": entry.quest.version,
        "submission_id": submission.get("submission_id"),
        "submitted_at": submission.get("submitted_at"),
        # What the participant was told did not block submission. A reviewer could otherwise
        # only infer an unrun check from an empty result list, which reads as "none declared".
        "advisories": tuple(submission.get("advisories") or ()),
        # Round 12 C3: a secret, a link out of the package and a file too large to scan all
        # fail the scan, and each needs its own words. See `scan_kinds`.
        "secret_scan_clean": not (scan_findings := scan_evidence(config, attempt.evidence_path)),
        "scan_kinds": scan_kinds(scan_findings),
        "evidence_hash": submission.get("evidence_hash"),
        "evidence_changed": bool(changed),
        # Which of the package and the declared proof outside it changed, so the reviewer
        # knows what to re-read rather than only that something moved.
        "changed_since_submission": tuple(changed),
        "outcomes": entry.quest.outcomes,
        "acceptance_criteria": entry.quest.acceptance_criteria,
        "required_proof": required,
        "results": results,
        "history": tuple(_decision_view(item) for item in history),
        "queue": (),
        "reproduction": _proof_document(world, attempt.evidence_path),
        # A decision needs the service, because recording one writes files.
        "can_decide": service.available and entry.state.id is QuestState.SUBMITTED,
        "blocked_reason": (
            "Start the local service to record a decision."
            if not service.available
            else f"This attempt is {entry.state.label.lower()}, not awaiting a decision."
        ),
        "decision_route": routes.action("record-review", entry.quest.id),
        # One definition of what the reviewer confirms, shared with the service (ADR-033).
        "confirm": CONFIRMATIONS["record-review"],
        # Each decision's own wording, which the script swaps in when one is chosen.
        "decision_confirmations": DECISION_CONFIRMATIONS,
    }


def _decision_view(document: dict[str, Any]) -> Any:
    """A stored review document, shaped for the template."""
    from types import SimpleNamespace

    return SimpleNamespace(
        decision=document.get("decision", "unknown"),
        reviewed_at=document.get("reviewed_at", ""),
        reviewer_display_name=(document.get("reviewer") or {}).get("display_name", "unknown"),
        verification_statement=document.get("verification_statement"),
        findings=tuple(
            SimpleNamespace(
                severity=finding.get("severity", ""), summary=finding.get("summary", "")
            )
            for finding in document.get("findings", [])
        ),
    )


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
        "submission_id": None,
        "submitted_at": None,
        "secret_scan_clean": None,
        "scan_kinds": frozenset(),
        "quest_version": 1,
        "published_version": None,
        "evidence_hash": None,
        "evidence_changed": False,
        "changed_since_submission": (),
        "outcomes": (),
        "acceptance_criteria": (),
        "required_proof": (),
        "results": (),
        "history": (),
        "queue": queue,
        "reproduction": None,
        "decision_route": None,
        "can_decide": False,
        "blocked_reason": (
            "Recording a decision needs the local service. Open a quest from the queue to "
            "review it."
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
        ("validation", "validating delivered behavior"),
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
        "application_version": APPLICATION_VERSION,
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
