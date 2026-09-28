"""Round 15 L1.

The evidence page's Repository panel — branch, changed/untracked counts, "Evidence
committed" — is a build-time snapshot: nothing on the read path re-runs `git_status.inspect`
live, only the last `build_site` call did. It carried no disclaimer saying so, unlike the
Environment Health page (known limitation 4) and the review page's own change-detection
notice (round 14 C4), which both say plainly that they report what was true at build time.

Reproduced: commit a proof file, build (the page correctly says "Evidence committed: yes"),
then edit that already-committed file with no further application action. `git status` now
shows it modified, but the page — untouched since the earlier build — still read "yes" with
no caveat, which a reviewer relying on it would take as a live guarantee it never was.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from quest_app.build import build_site
from quest_app.config import AppConfig
from quest_app.errors import ProblemReport
from quest_app.pipeline import load_world
from quest_app.view_models import offline_service_view

QUEST = "base-camp-repository-safety"
BUILT_AT = "2026-09-20T00:00:00+00:00"


def _git(root: Path, *arguments: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=True,
        capture_output=True,
        env={
            "PATH": "/usr/bin:/bin",
            "GIT_AUTHOR_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "test@example.invalid",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@example.invalid",
        },
    )


def _evidence_page_html(config: AppConfig) -> str:
    report = ProblemReport()
    world = load_world(config, report)
    assert world is not None, report.to_text()
    build_site(world, built_at=BUILT_AT, service=offline_service_view())
    page = config.generated_root / "evidence" / QUEST / "index.html"
    return page.read_text(encoding="utf-8")


def test_the_panel_names_the_build_it_reflects_and_says_it_is_not_a_live_read(
    config: AppConfig,
) -> None:
    _git(config.repo_root, "init", "-q", "-b", "main")
    _git(config.repo_root, "add", "-A")
    _git(config.repo_root, "commit", "-q", "-m", "initial")

    html = _evidence_page_html(config)

    assert "Evidence committed" in html
    assert "yes, as of this build" in html
    assert BUILT_AT in html
    assert "not a live read" in html


def test_editing_a_committed_proof_file_after_the_build_does_not_make_the_page_lie(
    config: AppConfig,
) -> None:
    """Round 15 L1's actual repro. The already-built page cannot know about the edit — the
    fix is that its wording never claimed a live truth to begin with."""
    _git(config.repo_root, "init", "-q", "-b", "main")
    _git(config.repo_root, "add", "-A")
    _git(config.repo_root, "commit", "-q", "-m", "initial")

    html = _evidence_page_html(config)
    assert "yes, as of this build" in html

    proof = config.participant_root / "evidence" / QUEST / "base-camp-attempt-001" / "PROOF.md"
    proof.write_text(proof.read_text(encoding="utf-8") + "\nEdited after the build.\n")

    status = subprocess.run(
        ["git", "-C", str(config.repo_root), "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert status.strip(), "the edit must actually be uncommitted, or this test proves nothing"

    # Nothing rebuilt the site after the edit — the page on disk is untouched, exactly the
    # round 15 L1 scenario. It must still carry the qualifier, not a bare "yes".
    stale_html = (config.generated_root / "evidence" / QUEST / "index.html").read_text(
        encoding="utf-8"
    )
    assert stale_html == html
    assert "yes, as of this build" in stale_html


def test_an_untracked_or_uncommitted_state_carries_the_same_qualifier(config: AppConfig) -> None:
    _git(config.repo_root, "init", "-q", "-b", "main")
    # Nothing committed at all: the evidence package is untracked.
    html = _evidence_page_html(config)

    assert "not yet, as of this build" in html
    assert BUILT_AT in html
    assert "not a live read" in html
