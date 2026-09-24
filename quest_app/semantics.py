"""Cross-document validation.

JSON Schema checks one document against one shape. It cannot know that a prerequisite names
a quest nobody wrote, that two quests unlock each other in a cycle, or that an attempt
claims `verified` with no approval behind it. `docs/ARCHITECTURE.md` lists what must be
rejected here and what should only warn; this module is that list, made executable.

The distinction matters: an error stops publication, a warning does not. Getting it wrong in
either direction is costly — a build that fails on an incomplete curriculum blocks authors,
and a build that shrugs at a broken reference ships a dead link to a participant.
"""

from __future__ import annotations

from quest_app.errors import ContentProblem, ProblemReport, Severity
from quest_app.models import AttemptState, ContentBundle, Quest
from quest_app.progress import ParticipantProgress, ParticipantState

DOC_ROUTE = "/docs/content-authoring/"


def validate_bundle(bundle: ContentBundle, report: ProblemReport) -> None:
    """Every cross-document rule for authored content."""
    _check_quest_references(bundle, report)
    _check_prerequisite_cycles(bundle, report)
    _check_proof(bundle, report)
    _check_badges(bundle, report)
    _check_tracks(bundle, report)
    _check_site(bundle, report)
    _check_reachability(bundle, report)


def _suggestion(unknown: str, known: list[str]) -> str | None:
    from quest_app.content_loader import suggest

    return suggest(unknown, known)


def _check_quest_references(bundle: ContentBundle, report: ProblemReport) -> None:
    quest_ids = sorted(bundle.quests)
    region_ids = sorted(bundle.regions)
    for quest in bundle.ordered_quests():
        if quest.region not in bundle.regions:
            report.add(
                ContentProblem.build(
                    code="semantic.unknown_region",
                    severity=Severity.ERROR,
                    public_message=f"Quest {quest.id!r} names a region that does not exist.",
                    source=quest.source,
                    entity_id=quest.id,
                    field_path="region",
                    expected=f"one of: {', '.join(region_ids)}",
                    received=quest.region,
                    suggestion=_suggestion(quest.region, region_ids),
                    documentation=DOC_ROUTE,
                )
            )
        for index, prerequisite in enumerate(quest.prerequisites):
            if prerequisite == quest.id:
                report.add(
                    ContentProblem(
                        code="semantic.self_prerequisite",
                        severity=Severity.ERROR,
                        public_message=f"Quest {quest.id!r} lists itself as a prerequisite.",
                        source=quest.source,
                        entity_id=quest.id,
                        field_path=f"prerequisites[{index}]",
                        expected="a different quest",
                    )
                )
            elif prerequisite not in bundle.quests:
                report.add(
                    ContentProblem.build(
                        code="semantic.unknown_prerequisite",
                        severity=Severity.ERROR,
                        public_message=(
                            f"Quest {quest.id!r} requires a quest that does not exist."
                        ),
                        source=quest.source,
                        entity_id=quest.id,
                        field_path=f"prerequisites[{index}]",
                        expected="an existing quest ID",
                        received=prerequisite,
                        suggestion=_suggestion(prerequisite, quest_ids),
                        documentation=DOC_ROUTE,
                    )
                )
        for index, related in enumerate(quest.related_quests):
            if related not in bundle.quests:
                report.add(
                    ContentProblem.build(
                        code="semantic.unknown_related_quest",
                        severity=Severity.ERROR,
                        public_message=f"Quest {quest.id!r} links to a quest that does not exist.",
                        source=quest.source,
                        entity_id=quest.id,
                        field_path=f"related_quests[{index}]",
                        expected="an existing quest ID",
                        received=related,
                        suggestion=_suggestion(related, quest_ids),
                    )
                )
        if quest.deprecated and not quest.related_quests:
            report.add(
                ContentProblem(
                    code="semantic.deprecated_without_successor",
                    severity=Severity.WARNING,
                    public_message=(f"Quest {quest.id!r} is deprecated but points nowhere else."),
                    source=quest.source,
                    entity_id=quest.id,
                    field_path="related_quests",
                    suggestion="Add a related quest so participants know what replaced it.",
                )
            )


