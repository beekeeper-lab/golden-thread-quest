"""An evidence file that is a link out of its package is neither shown, trusted nor cleared.

The build resolved only the evidence directory, so a `PROOF.md` that was a symbolic link to
any file the build could read was rendered into the site. The secret scan skipped links, so
it cleared a file it never read, and the evidence hash covered the link text, so pointing a
link elsewhere changed the rendered proof without changing the hash. Render, hash and scan
now agree: an entry that leads outside the package, once links are followed, is refused by
all three and reported by the loader.
"""

from __future__ import annotations

from pathlib import Path

from quest_app.build import _proof_document
from quest_app.config import AppConfig
from quest_app.errors import ProblemReport
from quest_app.evidence import evidence_hash, scan_evidence
from quest_app.pipeline import load_world
from quest_app.review import blocking, readiness_problems

QUEST = "jira-read-assigned-stories"
MARKER = "PRIVATE-NOTE-7731"


def _package(config: AppConfig) -> tuple[str, Path]:
    report = ProblemReport()
    world = load_world(config, report)
    assert world is not None, report.to_text()
    attempt = world.participant.progress.attempt_for(QUEST)
    return attempt.evidence_path, config.resolve_participant_path(attempt.evidence_path)


def _link_proof_to(package: Path, target: Path) -> None:
    (package / "PROOF.md").unlink()
    (package / "PROOF.md").symlink_to(target)


def test_a_proof_linked_outside_the_participant_root_is_not_rendered(
    config: AppConfig, tmp_path: Path
) -> None:
    evidence_path, package = _package(config)
    outside = tmp_path / "outside-secret.txt"
    outside.write_text(f"{MARKER} lives outside the participant root\n")
    _link_proof_to(package, outside)

    world = load_world(config, ProblemReport())
    assert world is not None
    rendered = _proof_document(world, evidence_path)
    assert rendered is None or MARKER not in rendered


def test_a_proof_linked_elsewhere_in_participant_is_not_rendered(config: AppConfig) -> None:
    """Inside `participant/` is still outside the package the reviewer is shown."""
    evidence_path, package = _package(config)
    source = config.participant_root / "context" / "proof-src.md"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(f"# {MARKER}\n")
    _link_proof_to(package, source)

    world = load_world(config, ProblemReport())
    assert world is not None
    rendered = _proof_document(world, evidence_path)
    assert rendered is None or MARKER not in rendered


def test_a_link_inside_the_package_still_renders(config: AppConfig) -> None:
    evidence_path, package = _package(config)
    (package / "notes.md").write_text(f"# {MARKER}\n")
    _link_proof_to(package, package / "notes.md")

    world = load_world(config, ProblemReport())
    assert world is not None
    assert MARKER in (_proof_document(world, evidence_path) or "")


def test_the_secret_scan_reports_a_link_out_of_the_package(
    config: AppConfig, tmp_path: Path
) -> None:
    evidence_path, package = _package(config)
    outside = tmp_path / "outside.txt"
    outside.write_text("nothing secret, but the scan may not read it\n")
    _link_proof_to(package, outside)

    findings = scan_evidence(config, evidence_path)
    assert [f.path for f in findings] == [f"{evidence_path}/PROOF.md"]
    assert "outside the evidence package" in findings[0].description


def test_a_submission_through_a_link_out_of_the_package_is_refused(config: AppConfig) -> None:
    """The route by which a rendered proof could be rewritten after approval unseen."""
    _, package = _package(config)
    source = config.participant_root / "context" / "proof-src.md"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("# Proof as reviewed\n")
    _link_proof_to(package, source)

    world = load_world(config, ProblemReport())
    assert world is not None
    quest = world.content.quests[QUEST]
    attempt = world.participant.progress.attempt_for(QUEST)
    problems = blocking(readiness_problems(quest, attempt, world.participant, config))
    assert any("PROOF.md" in problem for problem in problems), problems


def test_the_loader_reports_a_link_out_of_the_package(config: AppConfig, tmp_path: Path) -> None:
    _, package = _package(config)
    outside = tmp_path / "outside.txt"
    outside.write_text("x\n")
    _link_proof_to(package, outside)

    report = ProblemReport()
    assert load_world(config, report) is not None
    codes = {p.code for p in report.warnings}
    assert "evidence.link_outside_package" in codes
    # Never the absolute target: the problem names the package entry.
    assert str(tmp_path) not in report.to_text()


def test_the_hash_follows_a_link_inside_the_package(config: AppConfig) -> None:
    """Hashed by what it shows, as the build renders it — not by its link text."""
    evidence_path, package = _package(config)
    (package / "validation").mkdir(exist_ok=True)
    # Kept in `validation/`, which the hash skips, so only the link can carry a change.
    target = package / "validation" / "shown.md"
    target.write_text("# before\n")
    _link_proof_to(package, target)
    before = evidence_hash(config, evidence_path)
    target.write_text("# after\n")
    assert evidence_hash(config, evidence_path) != before
