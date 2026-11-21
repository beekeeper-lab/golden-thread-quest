"""Stubbed tests for the delta mode of sync.py. No network, and no changes to your workspace.

Each test copies sync.py into a temporary folder, loads that copy, and replaces its Jira call
with fake_jira.FakeJira, which answers from delta_fixture/timeline.json.

Expected results come from the quest's seven acceptance criteria (C1 to C7) and from the
timeline's own description of what happened at each moment. They do not come from sync.py.

The contract these tests assume, taken from the quest and the agreed design:
  - `sync.py --delta` runs a delta sync. With no saved cursor it fetches everything once.
  - The cursor is saved in participant/context/jira/sync-state.md on a line `- cursor: <Jira timestamp>`.
  - A delta run asks Jira for `updated >= <milliseconds>`, where milliseconds is the cursor minus 5 minutes.
  - A delta run also lists every assigned story with two fields only, `key` and `updated`, to spot
    stories that left the list and local copies that are missing or out of date.
  - A delta run prints `fetched:`, `new:`, `changed:`, `unchanged:` and `removed:` counts for that run.

Run from the repository root:
  python3 participant/skills/jira-read-assigned/tests/test_delta.py
Exit code 0 means every test passed.
"""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import sys
import tempfile
import urllib.parse
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
SYNC = Path(os.environ.get("SYNC_UNDER_TEST", SKILL_DIR / "sync.py"))
sys.path.insert(0, str(SKILL_DIR))
from fake_jira import FakeJira, to_ms  # noqa: E402

MARGIN_MS = 5 * 60 * 1000
LIST_FIELDS = "key,updated"  # the cheap list of everything assigned
# Newest `updated` among the stories Jira shows at each moment, read off timeline.json by hand.
NEWEST_AT_MOMENT_0 = "2026-11-02T09:00:00.000+0000"   # GTQ-205
NEWEST_AT_MOMENT_1 = "2026-11-03T01:05:00.000+1100"   # GTQ-206, which is 14:05:00 UTC on 2 November
TESTS = []


def test(function):
    TESTS.append(function)
    return function


class Sandbox:
    def __init__(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        skill = self.root / "participant" / "skills" / "jira-read-assigned"
        skill.mkdir(parents=True)
        shutil.copy(SYNC, skill / "sync.py")
        spec = importlib.util.spec_from_file_location("sync_under_test", skill / "sync.py")
        self.sync = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.sync)
        self.jira = FakeJira()
        self.sync.get_json = self.jira.get_json
        self.out = self.root / "participant" / "context" / "jira" / "assigned"
        self.stories_path = self.out / "stories.json"
        self.state_path = self.root / "participant" / "context" / "jira" / "sync-state.md"
        self.notes = self.out / "notes"

    def write_notes(self):
        """Participant-owned files: a note for a story that will change, one for a story that will be removed, and others."""
        (self.notes / "analysis").mkdir(parents=True)
        (self.notes / "GTQ-202.md").write_text("My note on story two.\nLine two, with trailing spaces   \n", encoding="utf-8")
        (self.notes / "GTQ-205.md").write_text("My note on story five, which later leaves my list.\n", encoding="utf-8")
        (self.notes / "analysis" / "risk-table.md").write_text("| risk | owner |\n|---|---|\n| late data | me |\n", encoding="utf-8")
        (self.notes / "scratch.bin").write_bytes(bytes(range(256)))

    def notes_digest(self):
        digest = hashlib.sha256()
        for path in sorted(self.notes.rglob("*")):
            digest.update(str(path.relative_to(self.notes)).encode("utf-8"))
            if path.is_file():
                digest.update(path.read_bytes())
        return digest.hexdigest()

    def run(self, *args, moment=None, fail_on_search=None, fail_on_request=None):
        if moment:
            self.jira.at(moment)
        self.jira.fail_on_search_number = fail_on_search
        self.jira.fail_on_request_number = fail_on_request
        self.jira._searches = 0
        self.jira.requests.clear()
        os.environ.update(JIRA_BASE_URL="https://example.invalid", JIRA_EMAIL="tester@example.invalid", JIRA_API_TOKEN="token-test")
        sys.argv = ["sync.py", *args]
        output = io.StringIO()
        try:
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                self.sync.main()
            return "ok", output.getvalue()
        except SystemExit as error:
            return f"stopped: {error}", output.getvalue()

    def delta(self, moment, **kwargs):
        return self.run("--delta", moment=moment, **kwargs)

    def everything(self):
        """Bytes of every file the sync may write, plus the notes digest."""
        files = {str(p.relative_to(self.root)): p.read_bytes() for p in sorted((self.root / "participant" / "context").rglob("*"))
                 if p.is_file() and self.notes not in p.parents}
        return files, self.notes_digest()

    def data(self):
        return json.loads(self.stories_path.read_text(encoding="utf-8"))

    def cursor_ms(self):
        match = re.search(r"^- cursor: (\S+)$", self.state_path.read_text(encoding="utf-8"), re.MULTILINE)
        assert match, "sync-state.md has no `- cursor:` line"
        return to_ms(match.group(1))

    def story_queries(self):
        """(jql, fields) for every story search in the last run."""
        found = []
        for path in self.jira.requests:
            query = urllib.parse.parse_qs(urllib.parse.urlparse(path).query)
            if "jql" in query and "issuetype = Story" in query["jql"][0]:
                found.append((query["jql"][0], query["fields"][0]))
        return found