def _check_prerequisite_cycles(bundle: ContentBundle, report: ProblemReport) -> None:
    """Depth-first search reporting the actual cycle, not just that one exists.

    An author with twenty quests needs the path, not the news.
    """
    white, grey, black = 0, 1, 2
    colour: dict[str, int] = dict.fromkeys(bundle.quests, white)
    reported: set[frozenset[str]] = set()

    def visit(quest_id: str, stack: list[str]) -> None:
        colour[quest_id] = grey
        for prerequisite in bundle.quests[quest_id].prerequisites:
            if prerequisite not in bundle.quests or prerequisite == quest_id:
                continue  # already reported as a reference error
            if colour[prerequisite] == grey:
                cycle = [*stack[stack.index(prerequisite) :], prerequisite]
                key = frozenset(cycle)
                if key not in reported:
                    reported.add(key)
                    quest = bundle.quests[quest_id]
                    report.add(
                        ContentProblem(
                            code="semantic.prerequisite_cycle",
                            severity=Severity.ERROR,
                            public_message=(
                                "These quests require each other, so none of them can ever unlock: "
                                + " → ".join(cycle)
                            ),
                            source=quest.source,
                            entity_id=quest.id,
                            field_path="prerequisites",
                            expected="a prerequisite graph with no cycles",
                            suggestion=(
                                "Remove one prerequisite in the loop. "
                                f"Start with {quest.id!r} → {prerequisite!r}."
                            ),
                            documentation=DOC_ROUTE,
                        )
                    )
            elif colour[prerequisite] == white:
                visit(prerequisite, [*stack, prerequisite])
        colour[quest_id] = black

    for quest_id in sorted(bundle.quests):
        if colour[quest_id] == white:
            visit(quest_id, [quest_id])


def _check_proof(bundle: ContentBundle, report: ProblemReport) -> None:
    for quest in bundle.ordered_quests():
        seen: dict[str, int] = {}
        for index, item in enumerate(quest.proof):
            if item.id in seen:
                report.add(
                    ContentProblem(
                        code="semantic.duplicate_proof_id",
                        severity=Severity.ERROR,
                        public_message=(
                            f"Quest {quest.id!r} declares proof {item.id!r} more than once."
                        ),
                        source=quest.source,
                        entity_id=quest.id,
                        field_path=f"proof[{index}].id",
                        expected="a proof ID unique within the quest",
                        suggestion="Rename one of them; evidence status is keyed by this ID.",
                    )
                )
            seen[item.id] = index
            if item.type == "validator" and item.validator not in quest.validators:
                report.add(
                    ContentProblem.build(
                        code="semantic.proof_validator_not_declared",
                        severity=Severity.ERROR,
                        public_message=(
                            f"Proof {item.id!r} runs a validator the quest does not declare."
                        ),
                        source=quest.source,
                        entity_id=quest.id,
                        field_path=f"proof[{index}].validator",
                        expected=(
                            "one of the quest's validators: "
                            + (", ".join(quest.validators) or "none declared")
                        ),
                        received=item.validator,
                        suggestion=f"Add {item.validator!r} to the quest's 'validators' list.",
                    )
                )
        if not quest.required_proof:
            report.add(
                ContentProblem(
                    code="semantic.no_required_proof",
                    severity=Severity.ERROR,
                    public_message=f"Quest {quest.id!r} requires no proof at all.",
                    source=quest.source,
                    entity_id=quest.id,
                    field_path="proof.required",
                    expected="at least one required proof item",
                    suggestion="A quest with no required proof cannot be reviewed.",
                )
            )


