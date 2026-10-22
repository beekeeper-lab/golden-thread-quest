"""Stubbed tests for sync.py. No network, and no changes to your workspace.

Each test copies sync.py and the Jira fixtures into a temporary folder, loads that copy,
and replaces its Jira call with a stub. Expected results come from SKILL.md and the quest,
not from the code. Run from the repository root:
  python3 participant/skills/jira-read-assigned/tests/test_sync.py
Exit code 0 means every test passed. Set SYNC_UNDER_TEST to a path to test another copy.
"""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import urllib.parse
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
REPO = SKILL_DIR.parents[2]
SYNC = Path(os.environ.get("SYNC_UNDER_TEST", SKILL_DIR / "sync.py"))
FIXTURES = REPO / "validators" / "fixtures" / "jira"
TESTS = []


def test(function):
    TESTS.append(function)
    return function


class Sandbox:
    """A temporary copy of the repository layout that sync.py expects, with Jira stubbed."""

    def __init__(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        skill = root / "participant" / "skills" / "jira-read-assigned"
        skill.mkdir(parents=True)
        shutil.copy(SYNC, skill / "sync.py")
        shutil.copytree(FIXTURES, root / "validators" / "fixtures" / "jira")
        spec = importlib.util.spec_from_file_location("sync_under_test", skill / "sync.py")
        self.sync = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.sync)
        self.stories_path = self.sync.OUT_DIR / "stories.json"
        self.story_pages = [[]]
        self.other_pages = [[]]
        self.requests = []
        self.sync.get_json = self.stub

    def stub(self, settings, path):
        self.requests.append(path)
        if path.startswith("/rest/api/3/myself"):
            return {"accountId": "acc-test", "emailAddress": "tester@example.invalid", "displayName": "Tester"}
        query = urllib.parse.parse_qs(urllib.parse.urlparse(path).query)
        pages = self.story_pages if "issuetype = Story" in query["jql"][0] else self.other_pages
        index = int(query["nextPageToken"][0][1:]) if "nextPageToken" in query else 0
        response = {"issues": pages[index]}
        if index + 1 < len(pages):
            response["nextPageToken"] = f"t{index + 1}"
        return response

    def run(self, *args, base_url="https://example.invalid", drop=None):
        os.environ.update(JIRA_BASE_URL=base_url, JIRA_EMAIL="tester@example.invalid", JIRA_API_TOKEN="token-test")
        if drop:
            os.environ.pop(drop)
        sys.argv = ["sync.py", *args]
        output = io.StringIO()
        try:
            with contextlib.redirect_stdout(output):
                self.sync.main()
            return "ok", output.getvalue()
        except SystemExit as error:
            return f"stopped: {error}", output.getvalue()

    def data(self):
        return json.loads(self.stories_path.read_text(encoding="utf-8"))

    def digest(self):
        return hashlib.sha256(self.stories_path.read_bytes()).hexdigest()

    def story_requests(self):
        return [p for p in self.requests if "search" in p and "issuetype+%3D+Story" in p]


def issue(key, comments=(), **extra_fields):
    fields = {
        "summary": f"Story {key}", "status": {"name": "To Do"}, "issuetype": {"name": "Story"},
        "assignee": {"accountId": "acc-test", "emailAddress": "tester@example.invalid", "displayName": "Tester"},
        "comment": {"comments": [{"id": cid, "created": "c", "updated": updated, "body": "comment body",
                                  "author": {"displayName": "Commenter"}} for cid, updated in comments],
                    "total": len(comments)},
    }
    fields.update(extra_fields)
    return {"key": key, "fields": fields}


def text(value, bold=False):
    return {"type": "text", "text": value, **({"marks": [{"type": "strong"}]} if bold else {})}


def heading(value):
    return {"type": "heading", "attrs": {"level": 2}, "content": [text(value)]}


def para(*parts):
    return {"type": "paragraph", "content": list(parts)}


def bullets(*items):
    return {"type": "bulletList", "content": [{"type": "listItem", "content": [para(text(i))]} for i in items]}


def checklist(*items):
    return {"type": "taskList", "content": [{"type": "taskItem", "attrs": {"state": s}, "content": [text(i)]} for i, s in items]}


def doc(*nodes):
    return {"type": "doc", "content": list(nodes)}


# Identity and pagination (acceptance criteria 1 and 3)