def counts(output):
    return {name: int(value) for name, value in re.findall(r"^(fetched|new|changed|unchanged|removed): (\d+)$", output, re.MULTILINE)}


def local_state(data):
    """What the participant holds, without the two fields that only record when a fetch happened."""
    stories = sorted(({k: v for k, v in story.items() if k != "retrieved_at"} for story in data["stories"]), key=lambda s: s["key"])
    return {"stories": stories, "removed": sorted(data["removed"], key=lambda r: r["key"])}


def synced_through(*moments):
    box = Sandbox()
    box.write_notes()
    for moment in moments:
        status, output = box.delta(moment)
        assert status == "ok", f"{moment}: {status}\n{output}"
    return box


def by_key(box):
    return {story["key"]: story for story in box.data()["stories"]}


@test
def c1_first_run_fetches_everything_and_later_runs_ask_only_for_changes():
    box = Sandbox()
    assert box.delta("moment-0")[0] == "ok"
    assert not any("updated >=" in jql for jql, _ in box.story_queries()), "the first run has no cursor, so it must not filter"
    status, output = box.delta("moment-1")
    assert status == "ok", output
    expected = to_ms(NEWEST_AT_MOMENT_0) - MARGIN_MS
    for jql, fields in box.story_queries():
        # Every story search is either the filtered one, or the cheap key-and-updated list.
        assert f"updated >= {expected}" in jql or fields == LIST_FIELDS, f"unfiltered full fetch in a delta run: {jql} [{fields}]"
    assert any(f"updated >= {expected}" in jql for jql, _ in box.story_queries())
    assert counts(output)["fetched"] == 3, output  # GTQ-202, GTQ-204, GTQ-206


@test
def c2_cursor_advances_to_jiras_newest_timestamp_after_success():
    box = Sandbox()
    assert box.delta("moment-0")[0] == "ok"
    assert box.cursor_ms() == to_ms(NEWEST_AT_MOMENT_0)
    assert box.delta("moment-1")[0] == "ok"
    assert box.cursor_ms() == to_ms(NEWEST_AT_MOMENT_1)  # written with a +1100 offset in the fixture


@test
def c3_failed_sync_leaves_cursor_and_stories_exactly_as_they_were():
    box = synced_through("moment-0")
    state_before, stories_before, notes_before = box.state_path.read_bytes(), box.stories_path.read_bytes(), box.notes_digest()
    status, _ = box.delta("moment-1", fail_on_search=2)  # the first page of changes arrived, the second did not
    assert status.startswith("stopped"), status
    assert box.state_path.read_bytes() == state_before
    assert box.stories_path.read_bytes() == stories_before
    assert box.notes_digest() == notes_before