def _check_badges(bundle: ContentBundle, report: ProblemReport) -> None:
    quest_ids = sorted(bundle.quests)
    region_ids = sorted(bundle.regions)
    all_tags = bundle.all_tags()
    for badge in bundle.ordered_badges():
        criteria = badge.criteria
        for field_name, values in (
            ("all_quests", criteria.all_quests),
            ("any_quests", criteria.any_quests),
        ):
            for index, quest_id in enumerate(values):
                if quest_id not in bundle.quests:
                    report.add(
                        ContentProblem.build(
                            code="semantic.badge_unknown_quest",
                            severity=Severity.ERROR,
                            public_message=f"Badge {badge.id!r} names a quest that does not exist.",
                            source=badge.source,
                            entity_id=badge.id,
                            field_path=f"criteria.{field_name}[{index}]",
                            expected="an existing quest ID",
                            received=quest_id,
                            suggestion=_suggestion(quest_id, quest_ids),
                        )
                    )
        if criteria.region and criteria.region not in bundle.regions:
            report.add(
                ContentProblem.build(
                    code="semantic.badge_unknown_region",
                    severity=Severity.ERROR,
                    public_message=f"Badge {badge.id!r} names a region that does not exist.",
                    source=badge.source,
                    entity_id=badge.id,
                    field_path="criteria.region",
                    expected="an existing region ID",
                    received=criteria.region,
                    suggestion=_suggestion(criteria.region, region_ids),
                )
            )
        if badge.award_type == "reviewer" and not criteria.reviewer_statement:
            report.add(
                ContentProblem(
                    code="semantic.badge_missing_reviewer_statement",
                    severity=Severity.ERROR,
                    public_message=(
                        f"Badge {badge.id!r} is reviewer-awarded but states no criterion."
                    ),
                    source=badge.source,
                    entity_id=badge.id,
                    field_path="criteria.reviewer_statement",
                    expected="a statement describing what the reviewer must confirm",
                    suggestion="A reviewer cannot award a badge whose bar is unwritten.",
                )
            )
        if badge.award_type == "automatic" and criteria.reviewer_statement:
            report.add(
                ContentProblem(
                    code="semantic.badge_automatic_with_reviewer_statement",
                    severity=Severity.ERROR,
                    public_message=(
                        f"Badge {badge.id!r} is automatic but carries a reviewer statement."
                    ),
                    source=badge.source,
                    entity_id=badge.id,
                    field_path="criteria.reviewer_statement",
                    expected="no reviewer statement on an automatic badge",
                    suggestion=(
                        "Either change award_type to 'reviewer' or remove the statement. "
                        "The interface must say truthfully which authority awarded a badge."
                    ),
                )
            )
        # Reachability: a warning, because curriculum is published incrementally.
        count = criteria.verified_quest_count
        if count is not None and count > len(bundle.quests):
            report.add(
                ContentProblem.build(
                    code="semantic.badge_unreachable",
                    severity=Severity.WARNING,
                    public_message=(
                        f"Badge {badge.id!r} needs {count} verified quests but only "
                        f"{len(bundle.quests)} exist."
                    ),
                    source=badge.source,
                    entity_id=badge.id,
                    field_path="criteria.verified_quest_count",
                    received=count,
                    suggestion="Nobody can earn this badge until more quests are published.",
                )
            )
        for index, tag in enumerate(criteria.required_tags):
            if tag not in all_tags:
                report.add(
                    ContentProblem.build(
                        code="semantic.badge_unreachable_tag",
                        severity=Severity.WARNING,
                        public_message=(
                            f"Badge {badge.id!r} requires tag {tag!r}, which no quest carries."
                        ),
                        source=badge.source,
                        entity_id=badge.id,
                        field_path=f"criteria.required_tags[{index}]",
                        received=tag,
                        suggestion=_suggestion(tag, all_tags)
                        or "Tag a quest with it, or remove the requirement.",
                    )
                )