@test
def identity_comes_from_jira(box):
    box.story_pages = [[issue("GTQ-1")]]
    box.run()
    jql = urllib.parse.parse_qs(urllib.parse.urlparse(box.story_requests()[0]).query)["jql"][0]
    assert box.requests[0].startswith("/rest/api/3/myself"), "the first request is not the identity call"
    assert jql == 'assignee = "acc-test" AND issuetype = Story', jql


@test
def pagination_follows_every_page_and_stores_each_story_once(box):
    box.story_pages = [[issue("GTQ-1"), issue("GTQ-2")], [issue("GTQ-2"), issue("GTQ-3")], [issue("GTQ-4")]]
    box.run()
    keys = [s["key"] for s in box.data()["stories"]]
    assert keys == ["GTQ-1", "GTQ-2", "GTQ-3", "GTQ-4"], keys
    assert len(box.story_requests()) == 3, f"{len(box.story_requests())} story requests"


@test
def repeated_page_token_stops_and_keeps_the_previous_file(box):
    box.story_pages = [[issue("GTQ-1")]]
    box.run()
    before = box.digest()
    box.sync.get_json = lambda s, p: {"accountId": "acc-test"} if "myself" in p else {"issues": [], "nextPageToken": "same"}
    outcome, _ = box.run()
    assert outcome.startswith("stopped") and "page token" in outcome, outcome
    assert box.digest() == before, "stories.json changed"


# Privacy and secrets (criterion 9)

@test
def people_and_private_fields_are_never_stored(box):
    box.story_pages = [[issue(
        "GTQ-1", comments=[("5", "u")],
        reporter={"displayName": "Reporter Person", "emailAddress": "reporter@example.invalid"},
        creator={"displayName": "Creator Person"},
        worklog={"worklogs": [{"comment": "private worklog note"}]},
        attachment=[{"filename": "private-file.xlsx"}],
        customfield_10001="Customer Name",
        issuelinks=[{"outwardIssue": {"fields": {"summary": "linked summary"}}}],
    )]]
    box.run()
    stored = box.stories_path.read_text(encoding="utf-8") + (box.sync.OUT_DIR / "index.md").read_text(encoding="utf-8")
    for value in ("Reporter Person", "reporter@example.invalid", "Creator Person", "private worklog note",
                  "private-file.xlsx", "Customer Name", "linked summary", "comment body", "Commenter",
                  "tester@example.invalid", "Tester", "token-test"):
        assert value not in stored, f"{value!r} was stored"
    fields = urllib.parse.parse_qs(urllib.parse.urlparse(box.story_requests()[0]).query)["fields"][0]
    assert "*all" not in fields and "reporter" not in fields, fields


# Fixture and live output stay apart (criterion 8)

@test
def fixture_run_will_not_replace_live_data(box):
    box.story_pages = [[issue("GTQ-1")]]
    box.run()
    before = box.digest()
    outcome, _ = box.run("--source", "happy-path")
    assert outcome.startswith("stopped"), outcome
    assert box.digest() == before, "live stories.json was replaced"


@test
def fixture_run_may_replace_an_empty_live_result(box):
    box.run()
    outcome, _ = box.run("--source", "happy-path")
    assert outcome == "ok" and box.data()["source"] == "happy-path", outcome


@test
def live_run_replaces_fixture_output_without_false_removals(box):
    box.run("--source", "happy-path")
    box.story_pages = [[issue("GTQ-1")]]
    outcome, printed = box.run()
    data = box.data()
    assert [s["key"] for s in data["stories"]] == ["GTQ-1"] and data["removed"] == [], data["removed"]
    assert "replaced, not merged" in printed, "no warning printed"


@test
def live_rerun_reports_a_story_that_left(box):
    box.story_pages = [[issue("GTQ-1")]]
    box.run()
    box.story_pages = [[]]
    box.run()
    assert box.data()["removed"] == [{"key": "GTQ-1", "last_known_status": "To Do"}], box.data()["removed"]


@test
def stories_json_with_no_source_is_treated_as_live(box):
    box.sync.OUT_DIR.mkdir(parents=True, exist_ok=True)
    box.stories_path.write_text(json.dumps({"stories": [{"key": "OLD-1", "status": "To Do"}], "removed": []}))
    before = box.digest()
    outcome, _ = box.run("--source", "happy-path")
    assert outcome.startswith("stopped") and box.digest() == before, outcome


# Comments (criterion 7)

@test
def comment_repeated_in_one_response_is_stored_once(box):
    box.story_pages = [[issue("GTQ-1", comments=[("5", "u"), ("5", "u"), ("6", "u")])]]
    box.run()
    assert [c["id"] for c in box.data()["stories"][0]["comments"]] == ["5", "6"]