@test
def c3_failure_while_checking_for_removals_also_leaves_the_cursor():
    for search_number in (3, 4, 5):
        box = synced_through("moment-0")
        state_before = box.state_path.read_bytes()
        status, _ = box.delta("moment-1", fail_on_search=search_number)
        if status == "ok":
            continue  # the run made fewer searches than this
        assert box.state_path.read_bytes() == state_before, f"cursor moved after a failure on search {search_number}"


@test
def c4_next_sync_recovers_what_the_failed_one_missed():
    box = synced_through("moment-0")
    box.delta("moment-1", fail_on_search=2)
    status, output = box.delta("moment-1")
    assert status == "ok", output
    twin = synced_through("moment-0", "moment-1")  # never failed
    assert local_state(box.data()) == local_state(twin.data())
    assert box.cursor_ms() == to_ms(NEWEST_AT_MOMENT_1)
    assert {"GTQ-202", "GTQ-204", "GTQ-206"} <= set(by_key(box))
    assert by_key(box)["GTQ-202"]["status"] == "In Progress"


@test
def c4_crash_after_stories_are_written_but_before_the_cursor_is_saved_recovers():
    box = synced_through("moment-0")
    state_before = box.state_path.read_bytes()
    real_write = box.sync.write_atomic

    def failing_write(path, text):
        if Path(path).name == "sync-state.md":
            raise OSError("disk full")
        return real_write(path, text)

    box.sync.write_atomic = failing_write
    try:
        box.delta("moment-1")
    except OSError:
        pass
    box.sync.write_atomic = real_write
    assert box.state_path.read_bytes() == state_before, "the cursor moved although saving it failed"
    assert box.delta("moment-1")[0] == "ok"
    twin = synced_through("moment-0", "moment-1")
    assert local_state(box.data()) == local_state(twin.data())


@test
def c5_run_reports_fetched_new_changed_unchanged_and_removed_counts():
    box = Sandbox()
    expected = [
        ("moment-0", {"fetched": 5, "new": 5, "changed": 0, "unchanged": 0, "removed": 0}),
        # 202 and 204 changed, 206 is new, 201 and 203 were not touched, 205 left the list.
        ("moment-1", {"fetched": 3, "new": 1, "changed": 2, "unchanged": 2, "removed": 1}),
        # 203 is the late arrival. 206 is fetched again inside the 5 minute overlap, and is identical.
        ("moment-2", {"fetched": 2, "new": 0, "changed": 1, "unchanged": 4, "removed": 0}),
        ("moment-3", {"fetched": 2, "new": 0, "changed": 0, "unchanged": 5, "removed": 0}),
    ]
    for moment, want in expected:
        status, output = box.delta(moment)
        assert status == "ok", output
        assert counts(output) == want, f"{moment}: {counts(output)} != {want}"


@test
def c6_notes_are_byte_identical_after_every_kind_of_run():
    box = Sandbox()
    box.write_notes()
    before = box.notes_digest()
    names_before = sorted(str(p.relative_to(box.notes)) for p in box.notes.rglob("*"))
    steps = (
        ("ok", lambda: box.delta("moment-0")),
        ("stopped", lambda: box.delta("moment-1", fail_on_search=2)),
        ("ok", lambda: box.delta("moment-1")),
        ("ok", lambda: box.delta("moment-2")),
        ("ok", lambda: box.delta("moment-3")),
        ("ok", lambda: box.run(moment="moment-3")),  # a full sync
    )
    for want, step in steps:
        status, output = step()
        assert status.startswith(want), f"{status}\n{output}"  # a run that did nothing proves nothing
        assert box.notes_digest() == before
    assert sorted(str(p.relative_to(box.notes)) for p in box.notes.rglob("*")) == names_before


