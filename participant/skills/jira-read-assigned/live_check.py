"""Live evidence runs for the delta mode of sync.py, against a real sandbox Jira. Everything here only reads from Jira.

It copies sync.py into a throwaway folder outside the repository and runs it there, so ticket data
never enters the repository. Needs JIRA_BASE_URL, JIRA_EMAIL and JIRA_API_TOKEN in the shell.

  live_check.py first  <throwaway-folder>   the first delta run, with nothing synced before
  live_check.py second <throwaway-folder>   after you change tickets in Jira: a run with a fault injected
                                            partway, the recovery run, a quiet run, and the comparisons

Two things differ from a normal run, and only these two:
  - the page size is 2 instead of 100, so that a handful of stories spans more than one page;
  - in the fault run, the second search request is cut off before it reaches Jira, and stops the
    run the same way sync.py stops when Jira returns an error.
Each step also saves what it printed to <throwaway-folder>/records/.
"""
import contextlib
from datetime import datetime
import hashlib
import importlib.util
import io
import json
import re
import shutil
import sys
import urllib.parse
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SKILL_DIR / "tests"))
from test_delta import local_state  # noqa: E402

LINES = []
PROBLEMS = []
PREFIX = "Delta final story"  # how the test tickets' summaries start


def say(text: str = "") -> None:
    print(text)
    LINES.append(text)


def check(label: str, held: bool) -> None:
    say(f"  [{'ok' if held else 'NOT OK'}] {label}")
    if not held:
        PROBLEMS.append(label)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class Live:
    """sync.py loaded from a copy inside the throwaway folder, talking to real Jira."""

    def __init__(self, root: Path):
        self.root = root.resolve()
        skill = self.root / "participant" / "skills" / "jira-read-assigned"
        skill.mkdir(parents=True, exist_ok=True)
        shutil.copy(SKILL_DIR / "sync.py", skill / "sync.py")
        spec = importlib.util.spec_from_file_location(f"sync_live_{abs(hash(str(self.root)))}", skill / "sync.py")
        self.sync = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.sync)
        self.sync.PAGE_SIZE = 2
        self.real_get_json = self.sync.get_json
        self.jira = self.root / "participant" / "context" / "jira"
        self.stories_path = self.jira / "assigned" / "stories.json"
        self.state_path = self.jira / "sync-state.md"
        self.notes = self.jira / "assigned" / "notes"

    def run(self, *args, cut_search_number=None):
        searches = {"count": 0, "sent": 0}
        self.sent_queries = []  # (jql, fields) of every search that really went to Jira in this run

        def get_json(settings, path):
            if self.sync.SEARCH_PATH in path:
                searches["count"] += 1
                if cut_search_number == searches["count"]:
                    sys.exit("Jira returned HTTP 503. (fault injected by live_check.py; this request was never sent)")
                searches["sent"] += 1
                query = urllib.parse.parse_qs(urllib.parse.urlparse(path).query)
                self.sent_queries.append((query["jql"][0], query["fields"][0]))
            return self.real_get_json(settings, path)

        self.sync.get_json = get_json
        sys.argv = ["sync.py", *args]
        output = io.StringIO()
        try:
            with contextlib.redirect_stdout(output):
                self.sync.main()
            status = "ok"
        except SystemExit as error:
            status = f"stopped: {error}"
        return status, output.getvalue(), searches["sent"]

    def show(self, title: str, status: str, output: str, sent: int) -> None:
        say(f"\n--- {title} ---")
        say(f"search requests that reached Jira: {sent}")
        say(f"result: {status}")
        for line in output.replace(str(self.root), "<throwaway>").rstrip().splitlines():
            say(f"  | {line}")
        say(f"state file now: {self.cursor_line()}")

    def cursor_line(self) -> str:
        if not self.state_path.exists():
            return "(no sync-state.md yet)"
        return next(line for line in self.state_path.read_text(encoding="utf-8").splitlines() if line.startswith("- cursor: "))

    def cursor_ms(self) -> int:
        """The saved cursor as milliseconds, worked out here and not by the code under test."""
        return own_ms(self.cursor_line()[len("- cursor: "):])

    def full_story_filters(self) -> list:
        """The `updated >=` numbers on every full-field story search sent in the last run (None where there was no filter)."""
        found = []
        for jql, fields in self.sent_queries:
            if "issuetype = Story" in jql and fields != "key,updated":
                match = re.search(r"updated >= (\d+)", jql)
                found.append(int(match.group(1)) if match else None)
        return found

    def data(self) -> dict:
        return json.loads(self.stories_path.read_text(encoding="utf-8"))

    def table(self) -> None:
        data = self.data()
        say("stories held locally (test tickets, synthetic text):")
        for story in sorted(data["stories"], key=lambda s: s["key"]):
            say(f"  {story['key']:<9} {story['status']:<12} updated {story['updated']}  {story['summary']}")
        say(f"removed: {json.dumps(data['removed'])}")

    def note_hashes(self) -> dict:
        return {str(p.relative_to(self.notes)): sha(p.read_bytes()) for p in sorted(self.notes.rglob("*")) if p.is_file()}