def _check_tracks(bundle: ContentBundle, report: ProblemReport) -> None:
    quest_ids = sorted(bundle.quests)
    for track in sorted(bundle.tracks.values(), key=lambda t: t.id):
        members: list[Quest] = []
        for index, quest_id in enumerate(track.quest_ids):
            quest = bundle.quests.get(quest_id)
            if quest is None:
                report.add(
                    ContentProblem.build(
                        code="semantic.track_unknown_quest",
                        severity=Severity.ERROR,
                        public_message=f"Track {track.id!r} names a quest that does not exist.",
                        source=track.source,
                        entity_id=track.id,
                        field_path=f"quest_ids[{index}]",
                        expected="an existing quest ID",
                        received=quest_id,
                        suggestion=_suggestion(quest_id, quest_ids),
                    )
                )
            else:
                members.append(quest)
        counts = {
            "intent": sum(1 for q in members if q.bookend == "intent"),
            "validation": sum(1 for q in members if q.bookend == "validation"),
            "cross-bookend": sum(1 for q in members if q.bookend == "cross-bookend"),
        }
        for label, minimum, actual in (
            ("intent_minimum", track.balance.intent_minimum, counts["intent"]),
            ("validation_minimum", track.balance.validation_minimum, counts["validation"]),
            ("cross_bookend_minimum", track.balance.cross_bookend_minimum, counts["cross-bookend"]),
        ):
            if actual < minimum:
                report.add(
                    ContentProblem.build(
                        code="semantic.track_balance_unmet",
                        severity=Severity.ERROR,
                        public_message=(
                            f"Track {track.id!r} promises {minimum} "
                            f"{label.removesuffix('_minimum')} "
                            f"quest(s) but contains {actual}."
                        ),
                        source=track.source,
                        entity_id=track.id,
                        field_path=f"balance.{label}",
                        expected=f"at least {minimum}",
                        received=actual,
                        suggestion="Add a quest with that bookend, or lower the minimum.",
                    )
                )


def _check_site(bundle: ContentBundle, report: ProblemReport) -> None:
    site = bundle.site
    if site.default_track not in bundle.tracks:
        report.add(
            ContentProblem.build(
                code="semantic.unknown_default_track",
                severity=Severity.ERROR,
                public_message="The site's default track does not exist.",
                source=site.source,
                field_path="default_track",
                expected=f"one of: {', '.join(sorted(bundle.tracks))}",
                received=site.default_track,
                suggestion=_suggestion(site.default_track, sorted(bundle.tracks)),
            )
        )
    seen: set[str] = set()
    for index, item in enumerate(site.navigation):
        if item.id in seen:
            report.add(
                ContentProblem(
                    code="semantic.duplicate_navigation_id",
                    severity=Severity.ERROR,
                    public_message=f"Navigation item {item.id!r} appears twice.",
                    source=site.source,
                    field_path=f"navigation[{index}].id",
                    expected="a unique navigation ID",
                )
            )
        seen.add(item.id)


def _check_reachability(bundle: ContentBundle, report: ProblemReport) -> None:
    """Warnings about curriculum shape. None of these stop a build."""
    for region in bundle.ordered_regions():
        if not bundle.quests_in_region(region.id):
            report.add(
                ContentProblem(
                    code="semantic.empty_region",
                    severity=Severity.WARNING,
                    public_message=f"Region {region.id!r} contains no quests.",
                    source=region.source,
                    entity_id=region.id,
                    suggestion=(
                        "It will appear on the map as an empty region until a quest names it."
                    ),
                )
            )
    for quest in bundle.ordered_quests():
        unreachable = [
            p for p in quest.prerequisites if p in bundle.quests and bundle.quests[p].deprecated
        ]
        if unreachable:
            report.add(
                ContentProblem(
                    code="semantic.prerequisite_deprecated",
                    severity=Severity.WARNING,
                    public_message=(
                        f"Quest {quest.id!r} requires deprecated quest(s): "
                        + ", ".join(unreachable)
                        + "."
                    ),
                    source=quest.source,
                    entity_id=quest.id,
                    field_path="prerequisites",
                    suggestion=(
                        "New participants are not recommended deprecated quests, so this may never "
                        "unlock."
                    ),
                )
            )


