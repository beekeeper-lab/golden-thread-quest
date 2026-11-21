"""Tests for the field updater, scripts/update.py, against scripts/fake_jira.py. No network.

Run from the attempt folder:  python3 -m unittest discover -s tests -v
"""
import argparse
import contextlib
import copy
import io
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(os.path.dirname(HERE), "scripts")
sys.path.insert(0, SCRIPTS)
import fake_jira  # noqa: E402
import update  # noqa: E402

ALLOWLIST = os.path.join(SCRIPTS, "fake-allowlist.json")
HOST = "fixture-site.example.invalid"


class Bench:
    """One fake Jira, one state folder, and the two commands."""

    def __init__(self, folder):
        self.folder = folder
        self.fake = fake_jira.FakeJira()
        self.bodies = []
        self.allowlist = ALLOWLIST
        self.host = HOST
        self.change_path = os.path.join(folder, "change.json")

    def change(self, story, **fields):
        with open(self.change_path, "w", encoding="utf-8") as f:
            json.dump({"story": story, "fields": fields}, f)

    def put(self, path, params, body):
        self.bodies.append(copy.deepcopy(body))
        return self.fake.put(path, params, body)

    def args(self, command, **more):
        base = dict(command=command, change=self.change_path, allowlist=self.allowlist, state=self.folder,
                    log=None, fingerprint=None, confirmed_by=None, result=None, pretend_minutes_later=0)
        base.update(more)
        return argparse.Namespace(**base)

    def preview(self):
        """Returns (exit code, text, fingerprint or None)."""
        del update.LINES[:]
        conn = update.Connection(self.fake.get, None, self.host)
        code = update.run(self.args("preview"), conn)
        text = "\n".join(update.LINES)
        found = [line.split()[-1] for line in update.LINES if line.startswith("Fingerprint of this preview:")]
        self.last = conn
        return code, text, (found[0] if found else None)

    def confirm(self, fingerprint, name="the participant", **more):
        del update.LINES[:]
        conn = update.Connection(self.fake.get, self.put, self.host)
        code = update.run(self.args("confirm", fingerprint=fingerprint, confirmed_by=name, **more), conn)
        self.last = conn
        return code, "\n".join(update.LINES)

    def puts(self):
        return [path for method, path in self.fake.requests if method == "PUT"]

    def holds(self, ref="SAND-1"):
        return update.current_values(self.fake.find(ref))