def own_ms(jira_timestamp: str) -> int:
    return int(datetime.strptime(jira_timestamp, "%Y-%m-%dT%H:%M:%S.%f%z").timestamp() * 1000)


def counts(output: str) -> dict:
    found = {}
    for line in output.splitlines():
        name, _, value = line.partition(": ")
        if name in ("fetched", "new", "changed", "unchanged", "removed") and value.isdigit():
            found[name] = int(value)
    return found


def first(root: Path) -> None:
    if root.exists():
        sys.exit(f"{root} already exists. Give a folder that does not exist yet, so the first run starts with nothing.")
    live = Live(root)
    (live.notes / "analysis").mkdir(parents=True)
    (live.notes / "my-analysis.md").write_text("My analysis of story two.\nIt has trailing spaces   \n", encoding="utf-8")
    (live.notes / "analysis" / "risk-table.md").write_text("| risk | owner |\n|---|---|\n| late data | me |\n", encoding="utf-8")
    (live.notes / "scratch.bin").write_bytes(bytes(range(256)))
    (root / "notes-before.json").write_text(json.dumps(live.note_hashes(), indent=2), encoding="utf-8")
    say("local analysis files before any sync (sha256):")
    for name, digest in live.note_hashes().items():
        say(f"  {digest}  notes/{name}")

    status, output, sent = live.run("--delta")
    live.show("live run 1: first delta run, nothing synced before", status, output, sent)
    if status != "ok":
        sys.exit("The first run did not succeed, so there is nothing to check yet.")
    live.table()
    stories = live.data()["stories"]
    times = sorted(own_ms(s["updated"]) for s in stories)
    say("\nchecks on live run 1:")
    check("5 stories came back, and all 5 are counted as new", counts(output) == {"fetched": 5, "new": 5, "changed": 0, "unchanged": 0, "removed": 0})
    newest = max(stories, key=lambda s: own_ms(s["updated"]))["updated"] if stories else None
    check("C2: the cursor is the newest `updated` timestamp Jira sent", live.cursor_line() == f"- cursor: {newest}")
    gap_ok = len(times) >= 2 and times[-1] - times[-2] > 5 * 60 * 1000
    check("the newest story is more than 5 minutes newer than the rest (needed to predict the next run's fetch count)", gap_ok)
    check("C6: analysis files have the same sha256 as before", live.note_hashes() == json.loads((root / "notes-before.json").read_text()))


