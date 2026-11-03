"""`gtq hand-in` and `gtq get-review` against real Git repositories (Phase 2A.1).

The fork and the program's repository are local bare repositories behind GitHub-shaped
URLs (`url.<path>.insteadOf`), so the commands parse the same remotes `install.sh` creates.
The GitHub CLI is a stand-in that records what it was asked, because opening a real pull
request is not something a test may do.

The pre-pilot rehearsal (`docs/pilot/PILOT-LOG.md`) found that a hand-in leaving
`participant/ACTIVITY.md` uncommitted makes the participant's pull of the review fail.
`test_review_round_trip` is that flow end to end.
"""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from pathlib import Path

import pytest
from quest_app import handin
from quest_app.handin import HandInError, check_for_review, get_review, hand_in, run_command

FORK_URL = "https://github.com/alice/golden-thread-quest.git"
UPSTREAM_URL = "https://github.com/beekeeper-lab/golden-thread-quest.git"
QUEST = "base-camp-repository-safety"
EVIDENCE = f"participant/evidence/{QUEST}/base-attempt-001"
SUBMITTED = f"attempts:\n- quest_id: {QUEST}\n  state: submitted\n"


def git(cwd: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True)
    return result.stdout.strip()


class FakeGh:
    """Answers `gh pr list` and `gh pr create` the way GitHub would for one fork."""

    def __init__(self) -> None:
        self.calls: list[list[str]] = []
        self.pull_request: str | None = None
        self.labels = ""

    def __call__(self, command: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        if command[0] != "gh":
            return run_command(command, cwd)
        self.calls.append(list(command))
        out = ""
        if command[1:3] == ["pr", "list"]:
            out = self.pull_request or ""
            if out and "url,labels,headRepositoryOwner" in command:
                out = f"{out}\t{self.labels}\n"
        elif command[1:3] == ["pr", "create"]:
            self.pull_request = "https://github.com/beekeeper-lab/golden-thread-quest/pull/7"
            out = self.pull_request + "\n"
        return subprocess.CompletedProcess(list(command), 0, out, "")

    def creates(self) -> list[list[str]]:
        return [call for call in self.calls if call[1:3] == ["pr", "create"]]


@pytest.fixture(autouse=True)
def isolated_git(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """No global or system Git configuration: identity and URLs come from the fixture."""
    empty = tmp_path / "gitconfig"
    empty.write_text("")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(empty))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")


def _redirect(repo: Path, fork: Path, upstream: Path) -> None:
    git(repo, "config", f"url.{fork}.insteadOf", FORK_URL)
    git(repo, "config", f"url.{upstream}.insteadOf", UPSTREAM_URL)


@pytest.fixture()
def world(tmp_path: Path) -> dict[str, Path]:
    upstream = tmp_path / "upstream.git"
    fork = tmp_path / "fork.git"
    seed = tmp_path / "seed"
    seed.mkdir()
    git(seed, "init", "--quiet", "--initial-branch=main")
    git(seed, "config", "user.name", "Maintainer")
    git(seed, "config", "user.email", "m@example.com")
    (seed / "README.md").write_text("program\n")
    git(seed, "add", ".")
    git(seed, "commit", "--quiet", "-m", "program")
    git(tmp_path, "clone", "--quiet", "--bare", str(seed), str(upstream))
    git(tmp_path, "clone", "--quiet", "--bare", str(seed), str(fork))

    participant = tmp_path / "participant-copy"
    git(tmp_path, "clone", "--quiet", str(fork), str(participant))
    _redirect(participant, fork, upstream)
    git(participant, "remote", "set-url", "origin", FORK_URL)
    git(participant, "remote", "add", "upstream", UPSTREAM_URL)
    git(participant, "config", "user.name", "Alice")
    git(participant, "config", "user.email", "alice@example.com")
    git(participant, "switch", "--quiet", "-c", "pilot/alice")

    (participant / EVIDENCE).mkdir(parents=True)
    (participant / EVIDENCE / "PROOF.md").write_text("# Proof\n")
    (participant / "participant" / "ACTIVITY.md").write_text("- started\n- submitted\n")
    (participant / "participant" / "progress.yaml").write_text(SUBMITTED)
    (participant / "notes-outside.txt").write_text("not participant work\n")
    return {"participant": participant, "fork": fork, "upstream": upstream, "root": tmp_path}


def _review(world: dict[str, Path], decision: str) -> None:
    """The pilot lead: check out the participant's branch, record a review, push it back."""
    lead = world["root"] / "lead-copy"
    if not lead.exists():
        git(world["root"], "clone", "--quiet", str(world["fork"]), str(lead))
        git(lead, "config", "user.name", "Lead")
        git(lead, "config", "user.email", "lead@example.com")
        git(lead, "switch", "--quiet", "pilot/alice")
    else:
        git(lead, "pull", "--quiet")
    (lead / EVIDENCE / "review.yaml").write_text(f"quest_id: {QUEST}\ndecision: {decision}\n")
    with (lead / "participant" / "ACTIVITY.md").open("a") as handle:
        handle.write(f"- reviewed: {decision}\n")
    git(lead, "add", "participant")
    git(lead, "commit", "--quiet", "-m", "Review")
    git(lead, "push", "--quiet")


def test_first_hand_in_commits_only_participant_work_and_opens_the_pull_request(
    world: dict[str, Path],
) -> None:
    gh = FakeGh()
    outcome = hand_in(world["participant"], runner=gh)

    assert outcome.headline == "Handed in. Your pull request is open."
    assert gh.pull_request in outcome.details
    pushed = git(world["fork"], "ls-tree", "-r", "--name-only", "pilot/alice")
    assert "participant/ACTIVITY.md" in pushed
    assert f"{EVIDENCE}/PROOF.md" in pushed
    assert "notes-outside.txt" not in pushed
    [create] = gh.creates()
    assert create[create.index("--head") + 1] == "alice:pilot/alice"
    assert create[create.index("--repo") + 1] == "beekeeper-lab/golden-thread-quest"
    assert create[create.index("--title") + 1] == "Pilot: Alice"


def test_hand_in_again_updates_the_same_pull_request(world: dict[str, Path]) -> None:
    gh = FakeGh()
    hand_in(world["participant"], runner=gh)
    assert hand_in(world["participant"], runner=gh).headline.startswith("Nothing new")

    (world["participant"] / EVIDENCE / "PROOF.md").write_text("# Proof\n\nFixed.\n")
    outcome = hand_in(world["participant"], runner=gh)

    assert outcome.headline == "Handed in. Your pull request now has your latest work."
    assert len(gh.creates()) == 1
    assert "Fixed." in git(world["fork"], "show", f"pilot/alice:{EVIDENCE}/PROOF.md")


def test_review_round_trip(world: dict[str, Path]) -> None:
    gh = FakeGh()
    hand_in(world["participant"], runner=gh)
    assert get_review(world["participant"], runner=gh).headline.startswith("No review yet")

    _review(world, "needs_changes")
    outcome = get_review(world["participant"], runner=gh)
    assert outcome.headline == "Your review is in."
    assert f"{QUEST}: Needs changes" in outcome.details

    (world["participant"] / EVIDENCE / "PROOF.md").write_text("# Proof\n\nFixed.\n")
    hand_in(world["participant"], runner=gh)
    _review(world, "approved")
    assert f"{QUEST}: Verified" in get_review(world["participant"], runner=gh).details


def test_get_review_refuses_while_work_is_not_handed_in(world: dict[str, Path]) -> None:
    gh = FakeGh()
    hand_in(world["participant"], runner=gh)
    _review(world, "approved")
    (world["participant"] / EVIDENCE / "PROOF.md").write_text("edited after hand-in\n")
    head = git(world["participant"], "rev-parse", "HEAD")

    with pytest.raises(HandInError, match="not handed in yet"):
        get_review(world["participant"], runner=gh)
    assert git(world["participant"], "rev-parse", "HEAD") == head


def test_hand_in_refuses_on_main(world: dict[str, Path]) -> None:
    git(world["participant"], "switch", "--quiet", "main")
    with pytest.raises(HandInError, match="not on your own pilot branch"):
        hand_in(world["participant"], runner=FakeGh())


def test_hand_in_without_a_git_identity_refuses_before_committing(
    world: dict[str, Path],
) -> None:
    git(world["participant"], "config", "--unset", "user.name")
    head = git(world["participant"], "rev-parse", "HEAD")
    with pytest.raises(HandInError, match="does not know your name"):
        hand_in(world["participant"], runner=FakeGh())
    assert git(world["participant"], "rev-parse", "HEAD") == head


def test_a_failed_push_says_the_work_is_kept(world: dict[str, Path]) -> None:
    git(world["participant"], "config", "--unset", f"url.{world['fork']}.insteadOf")
    git(world["participant"], "config", f"url.{world['root'] / 'missing.git'}.insteadOf", FORK_URL)
    with pytest.raises(HandInError, match="saved on this computer"):
        hand_in(world["participant"], runner=FakeGh())
    assert git(world["participant"], "status", "--porcelain", "--", "participant") == ""


def test_a_copy_not_made_by_setup_is_named(world: dict[str, Path]) -> None:
    git(world["participant"], "remote", "remove", "upstream")
    with pytest.raises(HandInError, match="no GitHub `upstream` link"):
        hand_in(world["participant"], runner=FakeGh())


def test_only_allowlisted_commands_run(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="not permitted"):
        run_command(["git", "reset", "--hard"], tmp_path)
    with pytest.raises(ValueError, match="not permitted"):
        run_command(["sh", "-c", "true"], tmp_path)


def test_an_edit_after_hand_in_is_combined_with_the_review(world: dict[str, Path]) -> None:
    """Verify pass V1: this sequence used to leave the branch ahead 1, behind 1."""
    gh = FakeGh()
    participant = world["participant"]
    hand_in(participant, runner=gh)
    _review(world, "needs_changes")
    (participant / EVIDENCE / "notes.md").write_text("one more thing\n")

    with pytest.raises(HandInError, match="not handed in yet"):
        get_review(participant, runner=gh)
    outcome = hand_in(participant, runner=gh)

    assert outcome.headline == "Handed in. Your pull request now has your latest work."
    assert f"Your reviewer's decision came in too: {QUEST}: Needs changes" in outcome.details
    assert outcome.brought_in
    on_github = git(world["fork"], "ls-tree", "-r", "--name-only", "pilot/alice")
    assert f"{EVIDENCE}/notes.md" in on_github
    assert f"{EVIDENCE}/review.yaml" in on_github
    in_step = git(participant, "rev-list", "--count", "origin/pilot/alice...HEAD")
    assert in_step == "0"
    assert get_review(participant, runner=gh).headline.startswith("No review yet")


def test_a_real_conflict_changes_nothing(world: dict[str, Path]) -> None:
    gh = FakeGh()
    participant = world["participant"]
    hand_in(participant, runner=gh)
    lead = world["root"] / "lead-copy"
    _review(world, "needs_changes")
    (lead / EVIDENCE / "PROOF.md").write_text("# Proof\n\nThe reviewer's version.\n")
    git(lead, "commit", "--quiet", "-am", "Reviewer edits the proof")
    git(lead, "push", "--quiet")
    (participant / EVIDENCE / "PROOF.md").write_text("# Proof\n\nMy version.\n")

    with pytest.raises(HandInError, match="changed the same part"):
        hand_in(participant, runner=gh)

    assert git(participant, "status", "--porcelain", "--", "participant") == ""
    assert "My version." in (participant / EVIDENCE / "PROOF.md").read_text()
    assert not (participant / ".git" / "MERGE_HEAD").exists()


def test_hand_in_refuses_when_nothing_is_submitted(world: dict[str, Path]) -> None:
    progress = world["participant"] / "participant" / "progress.yaml"
    progress.write_text(SUBMITTED.replace("submitted", "in_progress"))
    gh = FakeGh()
    with pytest.raises(HandInError, match="Nothing is waiting for review"):
        hand_in(world["participant"], runner=gh)
    assert gh.calls == []


def test_get_review_before_any_hand_in_says_so(world: dict[str, Path]) -> None:
    outcome = get_review(world["participant"], runner=FakeGh())
    assert outcome.headline.startswith("Nothing handed in yet")


def test_hand_in_names_every_file_it_left_out(world: dict[str, Path]) -> None:
    """Phase 2A.2: files matching `.gitignore` were left out of the hand-in without a word."""
    participant = world["participant"]
    (participant / ".gitignore").write_text("*.token\n**/secrets/\n")
    (participant / EVIDENCE / "api.token").write_text("redacted\n")
    (participant / EVIDENCE / "secrets").mkdir()
    (participant / EVIDENCE / "secrets" / "env.txt").write_text("redacted\n")

    outcome = hand_in(participant, runner=FakeGh())

    pushed = git(world["fork"], "ls-tree", "-r", "--name-only", "pilot/alice")
    assert "api.token" not in pushed
    assert "secrets/env.txt" not in pushed
    text = outcome.to_text()
    assert f"{EVIDENCE}/api.token" in text
    assert f"{EVIDENCE}/secrets/env.txt" in text
    assert "reviewer will not see them" in text


def test_hand_in_with_nothing_left_out_says_nothing_about_it(world: dict[str, Path]) -> None:
    """The verify pass found the application's own lock file and a Finder `.DS_Store`
    reported as secret-like on every hand-in after a browser action."""
    participant = world["participant"]
    (participant / ".gitignore").write_text(".progress.lock\n.DS_Store\n*.token\n")
    (participant / "participant" / ".progress.lock").write_text("")
    (participant / EVIDENCE / ".DS_Store").write_bytes(b"\0\0\0\1Bud1")
    outcome = hand_in(participant, runner=FakeGh())
    assert "Not sent" not in outcome.to_text()


def test_a_left_out_name_is_shown_as_it_was_saved(world: dict[str, Path]) -> None:
    participant = world["participant"]
    (participant / ".gitignore").write_text("*.token\n")
    (participant / EVIDENCE / "my café key.token").write_text("redacted\n")
    outcome = hand_in(participant, runner=FakeGh())
    assert f"{EVIDENCE}/my café key.token" in outcome.to_text()


def test_check_for_review_says_where_the_pull_request_stands(world: dict[str, Path]) -> None:
    gh = FakeGh()
    hand_in(world["participant"], runner=gh)

    gh.labels = ""
    waiting = check_for_review(world["participant"], runner=gh)
    assert waiting.headline.startswith("No review yet")
    assert any("has not run yet" in line for line in waiting.details)

    gh.labels = "gtq:needs-fixes"
    assert any(
        "found something to fix" in line
        for line in check_for_review(world["participant"], runner=gh).details
    )

    gh.labels = "gtq:ready-for-review"
    ready = check_for_review(world["participant"], runner=gh)
    assert any("waiting for a reviewer" in line for line in ready.details)
    assert gh.pull_request in ready.details


def test_check_for_review_brings_a_decision_in(world: dict[str, Path]) -> None:
    gh = FakeGh()
    hand_in(world["participant"], runner=gh)
    _review(world, "approved")
    outcome = check_for_review(world["participant"], runner=gh)
    assert outcome.brought_in
    assert f"{QUEST}: Verified" in outcome.details


def test_hand_in_no_longer_tells_the_participant_to_post_in_slack(
    world: dict[str, Path],
) -> None:
    outcome = hand_in(world["participant"], runner=FakeGh())
    assert "Slack" not in outcome.to_text()
    assert "You do not need to tell anyone" in outcome.to_text()


def test_a_branch_carrying_changes_outside_participant_is_not_brought_in(
    world: dict[str, Path],
) -> None:
    gh = FakeGh()
    hand_in(world["participant"], runner=gh)
    _review(world, "approved")
    lead = world["root"] / "lead-copy"
    (lead / "README.md").write_text("changed program\n")
    git(lead, "add", "README.md")
    git(lead, "commit", "--quiet", "-m", "Not a review")
    git(lead, "push", "--quiet")
    head = git(world["participant"], "rev-parse", "HEAD")

    with pytest.raises(HandInError, match="outside your participant folder"):
        check_for_review(world["participant"], runner=gh)
    assert git(world["participant"], "rev-parse", "HEAD") == head


def test_installed_dependencies_are_counted_not_listed(world: dict[str, Path]) -> None:
    """2026-10-31: `npm install` under `participant/` put 190 Playwright files in the
    "named like passwords or keys" list, burying the `api.token` that belonged there."""
    participant = world["participant"]
    (participant / ".gitignore").write_text("node_modules/\n.venv/\n*.token\n")
    for folder in ("participant/node_modules/x", "participant/tests/.venv/lib"):
        (participant / folder).mkdir(parents=True)
    (participant / "participant" / "node_modules" / "x" / "package.json").write_text("{}\n")
    (participant / "participant" / "node_modules" / "x" / "index.js").write_text("\n")
    (participant / "participant" / "tests" / ".venv" / "lib" / "site.py").write_text("\n")
    (participant / EVIDENCE / "api.token").write_text("redacted\n")
    details = hand_in(participant, runner=FakeGh()).details
    secret_list = details[details.index(f"  {EVIDENCE}/api.token") - 1 :]
    assert not any("package.json" in line or "site.py" in line for line in details)
    assert "Also not sent: 2 files in participant/node_modules/" in "\n".join(details)
    assert "Also not sent: 1 file in participant/tests/.venv/" in "\n".join(details)
    assert secret_list[0].startswith("Not sent: these files are named like passwords")


def test_a_secret_named_file_inside_a_dependency_folder_is_still_listed(
    world: dict[str, Path],
) -> None:
    """Review of PR #50: dropping the whole folder hid `node_modules/x/api.token`."""
    participant = world["participant"]
    (participant / ".gitignore").write_text("node_modules/\n.venv/\n*.token\n.env\n")
    (participant / "participant" / "node_modules" / "x").mkdir(parents=True)
    (participant / "participant" / ".venv").mkdir(parents=True)
    (participant / "participant" / "node_modules" / "x" / "api.token").write_text("redacted\n")
    (participant / "participant" / "node_modules" / "x" / "index.js").write_text("\n")
    (participant / "participant" / ".venv" / ".env").write_text("redacted\n")
    text = hand_in(participant, runner=FakeGh()).to_text()
    assert "participant/node_modules/x/api.token" in text
    assert "participant/.venv/.env" in text
    assert "named like passwords or keys" in text
    assert "index.js" not in text
    assert "Also not sent: 1 file in participant/node_modules/" in text
    pushed = git(world["fork"], "ls-tree", "-r", "--name-only", "pilot/alice")
    assert "node_modules" not in pushed and ".venv" not in pushed


def test_dependency_folders_with_no_ignore_rule_are_handed_in_without_a_word(
    world: dict[str, Path],
) -> None:
    """What hand-in does when nothing ignores `node_modules/`: `git add participant/` sends it
    like any other file, and the note says nothing. This is pinned, not endorsed. The
    program's own `.gitignore` ignores these folders at any depth (the next test), so it
    happens only if a participant removes that rule."""
    participant = world["participant"]
    (participant / ".gitignore").write_text("*.token\n")
    (participant / "participant" / "node_modules" / "x").mkdir(parents=True)
    (participant / "participant" / "node_modules" / "x" / "package.json").write_text("{}\n")
    text = hand_in(participant, runner=FakeGh()).to_text()
    pushed = git(world["fork"], "ls-tree", "-r", "--name-only", "pilot/alice")
    assert "participant/node_modules/x/package.json" in pushed
    assert "node_modules" not in text


PROGRAM_GITIGNORE = Path(__file__).resolve().parents[2] / ".gitignore"


def test_the_program_ignores_dependency_folders_wherever_a_participant_installs(
    tmp_path: Path,
) -> None:
    """The guard against the case above is the repository's own `.gitignore`. The rules are
    copied into a new repository, so the test does not need to run inside a checkout."""
    git(tmp_path, "init", "--quiet")
    (tmp_path / ".gitignore").write_text(PROGRAM_GITIGNORE.read_text())
    paths = [
        "participant/node_modules/x/package.json",
        "participant/tests/playwright/node_modules/x/package.json",
        "participant/.venv/lib/site.py",
        "participant/tests/venv/lib/site.py",
    ]
    result = subprocess.run(
        ["git", "check-ignore", "--no-index", "-v", "-n", "--", *paths],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    lines = result.stdout.splitlines()
    assert len(lines) == len(paths), result.stderr
    # A matching rule that starts with `!` means "do not ignore", so it must not count.
    patterns = [line.split("\t")[0].split(":", 2)[2] for line in lines if not line.startswith("::")]
    assert len(patterns) == len(paths), lines
    assert not [pattern for pattern in patterns if pattern.startswith("!")], lines


def test_package_files_under_build_folders_are_not_called_secrets(world: dict[str, Path]) -> None:
    """Review of PR #50, with the program's real ignore rules: `dist/` and `__pycache__/` are
    build and cache rules, so a package file they match is not named like a secret."""
    participant = world["participant"]
    (participant / ".gitignore").write_text(PROGRAM_GITIGNORE.read_text())
    base = participant / "participant" / "tests"
    files = {
        "node_modules/somepkg/dist/index.js": "\n",
        "node_modules/playwright/lib/cli/testActions.js": "\n",
        "node_modules/playwright-core/lib/server/build/out.js": "\n",
        ".venv/lib/python3.12/site-packages/pkg/__init__.py": "\n",
        ".venv/lib/python3.12/site-packages/pkg/__pycache__/__init__.cpython-312.pyc": "\n",
        ".venv/lib/python3.12/site-packages/pkg/dist/data.txt": "\n",
        "node_modules/somepkg/.npmrc": "redacted\n",
        ".venv/.env": "redacted\n",
        "node_modules/somepkg/dist/api.token": "\n",
        "node_modules/somepkg/build/secrets/key.txt": "redacted\n",
    }
    for name, text in files.items():
        (base / name).parent.mkdir(parents=True, exist_ok=True)
        (base / name).write_text(text)
    (participant / EVIDENCE / "api.token").write_text("redacted\n")
    text = hand_in(participant, runner=FakeGh()).to_text()
    assert f"{EVIDENCE}/api.token" in text
    assert "participant/tests/node_modules/somepkg/.npmrc" in text
    assert "participant/tests/.venv/.env" in text
    # A secret's name still counts when it sits inside a build or cache folder.
    assert "participant/tests/node_modules/somepkg/dist/api.token" in text
    assert "participant/tests/node_modules/somepkg/build/secrets/key.txt" in text
    for name in ("index.js", "testActions.js", "out.js", "__init__", "data.txt"):
        assert name not in text, name
    assert "Also not sent: 3 files in participant/tests/node_modules/" in text
    assert "Also not sent: 2 files in participant/tests/.venv/" in text


def test_a_rule_that_un_ignores_a_name_does_not_make_it_a_secret(world: dict[str, Path]) -> None:
    """With `-v`, Git also reports a matching `!` rule, which says the name is not ignored."""
    participant = world["participant"]
    (participant / ".gitignore").write_text("node_modules/\n*.token\n!sample.token\n")
    (participant / "participant" / "node_modules" / "x").mkdir(parents=True)
    (participant / "participant" / "node_modules" / "x" / "sample.token").write_text("demo\n")
    text = hand_in(participant, runner=FakeGh()).to_text()
    assert "sample.token" not in text
    assert "Also not sent: 1 file in participant/node_modules/" in text


class GitCannotAnswer(FakeGh):
    """`git check-ignore` fails, or answers for fewer paths than it was asked about."""

    def __init__(self, how: str) -> None:
        super().__init__()
        self.how = how

    def __call__(self, command: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        if list(command[:2]) == ["git", "check-ignore"]:
            if self.how == "fails":
                return subprocess.CompletedProcess(list(command), 128, "", "fatal: broken\n")
            answer = run_command(command, cwd)
            short = "".join(answer.stdout.splitlines(keepends=True)[:-1])
            return subprocess.CompletedProcess(list(command), answer.returncode, short, "")
        return super().__call__(command, cwd)


@pytest.mark.parametrize("how", ["fails", "short"])
def test_when_git_cannot_say_which_rule_matched_every_package_file_is_listed(
    world: dict[str, Path], how: str
) -> None:
    """Review of PR #50: the fallback is what keeps a real secret from being hidden, so when
    Git cannot answer, every file in the dependency folder is listed and none is counted."""
    participant = world["participant"]
    (participant / ".gitignore").write_text(PROGRAM_GITIGNORE.read_text())
    package = participant / "participant" / "node_modules" / "x"
    (package / "dist").mkdir(parents=True)
    for name in ("index.js", "dist/main.js", "api.token"):
        (package / name).write_text("\n")
    text = hand_in(participant, runner=GitCannotAnswer(how)).to_text()
    note = text[text.index("named like passwords or keys") :]
    for name in ("index.js", "dist/main.js", "api.token"):
        assert f"participant/node_modules/x/{name}" in note, name
    assert "Also not sent" not in text


def test_package_files_are_matched_to_their_rule_across_batches(
    world: dict[str, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """With a batch of two, five files take three `check-ignore` calls; each answer must be
    read against its own path, so the two secrets in the second and third batch are found."""
    monkeypatch.setattr(handin, "_CHECK_IGNORE_BATCH", 2)
    participant = world["participant"]
    (participant / ".gitignore").write_text(PROGRAM_GITIGNORE.read_text())
    package = participant / "participant" / "node_modules" / "x"
    package.mkdir(parents=True)
    for name in ("a.js", "b.js", "c.token", "d.js", "e.token"):
        (package / name).write_text("\n")
    runner = CountingRunner()
    text = hand_in(participant, runner=runner).to_text()
    assert "participant/node_modules/x/c.token" in text
    assert "participant/node_modules/x/e.token" in text
    for name in ("a.js", "b.js", "d.js"):
        assert name not in text, name
    assert "Also not sent: 3 files in participant/node_modules/" in text
    assert runner.check_ignore_calls == 3


class CountingRunner(FakeGh):
    def __init__(self) -> None:
        super().__init__()
        self.check_ignore_calls = 0

    def __call__(self, command: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        if list(command[:2]) == ["git", "check-ignore"]:
            self.check_ignore_calls += 1
        return super().__call__(command, cwd)


@pytest.mark.parametrize(
    ("line", "rule"),
    [
        (".gitignore:44:*.token\tparticipant/x/a.token", "*.token"),
        ("C:/Users/x/ignore:3:*.token\tparticipant/x/a.token", "*.token"),
        (".gitignore:3:!sample.token\tparticipant/x/sample.token", "!sample.token"),
        ("::\tparticipant/x/index.js", ""),
    ],
)
def test_the_matching_rule_is_read_even_when_its_file_path_has_a_colon(
    line: str, rule: str
) -> None:
    """Review of PR #50: a `core.excludesFile` on a Windows drive (`C:/...`) gave `3:*.token`."""
    assert handin._rule(line) == rule


def test_a_secret_inside_any_build_or_cache_folder_is_still_listed(world: dict[str, Path]) -> None:
    """Review of PR #50: `*.egg-info/` was a not-a-secret rule whose folders were never taken
    out of the path, so Git named the folder's rule and `pkg.egg-info/api.token` was counted.
    Every folder rule on that list gets a secret inside a folder it matches."""
    participant = world["participant"]
    (participant / ".gitignore").write_text(PROGRAM_GITIGNORE.read_text())
    site = participant / "participant" / "tests" / ".venv" / "lib" / "site-packages"
    folders = sorted(
        rule.removesuffix("/").replace("*", "pkg")
        for rule in handin._NOT_SECRET_RULES
        # Hand-in drops everything under `__pycache__/` as housekeeping before this check
        # (older than PR #50, in the parking lot), so that folder cannot be tested here.
        if rule.endswith("/") and rule != "__pycache__/"
    )
    assert "pkg.egg-info" in folders
    for folder in folders:
        (site / folder).mkdir(parents=True, exist_ok=True)
        (site / folder / "api.token").write_text("\n")
    text = hand_in(participant, runner=FakeGh()).to_text()
    note = text[text.index("named like passwords or keys") :]
    missing = [
        folder
        for folder in folders
        if f"participant/tests/.venv/lib/site-packages/{folder}/api.token" not in note
    ]
    assert not missing, missing
