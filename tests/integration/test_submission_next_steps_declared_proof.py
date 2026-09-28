"""Round 15 E9.

`submission_instructions`'s suggested `git add` named only the evidence package and
`participant/progress.yaml`. Every quest's required proof also names files outside that
package — `participant/context/**`, `participant/skills/**` — which
`proof_paths_outside_package` already exists to find (it is what the changed-evidence check
reads), but the submission's own suggested `git add` never mentioned it. A participant or
agent following the JSON result's `next_steps` literally pushed a branch missing that proof,
and a reviewer's clone then showed it `missing` with nothing to read.

The text CLI compounded it: it read `result["next"]`, a key `submit-for-review` never sets
(the key is `next_steps`), so `quest action submit-for-review` printed nothing here at all —
the one surface a Cowork sandbox has no browser to fall back on.
"""

from __future__ import annotations

import dataclasses
import shlex
import subprocess
import sys
from pathlib import Path

from quest_app.actions import ActionRunner
from quest_app.config import AppConfig
from quest_app.content_loader import SchemaSet
from quest_app.errors import ProblemReport
from quest_app.models import ProofRequirement
from quest_app.pipeline import load_world

JIRA = "jira-read-assigned-stories"
JIRA_OUTSIDE = (
    "participant/context/jira/assigned/index.md",
    "participant/context/jira/assigned/stories.json",
    "participant/skills/jira-read-assigned/SKILL.md",
)
REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _runner(config: AppConfig) -> ActionRunner:
    def load():  # type: ignore[no-untyped-def]
        report = ProblemReport()
        world = load_world(config, report)
        assert world is not None, report.to_text()
        return world

    return ActionRunner(config, SchemaSet(config.schemas_root), load)


def _git_add_line(next_steps: str) -> str:
    (line,) = (line for line in next_steps.splitlines() if line.startswith("git add "))
    return line


def test_the_suggested_git_add_names_every_declared_proof_path_outside_the_package(
    config: AppConfig,
) -> None:
    result = _runner(config).perform("submit-for-review", {"quest_id": JIRA, "confirm": True})

    add_line = _git_add_line(result["next_steps"])
    assert f"participant/evidence/{JIRA}/jira-attempt-001" in add_line
    assert "participant/progress.yaml" in add_line
    for path in JIRA_OUTSIDE:
        assert path in add_line, f"{path} missing from the suggested git add: {add_line}"


def test_a_quest_declaring_no_proof_outside_the_package_keeps_the_original_wording(
    config: AppConfig,
) -> None:
    """The widening only applies when `proof_paths_outside_package` finds something.

    Real content always declares at least a validator or a package-relative path, so this
    exercises `_next_steps_for_submission` directly against a quest whose declared proof has
    been stripped to nothing, rather than hunting for real content that happens to have none.
    """
    from quest_app.actions import _next_steps_for_submission

    report = ProblemReport()
    world = load_world(config, report)
    assert world is not None, report.to_text()
    quest = dataclasses.replace(world.content.quests[JIRA], proof=())
    attempt = world.participant.progress.attempt_for(JIRA)

    from quest_app.review import submission_instructions

    unwidened = submission_instructions(quest.id, attempt.attempt_id, None)
    assert _next_steps_for_submission(quest, attempt) == unwidened


def test_the_suggested_git_add_shell_quotes_a_proof_path_with_a_space(config: AppConfig) -> None:
    """Round 16 E9.

    `relativePath` in `schemas/quest.schema.json` allows a space or a shell metacharacter,
    so a declared proof path is authored, not generated, and this text is not something
    that can trust it to appear unquoted in a command meant to be pasted into a shell.
    Unquoted, a space adds the wrong pathspecs to `git add`, and `$(...)` runs whatever it
    names the moment the suggestion is pasted.
    """
    from quest_app.actions import _next_steps_for_submission

    report = ProblemReport()
    world = load_world(config, report)
    assert world is not None, report.to_text()
    planted_path = "participant/context/notes $(touch /tmp/pwn).md"
    quest = dataclasses.replace(
        world.content.quests[JIRA],
        proof=(
            ProofRequirement(
                id="ac-planted",
                type="file",
                description="planted for this test",
                path=planted_path,
            ),
        ),
    )
    attempt = world.participant.progress.attempt_for(JIRA)

    add_line = _git_add_line(_next_steps_for_submission(quest, attempt))

    assert add_line == (
        f"git add participant/evidence/{JIRA}/{attempt.attempt_id} participant/progress.yaml "
        f"{shlex.quote(planted_path)}"
    ), add_line
    assert add_line.count(planted_path) == 1, (
        "the path must appear exactly once, as a single shell-quoted token, not also bare"
    )


def test_the_text_cli_prints_the_next_steps(tmp_path: Path) -> None:
    """The bug: `result.get("next")` where the key is `next_steps`, so nothing printed."""
    participant = tmp_path / "participant"
    base = REPO_ROOT / "fixtures" / "participant"
    import shutil

    shutil.copytree(base, participant)

    env = {
        **__import__("os").environ,
        "GTQ_GENERATED_ROOT": str(tmp_path / "generated"),
        "GTQ_LOCAL_DATA_ROOT": str(tmp_path / "local-data"),
    }
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "quest_app.cli",
            "action",
            "submit-for-review",
            "--quest",
            JIRA,
            "--confirm",
            "--participant-root",
            str(participant),
        ],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "next steps:" in result.stdout, result.stdout
    assert "git add" in result.stdout
    assert "gh pr create" in result.stdout
    for path in JIRA_OUTSIDE:
        assert path in result.stdout
