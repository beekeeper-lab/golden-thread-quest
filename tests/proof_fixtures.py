"""Put a quest's required proof in place, the way a participant has to before submitting.

Since Phase 2A a submission is refused while a required file, folder or command record is
missing (`review.missing_required_proof`). Most tests that submit are about something after
that point, so they call this first. It writes only what is absent, and never overwrites a
file a test wrote on purpose.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from quest_app.evidence import proof_location

REPO_ROOT = Path(__file__).resolve().parents[1]
_FILE_PROOF_TYPES = frozenset({"file", "directory", "command-record"})


def _front_matter(quest_id: str, content_root: Path) -> dict[str, object]:
    for path in sorted((content_root / "quests").glob("*/*.md")):
        text = path.read_text(encoding="utf-8")
        data = yaml.safe_load(text.split("---", 2)[1]) or {}
        if data.get("id") == quest_id:
            return data
    raise LookupError(f"no quest {quest_id!r} under {content_root}")


def _evidence_path(participant_root: Path, quest_id: str) -> str | None:
    progress = participant_root / "progress.yaml"
    if not progress.exists():
        return None
    data = yaml.safe_load(progress.read_text(encoding="utf-8")) or {}
    for attempt in reversed(data.get("attempts", [])):
        if attempt.get("quest_id") == quest_id:
            return str(attempt.get("evidence_path"))
    return None


def place_required_proof(
    participant_root: Path, quest_id: str, content_root: Path = REPO_ROOT / "content"
) -> None:
    """Write every required file-like proof item of `quest_id` that is not there yet."""
    evidence_path = _evidence_path(participant_root, quest_id)
    proof = _front_matter(quest_id, content_root).get("proof") or {}
    for item in proof.get("required", []):  # type: ignore[union-attr]
        if item.get("type") not in _FILE_PROOF_TYPES or not item.get("path"):
            continue
        location = proof_location(item["path"], evidence_path)
        target = participant_root / Path(location).relative_to("participant")
        if item["type"] == "directory":
            target.mkdir(parents=True, exist_ok=True)
            if not any(target.iterdir()):
                (target / "README.md").write_text("Placed by the test suite.\n")
        elif not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("Placed by the test suite.\n")