@test
def c7_full_resync_over_the_delta_state_changes_nothing():
    box = synced_through("moment-0", "moment-1", "moment-2", "moment-3")
    from_deltas = local_state(box.data())
    status, output = box.run(moment="moment-3")  # full sync, same folder
    assert status == "ok", output
    assert local_state(box.data()) == from_deltas


@test
def c7_full_sync_from_scratch_holds_the_same_stories_as_the_deltas():
    deltas = synced_through("moment-0", "moment-1", "moment-2", "moment-3")
    scratch = Sandbox()
    assert scratch.run(moment="moment-3")[0] == "ok"
    # A from-scratch sync cannot know GTQ-205 was ever held, so only the stories are compared here.
    assert local_state(scratch.data())["stories"] == local_state(deltas.data())["stories"]


@test
def margin_catches_an_edit_that_jira_showed_late():
    box = synced_through("moment-0", "moment-1", "moment-2")
    assert by_key(box)["GTQ-203"]["summary"] == "Synthetic story three, reworded"


@test
def cursor_does_not_move_when_nothing_newer_arrives():
    box = synced_through("moment-0", "moment-1", "moment-2")
    assert box.cursor_ms() == to_ms(NEWEST_AT_MOMENT_1)  # GTQ-203's late edit is older than the cursor
    box.delta("moment-3")
    assert box.cursor_ms() == to_ms(NEWEST_AT_MOMENT_1)


@test
def story_that_left_the_list_is_reported_removed_and_found_with_the_cheap_list_request():
    box = synced_through("moment-0", "moment-1")
    data = box.data()
    assert "GTQ-205" not in by_key(box)
    assert data["removed"] == [{"key": "GTQ-205", "last_known_status": "To Do"}]
    assert any(fields == LIST_FIELDS and "updated" not in jql for jql, fields in box.story_queries())


@test
def story_that_comes_back_is_no_longer_listed_as_removed():
    box = synced_through("moment-0", "moment-1")
    moment_2 = box.jira.timeline["moments"][2]
    moment_2["stories"].append({"key": "GTQ-205", "summary": "Synthetic story five", "status": "To Do",
                                "updated": "2026-11-02T15:00:00.000+0000", "comments": []})
    assert box.delta("moment-2")[0] == "ok"
    assert "GTQ-205" in by_key(box)
    assert box.data()["removed"] == []


@test
def story_that_comes_back_without_a_new_timestamp_is_held_again():
    """Found in review. Jira lists GTQ-205 as assigned again, but its `updated` is older than the cursor."""
    box = synced_through("moment-0", "moment-1")
    moment_2 = box.jira.timeline["moments"][2]
    moment_2["stories"].append({"key": "GTQ-205", "summary": "Synthetic story five", "status": "To Do",
                                "updated": "2026-11-02T09:00:00.000+0000", "comments": []})
    status, output = box.delta("moment-2")
    assert status == "ok", output
    assert "GTQ-205" in by_key(box), "Jira says GTQ-205 is assigned, but it is not held"
    assert box.data()["removed"] == []
    scratch = Sandbox()
    scratch.jira.timeline = box.jira.timeline
    assert scratch.run(moment="moment-2")[0] == "ok"
    assert local_state(scratch.data())["stories"] == local_state(box.data())["stories"]  # C7


@test
def story_missing_from_one_keys_list_is_held_again_on_the_next_run():
    """Found in review. One keys-only answer leaves GTQ-201 out by mistake; the next answer is complete."""
    box = synced_through("moment-0", "moment-1", "moment-2")
    real = box.jira.get_json

    def forgetful(settings, path):
        response = real(settings, path)
        query = urllib.parse.parse_qs(urllib.parse.urlparse(path).query)
        if query.get("fields") == [LIST_FIELDS]:
            response["issues"] = [issue for issue in response["issues"] if issue["key"] != "GTQ-201"]
        return response

    box.sync.get_json = forgetful
    box.delta("moment-3")
    box.sync.get_json = real
    assert box.delta("moment-3")[0] == "ok"
    assert "GTQ-201" in by_key(box), "GTQ-201 is assigned in Jira, but it is in neither the stories nor the removed list"