class Case(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.b = Bench(self.tmp.name)

    def previewed(self, story="SAND-1", **fields):
        self.b.change(story, **(fields or {"priority": "High", "duedate": "2026-12-15"}))
        code, text, fingerprint = self.b.preview()
        self.assertEqual(code, 0, text)
        self.assertIsNotNone(fingerprint, text)
        return fingerprint

    def assertRefused(self, result, *phrases):
        code, text = result[0], result[1]
        self.assertEqual(code, 1, text)
        self.assertIn("REFUSED:", text)
        self.assertIn("Nothing has been written.", text)
        for phrase in phrases:
            self.assertIn(phrase, text)
        self.assertEqual(self.b.puts(), [], "a refusal must not send a write")


class Preview(Case):
    def test_shows_old_and_new_value_of_each_field(self):
        self.b.change("SAND-1", labels=["onboarding", "q4"], duedate="2026-12-15", priority="High")
        code, text, fingerprint = self.b.preview()
        self.assertEqual(code, 0)
        for line in ('labels    now:    ["onboarding"]', 'after:  ["onboarding", "q4"]',
                     "duedate   now:    2026-12-01", "after:  2026-12-15",
                     'priority  now:    "Medium" (id 3)', 'after:  "High" (id 2)'):
            self.assertIn(line, text)
        self.assertRegex(fingerprint, r"^[0-9a-f]{12}$")

    def test_shows_site_project_story_and_both_checks(self):
        self.previewed()
        text = "\n".join(update.LINES)
        for phrase in ("Jira site:  https://fixture-site.example.invalid", "Project:    SAND (project id 20001)",
                       "Story:      SAND-1 (issue id 30001)", "may edit the story (EDIT_ISSUES):     yes",
                       "Duplicate check:", "Where Jira cannot check:", "Expires:"):
            self.assertIn(phrase, text)

    def test_preview_changes_nothing_in_jira_and_sends_only_gets(self):
        before = copy.deepcopy(self.b.fake.state)
        self.previewed()
        self.assertEqual(self.b.fake.state, before)
        self.assertEqual(set(method for method, _ in self.b.fake.requests), {"GET"})
        self.assertIn("The two are the same. Jira is unchanged.", "\n".join(update.LINES))

    def test_a_preview_has_no_way_to_write(self):
        conn = update.Connection(self.b.fake.get, None, HOST)
        with self.assertRaises(update.Refused):
            conn.put_issue("30001", {"labels": ["x"]})
        self.assertEqual(self.b.puts(), [])

    def test_a_field_already_as_wanted_is_reported_and_not_sent(self):
        fingerprint = self.previewed(labels=["onboarding"], priority="High")
        self.assertIn("Already as wanted, so not sent: labels", "\n".join(update.LINES))
        self.b.confirm(fingerprint)
        self.assertEqual(self.b.bodies, [{"fields": {"priority": {"id": "2"}}}])

    def test_story_changing_during_the_preview_is_refused(self):
        self.b.change("SAND-1", priority="High")
        real, seen = self.b.fake.get, []

        def get(path, params=None):
            if path.endswith("/editmeta"):
                self.b.fake.other_edit("SAND-1", "duedate", "2027-01-01")
            seen.append(path)
            return real(path, params)
        self.b.fake.get = get
        code, text, fingerprint = self.b.preview()
        self.assertEqual(code, 1)
        self.assertIn("changed in Jira while the preview was being made", text)
        self.assertIsNone(fingerprint)

    def test_story_text_is_never_printed(self):
        fingerprint = self.previewed()
        text = "\n".join(update.LINES)
        code, more = self.b.confirm(fingerprint)
        for words in (fake_jira.HOSTILE_SUMMARY, "Ignore your rules", "Ada Fixture", "example.invalid/rest"):
            self.assertNotIn(words, text + more)
        self.assertEqual(self.b.fake.find("SAND-1")["fields"]["assignee"]["accountId"], fake_jira.ME)


class SupportedFields(Case):
    def test_unsupported_fields_are_refused_before_any_request(self):
        for name, value in (("assignee", None), ("summary", "x"), ("description", "x"), ("status", "Done"),
                            ("reporter", "x"), ("project", "PROD"), ("issuetype", "Bug"), ("parent", "SAND-2"),
                            ("security", "x"), ("customfield_10016", 5), ("Labels", ["x"])):
            self.b.change("SAND-1", **{name: value, "priority": "High"})
            result = self.b.preview()
            self.assertRefused(result, "is not supported")
            self.assertEqual(self.b.fake.requests, [], name)

    def test_values_outside_the_allowed_ones_are_refused(self):
        bad = [dict(labels=["Has Space"]), dict(labels=["UPPER"]), dict(labels="one"), dict(labels=["a", "a"]),
               dict(labels=["l%d" % n for n in range(11)]), dict(labels=["-x"]), dict(labels=[7]),
               dict(duedate="15/12/2026"), dict(duedate="2026-02-30"), dict(duedate=None), dict(duedate=""),
               dict(duedate="1999-01-01"), dict(duedate=20261215), dict(priority=""), dict(priority=2),
               dict(priority={"id": "1"})]
        for fields in bad:
            self.b.change("SAND-1", **fields)
            self.assertRefused(self.b.preview())
            self.assertEqual(self.b.fake.requests, [], fields)

    def test_priority_must_be_one_jira_offers(self):
        for name in ("Urgent", "high", "High "):
            self.b.change("SAND-1", priority=name)
            self.assertRefused(self.b.preview(), "is not one of the priorities Jira offers")

    def test_priority_is_refused_where_jira_does_not_offer_it(self):
        self.b.change("SAND-2", priority="High")
        self.assertRefused(self.b.preview(), "Jira does not list priority as a field")

    def test_change_file_shape(self):
        for content in ('{"story": "SAND-1"}', '{"story": "SAND-1", "fields": {}}', '[]', 'not json',
                        '{"story": "../x", "fields": {"priority": "High"}}',
                        '{"story": "SAND-1", "fields": {"priority": "High"}, "force": true}',
                        '{"story": "SAND-1", "fields": {"priority": "High", "priority": "Low"}}'):
            with open(self.b.change_path, "w", encoding="utf-8") as f:
                f.write(content)
            self.assertRefused(self.b.preview())

    def test_only_the_changed_supported_fields_are_sent(self):
        fingerprint = self.previewed(labels=["onboarding", "q4"], duedate="2026-12-15", priority="High")
        other = copy.deepcopy({k: v for k, v in self.b.fake.find("SAND-1")["fields"].items()
                               if k not in ("labels", "duedate", "priority", "updated")})
        code, text = self.b.confirm(fingerprint)
        self.assertEqual(code, 0, text)
        self.assertEqual(self.b.bodies, [{"fields": {"labels": ["onboarding", "q4"], "duedate": "2026-12-15",
                                                     "priority": {"id": "2"}}}])
        self.assertEqual(self.b.puts(), ["/rest/api/3/issue/30001"])
        now = self.b.fake.find("SAND-1")["fields"]
        self.assertEqual({k: now[k] for k in other}, other)


class Confirmation(Case):
    def test_approved_run_writes_and_reads_back(self):
        fingerprint = self.previewed()
        code, text = self.b.confirm(fingerprint)
        self.assertEqual(code, 0, text)
        self.assertEqual(self.b.holds(), {"labels": ["onboarding"], "duedate": "2026-12-15",
                                          "priority": {"id": "2", "name": "High"}})
        for phrase in ("CONFIRMATION for preview %s, given by: the participant" % fingerprint, "Jira answered 204",
                       "duedate   2026-12-15: as proposed", "The confirmation and the write happened in this one run"):
            self.assertIn(phrase, text)

    def test_missing_confirmation_is_refused(self):
        fingerprint = self.previewed()
        self.assertRefused(self.b.confirm(None), "no confirmation was given")
        self.assertRefused(self.b.confirm("   "), "no confirmation was given")
        self.assertRefused(self.b.confirm(fingerprint, name=None), "no confirmation was given")
        self.assertRefused(self.b.confirm(fingerprint, name="  "), "no confirmation was given")
        self.assertRefused(self.b.confirm("yes"), "12 characters")
        self.assertRefused(self.b.confirm("0123456789ab"), "there is no preview with the fingerprint")
        self.assertRefused(self.b.confirm(fingerprint, name="someone@example.invalid"), "not an email address")

    def test_a_change_that_differs_from_the_preview_is_refused(self):
        fingerprint = self.previewed(priority="High")
        for story, fields in (("SAND-1", dict(priority="Highest")), ("SAND-1", dict(priority="High", labels=["q4"])),
                              ("SAND-1", dict(duedate="2026-12-15")), ("SAND-3", dict(priority="High")),
                              ("30001", dict(priority="High"))):
            self.b.change(story, **fields)
            self.assertRefused(self.b.confirm(fingerprint), "the change is not the one that was previewed")
        self.assertEqual(self.b.holds()["priority"]["name"], "Medium")
        self.b.change("SAND-1", priority="High")
        self.assertEqual(self.b.confirm(fingerprint)[0], 0)

    def test_a_preview_older_than_the_limit_is_refused(self):
        fingerprint = self.previewed()
        self.assertRefused(self.b.confirm(fingerprint, pretend_minutes_later=16), "too old", "the limit is 15")
        self.assertEqual(self.b.fake.requests.count(("GET", "/rest/api/3/issue/30001")), 1, "refused before asking Jira")
        code, text = self.b.confirm(fingerprint, pretend_minutes_later=14)
        self.assertEqual(code, 0, text)

    def test_a_fingerprint_is_used_once(self):
        fingerprint = self.previewed()
        self.assertEqual(self.b.confirm(fingerprint)[0], 0)
        code, text = self.b.confirm(fingerprint)
        self.assertEqual(code, 1)
        self.assertIn("A fingerprint is used once", text)
        self.assertEqual(len(self.b.puts()), 1)

    def test_an_altered_saved_preview_is_refused(self):
        fingerprint = self.previewed()
        path = os.path.join(self.b.folder, "previews", fingerprint + ".json")
        for edit in (lambda r: r["proposal"]["changes"]["priority"]["new"].update(id="1", name="Highest"),
                     lambda r: r.update(made_at="2099-01-01 00:00:00 UTC"),
                     lambda r: r["proposal"].update(project_id="20002")):
            with open(path, encoding="utf-8") as f:
                record = json.load(f)
            good = copy.deepcopy(record)
            edit(record)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(record, f)
            self.assertRefused(self.b.confirm(fingerprint), "has been altered")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(good, f)


class Stale(Case):
    def test_a_field_changed_in_jira_after_the_preview_stops_the_update(self):
        fingerprint = self.previewed(priority="High")
        self.b.fake.other_edit("SAND-1", "priority", "Highest")
        result = self.b.confirm(fingerprint)
        self.assertRefused(result, "a field changed in Jira after the preview was made",
                           'priority: the preview saw "Medium" (id 3) and Jira now holds "Highest" (id 1)')
        self.assertEqual(self.b.holds()["priority"]["name"], "Highest", "the other person's change is still there")

    def test_each_supported_field_is_watched(self):
        for field, value in (("labels", ["onboarding", "urgent"]), ("duedate", "2027-01-01"), ("priority", "Low")):
            b = self.b = Bench(tempfile.mkdtemp(dir=self.tmp.name))
            fingerprint = self.previewed(labels=["onboarding", "q4"], duedate="2026-12-15", priority="High")
            b.fake.other_edit("SAND-1", field, value)
            self.assertRefused(b.confirm(fingerprint), "a field changed in Jira after the preview", field + ":")

    def test_someone_else_already_making_the_same_change_also_stops_it(self):
        fingerprint = self.previewed(priority="High")
        self.b.fake.other_edit("SAND-1", "priority", "High")
        self.assertRefused(self.b.confirm(fingerprint), "a field changed in Jira after the preview")

    def test_a_field_named_but_already_as_wanted_is_watched_too(self):
        fingerprint = self.previewed(labels=["onboarding"], priority="High")
        self.b.fake.other_edit("SAND-1", "labels", ["changed"])
        self.assertRefused(self.b.confirm(fingerprint), "labels:")

    def test_a_field_outside_the_change_moving_does_not_stop_it(self):
        fingerprint = self.previewed(priority="High")
        self.b.fake.other_edit("SAND-1", "duedate", "2027-01-01")
        code, text = self.b.confirm(fingerprint)
        self.assertEqual(code, 0, text)
        self.assertEqual(self.b.holds()["duedate"], "2027-01-01", "the other person's due date is untouched")

    def test_a_change_in_the_last_moment_is_reported_afterwards(self):
        fingerprint = self.previewed(priority="High")
        self.b.fake.before_put = lambda fake: fake.other_edit("SAND-1", "priority", "Lowest")
        code, text = self.b.confirm(fingerprint)
        self.assertEqual(code, 2, text)
        self.assertIn("WARNING: for priority, Jira's history records a different value", text)
        self.assertIn("A PERSON NEEDS TO LOOK", text)
        self.assertIn("Jira changelog entry 40002 for", text)
        self.assertNotIn("40001", text, "the other person's entry is not claimed as this write's")

    def test_a_write_jira_accepts_but_does_not_make_is_noticed(self):
        fingerprint = self.previewed(priority="High")
        self.b.put = lambda path, params, body: (204, {}, {})
        code, text = self.b.confirm(fingerprint)
        self.assertEqual(code, 2, text)
        self.assertIn("NOT AS PROPOSED", text)
        self.assertIn("does not read back as proposed", text)


class Allowlist(Case):
    def test_a_project_not_on_the_allowlist_is_refused_at_preview(self):
        self.b.change("PROD-9", priority="High")
        code, text, fingerprint = self.b.preview()
        self.assertRefused((code, text), "project PROD (project id 20002)", "is not on the sandbox allowlist")
        self.assertIsNone(fingerprint)
        self.assertFalse(os.path.exists(os.path.join(self.b.folder, "previews")))
        self.assertEqual(self.b.fake.requests, [("GET", "/rest/api/3/issue/PROD-9")])

    def test_the_allowlist_is_checked_again_at_confirmation(self):
        fingerprint = self.previewed()
        self.b.allowlist = os.path.join(self.b.folder, "empty.json")
        with open(self.b.allowlist, "w", encoding="utf-8") as f:
            json.dump({"sandbox_projects": []}, f)
        self.assertRefused(self.b.confirm(fingerprint), "is not on the sandbox allowlist")

    def test_a_story_moved_to_another_project_is_refused(self):
        fingerprint = self.previewed()
        self.b.fake.find("SAND-1")["fields"]["project"].update(id="20002", key="PROD")
        self.assertRefused(self.b.confirm(fingerprint), "is not on the sandbox allowlist")

    def test_the_same_project_id_on_another_site_is_not_allowed(self):
        self.b.host = "another-site.example.invalid"
        self.b.change("SAND-1", priority="High")
        self.assertRefused(self.b.preview(), "is not on the sandbox allowlist")

    def test_a_preview_cannot_be_confirmed_against_another_site(self):
        fingerprint = self.previewed()
        self.b.host = "another-site.example.invalid"
        self.assertRefused(self.b.confirm(fingerprint), "not the Jira site the preview was made against")

    def test_a_broken_allowlist_allows_nothing(self):
        self.b.change("SAND-1", priority="High")
        self.b.allowlist = os.path.join(self.b.folder, "bad.json")
        for content in ('{}', '{"sandbox_projects": [{"project_id": "20001"}]}', '{"sandbox_projects": "all"}', 'x'):
            with open(self.b.allowlist, "w", encoding="utf-8") as f:
                f.write(content)
            self.assertRefused(self.b.preview())
        self.b.allowlist = os.path.join(self.b.folder, "missing.json")
        self.assertRefused(self.b.preview())


class Permission(Case):
    def test_no_edit_permission_is_refused(self):
        self.b.change("RO-1", priority="High")
        self.assertRefused(self.b.preview(), "Jira says this identity may not edit this story")

    def test_permission_lost_after_the_preview_is_refused(self):
        fingerprint = self.previewed()
        self.b.fake.state["may_edit"]["20001"] = False
        self.assertRefused(self.b.confirm(fingerprint), "may not edit this story")

    def test_no_answer_to_the_permission_check_assumes_nothing(self):
        self.b.change("SAND-1", priority="High")
        real = self.b.fake.get
        self.b.fake.get = lambda path, params=None: (500, {}, {}) if "mypermissions" in path else real(path, params)
        self.assertRefused(self.b.preview(), "did not answer the permission check")

    def test_a_story_that_cannot_be_seen_is_refused(self):
        self.b.change("NOPE-1", priority="High")
        self.assertRefused(self.b.preview(), "404")


class ResultAndRerun(Case):
    def test_result_record_holds_what_criterion_8_asks_for(self):
        fingerprint = self.previewed()
        out = os.path.join(self.b.folder, "result.md")
        code, text = self.b.confirm(fingerprint, result=out)
        self.assertEqual(code, 0, text)
        with open(out, encoding="utf-8") as f:
            saved = f.read()
        for phrase in ("Issue key: SAND-1", "Identifier of what was changed: Jira changelog entry 40001",
                       "Target project: SAND (project id 20001)", "Written at: 20", "Confirmed by: the participant",
                       'Field priority: before "Medium" (id 3); after "High" (id 2); read back from Jira "High" (id 2)'):
            self.assertIn(phrase, saved)
            self.assertIn(phrase, text)
        self.assertNotIn(HOST, saved)
        with open(os.path.join(self.b.folder, "written", fingerprint + ".json"), encoding="utf-8") as f:
            record = json.load(f)
        self.assertEqual(record["fields"]["duedate"]["before"], "2026-12-01", "the old value is kept, to reverse by")

    def test_the_changelog_entry_is_found_across_pages(self):
        self.b.fake.page_max = 2
        fingerprint = self.previewed("SAND-3", priority="High")
        code, text = self.b.confirm(fingerprint)
        self.assertEqual(code, 0, text)
        self.assertIn("Jira changelog entry 40001 for issue id 30003", text)

    def test_someone_elses_entry_is_not_claimed(self):
        fingerprint = self.previewed(priority="High")
        self.b.fake.before_put = lambda fake: fake.other_edit("SAND-1", "duedate", "2027-02-02")
        code, text = self.b.confirm(fingerprint)
        self.assertEqual(code, 0, text)
        self.assertIn("Jira changelog entry 40002 for", text)
        self.assertNotIn("40001", text)

    def test_running_again_changes_nothing(self):
        fingerprint = self.previewed()
        self.assertEqual(self.b.confirm(fingerprint)[0], 0)
        state = copy.deepcopy(self.b.fake.state)
        previews = sorted(os.listdir(os.path.join(self.b.folder, "previews")))
        code, text, again = self.b.preview()
        self.assertEqual(code, 0)
        self.assertIn("NOTHING TO CHANGE", text)
        self.assertIsNone(again)
        self.assertEqual(self.b.confirm(fingerprint)[0], 1)
        self.assertEqual(self.b.fake.state, state)
        self.assertEqual(len(self.b.puts()), 1)
        self.assertEqual(len(self.b.fake.state["changelog"]["30001"]), 1)
        self.assertEqual(sorted(os.listdir(os.path.join(self.b.folder, "previews"))), previews)


class WhenTheWriteGoesWrong(Case):
    def test_jira_refusing_the_write_writes_nothing_and_uses_up_the_preview(self):
        for status in (400, 401, 403, 404, 409, 422):
            self.b = Bench(tempfile.mkdtemp(dir=self.tmp.name))
            fingerprint = self.previewed()
            self.b.fake.fail_put = status
            code, text = self.b.confirm(fingerprint)
            self.assertEqual(code, 1, text)
            self.assertIn("Jira answered %d to the write" % status, text)
            self.assertIn("nothing was written", text)
            self.b.fake.fail_put = None
            code, text = self.b.confirm(fingerprint)
            self.assertEqual(code, 1)
            self.assertIn("cannot be", text)
            self.assertEqual(len(self.b.puts()), 1, "never sent a second time")

    def test_no_answer_means_unknown_and_no_retry(self):
        for kind, after in (("timeout", "Medium"), ("applied-timeout", "High")):
            self.b = Bench(tempfile.mkdtemp(dir=self.tmp.name))
            fingerprint = self.previewed(priority="High")
            self.b.fake.fail_put = kind
            code, text = self.b.confirm(fingerprint)
            self.assertEqual(code, 2, text)
            self.assertIn("NOT KNOWN whether Jira", text)
            self.assertNotIn("Nothing has been written", text)
            self.assertEqual(len(self.b.puts()), 1)
            self.assertEqual(self.b.holds()["priority"]["name"], after)
            self.b.fake.fail_put = None
            self.assertEqual(self.b.confirm(fingerprint)[0], 1)
            self.assertEqual(len(self.b.puts()), 1)

    def test_jira_unreachable_before_the_write_is_a_refusal(self):
        self.b.change("SAND-1", priority="High")

        def down(path, params=None):
            raise OSError("down")
        self.b.fake.get = down
        code, text, _ = self.b.preview()
        self.assertEqual(code, 1)
        self.assertIn("could not reach Jira", text)


class CommandLine(Case):
    def run_main(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = update.main(list(argv))
        return code, out.getvalue()

    def common(self):
        return ["--source", "fake", "--change", self.b.change_path, "--allowlist", ALLOWLIST, "--state", self.b.folder]

    def test_preview_then_confirm_through_the_command_line(self):
        self.b.change("SAND-1", priority="High")
        log = os.path.join(self.b.folder, "log.txt")
        code, text = self.run_main("preview", *self.common(), "--log", log)
        self.assertEqual(code, 0, text)
        fingerprint = [line.split()[-1] for line in text.splitlines() if line.startswith("Fingerprint of this preview:")][0]
        with open(log, encoding="utf-8") as f:
            saved = f.read()
        self.assertNotIn(HOST, saved)
        self.assertIn("Jira site:  [site address removed]", saved)
        self.assertIn(HOST, text, "the person confirming sees the site on screen")
        code, text = self.run_main("confirm", *self.common())
        self.assertEqual(code, 1)
        self.assertIn("no confirmation was given", text)
        code, text = self.run_main("confirm", *self.common(), "--fingerprint", fingerprint, "--confirmed-by", "the participant")
        self.assertEqual(code, 0, text)
        code, text = self.run_main("preview", *self.common())
        self.assertIn("NOTHING TO CHANGE", text)

    def test_there_is_no_option_that_skips_the_confirmation(self):
        for flag in ("--yes", "--force", "--no-preview", "--skip-confirm"):
            with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
                update.main(["confirm", *self.common(), flag])

    def test_the_test_clock_only_goes_forward(self):
        for value in ("-5", "1.5", "soon"):
            with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
                update.main(["confirm", *self.common(), "--pretend-minutes-later=%s" % value])

    def test_output_holding_a_credential_is_not_shown_or_saved(self):
        self.b.change("SAND-1", priority="High")
        log = os.path.join(self.b.folder, "log.txt")
        conn = update.Connection(self.b.fake.get, None, HOST)
        with mock.patch.object(update, "make_live", return_value=(conn, ["SAND-1"])):
            code, text = self.run_main("preview", "--source", "live", "--change", self.b.change_path,
                                       "--allowlist", ALLOWLIST, "--state", self.b.folder, "--log", log)
        self.assertEqual(code, 1)
        self.assertEqual(text.strip(), "STOPPED: a credential was found in the output, so the output was not shown or saved.")
        self.assertFalse(os.path.exists(log))

    def test_live_connection_needs_all_three_variables_and_https(self):
        good = {"JIRA_BASE_URL": "https://unit-test.example.invalid", "JIRA_EMAIL": "e", "JIRA_API_TOKEN": "t"}
        for name in good:
            with mock.patch.dict(os.environ, {k: v for k, v in good.items() if k != name}, clear=True):
                with self.assertRaises(update.Refused):
                    update.make_live(False)
        with mock.patch.dict(os.environ, dict(good, JIRA_BASE_URL="http://unit-test.example.invalid"), clear=True):
            with self.assertRaises(update.Refused):
                update.make_live(False)

    def test_live_preview_has_no_put_and_live_put_takes_one_kind_of_path(self):
        good = {"JIRA_BASE_URL": "https://unit-test.example.invalid", "JIRA_EMAIL": "e", "JIRA_API_TOKEN": "t"}
        with mock.patch.dict(os.environ, good, clear=True):
            reader, _ = update.make_live(False)
            writer, _ = update.make_live(True)
        self.assertIsNone(reader._put)
        for path in ("/rest/api/3/issue/30001/transitions", "/rest/api/3/issue/SAND-1", "/rest/api/3/project/1",
                     "/rest/api/3/issue/1/../../user"):
            with self.assertRaises(update.Refused):
                writer._put(path, None, {"fields": {}})
        for fields in ({"assignee": None}, {}, {"labels": ["a"], "summary": "x"}):
            with self.assertRaises(update.Refused):
                writer.put_issue("30001", fields)
        with self.assertRaises(update.Refused):
            writer.put_issue("SAND-1", {"labels": ["a"]})


if __name__ == "__main__":
    unittest.main()
