"""Receiving upstream curriculum without losing participant work.

The whole design of this repository exists so that a participant can take improvements to
the curriculum while keeping everything they wrote. That only holds if the update path
refuses to proceed when it cannot guarantee it, so this module is mostly preflight checks
and a backup, and it performs no Git operation that rewrites anything.

It deliberately does **not** run the merge. `git merge` on someone else's repository, with
their uncommitted work in it, is not a decision an application should make. The module
reports what it found, names a backup branch for the participant to create, prints the
exact commands, and stops. It creates nothing: every Git command it is permitted to run is
read-only, which is the point.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from quest_app.config import AppConfig
from quest_app.git_status import inspect

TIMEOUT_SECONDS = 20

# Every Git command this module may run. All of them are read-only: the fetch, the backup
# branch and the merge are printed for the participant to run, never run here.
PERMITTED_COMMANDS: frozenset[tuple[str, ...]] = frozenset(
    {
        ("remote",),
        ("branch", "--list"),
        ("rev-parse", "--git-path", "MERGE_HEAD"),
    }
)


@dataclass(frozen=True, slots=True)
class Finding:
    id: str
    status: str
    summary: str
    remediation: str | None = None

    @property
    def blocks(self) -> bool:
        return self.status == "fail"


@dataclass(frozen=True, slots=True)
class Preflight:
    findings: tuple[Finding, ...]
    # Named, not created. A field called `backup_branch` on a result object reads as a
    # branch that exists, and nothing here makes one: `PERMITTED_COMMANDS` is read-only.
    proposed_backup_branch: str | None = None
    instructions: str = ""
    notes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def safe_to_proceed(self) -> bool:
        return not any(finding.blocks for finding in self.findings)


def _git(repo_root: Path, arguments: tuple[str, ...]) -> str | None:
    if arguments not in PERMITTED_COMMANDS:
        raise ValueError(f"git command not permitted during update: {arguments!r}")
    try:
        result = subprocess.run(  # noqa: S603
            ["git", "-C", str(repo_root), *arguments],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def merge_in_progress(repo_root: Path) -> bool:
    """Whether Git is mid-merge here. Public: `update_command` checks it before migrating too."""
    marker = _git(repo_root, ("rev-parse", "--git-path", "MERGE_HEAD"))
    if not marker:
        return False
    path = Path(marker)
    return (path if path.is_absolute() else repo_root / path).exists()


def backup_branch_name() -> str:
    return f"backup/pre-update-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"


def preflight(config: AppConfig) -> Preflight:
    """Everything that must be true before a participant merges upstream.

    A dirty working tree is a hard stop. Merging on top of uncommitted work is how someone
    loses an afternoon, and the participant almost always wants to commit first anyway.
    """
    findings: list[Finding] = []
    status = inspect(config.repo_root)

    if not status.available:
        return Preflight(
            findings=(
                Finding(
                    id="repository",
                    status="fail",
                    summary="This is not a Git repository, so there is nothing to update from.",
                    remediation="Clone your fork, then run this again.",
                ),
            )
        )

    findings.append(
        Finding(id="repository", status="pass", summary=f"On branch {status.branch or 'unknown'}.")
    )

    if merge_in_progress(config.repo_root):
        # Checked before the working tree, whose advice is to commit everything: during a
        # conflict that commits the conflict markers.
        findings.append(
            Finding(
                id="merge-in-progress",
                status="fail",
                summary="A merge is in progress. Files with conflicts still hold conflict markers.",
                remediation=(
                    "Resolve each conflict, `git add` the file, then `git commit`; or undo "
                    "the merge with `git merge --abort`."
                ),
            )
        )
    elif not status.clean:
        findings.append(
            Finding(
                id="working-tree",
                status="fail",
                summary=(
                    f"{status.changed} changed and {status.untracked} untracked file(s). "
                    "Merging on top of uncommitted work risks losing it."
                ),
                remediation="git add -A && git commit -m 'Work in progress'",
            )
        )
    else:
        findings.append(
            Finding(id="working-tree", status="pass", summary="The working tree is clean.")
        )

    remotes = (_git(config.repo_root, ("remote",)) or "").split()
    if "upstream" not in remotes:
        findings.append(
            Finding(
                id="upstream-remote",
                status="fail",
                summary="No 'upstream' remote is configured.",
                remediation="git remote add upstream <canonical repository URL>",
            )
        )
    else:
        findings.append(
            Finding(
                id="upstream-remote", status="pass", summary="An 'upstream' remote is configured."
            )
        )

    participant_root = config.participant_root
    if participant_root.exists():
        findings.append(
            Finding(
                id="participant-files",
                status="pass",
                summary=(
                    f"Your work is in {config.relative(participant_root)} and is never replaced "
                    "by an update."
                ),
            )
        )
    else:
        findings.append(
            Finding(
                id="participant-files",
                status="warning",
                summary="No participant directory exists yet, so there is nothing to protect.",
            )
        )

    # One name, used twice. Two calls a second apart produced a `Preflight` whose
    # `backup_branch` named a different branch from the one its own instructions create.
    backup = backup_branch_name()
    return Preflight(
        findings=tuple(findings),
        proposed_backup_branch=backup,
        instructions=update_instructions(backup, status.branch or "main"),
        notes=(
            "Nothing under participant/ is replaced by an update. The merge may still produce "
            "a conflict there if you and upstream changed the same file.",
            "In-progress attempts stay on the quest version you started, whatever upstream "
            "publishes.",
        ),
    )


def update_instructions(backup: str, branch: str) -> str:
    """The exact commands, for the participant to run and read first.

    The backup branch is created before anything else so there is always one command that
    puts everything back.
    """
    return (
        f"git branch {backup}                 # a way back, created before anything changes\n"
        "git fetch upstream\n"
        "git log --oneline HEAD..upstream/main   # read what is coming\n"
        "git merge upstream/main\n"
        "make validate-content                   # confirm your state still loads\n"
        "make migrate      # only if validate-content says your progress schema is old\n"
        "\n"
        f"# If the merge goes wrong: git merge --abort, or git reset --hard {backup}"
    )


def migration_report(config: AppConfig) -> tuple[list[str], list[str]]:
    """What a migration would do, without doing it.

    Returns (steps, warnings). Running it is a separate, explicit act.

    Callable only when nothing else is wrong with the file: `update_command` checks
    `merge_in_progress` first and does not call this while conflict markers may still be in
    it. `store.read()` is called anyway, and guarded here too, because a merge is not the
    only way this file arrives broken — a hostile clone can commit any of the other shapes
    `StoreError` now reports instead of raising past this function (E2).
    """
    from quest_app.errors import ProblemReport
    from quest_app.migrations import MigrationError, attempts_on_older_quest_versions, migrate
    from quest_app.pipeline import load_world
    from quest_app.store import ProgressStore, StoreError

    store = ProgressStore(config)
    if not store.path.exists():
        return [], ["No participant progress file exists yet."]

    try:
        data = store.read()
    except StoreError as exc:
        return [], [str(exc)]
    try:
        _, applied = migrate(data)
    except MigrationError as exc:
        return [], [str(exc)]

    warnings: list[str] = []
    world = load_world(config, ProblemReport())
    if world is not None:
        quest_versions = {quest.id: quest.version for quest in world.content.quests.values()}
        stale = attempts_on_older_quest_versions(data, quest_versions)
        warnings.extend(
            f"{attempt['quest_id']} is on version {attempt['quest_version']}; "
            f"version {quest_versions[attempt['quest_id']]} is published. "
            "Your attempt is not moved automatically."
            for attempt in stale
        )
    return applied, warnings


def apply_migrations(config: AppConfig) -> tuple[list[str], list[str]]:
    """Move `progress.yaml` to the schema this build reads. Returns (steps, problems).

    The explicit act `migration_report` describes. The migrated document is validated by the
    store before it replaces the original, and the whole participant state is loaded again
    afterwards; if that load fails, the original bytes are put back exactly (E9: bytes, not
    text, so a CRLF file is restored as CRLF rather than normalized to LF on the way through).

    The whole read-modify-write runs under `store.exclusive()` (E8): every action holds this
    lock across the same shape of sequence, and `make migrate` is the one mutator of
    `progress.yaml` that did not, so it could interleave with an action running at the same
    moment instead of waiting its turn.
    """
    from quest_app.content_loader import SchemaSet
    from quest_app.errors import ProblemReport
    from quest_app.migrations import MigrationError, migrate
    from quest_app.pipeline import load_world
    from quest_app.safe_io import UnsafeStateFileError, read_bounded_bytes
    from quest_app.store import ProgressStore, StoreError, atomic_write_bytes

    store = ProgressStore(config)
    if not store.path.exists():
        return [], ["No participant progress file exists yet."]

    with store.exclusive():
        try:
            original = read_bounded_bytes(store.path)
        except UnsafeStateFileError as exc:
            return [], [f"The participant progress file is not safe to read: {exc}"]
        except OSError as exc:
            return [], [
                f"The participant progress file could not be read: "
                f"{exc.strerror or 'unknown error'}."
            ]
        try:
            data = store.read()
        except StoreError as exc:
            return [], [str(exc)]
        try:
            migrated, applied = migrate(data)
        except MigrationError as exc:
            return [], [str(exc)]
        if not applied:
            return [], []
        try:
            store.write(migrated, SchemaSet(config.schemas_root))
        except StoreError as exc:
            return [], [f"The migrated file did not validate, so nothing was changed: {exc}"]
        report = ProblemReport()
        if load_world(config, report) is None:
            atomic_write_bytes(config.participant_root, store.path, original)
            return [], [
                "Your state did not load after migrating, so the original was restored.",
                report.to_text(),
            ]
        return applied, []
