"""Hand in quest work, and pick up a review, with one command each.

Participants are business analysts and manual testers, not developers (Phase 2A.1). The
0.2.0 hand-in was five Git steps and a pull request form, and picking up a review was a
`git pull` whose refusals are written for developers. `gtq hand-in` and `gtq get-review`
do the same steps and explain every refusal in plain words.

Pushing and opening a pull request claim, on the participant's behalf, that work is ready
(`review.submission_instructions`). So only these terminal commands do it, and only when
the participant runs them. The browser and the local service still never push, never open
a pull request and never merge. Hand-in stages `participant/` alone, so nothing outside
the participant's own folder is committed.

The repository layout is the one `install.sh` creates. `origin` is the participant's fork,
`upstream` is the program's repository, and the participant works on one branch that is
not `main`.
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import yaml

TIMEOUT_SECONDS = 120
PARTICIPANT_DIR = "participant"
UPSTREAM_REMOTE = "upstream"
PROTECTED_BRANCHES = frozenset({"main", "master"})
NOTHING_HANDED_IN = (
    "Nothing handed in yet, so there is no review to bring in. Run `gtq hand-in` after you "
    "submit a quest."
)

# A GitHub remote URL, HTTPS or SSH, reduced to owner/name.
_GITHUB_REMOTE = re.compile(r"github\.com[:/](?P<owner>[^/]+)/(?P<name>[^/]+?)(?:\.git)?/?$")

# Every command this module may run, by program and subcommand. `run_command` refuses
# anything else, so no argument built from a remote URL or a branch name can pick the program.
PERMITTED_COMMANDS: frozenset[tuple[str, str]] = frozenset(
    {
        ("git", "add"),
        ("git", "commit"),
        ("git", "config"),
        ("git", "diff"),
        ("git", "fetch"),
        ("git", "merge"),
        ("git", "push"),
        ("git", "rev-list"),
        ("git", "rev-parse"),
        ("git", "status"),
        ("git", "symbolic-ref"),
        ("gh", "pr"),
    }
)

Runner = Callable[[Sequence[str], Path], "subprocess.CompletedProcess[str]"]


class HandInError(Exception):
    """A refusal, worded for the participant. Nothing after the failing step ran."""


@dataclass(frozen=True, slots=True)
class Outcome:
    headline: str
    details: list[str] = field(default_factory=list)
    # True when the reviewer's commits came in, so the site must be rebuilt to show them.
    brought_in: bool = False

    def to_text(self) -> str:
        return "\n".join([self.headline, *(f"  {line}" for line in self.details)])


def run_command(command: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    if tuple(command[:2]) not in PERMITTED_COMMANDS:
        raise ValueError(f"command not permitted for hand-in: {list(command[:2])!r}")
    try:
        return subprocess.run(  # noqa: S603 - program and subcommand are allowlisted above
            list(command),
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            timeout=TIMEOUT_SECONDS,
        )
    except FileNotFoundError as exc:
        raise HandInError(
            f"The program `{command[0]}` is not installed. Run the setup line from the "
            "pilot guide again; it installs what is missing."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise HandInError(
            f"`{' '.join(command[:2])}` took longer than {TIMEOUT_SECONDS} seconds. Check your "
            "internet connection and try again."
        ) from exc


def _last_line(result: subprocess.CompletedProcess[str]) -> str:
    lines = [line.strip() for line in (result.stderr or result.stdout).splitlines()]
    lines = [line for line in lines if line]
    return lines[-1] if lines else f"exit status {result.returncode}"


class _Repo:
    def __init__(self, root: Path, runner: Runner) -> None:
        self.root = root
        self.runner = runner

    def git(self, *args: str) -> subprocess.CompletedProcess[str]:
        return self.runner(["git", *args], self.root)

    def gh(self, *args: str) -> subprocess.CompletedProcess[str]:
        return self.runner(["gh", *args], self.root)

    def branch(self) -> str:
        result = self.git("symbolic-ref", "--quiet", "--short", "HEAD")
        name = result.stdout.strip()
        if result.returncode != 0 or not name:
            raise HandInError(
                "Your copy is not on a branch, so there is nowhere to hand in to. Ask in the "
                "pilot's Slack thread; this needs a person to look."
            )
        if name in PROTECTED_BRANCHES:
            raise HandInError(
                f"Your copy is on `{name}`, not on your own pilot branch. Run the setup line "
                "from the pilot guide again; it puts you back on your branch."
            )
        return name

    def remote_slug(self, remote: str) -> tuple[str, str]:
        # The configured value, not `remote get-url`, which applies `insteadOf` rewrites.
        result = self.git("config", "--get", f"remote.{remote}.url")
        match = _GITHUB_REMOTE.search(result.stdout.strip()) if result.returncode == 0 else None
        if match is None:
            raise HandInError(
                f"This copy has no GitHub `{remote}` link, so it was not made by the setup "
                "line. Run the setup line from the pilot guide."
            )
        return match.group("owner"), match.group("name")

    def pending_changes(self) -> list[str]:
        """Changed or new files under `participant/` that are not committed."""
        result = self.git("status", "--porcelain", "--untracked-files=all", "--", PARTICIPANT_DIR)
        if result.returncode != 0:
            raise HandInError(f"Git could not read your folder: {_last_line(result)}")
        return [line[3:] for line in result.stdout.splitlines() if line.strip()]

    def ignored_files(self) -> list[str]:
        """Files under `participant/` that `.gitignore` keeps out of every hand-in.

        Phase 2A.2: `git add participant/` skips them without a word, so a participant who
        saved proof as `api.token` or under a `secrets/` folder handed in without it, and
        the reviewer saw a required file as missing. They stay out, because the patterns
        are there for real secrets; hand-in now names each one instead.
        """
        # `-z` so Git prints each path as it is: without it a name with a space comes back in
        # quotes and a non-ASCII one as octal escapes, which is not what the participant saved.
        result = self.git(
            "status", "--porcelain", "-z", "--ignored", "--untracked-files=all",
            "--", PARTICIPANT_DIR,
        )  # fmt: skip
        if result.returncode != 0:
            return []
        return sorted(
            entry[3:]
            for entry in result.stdout.split("\0")
            if entry.startswith("!! ") and not _is_housekeeping(entry[3:])
        )

    def unpushed(self, branch: str) -> bool:
        if self.git("rev-parse", "--verify", "--quiet", f"origin/{branch}").returncode != 0:
            return True
        ahead = self.git("rev-list", "--count", f"origin/{branch}..HEAD")
        return ahead.returncode != 0 or ahead.stdout.strip() != "0"


def _identity_problem(repo: _Repo) -> bool:
    return any(repo.git("config", key).stdout.strip() == "" for key in ("user.name", "user.email"))


def _submitted(repo: _Repo) -> bool:
    """Whether any attempt in `participant/progress.yaml` is waiting for review."""
    try:
        text = (repo.root / PARTICIPANT_DIR / "progress.yaml").read_text(encoding="utf-8")
        progress = yaml.safe_load(text)
    except (OSError, yaml.YAMLError):
        return False
    attempts = progress.get("attempts") if isinstance(progress, dict) else None
    return any(
        isinstance(attempt, dict) and attempt.get("state") == "submitted"
        for attempt in attempts or ()
    )


def _combine_with_github(repo: _Repo, branch: str) -> str | None:
    """Bring in what the reviewer pushed, keeping the participant's own commits.

    Returns the commit before anything came in, or None when the branch was never handed
    in. A fast-forward when only the reviewer changed something, a merge when both did,
    and on a conflict the merge is undone, so the copy is exactly as it was.
    """
    if repo.git("rev-parse", "--verify", "--quiet", f"origin/{branch}").returncode != 0:
        return None
    fetched = repo.git("fetch", "--quiet", "origin", branch)
    if fetched.returncode != 0:
        raise HandInError(
            f"Could not reach GitHub: {_last_line(fetched)}. Check your internet connection "
            "and try again. Nothing was changed."
        )
    before = repo.git("rev-parse", "HEAD").stdout.strip()
    if repo.git("merge", "--ff-only", "--quiet", "FETCH_HEAD").returncode == 0:
        return before
    if repo.git("merge", "--no-edit", "--quiet", "FETCH_HEAD").returncode == 0:
        return before
    repo.git("merge", "--abort")
    raise HandInError(
        "You and your reviewer changed the same part of the same file, so the two cannot "
        "be combined automatically. Your work is saved on this computer and nothing of "
        "yours was lost. Ask in the pilot's Slack thread."
    )


def hand_in(repo_root: Path, runner: Runner = run_command) -> Outcome:
    repo = _Repo(repo_root, runner)
    branch = repo.branch()
    upstream_owner, upstream_name = repo.remote_slug(UPSTREAM_REMOTE)
    fork_owner, _ = repo.remote_slug("origin")
    if not _submitted(repo):
        raise HandInError(
            "Nothing is waiting for review, so there is nothing to hand in. Finish a quest "
            "and click Submit for review on its evidence page first."
        )

    left_out = _left_out_note(repo.ignored_files())
    changes = repo.pending_changes()
    if changes:
        if _identity_problem(repo):
            raise HandInError(
                "Git does not know your name yet. Run the setup line from the pilot guide "
                "again; it sets it from your GitHub account."
            )
        added = repo.git("add", "--", PARTICIPANT_DIR)
        if added.returncode != 0:
            raise HandInError(f"Git could not collect your files: {_last_line(added)}")
        committed = repo.git("commit", "--quiet", "-m", "Hand in quest work")
        if committed.returncode != 0:
            raise HandInError(f"Git could not save your work: {_last_line(committed)}")

    # The reviewer may have pushed since the last hand-in. Combining first keeps the push a
    # fast-forward, so an edit made after handing in never leaves the copy stuck.
    before = _combine_with_github(repo, branch)
    decisions = _decisions(repo, before) if before else []

    pushed_now = False
    if repo.unpushed(branch):
        pushed = repo.git("push", "--quiet", "--set-upstream", "origin", branch)
        if pushed.returncode != 0:
            raise HandInError(
                "Your work is saved on this computer, but sending it to GitHub failed: "
                f"{_last_line(pushed)}. Run `gtq hand-in` again; if it fails again, ask in "
                "Slack. Nothing is lost."
            )
        pushed_now = True

    upstream = f"{upstream_owner}/{upstream_name}"
    listed = repo.gh(
        "pr", "list", "--repo", upstream, "--head", branch, "--state", "open",
        "--json", "url,headRepositoryOwner",
        "--jq", f'.[] | select(.headRepositoryOwner.login == "{fork_owner}") | .url',
    )  # fmt: skip
    if listed.returncode != 0:
        raise HandInError(
            f"Your work is on GitHub, but finding your pull request failed: {_last_line(listed)}"
        )
    existing = listed.stdout.strip().splitlines()
    review_note = [f"Your reviewer's decision came in too: {line}" for line in decisions]
    if existing:
        if pushed_now:
            headline = "Handed in. Your pull request now has your latest work."
        else:
            headline = "Nothing new to hand in. Your pull request already has all your work."
        return Outcome(
            headline,
            [existing[0], *review_note, *left_out, "Post in the pilot's Slack thread."],
            brought_in=bool(decisions),
        )

    name = repo.git("config", "user.name").stdout.strip() or fork_owner
    created = repo.gh(
        "pr", "create", "--repo", upstream, "--base", "main",
        "--head", f"{fork_owner}:{branch}",
        "--title", f"Pilot: {name}",
        "--body", "Pilot hand-in, made by `gtq hand-in`. Never merged: the reviewer "
        "pushes the review to this branch.",
    )  # fmt: skip
    if created.returncode != 0:
        raise HandInError(
            "Your work is on GitHub, but opening the pull request failed: "
            f"{_last_line(created)}. Run `gtq hand-in` again, or ask in Slack."
        )
    url = created.stdout.strip().splitlines()[-1] if created.stdout.strip() else ""
    return Outcome(
        "Handed in. Your pull request is open.",
        [url, *left_out, "Post in the pilot's Slack thread that a quest is ready."],
    )


# Ignored files that are nobody's proof: the application's own lock beside progress.yaml
# (`store.LOCK_FILENAME`, created on the first action and kept), and what an operating system
# or editor drops into a folder it opens. Phase 2A.2's verify pass found the lock and a Mac
# Finder `.DS_Store` reported as "named like passwords or keys" on every hand-in.
_HOUSEKEEPING_NAMES = frozenset({".progress.lock", ".DS_Store", "Thumbs.db", "desktop.ini"})
_HOUSEKEEPING_SUFFIXES = (".swp", ".pyc", ".pyo")


def _is_housekeeping(path: str) -> bool:
    parts = path.split("/")
    return (
        parts[-1] in _HOUSEKEEPING_NAMES
        or parts[-1].endswith(_HOUSEKEEPING_SUFFIXES)
        or "__pycache__" in parts
    )


def _left_out_note(paths: list[str]) -> list[str]:
    """What hand-in tells the participant about files it would not send."""
    if not paths:
        return []
    return [
        "Not sent: these files are named like passwords or keys, so they are never handed in, "
        "and your reviewer will not see them:",
        *(f"  {path}" for path in paths),
        "If one of them is proof the quest asks for, take any secret out of it, save it under "
        "the name the quest's evidence page shows, and run `gtq hand-in` again.",
    ]


def _decisions(repo: _Repo, before: str) -> list[str]:
    """One line per review record the pull brought in, from the record itself."""
    changed = repo.git("diff", "--name-only", f"{before}..HEAD", "--", PARTICIPANT_DIR)
    words = {"approved": "Verified", "needs_changes": "Needs changes", "rejected": "Rejected"}
    lines = []
    for path in changed.stdout.splitlines():
        if not path.endswith("/review.yaml"):
            continue
        try:
            record = yaml.safe_load((repo.root / path).read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            continue
        if isinstance(record, dict):
            decision = words.get(str(record.get("decision")), str(record.get("decision")))
            lines.append(f"{record.get('quest_id', path)}: {decision}")
    return lines


def get_review(repo_root: Path, runner: Runner = run_command) -> Outcome:
    repo = _Repo(repo_root, runner)
    branch = repo.branch()
    repo.remote_slug("origin")
    if repo.git("rev-parse", "--verify", "--quiet", f"origin/{branch}").returncode != 0:
        return Outcome(NOTHING_HANDED_IN)

    changes = repo.pending_changes()
    if changes:
        shown = changes[:5] + ([f"... and {len(changes) - 5} more"] if len(changes) > 5 else [])
        raise HandInError(
            "You have work that is not handed in yet, so the review cannot be brought in "
            "without mixing the two. If you meant to hand it in, run `gtq hand-in` first. "
            "Otherwise ask in Slack. Files: " + ", ".join(shown)
        )

    before = _combine_with_github(repo, branch)
    if before is None:
        return Outcome(NOTHING_HANDED_IN)
    after = repo.git("rev-parse", "HEAD").stdout.strip()
    if after == before:
        return Outcome(
            "No review yet. Your reviewer posts in Slack when it is ready; run this again then."
        )
    decisions = _decisions(repo, before) or ["Your reviewer's changes are in."]
    return Outcome(
        "Your review is in.",
        [*decisions, "Reload the application in your browser, or run `gtq start`."],
        brought_in=True,
    )
