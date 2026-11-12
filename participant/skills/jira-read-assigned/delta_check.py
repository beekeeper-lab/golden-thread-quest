"""Evidence runs for the delta mode of sync.py, against the fake Jira and its synthetic tickets.

Each run copies sync.py into a temporary folder and never touches your workspace or the network.
  python3 participant/skills/jira-read-assigned/delta_check.py delta
  python3 participant/skills/jira-read-assigned/delta_check.py failed
  python3 participant/skills/jira-read-assigned/delta_check.py intact
Exit code 0 means every check in that run held. Any other exit code means one did not.
"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "tests"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fake_jira import to_ms  # noqa: E402
from test_delta import Sandbox, counts, local_state  # noqa: E402

PROBLEMS = []


def check(label: str, held: bool) -> None:
    print(f"  [{'ok' if held else 'NOT OK'}] {label}")
    if not held:
        PROBLEMS.append(label)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def cursor_line(box) -> str:
    if not box.state_path.exists():
        return "(no sync-state.md yet)"
    return next(line for line in box.state_path.read_text(encoding="utf-8").splitlines() if line.startswith("- cursor: "))


def show_run(box, title: str, status: str, output: str) -> None:
    print(f"\n--- {title} ---")
    print(f"what the fake Jira holds: {box.jira._snapshot()['what_happened']}")
    print("story searches sent to Jira:")
    for jql, fields in box.story_queries():
        print(f"  jql: {jql}")
        print(f"       fields: {'key and updated time only' if fields == 'key' else 'full story fields'}")
    print(f"result: {status}")
    for line in output.replace(str(box.root.resolve()), "<sandbox>").replace(str(box.root), "<sandbox>").rstrip().splitlines():
        print(f"  | {line}")
    print(f"state file now: {cursor_line(box)}")


def delta_run() -> None:
    box = Sandbox()
    box.write_notes()
    status, output = box.delta("moment-0")
    show_run(box, "run 1: first delta run, no cursor saved yet", status, output)
    status, output = box.delta("moment-1")
    show_run(box, "run 2: delta run after changes in Jira", status, output)
    print("\nchecks on run 2:")
    full = [jql for jql, fields in box.story_queries() if fields != "key,updated"]
    check(f"C1: every search for full story fields carried the same `updated >=` filter ({len(full)} pages of it)",
          bool(full) and len(set(full)) == 1 and "updated >=" in full[0])
    check("C1: every other story search asked for the key and updated time only", all("updated >=" in j or f == "key,updated" for j, f in box.story_queries()))
    expected_ms = to_ms("2026-11-02T09:00:00.000+0000") - 5 * 60 * 1000
    check(f"C1: the filter was `updated >= {expected_ms}`, which is 09:00:00 UTC (the cursor) minus 5 minutes",
          bool(full) and f"updated >= {expected_ms}" in full[0])
    check("C1, C5: counts are exactly fetched 3, new 1, changed 2, unchanged 2, removed 1 (GTQ-202, GTQ-204, GTQ-206 fetched, not all 5)",
          counts(output) == {"fetched": 3, "new": 1, "changed": 2, "unchanged": 2, "removed": 1})
    status, output = box.delta("moment-2")
    show_run(box, "run 3: an edit that Jira showed late", status, output)
    print("\nchecks on run 3:")
    summary = {s["key"]: s["summary"] for s in box.data()["stories"]}["GTQ-203"]
    check("GTQ-203's edit at 14:02:30 was picked up although the cursor was already 14:05:00", summary.endswith("reworded"))
    status, output = box.delta("moment-3")
    show_run(box, "run 4: nothing changed in Jira", status, output)
    print("\nchecks on run 4:")
    check("C5: counts are exactly fetched 2, new 0, changed 0, unchanged 5, removed 0",
          counts(output) == {"fetched": 2, "new": 0, "changed": 0, "unchanged": 5, "removed": 0})


def failed_run() -> None:
    box = Sandbox()
    box.write_notes()
    status, output = box.delta("moment-0")
    show_run(box, "run 1: first delta run succeeds", status, output)
    state_before, stories_before = box.state_path.read_bytes(), box.stories_path.read_bytes()
    print(f"\nbefore the failing run: sync-state.md sha256 {sha(state_before)}")
    print(f"                        stories.json  sha256 {sha(stories_before)}")

    status, output = box.delta("moment-1", fail_on_search=2)
    show_run(box, "run 2: Jira fails on the second page of changes", status, output)
    print(f"\nafter the failing run:  sync-state.md sha256 {sha(box.state_path.read_bytes())}")
    print(f"                        stories.json  sha256 {sha(box.stories_path.read_bytes())}")
    print("\nchecks on run 2:")
    check("the run stopped with an error", status.startswith("stopped"))
    check("C2, C3: sync-state.md is byte-identical, so the cursor did not move", box.state_path.read_bytes() == state_before)
    check("C3: stories.json is byte-identical, so no half-finished result was saved", box.stories_path.read_bytes() == stories_before)

    status, output = box.delta("moment-1")
    show_run(box, "run 3: the next run, with Jira working again", status, output)
    twin = Sandbox()
    twin.delta("moment-0")
    twin.delta("moment-1")
    held = {s["key"]: s["status"] for s in box.data()["stories"]}
    print(f"\nstories held after run 3: {json.dumps(held, sort_keys=True)}")
    print(f"removed after run 3: {json.dumps(box.data()['removed'])}")
    print("\nchecks on run 3:")
    check("C4: GTQ-202, GTQ-204 and GTQ-206, which the failed run missed, are now held", {"GTQ-202", "GTQ-204", "GTQ-206"} <= set(held))
    check("C4: the result equals a second sandbox that never had a failure", local_state(box.data()) == local_state(twin.data()))
    check("C2: the cursor advanced only now", cursor_line(box) == cursor_line(twin) and box.state_path.read_bytes() != state_before)


def file_hashes(box) -> dict:
    return {str(p.relative_to(box.notes)): sha(p.read_bytes()) for p in sorted(box.notes.rglob("*")) if p.is_file()}


def intact_run() -> None:
    box = Sandbox()
    box.write_notes()
    before = file_hashes(box)
    print("local analysis files before any sync (sha256):")
    for name, digest in before.items():
        print(f"  {digest}  notes/{name}")
    steps = [
        ("first delta run", lambda: box.delta("moment-0")),
        ("delta run that fails partway", lambda: box.delta("moment-1", fail_on_search=2)),
        ("delta run that recovers", lambda: box.delta("moment-1")),
        ("delta run with a late edit", lambda: box.delta("moment-2")),
        ("delta run with no changes", lambda: box.delta("moment-3")),
    ]
    for title, step in steps:
        status, _ = step()
        after = file_hashes(box)
        print(f"\nafter: {title} ({status.split(':')[0]})")
        for name, digest in after.items():
            print(f"  {digest}  notes/{name}")
        check(f"C6: same files, same sha256 after the {title}", after == before)

    from_deltas = local_state(box.data())
    canonical = lambda value: sha(json.dumps(value, sort_keys=True).encode("utf-8"))  # noqa: E731
    print("\n--- full resync compared with the accumulated deltas ---")
    print("compared: every stored field of every story, and the removed list. `retrieved_at` is left out,")
    print("because it records when a story was fetched, and a full resync fetches everything again.")
    print(f"state built by 4 delta runs:           sha256 {canonical(from_deltas)}")
    status, _ = box.run(moment="moment-3")
    after_full = local_state(box.data())
    print(f"same folder after a full resync ({status}):  sha256 {canonical(after_full)}")
    check("C7: a full resync over the delta-built state changed nothing", after_full == from_deltas)
    check("C6: same files, same sha256 after the full resync", file_hashes(box) == before)
    scratch = Sandbox()
    scratch.run(moment="moment-3")
    from_scratch = local_state(scratch.data())
    print(f"\nstories from the delta runs:            sha256 {canonical(from_deltas['stories'])}")
    print(f"stories from a full sync into an empty folder: sha256 {canonical(from_scratch['stories'])}")
    check("C7: a full sync into an empty folder holds the same stories", from_scratch["stories"] == from_deltas["stories"])
    print(f"removed list from the delta runs: {json.dumps(from_deltas['removed'])}")
    print(f"removed list from the empty-folder full sync: {json.dumps(from_scratch['removed'])}")
    print("  (expected to differ: a sync into an empty folder cannot know GTQ-205 was ever held)")


def main() -> None:
    runs = {"delta": delta_run, "failed": failed_run, "intact": intact_run}
    if len(sys.argv) != 2 or sys.argv[1] not in runs:
        sys.exit("Usage: delta_check.py delta|failed|intact")
    print(f"delta_check.py {sys.argv[1]}: fake Jira, synthetic tickets from delta_fixture/timeline.json, temporary folder")
    runs[sys.argv[1]]()
    print(f"\nRESULT: {'every check held' if not PROBLEMS else str(len(PROBLEMS)) + ' check(s) did NOT hold'}")
    sys.exit(1 if PROBLEMS else 0)


if __name__ == "__main__":
    main()