def validate_progress_against_content(
    progress: ParticipantProgress, bundle: ContentBundle, report: ProblemReport
) -> None:
    """Integrity rules that need both the participant's record and the curriculum.

    The important one is the last: a `verified` attempt without a matching approval is the
    exact forgery the whole claimed-versus-verified model exists to prevent (ADR-011).
    """
    quest_ids = sorted(bundle.quests)
    for attempt in progress.attempts:
        quest = bundle.quests.get(attempt.quest_id)
        if quest is None:
            report.add(
                ContentProblem.build(
                    code="progress.unknown_quest",
                    severity=Severity.ERROR,
                    public_message=(
                        f"Attempt {attempt.attempt_id!r} refers to a quest that does not exist."
                    ),
                    source=progress.source,
                    entity_id=attempt.attempt_id,
                    field_path="attempts[].quest_id",
                    expected="an existing quest ID",
                    received=attempt.quest_id,
                    suggestion=_suggestion(attempt.quest_id, quest_ids),
                )
            )
            continue
        if attempt.quest_version > quest.version:
            report.add(
                ContentProblem.build(
                    code="progress.future_quest_version",
                    severity=Severity.ERROR,
                    public_message=(
                        f"Attempt {attempt.attempt_id!r} was recorded against quest version "
                        f"{attempt.quest_version}, but only version {quest.version} exists."
                    ),
                    source=progress.source,
                    entity_id=attempt.attempt_id,
                    field_path="attempts[].quest_version",
                    expected=f"at most {quest.version}",
                    received=attempt.quest_version,
                    suggestion=(
                        "The content may have been rolled back. Restore it or correct the attempt."
                    ),
                )
            )
        elif attempt.quest_version < quest.version:
            report.add(
                ContentProblem(
                    code="progress.outdated_quest_version",
                    severity=Severity.WARNING,
                    public_message=(
                        f"Attempt {attempt.attempt_id!r} is on version {attempt.quest_version} of "
                        f"{quest.id!r}; version {quest.version} is available."
                    ),
                    source=progress.source,
                    entity_id=attempt.attempt_id,
                    field_path="attempts[].quest_version",
                    suggestion=(
                        "In-progress work is never migrated automatically. The quest page says so."
                    ),
                )
            )

        if attempt.content_hash != quest.content_hash:
            # The hash is what distinguishes "the quest text changed" from "the version
            # number changed". Stored and never compared, it was decoration: 64 zeros
            # validated (Stage 2 audit H4).
            #
            # A mismatch is always a warning, never a build error, including for a verified
            # attempt. `CONTENT-MODEL.md` is explicit that "previously verified attempts
            # remain verified unless a documented program policy explicitly revokes them",
            # and the hash covers editorial fields too, so failing the build here would let
            # a typo fix in a Hints section invalidate someone's approved work. The
            # participant's and reviewer's job is to be told; the build's job is not to
            # stop. Surfacing a stale approval in the interface is Stage 7's changed-evidence
            # detection, which this warning feeds.
            verified = attempt.recorded_state is AttemptState.VERIFIED
            report.add(
                ContentProblem.build(
                    code="progress.content_hash_mismatch",
                    severity=Severity.WARNING,
                    public_message=(
                        f"Attempt {attempt.attempt_id!r} was approved against a different "
                        f"version of the text of {quest.id!r}, so the approval may be stale."
                        if verified
                        else f"The text of {quest.id!r} has changed since attempt "
                        f"{attempt.attempt_id!r} was recorded."
                    ),
                    source=progress.source,
                    entity_id=attempt.attempt_id,
                    field_path="attempts[].content_hash",
                    expected=quest.content_hash,
                    received=attempt.content_hash,
                    suggestion=(
                        "The approval stands. A reviewer may re-review if the acceptance "
                        "criteria changed materially."
                        if verified
                        else "Your work is untouched. The quest page shows what changed."
                    ),
                )
            )