def second(root: Path) -> None:
    if not (root / "notes-before.json").exists():
        sys.exit("Run the `first` step on this folder before the `second` step.")
    live = Live(root)
    notes_before = json.loads((root / "notes-before.json").read_text())
    state_before, stories_before = live.state_path.read_bytes(), live.stories_path.read_bytes()
    say("Changes made in Jira since live run 1: story one reworded, story two moved to In Progress,")
    say("story six created, story four unassigned. Stories three and five were not touched.")
    say(f"\nbefore the fault run: sync-state.md sha256 {sha(state_before)}")
    say(f"                      stories.json  sha256 {sha(stories_before)}")

    cursor_before = live.cursor_ms()
    expected_filter = cursor_before - 5 * 60 * 1000
    status, output, sent = live.run("--delta", cut_search_number=2)
    live.show("live run 2: fault injected after one real page of changes came back", status, output, sent)
    say(f"\nafter the fault run:  sync-state.md sha256 {sha(live.state_path.read_bytes())}")
    say(f"                      stories.json  sha256 {sha(live.stories_path.read_bytes())}")
    say("\nchecks on live run 2:")
    check("exactly one search request reached Jira before the fault", sent == 1)
    check("the run stopped with an error", status.startswith("stopped"))
    check("C2, C3: sync-state.md is byte-identical, so the cursor did not move", live.state_path.read_bytes() == state_before)
    check("C3: stories.json is byte-identical", live.stories_path.read_bytes() == stories_before)
    check("C6: analysis files have the same sha256 as before", live.note_hashes() == notes_before)

    status, output, sent = live.run("--delta")
    live.show("live run 3: the next run, no fault", status, output, sent)
    live.table()
    held = {s["summary"]: s for s in live.data()["stories"]}
    say("\nchecks on live run 3:")
    say(f"filter on each full-field story search sent to Jira: {live.full_story_filters()}  (cursor minus 5 minutes is {expected_filter})")
    check("C1: every full-field story search sent to Jira carried `updated >=` the cursor minus 5 minutes",
          bool(live.full_story_filters()) and set(live.full_story_filters()) == {expected_filter})
    check("C1: 4 stories fetched (one, two, six, and five inside the 5 minute overlap), not all of them", counts(output).get("fetched") == 4)
    check("C5: counts are new 1, changed 2, unchanged 2, removed 1",
          {k: counts(output).get(k) for k in ("new", "changed", "unchanged", "removed")} == {"new": 1, "changed": 2, "unchanged": 2, "removed": 1})
    check("C4: the reworded story one is held", f"{PREFIX} one, reworded" in held)
    check("C4: story two is In Progress", held.get(f"{PREFIX} two", {}).get("status") == "In Progress")
    check("C4: story six is held", f"{PREFIX} six" in held)
    check("story four is no longer held and is listed as removed", f"{PREFIX} four" not in held and len(live.data()["removed"]) == 1)
    check("C2: the cursor value moved forward only now", live.cursor_ms() > cursor_before)
    check("C6: analysis files have the same sha256 as before", live.note_hashes() == notes_before)

    cursor_after_run_3 = live.cursor_ms()
    status, output, sent = live.run("--delta")
    live.show("live run 4: nothing changed in Jira since run 3", status, output, sent)
    say("\nchecks on live run 4:")
    check("C5: counts are new 0, changed 0, unchanged 5, removed 0",
          {k: counts(output).get(k) for k in ("new", "changed", "unchanged", "removed")} == {"new": 0, "changed": 0, "unchanged": 5, "removed": 0})
    check("the cursor value did not move, because nothing newer arrived", live.cursor_ms() == cursor_after_run_3)
    check("C6: analysis files have the same sha256 as before", live.note_hashes() == notes_before)

    canonical = lambda value: sha(json.dumps(value, sort_keys=True).encode("utf-8"))  # noqa: E731
    from_deltas = local_state(live.data())
    state_after_deltas = live.state_path.read_bytes()
    say("\n--- full resync compared with the accumulated deltas (live) ---")
    say("compared: every stored field of every story, and the removed list. `retrieved_at` is left out,")
    say("because it records when a story was fetched, and a full resync fetches everything again.")
    say(f"state built by the delta runs:           sha256 {canonical(from_deltas)}")
    status, _, _ = live.run()
    after_full = local_state(live.data())
    say(f"same folder after a full resync ({status}):  sha256 {canonical(after_full)}")
    check("C7: a full resync over the delta-built state changed nothing", status == "ok" and after_full == from_deltas)
    scratch_root = root.with_name(root.name + "-scratch")
    shutil.rmtree(scratch_root, ignore_errors=True)
    scratch = Live(scratch_root)
    status, _, _ = scratch.run()
    from_scratch = local_state(scratch.data())
    say(f"stories from the delta runs:                   sha256 {canonical(from_deltas['stories'])}")
    say(f"stories from a full sync into an empty folder: sha256 {canonical(from_scratch['stories'])}")
    check("C7: a full sync into an empty folder holds the same stories", status == "ok" and from_scratch["stories"] == from_deltas["stories"])
    say("\n--- live run 5, in a copy of the folder: an older stories.json and a cursor set to the year 2099 ---")
    say("The copy gets the stories.json from before live run 2, and its cursor is edited to 2099, so the")
    say("`updated >=` filter can return nothing. The run has to notice stale and missing stories from the list alone.")
    damaged_root = root.with_name(root.name + "-damaged")
    shutil.rmtree(damaged_root, ignore_errors=True)
    shutil.copytree(root, damaged_root)
    damaged = Live(damaged_root)
    damaged.stories_path.write_bytes(stories_before)
    damaged.state_path.write_text(re.sub(r"^- cursor: .*$", "- cursor: 2099-01-01T00:00:00.000+0000",
                                         damaged.state_path.read_text(encoding="utf-8"), flags=re.MULTILINE), encoding="utf-8")
    status, output, sent = damaged.run("--delta")
    damaged.show("live run 5", status, output, sent)
    by_key_queries = [jql for jql, _ in damaged.sent_queries if "key in (" in jql]
    say(f"searches by key sent to Jira: {len(by_key_queries)}")
    say("\nchecks on live run 5:")
    check("3 stories were fetched, and the 3 named in the by-key warning are stories one, two and six",
          status == "ok" and counts(output).get("fetched") == 3 and len(by_key_queries) >= 1
          and all(held_key in output for held_key in (held[f"{PREFIX} one, reworded"]["key"], held[f"{PREFIX} two"]["key"], held[f"{PREFIX} six"]["key"])))
    check("counts are new 1, changed 2, unchanged 2, removed 1",
          {k: counts(output).get(k) for k in ("new", "changed", "unchanged", "removed")} == {"new": 1, "changed": 2, "unchanged": 2, "removed": 1})
    check("the damaged copy ended in the same local state as the healthy delta runs", status == "ok" and local_state(damaged.data()) == from_deltas)
    check("C6: the damaged copy's analysis files have the same sha256 as before the first sync", damaged.note_hashes() == notes_before)
    say("  (the copy's cursor stays at 2099, because the cursor never moves backward; a full sync does not reset it either)")

    say("\nlocal analysis files in the main throwaway folder after live runs 1 to 4 and the full resync (sha256):")
    for name, digest in live.note_hashes().items():
        say(f"  {digest}  notes/{name}")
    check("C6: analysis files have the same sha256 as before the first sync", live.note_hashes() == notes_before)
    check("the full resync left sync-state.md alone", live.state_path.read_bytes() == state_after_deltas)


def main() -> None:
    steps = {"first": first, "second": second}
    if len(sys.argv) != 3 or sys.argv[1] not in steps:
        sys.exit("Usage: live_check.py first|second <throwaway-folder>")
    step, root = sys.argv[1], Path(sys.argv[2])
    say(f"live_check.py {step}: real sandbox Jira, read-only, page size 2, throwaway folder outside the repository")
    say(f"sync.py copied into the throwaway folder for this step: sha256 {sha((SKILL_DIR / 'sync.py').read_bytes())}")
    try:
        steps[step](root)
        say(f"\nRESULT: {'every check held' if not PROBLEMS else str(len(PROBLEMS)) + ' check(s) did NOT hold'}")
    finally:
        if root.exists():
            (root / "records").mkdir(exist_ok=True)
            (root / "records" / f"{step}.txt").write_text("\n".join(LINES) + "\n", encoding="utf-8")
    sys.exit(1 if PROBLEMS else 0)


if __name__ == "__main__":
    main()
