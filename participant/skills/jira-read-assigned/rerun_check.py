"""Safe-rerun check for the Jira read-assigned sync.

Part A runs the sync twice for each fixture and checks that the second run changes nothing
except timestamps, that no comment is stored twice, and that participant notes are untouched.
Part B runs the real merge and write code twice in a temporary folder, with Jira's answer
changing between runs, to show the merge rules at work.

Run from the repository root:
  python3 participant/skills/jira-read-assigned/rerun_check.py
Part A overwrites participant/context/jira/assigned/stories.json and index.md with fixture
output, then restores the happy-path output. It reads the notes folder and never writes to it.
Exit codes: 0 all checks pass, 1 a check failed, 2 no notes file existed to check.
"""
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SYNC = HERE / "sync.py"
OUT = HERE.parents[1] / "context" / "jira" / "assigned"
FIXTURES = ("happy-path", "pagination", "stale-item", "duplicate-comment")
TIMESTAMP_KEYS = {"synced_at", "retrieved_at"}


def run_sync(fixture: str) -> dict:
    subprocess.run([sys.executable, str(SYNC), "--source", fixture], check=True, capture_output=True, text=True)
    return json.loads((OUT / "stories.json").read_text(encoding="utf-8"))


def without_timestamps(value):
    if isinstance(value, dict):
        return {key: without_timestamps(item) for key, item in value.items() if key not in TIMESTAMP_KEYS}
    if isinstance(value, list):
        return [without_timestamps(item) for item in value]
    return value


def notes_hashes() -> dict:
    notes = OUT / "notes"
    if not notes.is_dir():
        return {}
    return {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(notes.glob("*.md"))}


def duplicate_comment_ids(data: dict) -> list:
    found = []
    for story in data["stories"]:
        ids = [comment["id"] for comment in story.get("comments", [])]
        found += [f"{story['key']}:{comment_id}" for comment_id in sorted(set(ids)) if ids.count(comment_id) > 1]
    return found


def part_a() -> tuple:
    """Return (failures, notes_checked)."""
    print("Part A: each fixture, run twice, in the workspace")
    notes_before = notes_hashes()
    print(f"  notes files checked: {', '.join(notes_before) or 'none found'}")
    failures = 0
    for fixture in FIXTURES:
        first = run_sync(fixture)
        second = run_sync(fixture)
        same = without_timestamps(first) == without_timestamps(second)
        duplicates = duplicate_comment_ids(second)
        passed = same and not duplicates
        failures += not passed
        print(
            f"  {fixture}: {'PASS' if passed else 'FAIL'} | stories {len(second['stories'])} "
            f"| removed {[entry['key'] for entry in second['removed']]} "
            f"| unchanged apart from timestamps: {same} | duplicate comments: {duplicates or 'none'}"
        )
    run_sync("happy-path")
    print("  stories.json restored to the happy-path output")
    if not notes_before:
        print("  notes unchanged: NOT EXERCISED (no notes files existed)")
        return failures, False
    notes_same = notes_hashes() == notes_before
    failures += not notes_same
    print(f"  notes unchanged: {'PASS' if notes_same else 'FAIL'}")
    return failures, True


def part_b() -> int:
    """Run the real merge and write code twice in a temporary folder. Return the number of failures."""
    print("Part B: two runs with a changed answer from Jira, in a temporary folder")
    spec = importlib.util.spec_from_file_location("sync", SYNC)
    sync = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sync)

    def story(key: str, comment_ids: list) -> dict:
        return {"key": key, "status": "To Do", "summary": f"Story {key}", "comments": [{"id": i} for i in comment_ids]}

    with tempfile.TemporaryDirectory() as temp:
        sync.OUT_DIR = Path(temp)
        sync.NOTES_DIR = Path(temp) / "notes"
        sync.NOTES_DIR.mkdir()
        note = sync.NOTES_DIR / "GTQ-1.md"
        note.write_text("Participant note.\n", encoding="utf-8")

        # Run 1: Jira returns GTQ-1 with comment 7, and GTQ-2.
        first = [sync.record_from_fixture(story("GTQ-1", ["7"]), "run-1", []),
                 sync.record_from_fixture(story("GTQ-2", []), "run-1", [])]
        stories, removed = sync.merge(first, {}, [])
        sync.write_outputs(stories, removed, [], "demo", "run-1")

        # Run 2: GTQ-2 is gone, and GTQ-1 now has comments 7 and 8.
        previous = sync.load_existing()
        second = [sync.record_from_fixture(story("GTQ-1", ["7", "8"]), "run-2", [])]
        stories, removed = sync.merge(second, {s["key"]: s for s in previous["stories"]}, previous["removed"])
        sync.write_outputs(stories, removed, [], "demo", "run-2")

        result = sync.load_existing()
        index = (sync.OUT_DIR / "index.md").read_text(encoding="utf-8")
        checks = {
            "comment 7 stored once, comment 8 added once": [c["id"] for c in result["stories"][0]["comments"]] == ["7", "8"],
            "GTQ-2 reported under removed, not deleted": result["removed"] == [{"key": "GTQ-2", "last_known_status": "To Do"}],
            "participant note unchanged": note.read_text(encoding="utf-8") == "Participant note.\n",
            "index links the note": "[notes](notes/GTQ-1.md)" in index,
        }
    for name, passed in checks.items():
        print(f"  {name}: {'PASS' if passed else 'FAIL'}")
    return sum(not passed for passed in checks.values())


def main() -> int:
    failures_a, notes_checked = part_a()
    failures_b = part_b()
    if failures_a or failures_b:
        print("Result: FAIL")
        return 1
    if not notes_checked:
        print("Result: INCOMPLETE. Add a notes file under participant/context/jira/assigned/notes/ and run again.")
        return 2
    print("Result: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