@test
def comment_timestamps_refresh_and_old_comments_are_kept(box):
    box.story_pages = [[issue("GTQ-1", comments=[("5", "first")])]]
    box.run()
    box.story_pages = [[issue("GTQ-1", comments=[("5", "second"), ("6", "x")])]]
    box.run()
    box.story_pages = [[issue("GTQ-1", comments=[("6", "x")])]]
    box.run()
    comments = [(c["id"], c["updated"]) for c in box.data()["stories"][0]["comments"]]
    assert comments == [("5", "second"), ("6", "x")], comments


# Acceptance criteria (criterion 4)

@test
def acceptance_criteria_variants(box):
    cases = [
        (doc(heading("Acceptance criteria"), bullets("A1", "A2")), (True, ["A1", "A2"])),
        (doc(heading("ACCEPTANCE CRITERIA"), bullets("A1")), (True, ["A1"])),
        (doc(heading("Acceptance Criteria:"), bullets("A1")), (True, ["A1"])),
        (doc(para(text("Acceptance criteria", bold=True)), bullets("A1")), (True, ["A1"])),
        (doc(heading("Acceptance criteria"), checklist(("A1", "TODO"), ("A2", "DONE"))), (True, ["A1", "A2"])),
        (doc(heading("Acceptance criteria"), bullets("A1"), heading("Notes"), bullets("N1")), (True, ["A1"])),
        (doc(heading("AC"), bullets("A1")), (False, [])),
        (doc(para(text("Acceptance criteria", bold=True), text(" are below")), bullets("A1")), (False, [])),
        (doc(heading("Acceptance criteria"), para(text("TBD"))), (True, [])),
        (None, (False, [])),
    ]
    for number, (description, expected) in enumerate(cases, start=1):
        got = box.sync.acceptance_criteria(description)
        assert got == expected, f"case {number}: got {got}, expected {expected}"


@test
def missing_or_empty_criteria_are_flagged_with_a_reason(box):
    box.story_pages = [[
        issue("GTQ-1", description=doc(heading("Acceptance criteria"), bullets("A1"))),
        issue("GTQ-2", description=doc(heading("Acceptance criteria"), para(text("TBD")))),
        issue("GTQ-3", description=doc(para(text("No criteria here.")))),
    ]]
    box.run()
    index = (box.sync.OUT_DIR / "index.md").read_text(encoding="utf-8")
    section = index.split("## Missing acceptance criteria")[1].split("## Not synced")[0]
    assert "| GTQ-2 | heading with no items |" in section and "| GTQ-3 | no heading |" in section, section
    assert "GTQ-1" not in section, "a story with criteria was flagged"


@test
def checklists_are_kept_in_the_markdown_description(box):
    markdown = box.sync.adf_to_markdown(doc(checklist(("A1", "TODO"), ("A2", "DONE"))))
    assert markdown == "- [ ] A1\n- [x] A2", repr(markdown)


# Settings and inputs (section 2)

@test
def missing_variable_is_named_and_nothing_is_written(box):
    outcome, _ = box.run(drop="JIRA_API_TOKEN")
    assert outcome == "stopped: Missing environment variable: JIRA_API_TOKEN", outcome
    assert not box.stories_path.exists()


@test
def base_url_must_be_https_and_loses_a_trailing_slash(box):
    outcome, _ = box.run(base_url="http://example.invalid")
    assert outcome.startswith("stopped") and not box.requests and not box.stories_path.exists(), outcome
    box.story_pages = [[issue("GTQ-1")]]
    box.run(base_url="https://example.invalid/")
    assert box.data()["stories"][0]["source_url"] == "https://example.invalid/browse/GTQ-1"


@test
def fixture_must_be_inside_the_fixture_folder(box):
    outcome, _ = box.run("--source", "../../../etc/passwd")
    assert outcome.startswith("stopped") and "fixtures" in outcome, outcome


def main() -> int:
    failures = 0
    for function in TESTS:
        box = Sandbox()
        try:
            function(box)
            print(f"PASS  {function.__name__}")
        except AssertionError as error:
            failures += 1
            print(f"FAIL  {function.__name__}: {error}")
        except Exception as error:  # a crash is a failure, not a pass
            failures += 1
            print(f"FAIL  {function.__name__}: {type(error).__name__}: {error}")
        finally:
            box.temp.cleanup()
    print(f"{len(TESTS) - failures} of {len(TESTS)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