def validate_local_validation_claims(
    participant: ParticipantState, bundle: ContentBundle, report: ProblemReport
) -> None:
    """A `locally_validated` attempt must have the validator results the state claims.

    The state is shown under the registered validator's authority — "required automated
    checks passed" — and the transition guard refuses it without qualifying results. A
    participant could still write it into `progress.yaml` by hand, and it loaded and was
    displayed exactly as if the checks had passed (ADR-030 says such a claim is refused).

    The rule is that every declared validator has *a* qualifying result for this attempt,
    not that its latest one qualifies. ADR-017 says a failing re-run leaves the attempt
    where it was, so a pass followed by a fail is a legitimate record, not a forgery; an
    error there would take the whole site down for following the documented flow. A quest
    that declares no validators reaches the state on the participant's word, and says so.
    Only `locally_validated` is checked: no later state implies it, because submission is
    allowed straight from `evidence_ready`.

    A validator missing from `passed` is only ever a forgery when it could have been run:
    when `attempt.quest_version` is not the quest's current version, an upstream update may
    have *added* a validator since this attempt validated (ADR-017, amended round 12). This
    application keeps no record of an earlier version's declared validators, so it cannot
    tell "never ran it" from "it did not exist yet" — and refusing to load punished the
    second case for looking exactly like the first, including refusing the one action,
    `run-validator`, that would clear it. The version mismatch alone is not enough to
    excuse it, though: an attempt with *no* qualifying result at all is exactly the
    wholesale forgery this check exists to catch, version mismatch or not. So: a version
    mismatch with at least one qualifying result downgrades each missing validator to a
    named warning instead of failing the load; same version, or no qualifying result at
    all, is still the error.
    """
    for attempt in participant.progress.attempts:
        if attempt.recorded_state is not AttemptState.LOCALLY_VALIDATED:
            continue
        quest = bundle.quests.get(attempt.quest_id)
        if quest is None or not quest.validators:
            continue
        passed = {
            result.validator_id for result in participant.results_for(attempt) if result.qualifies
        }
        missing = [validator for validator in quest.validators if validator not in passed]
        if not missing:
            continue
        if attempt.quest_version != quest.version and passed:
            for validator in missing:
                report.add(
                    ContentProblem.build(
                        code="progress.locally_validated_missing_new_validator",
                        severity=Severity.WARNING,
                        public_message=(
                            f"Attempt {attempt.attempt_id!r} claims local validation, but "
                            f"{validator!r} has no qualifying result for it. The attempt "
                            f"validated against version {attempt.quest_version} of "
                            f"{quest.id!r}; version {quest.version} is published now, and "
                            "this application keeps no record of which validators an "
                            "earlier version required."
                        ),
                        source=participant.progress.source,
                        entity_id=attempt.attempt_id,
                        field_path="attempts[].state",
                        expected=f"a qualifying result from {validator!r}",
                        suggestion=f"Run {validator!r} to confirm the attempt still qualifies.",
                    )
                )
            continue
        report.add(
            ContentProblem.build(
                code="progress.unvalidated_locally_validated_state",
                severity=Severity.ERROR,
                public_message=(
                    f"Attempt {attempt.attempt_id!r} claims local validation, but "
                    f"{', '.join(missing)} has no qualifying result for it."
                ),
                source=participant.progress.source,
                entity_id=attempt.attempt_id,
                field_path="attempts[].state",
                expected="a passing or warning result from every declared validator",
                suggestion=(
                    "Local validation comes from validator results, not from this file. Set "
                    "the state back to 'evidence_ready', run the checks, then record local "
                    "validation."
                ),
            )
        )
