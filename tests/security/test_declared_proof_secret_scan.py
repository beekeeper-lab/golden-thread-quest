"""Round 13 C1 and C2.

C1: the secret scan covered only the attempt's evidence package. A quest's declared proof
commonly names files outside it (`participant/context/**`, `participant/skills/**`), and a
token planted there passed every gate and every page said the evidence was clean.
`scan_declared_proof` (`quest_app/evidence.py`) is what every gate and page must call
instead of `scan_evidence` alone, and this file proves each one actually does.

C2: `mark-evidence-ready`'s gate (`actions.py` `_require_clean_secret_scan`) used to call a
link out of the package or an oversized file "secret-like". It now shares
`describe_scan_findings` with the submission gate (`readiness_problems`), so both word a
finding the same way.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from quest_app.actions import ActionRunner
from quest_app.build import build_site
from quest_app.config import AppConfig
from quest_app.content_loader import SchemaSet
from quest_app.errors import ProblemReport
from quest_app.evidence import MAX_EVIDENCE_FILE_BYTES, scan_declared_proof, scan_evidence
from quest_app.pipeline import load_world
from quest_app.review import blocking, readiness_problems
from quest_app.store import StoreError

QUEST = "jira-read-assigned-stories"
LEAKED = "ghp_abcdefghijklmnopqrstuvwxyz0123456789"  # secret-scan: allow


def _world(config: AppConfig):  # type: ignore[no-untyped-def]
    report = ProblemReport()
    world = load_world(config, report)
    assert world is not None, report.to_text()
    return world


def _runner(config: AppConfig) -> ActionRunner:
    def load():  # type: ignore[no-untyped-def]
        return _world(config)

    return ActionRunner(config, SchemaSet(config.schemas_root), load)


def _plant_outside_package_secret(config: AppConfig) -> Path:
    """A secret in a file the quest declares as proof, outside its evidence package.

    `participant/skills/jira-read-assigned/SKILL.md` is one of this quest's own required
    proof paths (see `content/quests/jira-jungle/read-assigned-stories.md`), and it is not
    under the attempt's evidence directory.
    """
    target = config.resolve_participant_path("participant/skills/jira-read-assigned/SKILL.md")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"# Jira sync skill\n\ntoken={LEAKED}\n")
    return target


class TestScanDeclaredProofCoversFilesOutsideThePackage:
    def test_scan_declared_proof_finds_it_where_scan_evidence_alone_would_not(
        self, config: AppConfig
    ) -> None:
        world = _world(config)
        quest = world.content.quests[QUEST]
        attempt = world.participant.progress.attempt_for(QUEST)
        _plant_outside_package_secret(config)

        assert scan_evidence(config, attempt.evidence_path) == []
        findings = scan_declared_proof(config, quest, attempt.evidence_path)
        assert any(f.path.endswith("SKILL.md") for f in findings), findings

    def test_the_submission_gate_refuses_it(self, config: AppConfig) -> None:
        world = _world(config)
        quest = world.content.quests[QUEST]
        attempt = world.participant.progress.attempt_for(QUEST)
        _plant_outside_package_secret(config)

        problems = blocking(readiness_problems(quest, attempt, world.participant, config))
        assert any("secret-like" in problem for problem in problems), problems

    def test_the_mark_evidence_ready_gate_refuses_it(self, config: AppConfig) -> None:
        runner = _runner(config)
        _plant_outside_package_secret(config)
        runner.perform("reopen-evidence", {"quest_id": QUEST})
        with pytest.raises(StoreError, match="secret-like"):
            runner.perform("mark-evidence-ready", {"quest_id": QUEST})

    @pytest.mark.slow
    def test_the_evidence_page_reports_it(self, config: AppConfig) -> None:
        _plant_outside_package_secret(config)
        build_site(_world(config))
        page = (config.generated_root / "evidence" / QUEST / "index.html").read_text()
        assert "found nothing secret-like" not in page, page
        assert "Possible secret in your evidence" in page, page

    @pytest.mark.slow
    def test_the_review_page_reports_it(self, config: AppConfig) -> None:
        _plant_outside_package_secret(config)
        build_site(_world(config))
        page = (config.generated_root / "review" / QUEST / "index.html").read_text()
        assert "The scan found something secret-like" in page, page


class TestMarkEvidenceReadyDescribesEachKindOfFinding:
    """C2: a secret, a link and an oversized file must each be worded for what they are."""

    def _reopen_and_mark_ready(self, config: AppConfig) -> str:
        runner = _runner(config)
        runner.perform("reopen-evidence", {"quest_id": QUEST})
        with pytest.raises(StoreError) as excinfo:
            runner.perform("mark-evidence-ready", {"quest_id": QUEST})
        return str(excinfo.value)

    def test_a_secret_is_worded_as_secret(self, config: AppConfig) -> None:
        attempt = _world(config).participant.progress.attempt_for(QUEST)
        package = config.resolve_participant_path(attempt.evidence_path)
        (package / "notes.md").write_text(f"token={LEAKED}\n")

        message = self._reopen_and_mark_ready(config)
        assert "secret-like" in message, message
        assert "link" not in message, message

    def test_a_link_out_of_the_package_is_worded_as_a_link_not_a_secret(
        self, config: AppConfig, tmp_path: Path
    ) -> None:
        attempt = _world(config).participant.progress.attempt_for(QUEST)
        package = config.resolve_participant_path(attempt.evidence_path)
        outside = tmp_path / "outside.txt"
        outside.write_text("nothing secret, but the scan may not read it\n")
        (package / "escape.txt").symlink_to(outside)

        message = self._reopen_and_mark_ready(config)
        assert "is a link that leads outside the evidence package" in message, message
        assert "secret-like" not in message, message

    def test_an_oversized_file_is_worded_as_too_large_not_a_secret(self, config: AppConfig) -> None:
        attempt = _world(config).participant.progress.attempt_for(QUEST)
        package = config.resolve_participant_path(attempt.evidence_path)
        (package / "huge.log").write_bytes(b"x" * (MAX_EVIDENCE_FILE_BYTES + 1))

        message = self._reopen_and_mark_ready(config)
        assert "secret-like" not in message, message
        assert "cannot be checked" in message or "MB" in message, message