@test
def c2_c3_failure_at_every_request_position_changes_nothing_and_recovers():
    """Found in review: the earlier failure tests only covered some positions."""
    twin = synced_through("moment-0", "moment-1")
    failed_positions = 0
    for position in range(1, 50):
        box = synced_through("moment-0")
        before = box.everything()
        status, _ = box.delta("moment-1", fail_on_request=position)
        if status == "ok":
            break
        failed_positions += 1
        assert box.everything() == before, f"something changed after a failure on request {position}"
        assert box.delta("moment-1")[0] == "ok"
        assert local_state(box.data()) == local_state(twin.data()), f"no full recovery after a failure on request {position}"
        assert box.cursor_ms() == twin.cursor_ms()
    # /myself, two pages of changes, three pages of keys, one search for other items
    assert failed_positions == 7, f"expected 7 requests in this run, saw {failed_positions}"


@test
def c2_cursor_file_is_written_once_and_last():
    box = synced_through("moment-0")
    real_write, written = box.sync.write_atomic, []

    def recording_write(path, text):
        written.append(Path(path).name)
        return real_write(path, text)

    box.sync.write_atomic = recording_write
    assert box.delta("moment-1")[0] == "ok"
    assert written[-1] == "sync-state.md" and written.count("sync-state.md") == 1, written
    assert {"stories.json", "index.md"} <= set(written[:-1]), written


@test
def c3_failure_writing_stories_or_index_leaves_the_cursor_and_recovers():
    twin = synced_through("moment-0", "moment-1")
    for name in ("stories.json", "index.md"):
        box = synced_through("moment-0")
        state_before, notes_before = box.state_path.read_bytes(), box.notes_digest()
        real_write = box.sync.write_atomic

        def failing_write(path, text, name=name, real_write=real_write):
            if Path(path).name == name:
                raise OSError("disk full")
            return real_write(path, text)

        box.sync.write_atomic = failing_write
        try:
            box.delta("moment-1")
        except OSError:
            pass
        box.sync.write_atomic = real_write
        assert box.state_path.read_bytes() == state_before, f"the cursor moved although writing {name} failed"
        assert box.notes_digest() == notes_before
        assert box.delta("moment-1")[0] == "ok"
        assert local_state(box.data()) == local_state(twin.data()), name
        assert box.cursor_ms() == twin.cursor_ms()


@test
def cursor_does_not_move_backward_when_only_older_stories_are_fetched():
    box = synced_through("moment-0", "moment-1")
    moment_2 = box.jira.timeline["moments"][2]
    moment_2["stories"] = [story for story in moment_2["stories"] if story["key"] != "GTQ-206"]  # the newest one leaves
    assert box.delta("moment-2")[0] == "ok"
    assert box.cursor_ms() == to_ms(NEWEST_AT_MOMENT_1)


@test
def cursor_line_with_an_unreadable_value_stops_the_run():
    box = synced_through("moment-0")
    text = box.state_path.read_text(encoding="utf-8")
    broken = re.sub(r"^- cursor: .*$", "- cursor: last tuesday", text, flags=re.MULTILINE)
    box.state_path.write_text(broken, encoding="utf-8")
    stories_before = box.stories_path.read_bytes()
    status, _ = box.delta("moment-1")
    assert status.startswith("stopped"), status
    assert box.stories_path.read_bytes() == stories_before and box.state_path.read_text(encoding="utf-8") == broken


@test
def stored_comment_is_kept_when_a_changed_story_no_longer_returns_it():
    box = synced_through("moment-0", "moment-1")
    for story in box.jira.timeline["moments"][2]["stories"]:
        if story["key"] == "GTQ-204":
            story.update(comments=["9002"], updated="2026-11-02T14:30:00.000+0000")
    assert box.delta("moment-2")[0] == "ok"
    assert [comment["id"] for comment in by_key(box)["GTQ-204"]["comments"]] == ["9001", "9002"]


