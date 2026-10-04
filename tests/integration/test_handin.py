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
from quest_app.handin import HandInError, get_review, hand_in, run_command

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

    def __call__(self, command: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        if command[0] != "gh":
            return run_command(command, cwd)
        self.calls.append(list(command))
        out = ""
        if command[1:3] == ["pr", "list"]:
            out = self.pull_request or ""
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
    outcome = hand_in(world["participant"], runner=FakeGh())
    assert "Not sent" not in outcome.to_text()
