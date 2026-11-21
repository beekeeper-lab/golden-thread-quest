"""Tests for the create workflow, create.py, against this skill's fake_jira.py. No network.

Run from the repository root:
    python3 -m unittest discover -s participant/skills/jira-create-story/tests -v
"""
import argparse
import contextlib
import copy
import datetime
import hashlib
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, SKILL)
import create  # noqa: E402
from create import pv  # noqa: E402

fake_jira = create.load_fake()
REAL = os.path.join(create.ROOT, "participant", "context", "jira")
HOST = "fixture-site.example.invalid"


class Case(unittest.TestCase):
    """A copy of the draft, its notes and the catalog in a temporary folder, a fake Jira, and the four commands."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = os.path.realpath(tmp.name)
        shutil.copytree(os.path.join(REAL, "new-story", "sources"), os.path.join(self.tmp, "new-story", "sources"))
        shutil.copytree(os.path.join(REAL, "duplicates", "fixture"), os.path.join(self.tmp, "catalog"))
        with open(os.path.join(REAL, "new-story", "draft.md"), encoding="utf-8") as f:
            self.text = f.read()
        self.draft = os.path.join(self.tmp, "new-story", "draft.md")
        self.link = os.path.join(self.tmp, "new-story", "linked.md")
        self.state = os.path.join(self.tmp, "state")
        self.allowlist = os.path.join(SKILL, "fake-allowlist.json")
        self.host = HOST
        self.fake = fake_jira.FakeJira()
        self.write_draft()
        patch = mock.patch.object(pv, "CONTEXT", self.tmp)
        patch.start()
        self.addCleanup(patch.stop)

    def write_draft(self):
        with open(self.draft, "w", encoding="utf-8") as f:
            f.write(self.text)

    def edit(self, old, new):
        self.assertIn(old, self.text)
        self.text = self.text.replace(old, new)
        self.write_draft()

    def run_command(self, command, **more):
        args = dict(command=command, draft=self.draft, link=self.link, allowlist=self.allowlist,
                    catalog=os.path.join(self.tmp, "catalog"), state=self.state, log=None, result=None, fingerprint=None,
                    confirmed_by=None, pretend_minutes_later=0, today=datetime.date(2026, 11, 19))
        args.update(more)
        del create.LINES[:]
        self.conn = create.Connection(self.fake.get, self.fake.post if command == "confirm" else None, self.host)
        code = create.run(argparse.Namespace(**args), self.conn)
        return code, "\n".join(create.LINES)

    def preview(self):
        code, text = self.run_command("preview")
        found = re.findall(r"^Fingerprint of this preview: ([0-9a-f]{12})$", text, re.M)
        return code, text, (found[0] if found else None)

    def previewed(self):
        code, text, fingerprint = self.preview()
        self.assertEqual(code, 0, text)
        self.assertIsNotNone(fingerprint)
        return fingerprint

    def confirm(self, fingerprint, name="the participant", **more):
        return self.run_command("confirm", fingerprint=fingerprint, confirmed_by=name, **more)

    def created(self):
        fingerprint = self.previewed()
        code, text = self.confirm(fingerprint)
        self.assertEqual(code, 0, text)
        return fingerprint, text

    def posts(self):
        return [path for method, path in self.fake.requests if method == "POST"]

    def rpt(self):
        return [item["key"] for item in self.fake.issues if item["key"].startswith("RPT-")]

    def linked(self):
        return create.read_link(self.link)

    def record(self, fingerprint):
        with open(os.path.join(self.state, "create-story-previews", fingerprint + ".json"), encoding="utf-8") as f:
            return json.load(f)

    def assertRefused(self, result, *phrases):
        code, text = result[0], result[1]
        self.assertEqual(code, 1, text)
        self.assertIn("REFUSED:", text)
        self.assertIn("Nothing has been written to Jira.", text)
        for phrase in phrases:
            self.assertIn(phrase, text)

    def assertNothingCreated(self):
        self.assertEqual(self.posts(), [])
        self.assertEqual(len(self.rpt()), 7)


class Preview(Case):
    def test_it_shows_the_site_project_fields_payload_and_checks_and_writes_nothing(self):
        before = copy.deepcopy(self.fake.issues)
        code, text, fingerprint = self.preview()
        self.assertEqual(code, 0, text)
        for phrase in ("PREVIEW OF CREATING ONE STORY. Nothing has been written to Jira.", "Jira site:   https://fixture-site.example.invalid",
                       "Project:     RPT (project id 30000). On the sandbox allowlist: yes.", "one new story would be created",
                       "THE EXACT PAYLOAD.", "(CREATE_ISSUES):   yes", "Duplicate checks:", "1. This draft's own link file: there is none",
                       "2. Asked of Jira, stories in RPT with this title: 0 with exactly this title", "3. Duplicate search:",
                       "Where Jira cannot check:", "The two are the same. Jira is unchanged.", "Every one was a GET", "Expires:"):
            self.assertIn(phrase, text)
        self.assertEqual(self.fake.issues, before)
        self.assertEqual(set(method for method, _ in self.fake.requests), {"GET"})
        self.assertFalse(os.path.exists(self.link), "a preview does not make a link file")

    def test_the_payload_shown_carries_the_marker_and_is_the_one_saved(self):
        code, text, fingerprint = self.preview()
        shown = json.loads(text.split("not a summary of it:\n")[1].split("\nAs sent it is")[0])
        record = self.record(fingerprint)
        self.assertEqual(shown, record["payload"])
        self.assertRegex(record["marker"], r"^gtq-[0-9a-f]{8}$")
        self.assertEqual(shown["fields"]["labels"], ["reporting", "revenue", record["marker"]])
        self.assertIn("The label %s is this preview's marker. It is not in the draft." % record["marker"], text)
        self.assertEqual(hashlib.sha256(pv.body_bytes(shown)).hexdigest(), record["payload_sha256"])

    def test_each_preview_has_its_own_marker(self):
        a = self.record(self.previewed())["marker"]
        b = self.record(self.previewed())["marker"]
        self.assertNotEqual(a, b)

    def test_a_preview_has_no_way_to_write(self):
        conn = create.Connection(self.fake.get, None, HOST)
        with self.assertRaises(create.Refused):
            conn.create(b"{}")
        self.assertEqual(self.posts(), [])

    def test_a_story_in_jira_with_the_same_title_is_reported_even_if_the_catalog_lacks_it(self):
        self.fake.issues.append(fake_jira.base.issue("30050", "RPT-50", "Story", "2026-11-19T09:00:00.000+0000"))
        self.fake.issues[-1]["fields"].update(summary="Quarterly revenue by plan report for the finance team", labels=[])
        code, text, _ = self.preview()
        self.assertEqual(code, 0)
        self.assertIn("stories in RPT with this title: 1 with exactly this title (issue id 30050)", text)
        self.assertIn("WARNING: the catalog holds 7 of project RPT's stories and Jira holds 8", text)

    def test_a_title_check_jira_will_not_run_is_said_not_to_have_been_made(self):
        real = self.fake.get
        self.fake.get = lambda path, params=None: (400, {}, {}) if "summary ~" in str((params or {}).get("jql")) else real(path, params)
        code, text, _ = self.preview()
        self.assertEqual(code, 0)
        self.assertIn("Jira would not run the search, so this was NOT checked.", text)

    def test_a_missing_required_field_or_a_false_citation_stops_the_preview(self):
        text = self.text
        self.edit('components: ["Reports"]\n', "")
        self.edit('- components: sources/intake-notes.md line 11: "under the component Reports"\n', "")
        self.assertRefused(self.preview(), '"Components" (components)')
        self.text = text
        self.edit("Tag it reporting and revenue", "Tag it urgent")
        self.assertRefused(self.preview(), "the citation for labels is not true")
        self.assertFalse(os.path.exists(self.state))


class ApprovedRun(Case):
    def test_it_creates_exactly_one_story_and_sends_exactly_the_previewed_bytes(self):
        fingerprint = self.previewed()
        record = self.record(fingerprint)
        code, text = self.confirm(fingerprint)
        self.assertEqual(code, 0, text)
        self.assertEqual(self.posts(), ["/rest/api/3/issue"])
        self.assertEqual(self.fake.bodies, [pv.body_bytes(record["payload"])])
        self.assertEqual(hashlib.sha256(self.fake.bodies[0]).hexdigest(), record["payload_sha256"])
        self.assertEqual(len(self.rpt()), 8)
        for phrase in ("CONFIRMATION for preview %s, given by: the participant" % fingerprint, "Jira answered 201 with the key RPT-10 and the issue id 30010",
                       "The confirmation and the write happened in this one run of the command.", "10 GET and 1 POST. The POST is the one create."):
            self.assertIn(phrase, text)

    def test_the_key_and_the_id_are_written_to_the_link_file(self):
        fingerprint, text = self.created()
        front, payload = self.linked()
        self.assertEqual((front["state"], front["jira_id"], front["jira_key"]), ("created", "30010", "RPT-10"))
        self.assertEqual(front["draft"], "draft.md")
        self.assertEqual(front["preview_fingerprint"][:12], fingerprint)
        self.assertEqual(front["confirmed_by"], "the participant")
        self.assertEqual(payload, self.record(fingerprint)["payload"])
        self.assertIn("Written to the link file: the key RPT-10 and the issue id 30010.", text)

    def test_the_story_is_read_back_by_id_and_compared_field_for_field(self):
        fingerprint, text = self.created()
        self.assertIn("READ BACK from Jira by issue id 30010, and compared with the payload field for field:", text)
        self.assertEqual(text.count(": the same"), 9)
        self.assertIn("read 2 block(s) of document: the same, identical as sent", text)
        self.assertIn('read "RPT" (id 30000): the same', text)
        self.assertNotIn("Made-up project", text)
        self.assertIn("Result: every field the payload sent reads back the same.", text)
        self.assertEqual(self.linked()[0]["comparison"], "every field the payload sent reads back the same")
        with open(self.link, encoding="utf-8") as f:
            saved = f.read()
        self.assertEqual(saved.count("| the same"), 9)
        self.assertIn(("GET", "/rest/api/3/issue/30010"), self.fake.requests)

    def test_what_jira_set_itself_is_listed_and_people_are_not_shown(self):
        fingerprint, text = self.created()
        with open(self.link, encoding="utf-8") as f:
            saved = f.read()
        for where in (text, saved):
            self.assertIn('"Medium" (id 3)', where)
            self.assertIn('"To Do" (id 1)', where)
            self.assertIn("a person, not shown", where)
            self.assertNotIn("Ada Fixture", where)
            self.assertNotIn("example.invalid", where.replace("https://fixture-site.example.invalid", ""))
            self.assertNotIn(fake_jira.ME, where)

    def test_the_result_record_holds_what_criterion_8_asks_for(self):
        fingerprint = self.previewed()
        out = os.path.join(self.tmp, "results", "create-story.md")
        code, text = self.confirm(fingerprint, result=out)
        with open(out, encoding="utf-8") as f:
            saved = f.read()
        for phrase in ("Issue key: RPT-10", "Identifier of what was created: Jira issue id 30010", "Target project: RPT (project id 30000)",
                       "Created at: 20", "Confirmed by: the participant, at 20", "Preview: fingerprint %s" % fingerprint):
            self.assertIn(phrase, saved)
            self.assertIn(phrase, text)
        self.assertNotIn(HOST, saved)

    def test_the_link_file_says_a_create_is_being_sent_before_it_is_sent(self):
        fingerprint = self.previewed()
        seen = {}
        real = self.fake.post

        def post(path, params=None, body=None):
            seen["front"] = create.read_link(self.link)[0]
            seen["record"] = self.record(fingerprint)["state"]
            return real(path, params, body)
        self.fake.post = post
        self.assertEqual(self.confirm(fingerprint)[0], 0)
        self.assertEqual((seen["front"]["state"], seen["front"]["jira_id"]), (create.SENT, None))
        self.assertEqual(seen["record"], "sending")

    def test_the_key_is_recorded_before_the_read_back_so_a_failed_read_back_loses_nothing(self):
        fingerprint = self.previewed()
        real = self.fake.get

        def get(path, params=None):
            if path == "/rest/api/3/issue/30010":
                raise OSError("down")
            return real(path, params)
        self.fake.get = get
        code, text = self.confirm(fingerprint)
        self.assertEqual(code, 2, text)
        self.assertIn("A PERSON NEEDS TO LOOK: after the create was sent, a read failed", text)
        front, _ = self.linked()
        self.assertEqual((front["state"], front["jira_id"], front["jira_key"]), ("created", "30010", "RPT-10"))
        self.fake.get = real
        code, text = self.run_command("verify")
        self.assertEqual(code, 0, text)


class RecordingTheKeyFails(Case):
    def test_if_the_link_file_cannot_be_written_first_the_create_is_not_sent(self):
        fingerprint = self.previewed()
        with mock.patch.object(create, "write_link", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                self.confirm(fingerprint)
        self.assertEqual(self.posts(), [])
        self.assertEqual(len(self.rpt()), 7)

    def test_if_the_key_cannot_be_written_it_is_printed_and_the_earlier_link_still_stops_the_next_run(self):
        fingerprint = self.previewed()
        real, calls = create.write_link, []

        def write_link(*args, **kwargs):
            calls.append(1)
            if len(calls) > 1:
                raise OSError("disk full")
            return real(*args, **kwargs)
        with mock.patch.object(create, "write_link", side_effect=write_link):
            code, text = self.confirm(fingerprint)
        self.assertEqual(code, 2, text)
        self.assertIn("the story was created as RPT-10 (issue id 30010) and the link file COULD NOT BE WRITTEN", text)
        self.assertEqual(self.linked()[0]["state"], create.SENT)
        self.assertRefused(self.preview(), "a create for this draft was sent and its result was never recorded")
        code, text = self.run_command("reconcile")
        self.assertEqual(code, 0, text)
        self.assertEqual(self.linked()[0]["jira_key"], "RPT-10")
        self.assertEqual(len(self.posts()), 1)


class Refusals(Case):
    def test_a_missing_confirmation_is_refused(self):
        fingerprint = self.previewed()
        self.assertRefused(self.confirm(None), "no confirmation was given")
        self.assertRefused(self.confirm("  "), "no confirmation was given")
        self.assertRefused(self.confirm(fingerprint, name=None), "no confirmation was given")
        self.assertRefused(self.confirm(fingerprint, name=" "), "no confirmation was given")
        self.assertRefused(self.confirm("yes"), "12 characters")
        self.assertRefused(self.confirm("0123456789ab"), "there is no preview with the fingerprint")
        self.assertRefused(self.confirm(fingerprint, name="someone@example.invalid"), "not an email address")
        self.assertNothingCreated()
        self.assertFalse(os.path.exists(self.link))

    def test_a_draft_changed_after_the_preview_is_refused(self):
        fingerprint = self.previewed()
        good = self.text
        for old, new, field in (("Quarterly revenue by plan report for the finance team", "Quarterly revenue by plan report for the sales team", "summary"),
                                ('duedate: "2027-01-15"', 'duedate: "2027-01-14"', "duedate"),
                                ("one sheet per region.", "one sheet per region.\n- Format: a spreadsheet, with one sheet per region.", "description")):
            self.text = good
            self.edit(old, new)
            self.assertRefused(self.confirm(fingerprint), "the change is not the one that was previewed: the payload now differs in %s" % field)
        self.text = good
        self.edit("Priority is left out on purpose.", "Priority is left out deliberately.")
        self.assertRefused(self.confirm(fingerprint), "the draft file has been edited since the preview")
        self.assertNothingCreated()
        self.text = good
        self.write_draft()
        self.assertEqual(self.confirm(fingerprint)[0], 0)

    def test_jira_asking_for_something_new_after_the_preview_is_refused(self):
        fingerprint = self.previewed()
        for field in self.fake.fields["30000"]:
            if field["fieldId"] == "customfield_10016":
                field["required"] = True
        self.assertRefused(self.confirm(fingerprint), '"Story Points" (customfield_10016)')
        self.assertNothingCreated()

    def test_a_preview_older_than_the_limit_is_refused(self):
        fingerprint = self.previewed()
        self.assertRefused(self.confirm(fingerprint, pretend_minutes_later=16), "too old", "the limit is 15")
        self.assertNothingCreated()
        self.assertEqual(self.confirm(fingerprint, pretend_minutes_later=14)[0], 0)

    def test_a_project_not_on_the_allowlist_is_refused(self):
        self.edit('project: "RPT"', 'project: "OPS"')
        code, text, fingerprint = self.preview()
        self.assertRefused((code, text), "project OPS (project id 30100)", "is not on the sandbox allowlist")
        self.assertIsNone(fingerprint)
        self.assertNothingCreated()

    def test_the_allowlist_is_checked_again_at_confirmation(self):
        fingerprint = self.previewed()
        self.allowlist = os.path.join(self.tmp, "empty.json")
        with open(self.allowlist, "w", encoding="utf-8") as f:
            json.dump({"sandbox_projects": []}, f)
        self.assertRefused(self.confirm(fingerprint), "is not on the sandbox allowlist")
        self.assertNothingCreated()

    def test_another_site_is_refused(self):
        fingerprint = self.previewed()
        self.host = "another-site.example.invalid"
        self.assertRefused(self.confirm(fingerprint), "is not on the sandbox allowlist")
        self.assertNothingCreated()

    def test_permission_lost_after_the_preview_is_refused(self):
        fingerprint = self.previewed()
        self.fake.may_create["30000"] = False
        self.assertRefused(self.confirm(fingerprint), "may not create stories in RPT")
        self.assertNothingCreated()

    def test_an_altered_saved_preview_is_refused(self):
        fingerprint = self.previewed()
        path = os.path.join(self.state, "create-story-previews", fingerprint + ".json")
        good = self.record(fingerprint)
        for edit in (lambda r: r["payload"]["fields"].update(summary="Something else"), lambda r: r.update(made_at="2099-01-01 00:00:00 UTC"),
                     lambda r: r.update(marker="gtq-00000000"), lambda r: r["project"].update(id="30100")):
            record = copy.deepcopy(good)
            edit(record)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(record, f)
            self.assertRefused(self.confirm(fingerprint), "has been altered")
        self.assertNothingCreated()

    def test_a_marker_already_in_jira_stops_the_create(self):
        fingerprint = self.previewed()
        self.fake.issues[1]["fields"]["labels"] = [self.record(fingerprint)["marker"]]
        self.assertRefused(self.confirm(fingerprint), "already exists in Jira (issue id 30002)")
        self.assertNothingCreated()


class RunningAgain(Case):
    def test_a_second_run_creates_nothing(self):
        fingerprint, _ = self.created()
        stories = copy.deepcopy(self.fake.issues)
        code, text, again = self.preview()
        self.assertRefused((code, text), "this draft has already been created in Jira as RPT-10 (issue id 30010)", "It is not created twice")
        self.assertIsNone(again)
        code, text = self.confirm(fingerprint)
        self.assertRefused((code, text), "A fingerprint is used once")
        self.assertEqual(self.fake.issues, stories)
        self.assertEqual(len(self.posts()), 1)
        self.assertEqual(len(self.rpt()), 8)

    def test_an_earlier_unused_preview_cannot_make_a_second_story(self):
        first = self.previewed()
        second = self.previewed()
        self.assertEqual(self.confirm(second)[0], 0)
        self.assertRefused(self.confirm(first), "already been created in Jira as RPT-10")
        self.assertEqual(len(self.posts()), 1)

    def test_a_link_file_for_another_draft_is_not_reused(self):
        self.created()
        other = os.path.join(self.tmp, "new-story", "other.md")
        shutil.copy(self.draft, other)
        self.draft = other
        self.assertRefused(self.preview(), "the link file belongs to another draft")

    def test_a_file_at_the_link_path_that_is_not_a_link_is_left_alone(self):
        with open(self.link, "w", encoding="utf-8") as f:
            f.write("# Somebody's notes\n")
        self.assertRefused(self.preview(), "is not a link this workflow wrote")
        with open(self.link, encoding="utf-8") as f:
            self.assertEqual(f.read(), "# Somebody's notes\n")


class WhenTheCreateGoesWrong(Case):
    def test_jira_refusing_creates_nothing_and_removes_the_link(self):
        for status in (400, 401, 403, 404, 422):
            self.fake = fake_jira.FakeJira()
            if os.path.exists(self.state):
                shutil.rmtree(self.state)
            fingerprint = self.previewed()
            self.fake.fail_post = status
            code, text = self.confirm(fingerprint)
            self.assertEqual(code, 1, text)
            self.assertIn("Jira answered %d to the create and made no story" % status, text)
            self.assertFalse(os.path.exists(self.link))
            self.assertEqual(len(self.rpt()), 7)
            self.fake.fail_post = None
            self.assertRefused(self.confirm(fingerprint), "cannot be used")
            self.assertEqual(len(self.posts()), 1, "never sent a second time")
            self.assertEqual(self.preview()[0], 0, "a new preview can be made")

    def test_jira_naming_the_fields_at_fault_is_passed_on(self):
        fingerprint = self.previewed()
        real = self.fake.post
        self.fake.post = lambda path, params=None, body=None: (self.fake.requests.append(("POST", path)), (400, {}, {"errorMessages": [], "errors": {"components": "Components is required."}}))[1]
        code, text = self.confirm(fingerprint)
        self.assertEqual(code, 1)
        self.assertIn("Fields Jira named: components", text)
        self.fake.post = real

    def test_no_answer_means_unknown_no_retry_and_a_link_that_says_so(self):
        fingerprint = self.previewed()
        self.fake.fail_post = "timeout"
        code, text = self.confirm(fingerprint)
        self.assertEqual(code, 2, text)
        self.assertIn("NOT KNOWN whether Jira created the story. It was not sent again", text)
        self.assertNotIn("Nothing has been written", text)
        self.assertEqual(len(self.posts()), 1)
        front, _ = self.linked()
        self.assertEqual((front["state"], front["jira_id"]), (create.SENT, None))
        with open(self.link, encoding="utf-8") as f:
            self.assertIn("A create was sent to Jira and its result has not been recorded.", f.read())
        self.fake.fail_post = None
        self.assertRefused(self.preview(), "a create for this draft was sent and its result was never recorded", "reconcile")
        self.assertRefused(self.confirm(fingerprint), "cannot be used again")
        self.assertEqual(len(self.posts()), 1)

    def test_reconcile_after_a_lost_answer_finds_the_story_by_its_marker_and_links_it(self):
        fingerprint = self.previewed()
        self.fake.fail_post = "applied-timeout"
        self.assertEqual(self.confirm(fingerprint)[0], 2)
        self.fake.fail_post = None
        self.assertEqual(len(self.rpt()), 8, "the story exists, and the workflow does not know its key")
        code, text = self.run_command("reconcile")
        self.assertEqual(code, 0, text)
        self.assertIn("FOUND exactly one: RPT-10, issue id 30010. It is linked now.", text)
        self.assertIn("Result: every field the payload sent reads back the same.", text)
        front, _ = self.linked()
        self.assertEqual((front["state"], front["jira_id"], front["jira_key"]), ("created", "30010", "RPT-10"))
        self.assertEqual(self.record(fingerprint)["state"], "written")
        self.assertEqual(len(self.posts()), 1)
        self.assertEqual(len(self.rpt()), 8)
        self.assertRefused(self.preview(), "already been created in Jira as RPT-10")
        self.assertRefused(self.run_command("reconcile"), "There is nothing to reconcile")

    def test_reconcile_when_nothing_was_created_says_not_found_and_creates_nothing(self):
        fingerprint = self.previewed()
        self.fake.fail_post = "timeout"
        self.confirm(fingerprint)
        self.fake.fail_post = None
        code, text = self.run_command("reconcile")
        self.assertEqual(code, 1, text)
        self.assertIn("NOT FOUND.", text)
        self.assertIn("Jira's search can lag", text)
        self.assertEqual(self.linked()[0]["state"], create.SENT)
        self.assertEqual(len(self.posts()), 1)
        self.assertEqual(len(self.rpt()), 7)

    def test_reconcile_copes_with_a_search_that_lags(self):
        fingerprint = self.previewed()
        self.fake.fail_post = "applied-timeout"
        self.confirm(fingerprint)
        self.fake.fail_post = None
        self.fake.search_lag = 1
        self.assertEqual(self.run_command("reconcile")[0], 1)
        self.assertEqual(self.run_command("reconcile")[0], 0)
        self.assertEqual(len(self.rpt()), 8)

    def test_reconcile_links_nothing_when_two_stories_carry_the_marker(self):
        fingerprint = self.previewed()
        self.fake.fail_post = "applied-timeout"
        self.confirm(fingerprint)
        self.fake.issues[1]["fields"]["labels"] = [self.record(fingerprint)["marker"]]
        self.assertRefused(self.run_command("reconcile"), "2 stories carry the marker")
        self.assertEqual(self.linked()[0]["state"], create.SENT)

    def test_an_unclear_answer_from_jira_is_not_treated_as_a_refusal(self):
        fingerprint = self.previewed()
        self.fake.fail_post = 500
        code, text = self.confirm(fingerprint)
        self.assertEqual(code, 2, text)
        self.assertIn("it is not certain that no story was made", text)
        self.assertEqual(self.linked()[0]["state"], create.SENT)

    def test_a_refusal_from_jira_that_nevertheless_made_a_story_is_not_called_nothing(self):
        fingerprint = self.previewed()
        real = self.fake.post

        def post(path, params=None, body=None):
            real(path, params, body)
            return 400, {}, {"errorMessages": ["confused"], "errors": {}}
        self.fake.post = post
        code, text = self.confirm(fingerprint)
        self.assertEqual(code, 2, text)
        self.assertTrue(os.path.exists(self.link))


class Compare(Case):
    def test_jiras_own_bookkeeping_in_the_description_is_not_a_difference_and_is_said(self):
        self.fake.decorate = True
        fingerprint, text = self.created()
        self.assertIn("the same text and structure; Jira's copy also holds its own block identifiers", text)
        self.assertIn("Result: every field the payload sent reads back the same.", text)

    def test_a_story_stored_differently_from_what_was_sent_is_reported(self):
        for name, corrupt in (("summary", lambda f: f.update(summary="Quarterly revenue report")),
                              ("labels", lambda f: f.update(labels=["reporting"])),
                              ("duedate", lambda f: f.update(duedate=None)),
                              ("components", lambda f: f.update(components=[{"id": "31002", "name": "Billing"}])),
                              ("customfield_10050", lambda f: f.update(customfield_10050={"id": "32003", "value": "Support"})),
                              ("parent", lambda f: f.update(parent=None)),
                              ("description", lambda f: f["description"]["content"][0]["content"][0].update(text="Something else."))):
            self.fake = fake_jira.FakeJira()
            for path in (self.state, self.link):
                if os.path.isdir(path):
                    shutil.rmtree(path)
                elif os.path.exists(path):
                    os.remove(path)
            self.fake.corrupt = corrupt
            fingerprint = self.previewed()
            code, text = self.confirm(fingerprint)
            self.assertEqual(code, 2, name)
            self.assertIn("Result: NOT ALL THE SAME: %s." % name, text)
            self.assertIn("does not read back as it was sent", text)
            front, _ = self.linked()
            self.assertEqual((front["jira_key"], front["comparison"]), ("RPT-10", "NOT ALL THE SAME: %s" % name))

    def test_plain_keeps_structure_and_text_and_drops_bookkeeping(self):
        a = {"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "x"}]}]}
        b = {"type": "doc", "version": 1, "content": [{"type": "paragraph", "attrs": {"localId": "1"}, "content": [{"type": "text", "text": "x"}]}]}
        c = {"type": "doc", "version": 1, "content": [{"type": "paragraph", "content": [{"type": "text", "text": "x", "marks": [{"type": "strong"}]}]}]}
        self.assertEqual(create.plain(a), create.plain(b))
        self.assertNotEqual(create.plain(a), create.plain(c))


class Verify(Case):
    def test_verify_matches_by_id_and_compares_again(self):
        self.created()
        code, text = self.run_command("verify")
        self.assertEqual(code, 0, text)
        self.assertIn("Matched to Jira by issue id 30010: found.", text)
        self.assertIn("The key in Jira is RPT-10, as the link file records.", text)
        self.assertIn("Result: every field the payload sent reads back the same.", text)
        self.assertEqual(set(method for method, _ in self.conn.sent), {"GET"})
        self.assertIn("exactly one story carries it, and it is this one", text)

    def test_verify_says_when_the_marker_no_longer_leads_to_the_story(self):
        self.created()
        self.fake.find("30010")["fields"]["labels"] = ["reporting", "revenue"]
        code, text = self.run_command("verify")
        self.assertIn("0 stories found. The marker does NOT lead to this story alone.", text)
        self.assertIn("Result: NOT ALL THE SAME: labels.", text)

    def test_a_changed_key_is_matched_by_id_and_recorded(self):
        self.created()
        self.fake.find("30010")["key"] = "OPS-77"
        code, text = self.run_command("verify")
        self.assertEqual(code, 0, text)
        self.assertIn("The key has CHANGED in Jira: the link file recorded RPT-10 and the story is now OPS-77.", text)
        front, _ = self.linked()
        self.assertEqual((front["jira_id"], front["jira_key"], front["earlier_keys"]), ("30010", "OPS-77", ["RPT-10"]))

    def test_a_story_changed_in_jira_since_is_reported(self):
        self.created()
        self.fake.find("30010")["fields"]["summary"] = "Edited by someone"
        code, text = self.run_command("verify")
        self.assertEqual(code, 2, text)
        self.assertIn("Result: NOT ALL THE SAME: summary.", text)
        self.assertNotIn("Edited by someone", text.replace('read "Edited by someone"', ""))

    def test_a_deleted_story_or_no_link_or_another_site_is_refused(self):
        self.assertRefused(self.run_command("verify"), "there is no link file")
        self.created()
        self.host = "another-site.example.invalid"
        self.assertRefused(self.run_command("verify"), "not the Jira site the link file was made against")
        self.host = HOST
        self.fake.issues = [item for item in self.fake.issues if item["id"] != "30010"]
        self.assertRefused(self.run_command("verify"), "Jira answered 404 for issue id 30010")
        self.assertEqual(self.linked()[0]["jira_id"], "30010")


class CommandLine(Case):
    def run_main(self, command, *argv):
        out = io.StringIO()
        base = [command, "--source", "fake", "--link", self.link, "--state", self.state]
        if command in ("preview", "confirm"):
            base += ["--draft", self.draft, "--allowlist", self.allowlist, "--catalog", os.path.join(self.tmp, "catalog"), "--today", "2026-11-19"]
        with contextlib.redirect_stdout(out):
            code = create.main(base + list(argv))
        return code, out.getvalue()

    def test_preview_confirm_rerun_and_verify_through_the_command_line(self):
        log = os.path.join(self.tmp, "log.txt")
        code, text = self.run_main("preview", "--log", log)
        self.assertEqual(code, 0, text)
        fingerprint = re.findall(r"^Fingerprint of this preview: ([0-9a-f]{12})$", text, re.M)[0]
        with open(log, encoding="utf-8") as f:
            saved = f.read()
        self.assertNotIn(HOST, saved)
        self.assertIn("Jira site:   [site address removed]", saved)
        self.assertIn(HOST, text)
        code, text = self.run_main("confirm")
        self.assertEqual(code, 1)
        self.assertIn("no confirmation was given", text)
        code, text = self.run_main("confirm", "--fingerprint", fingerprint, "--confirmed-by", "the participant")
        self.assertEqual(code, 0, text)
        self.assertIn("RPT-10", text)
        code, text = self.run_main("preview")
        self.assertEqual(code, 1)
        self.assertIn("It is not created twice", text)
        code, text = self.run_main("verify")
        self.assertEqual(code, 0, text)

    def test_there_is_no_option_that_skips_the_confirmation(self):
        for flag in ("--yes", "--force", "--no-preview", "--skip-confirm", "--retry"):
            with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
                self.run_main("confirm", flag)

    def test_the_test_clock_only_goes_forward(self):
        for value in ("-5", "1.5", "soon"):
            with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
                self.run_main("confirm", "--pretend-minutes-later=%s" % value)

    def test_output_holding_a_credential_is_not_shown_or_saved(self):
        log = os.path.join(self.tmp, "log.txt")
        conn = create.Connection(self.fake.get, None, HOST)
        out = io.StringIO()
        with mock.patch.object(create, "make_live", return_value=(conn, ["Quarterly revenue"])), contextlib.redirect_stdout(out):
            code = create.main(["preview", "--source", "live", "--link", self.link, "--state", self.state, "--draft", self.draft,
                                "--allowlist", self.allowlist, "--catalog", os.path.join(self.tmp, "catalog"), "--log", log])
        self.assertEqual(code, 1)
        self.assertEqual(out.getvalue().strip(), "STOPPED: a credential was found in the output, so the output was not shown or saved.")
        self.assertFalse(os.path.exists(log))

    def test_a_live_connection_writes_only_one_kind_of_request_and_a_preview_none(self):
        good = {"JIRA_BASE_URL": "https://unit-test.example.invalid", "JIRA_EMAIL": "e", "JIRA_API_TOKEN": "t"}
        with mock.patch.dict(os.environ, good, clear=True):
            reader, _ = create.make_live(False)
            writer, _ = create.make_live(True)
        self.assertIsNone(reader._post)
        for path, params, body in (("/rest/api/3/issue/30001", None, b"{}"), ("/rest/api/3/issue/bulk", None, b"{}"),
                                   ("/rest/api/3/issue", {"updateHistory": "true"}, b"{}"), ("/rest/api/3/issue", None, "{}"),
                                   ("/rest/api/3/issue/30001/transitions", None, b"{}")):
            with self.assertRaises(create.Refused):
                writer._post(path, params, body)
        for name in good:
            with mock.patch.dict(os.environ, {k: v for k, v in good.items() if k != name}, clear=True):
                with self.assertRaises(create.Refused):
                    create.make_live(True)

    def test_one_run_sends_at_most_one_create(self):
        conn = create.Connection(self.fake.get, self.fake.post, HOST)
        conn.create(b'{"fields": {}}')
        with self.assertRaises(create.Refused):
            conn.create(b'{"fields": {}}')
        self.assertEqual(len(self.posts()), 1)


if __name__ == "__main__":
    unittest.main()