@test
def index_is_rewritten_by_a_delta_run():
    box = synced_through("moment-0", "moment-1")
    index = (box.out / "index.md").read_text(encoding="utf-8")
    assert "GTQ-206" in index and "In Progress" in index


@test
def cursor_set_in_the_future_does_not_leave_held_stories_stale():
    """Found in review. The filter returns nothing, so the list's `updated` times must reveal the changes."""
    box = synced_through("moment-0")
    text = box.state_path.read_text(encoding="utf-8")
    box.state_path.write_text(re.sub(r"^- cursor: .*$", "- cursor: 2099-01-01T00:00:00.000+0000", text, flags=re.MULTILINE), encoding="utf-8")
    status, output = box.delta("moment-1")
    assert status == "ok", output
    twin = synced_through("moment-0", "moment-1")
    assert local_state(box.data()) == local_state(twin.data())
    assert by_key(box)["GTQ-202"]["status"] == "In Progress"


@test
def stories_file_rolled_back_to_an_older_copy_is_brought_up_to_date():
    box = synced_through("moment-0")
    old_copy = box.stories_path.read_bytes()
    assert box.delta("moment-1")[0] == "ok"
    box.stories_path.write_bytes(old_copy)  # the cursor is now ahead of what is stored
    status, output = box.delta("moment-2")
    assert status == "ok", output
    twin = synced_through("moment-0", "moment-1", "moment-2")
    assert local_state(box.data()) == local_state(twin.data())


@test
def edit_that_jira_showed_later_than_the_margin_is_still_picked_up():
    box = synced_through("moment-0", "moment-1")
    for story in box.jira.timeline["moments"][2]["stories"]:
        if story["key"] == "GTQ-203":
            story["updated"] = "2026-11-02T13:50:00.000+0000"  # 15 minutes before the cursor, far outside the margin
    status, output = box.delta("moment-2")
    assert status == "ok", output
    assert by_key(box)["GTQ-203"]["summary"] == "Synthetic story three, reworded"


def with_list_answer_changed(box, change):
    """Run `change(response)` on every answer to the cheap key-and-updated list request."""
    real = box.jira.get_json

    def patched(settings, path):
        response = real(settings, path)
        query = urllib.parse.parse_qs(urllib.parse.urlparse(path).query)
        if query.get("fields") == [LIST_FIELDS]:
            response = change(response)
        return response

    box.sync.get_json = patched
    return real


@test
def same_instant_written_with_another_offset_is_not_fetched_again():
    """Found in the second review. 14:00 +0000 and 01:00 +1100 the next day are the same instant."""
    box = synced_through("moment-0", "moment-1", "moment-2")
    for story in box.jira.timeline["moments"][2]["stories"]:
        if story["key"] == "GTQ-201":
            assert story["updated"] == "2026-11-01T14:00:00.000+0000"
            story["updated"] = "2026-11-02T01:00:00.000+1100"
    status, output = box.delta("moment-3")
    assert status == "ok", output
    assert not any("key in (" in jql for jql, _ in box.story_queries()), "a story was fetched by key although nothing changed"
    assert counts(output) == {"fetched": 2, "new": 0, "changed": 0, "unchanged": 5, "removed": 0}


@test
def a_hundred_and_twenty_missing_stories_are_all_fetched_by_key():
    """Found in the second review. More missing stories than fit in one by-key request."""
    box = synced_through("moment-0")
    extra = [{"key": f"GTQ-{n}", "summary": f"Synthetic old story {n}", "status": "To Do",
              "updated": "2026-10-30T10:00:00.000+0000", "comments": []} for n in range(400, 520)]
    box.jira.timeline["moments"][1]["stories"] += extra  # assigned now, but older than the cursor
    status, output = box.delta("moment-1")
    assert status == "ok", output
    assert {story["key"] for story in extra} <= set(by_key(box))
    assert len(by_key(box)) == 125  # 201 to 204 and 206, plus the 120
    scratch = Sandbox()
    scratch.jira.timeline = box.jira.timeline
    assert scratch.run(moment="moment-1")[0] == "ok"
    assert local_state(scratch.data())["stories"] == local_state(box.data())["stories"]


