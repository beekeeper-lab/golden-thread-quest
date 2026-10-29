"""Pre-check a pilot hand-in pull request and say, in plain words, what a participant should do.

It reads the participant's files as data. It never runs anything the participant wrote, so it is
safe to run from a workflow that has a token. It does not review and it never approves: it says
whether the hand-in is complete enough for a reviewer to look at, and, once a reviewer has
decided, where the decision is.

Usage:
    python tools/precheck.py --participant-root DIR --files-json FILE [--json OUT] [--comment OUT]

`--files-json` is GitHub's list of changed files for the pull request (`filename`, `status`,
`previous_filename`). `--participant-root` is a folder holding the pull request's
`participant/` content. Exit status is 0 whenever a verdict was produced, 2 for bad usage.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from review_check import check_files

MARKER = "<!-- gtq-precheck -->"
REVIEW_MARKER = "<!-- gtq-review-ready:{review_id} -->"

NEEDS_FIXES = "needs-fixes"
READY = "ready-for-review"
REVIEWED = "reviewed"
NOTHING = "nothing-submitted"
LABELS = {
    NEEDS_FIXES: "gtq:needs-fixes",
    READY: "gtq:ready-for-review",
    REVIEWED: "gtq:reviewed",
}

DECISION_WORDS = {"approved": "Verified", "needs_changes": "Needs changes", "rejected": "Rejected"}


@dataclass
class AttemptCheck:
    quest_id: str
    title: str
    problems: list[str] = field(default_factory=list)


@dataclass
class Decision:
    quest_id: str
    title: str
    decision: str
    review_id: str
    findings: int
    statement: str = ""
    summaries: list[str] = field(default_factory=list)
    reviewer: str = ""


@dataclass
class Result:
    status: str
    headline: str
    problems: list[str] = field(default_factory=list)
    checked: list[AttemptCheck] = field(default_factory=list)
    decisions: list[Decision] = field(default_factory=list)

    @property
    def label(self) -> str | None:
        return LABELS.get(self.status)


def check(
    repo_root: Path,
    participant_root: Path,
    files: list[dict[str, Any]],
    *,
    trust_reviews: bool = True,
) -> Result:
    """The verdict for one pull request. Never raises for anything a participant could write."""
    verdict = check_files(files)
    if not verdict.safe:
        shown = verdict.outside[:5]
        return Result(
            NEEDS_FIXES,
            "This pull request changes files outside your `participant/` folder, so it was not "
            "checked further.",
            [
                "Only your own `participant/` folder belongs in a hand-in. These do not: "
                + ", ".join(f"`{_safe(p)}`" for p in shown)
                + (f" and {len(verdict.outside) - 5} more" if len(verdict.outside) > 5 else "")
                + ". Run `gtq hand-in` again from your pilot branch; it sends only your own folder."
            ],
        )

    try:
        return _check_participant(repo_root, participant_root, trust_reviews)
    except Exception as exc:  # a verdict is always produced; never a crash dump in a comment
        return Result(
            NEEDS_FIXES,
            "The automatic check could not read your hand-in.",
            [
                f"The checker stopped on a problem it did not expect ({type(exc).__name__}). "
                "A person will look at it; you do not need to do anything yet."
            ],
        )


def _check_participant(repo_root: Path, participant_root: Path, trust_reviews: bool) -> Result:
    from quest_app.config import AppConfig
    from quest_app.errors import ProblemReport
    from quest_app.evidence import describe_scan_findings, scan_declared_proof
    from quest_app.models import AttemptState
    from quest_app.pipeline import load_world
    from quest_app.review import changes_since_submission, missing_required_proof, review_history

    config = AppConfig.for_repo(repo_root, participant_root=participant_root)
    report = ProblemReport()
    world = load_world(config, report)
    if world is None or world.participant is None:
        if world is not None:
            return Result(NOTHING, "Nothing has been submitted yet.")
        reasons = [
            _safe(p.public_message) for p in report.sorted_problems() if p.severity.stops_the_build
        ]
        return Result(
            NEEDS_FIXES,
            "Your progress record could not be read.",
            reasons[:5] or ["The file `participant/progress.yaml` is not readable."],
        )
    if not report.ok:
        reasons = [
            _safe(p.public_message) for p in report.sorted_problems() if p.severity.stops_the_build
        ]
        return Result(
            NEEDS_FIXES,
            "Your progress record has a problem.",
            reasons[:5]
            or ["The file `participant/progress.yaml` does not match what the app expects."],
        )

    checked: list[AttemptCheck] = []
    decisions: list[Decision] = []
    for attempt in world.participant.progress.attempts:
        quest = world.content.quests.get(attempt.quest_id)
        if quest is None:
            continue
        if attempt.recorded_state in (AttemptState.VERIFIED, AttemptState.NEEDS_CHANGES):
            # A review record is a file the participant can also write. It is announced only
            # when someone other than the author pushed to the branch (`--trust-reviews`).
            history = review_history(config, attempt) if trust_reviews else []
            if history:
                current = history[-1]
                decisions.append(
                    Decision(
                        quest.id,
                        quest.title,
                        str(current.get("decision", "")),
                        str(current.get("review_id", "")),
                        len(current.get("findings") or ()),
                        str(current.get("verification_statement") or ""),
                        [str(f.get("summary", "")) for f in current.get("findings") or ()],
                        str((current.get("reviewer") or {}).get("display_name", "")),
                    )
                )
            continue
        if attempt.recorded_state is not AttemptState.SUBMITTED:
            continue
        item = AttemptCheck(quest.id, quest.title)
        item.problems.extend(
            _safe(_plain(p)) for p in missing_required_proof(quest, attempt, (), config)
        )
        item.problems.extend(
            _safe(line)
            for line in describe_scan_findings(
                scan_declared_proof(config, quest, attempt.evidence_path)
            )
        )
        changed = changes_since_submission(config, attempt)
        if changed:
            item.problems.append(
                "These files changed after you clicked Submit for review: "
                + ", ".join(f"`{_safe(p)}`" for p in changed[:5])
                + ". Click Submit for review again, then run `gtq hand-in`."
            )
        checked.append(item)

    if any(item.problems for item in checked):
        return Result(
            NEEDS_FIXES,
            "A few things need fixing before a reviewer can look at this.",
            checked=checked,
            decisions=decisions,
        )
    if checked:
        return Result(
            READY,
            "Everything the automatic check looks for is in place. A reviewer will look next.",
            checked=checked,
            decisions=decisions,
        )
    if decisions:
        return Result(REVIEWED, "A reviewer has decided.", decisions=decisions)
    return Result(NOTHING, "Nothing has been submitted yet.")


def _safe(text: str) -> str:
    """Text that came from a participant's files, made harmless inside a GitHub comment.

    A filename or a value echoed by a loader message could otherwise close a code span, mention a
    person or a team (`@name`) or add a link under the bot's name.
    """
    cleaned = "".join(c for c in text if c.isprintable() and c not in "`<>[]@!|\\")
    return cleaned[:300]


def _plain(problem: str) -> str:
    return problem.replace("Required evidence is not in place:", "Missing:").replace(
        "Required evidence is empty:", "Empty:"
    )


def render_comment(result: Result) -> str:
    """The sticky comment. It never says approved or verified: only a reviewer decides that."""
    lines = [MARKER, "### Automatic check", "", result.headline, ""]
    for problem in result.problems:
        lines.append(f"- {problem}")
    for decision in result.decisions:
        word = DECISION_WORDS.get(decision.decision, decision.decision)
        lines.append(f"- **{decision.title}**: {word}")
    for item in result.checked:
        if item.problems:
            lines.append(f"**{item.title}**")
            lines.extend(f"- {p}" for p in item.problems)
        else:
            lines.append(f"**{item.title}**: all required files are in place.")
        lines.append("")
    if result.status == NEEDS_FIXES:
        lines += [
            "Fix these in the app, click **Submit for review** again, then run `gtq hand-in`. "
            "This comment updates by itself.",
        ]
    elif result.status == READY:
        lines += [
            "You do not need to message anyone. When a reviewer has decided, GitHub emails you, "
            "and the app's evidence page has a **Check for my review** button.",
            "",
            "_This check only looks that the files are there and clean. It is not a review._",
        ]
    return "\n".join(lines).rstrip() + "\n"


def render_review_ready(result: Result) -> list[tuple[str, str]]:
    """One new comment per decision, so GitHub sends an email. Edits to a comment send none."""
    comments = []
    # Only the newest decision: older ones were announced when they were made, and the first
    # run on a pull request that already has several must not post one comment for each.
    newest = max(result.decisions, key=lambda d: d.review_id, default=None)
    for decision in [newest] if newest else []:
        word = DECISION_WORDS.get(decision.decision, decision.decision)
        marker = REVIEW_MARKER.format(review_id=decision.review_id)
        if decision.decision == "approved":
            action = "Open the app and click **Check for my review**, then reload to see it."
            detail = f"\n> {_safe(decision.statement)[:600]}\n" if decision.statement else ""
        else:
            action = (
                f"There are {decision.findings} finding(s) to look at. Open the app, click "
                "**Check for my review**, then **Resume after review** on the quest."
            )
            detail = "".join(f"\n- {_safe(summary)[:300]}" for summary in decision.summaries[:10])
            detail = f"\n{detail}\n" if detail else ""
        who = f" by {_safe(decision.reviewer)}" if decision.reviewer else ""
        body = (
            f"{marker}\n### Your review is ready\n\n**{decision.title}**: {word}{who}.\n"
            f"{detail}\n{action}\n"
        )
        comments.append((decision.review_id, body))
    return comments


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--participant-root", type=Path, required=True)
    parser.add_argument("--files-json", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument(
        "--trust-reviews",
        action="store_true",
        help="announce review decisions; pass it only when a commit by someone other than the "
        "pull request's author is on the branch",
    )
    parser.add_argument("--json", type=Path, help="write the verdict as JSON here")
    parser.add_argument("--comment", type=Path, help="write the sticky comment here")
    parser.add_argument("--review-dir", type=Path, help="write one file per review-ready comment")
    args = parser.parse_args(argv[1:])
    files = json.loads(args.files_json.read_text(encoding="utf-8"))
    result = check(args.repo_root, args.participant_root, files, trust_reviews=args.trust_reviews)
    if args.json:
        args.json.write_text(
            json.dumps({**asdict(result), "label": result.label}, indent=2), encoding="utf-8"
        )
    if args.comment:
        args.comment.write_text(render_comment(result), encoding="utf-8")
    if args.review_dir:
        args.review_dir.mkdir(parents=True, exist_ok=True)
        for review_id, body in render_review_ready(result):
            (args.review_dir / f"{review_id}.md").write_text(body, encoding="utf-8")
    print(f"{result.status}: {result.headline}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