@test
def removed_story_that_is_listed_but_cannot_be_fetched_stays_removed():
    """Found in the second review. The list names GTQ-205 again, but the fetch by key returns nothing."""
    box = synced_through("moment-0", "moment-1")

    def also_list_205(response):
        response["issues"] = response["issues"] + [{"key": "GTQ-205", "fields": {"updated": "2026-11-02T09:00:00.000+0000"}}]
        return response

    with_list_answer_changed(box, also_list_205)
    status, output = box.delta("moment-2")
    assert status == "ok", output
    assert "GTQ-205" not in by_key(box)
    assert box.data()["removed"] == [{"key": "GTQ-205", "last_known_status": "To Do"}], "GTQ-205 is in neither list"
    assert "GTQ-205" in output and "not returned" in output, "the run should say the story was listed but could not be fetched"
    assert "fetched by key: GTQ-205" not in output


@test
def cursor_that_is_saved_can_always_be_read_back():
    """Found in the second review. One story's timestamp has no milliseconds, which the cursor reader rejects."""
    box = Sandbox()
    box.jira.timeline["moments"][0]["stories"][0]["updated"] = "2026-11-01T14:00:00+0000"
    status, output = box.delta("moment-0")
    assert status == "ok", output
    assert box.cursor_ms() == to_ms(NEWEST_AT_MOMENT_0)
    assert output.count("could not be read") == 1 and "GTQ-201" in output, output
    box.jira.timeline["moments"][1]["stories"][0]["updated"] = "2026-11-01T14:00:00+0000"
    status, output = box.delta("moment-1")
    assert status == "ok", f"the run after it could not read its own cursor: {status}"


@test
def jira_answer_without_an_issue_list_stops_the_run():
    """Found in the second review. An answer with no `issues` must not be read as "nothing is assigned"."""
    box = synced_through("moment-0")
    before = box.everything()

    def drop_issues(response):
        return {key: value for key, value in response.items() if key != "issues"}

    real = with_list_answer_changed(box, drop_issues)
    status, _ = box.delta("moment-1")
    box.sync.get_json = real
    assert status.startswith("stopped"), status
    assert box.everything() == before


@test
def unreadable_state_file_stops_the_run_instead_of_guessing():
    box = synced_through("moment-0")
    box.state_path.write_text("this is not a state file\n", encoding="utf-8")
    stories_before = box.stories_path.read_bytes()
    status, _ = box.delta("moment-1")
    assert status.startswith("stopped"), status
    assert box.stories_path.read_bytes() == stories_before
    assert box.state_path.read_text(encoding="utf-8") == "this is not a state file\n"


@test
def cursor_without_local_stories_falls_back_to_fetching_everything():
    box = synced_through("moment-0")
    box.stories_path.unlink()
    status, output = box.delta("moment-1")
    assert status == "ok", output
    assert set(by_key(box)) == {"GTQ-201", "GTQ-202", "GTQ-203", "GTQ-204", "GTQ-206"}


@test
def no_credentials_in_the_state_file_or_the_output():
    box = Sandbox()
    _, output = box.delta("moment-0")
    for secret in ("token-test", "tester@example.invalid"):
        assert secret not in output
        assert secret not in box.state_path.read_text(encoding="utf-8")


def main():
    failed = 0
    for function in TESTS:
        try:
            function()
            print(f"PASS  {function.__name__}")
        except Exception as error:  # noqa: BLE001
            failed += 1
            line = str(error).strip().splitlines()[0] if str(error).strip() else ""
            print(f"FAIL  {function.__name__}: {type(error).__name__} {line}")
    print(f"{len(TESTS) - failed} of {len(TESTS)} passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
