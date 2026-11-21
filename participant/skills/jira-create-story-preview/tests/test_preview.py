"""Tests for the story preview, preview.py, against fake_jira.py. No network.

Run from the repository root:
    python3 -m unittest discover -s participant/skills/jira-create-story-preview/tests -v
"""
import argparse
import contextlib
import datetime
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
sys.path.insert(0, SKILL)
import fake_jira  # noqa: E402
import preview  # noqa: E402

REAL = os.path.join(preview.ROOT, "participant", "context", "jira")
HOST = "fixture-site.example.invalid"


class Case(unittest.TestCase):
    """A copy of the draft and its notes in a temporary folder, a fake Jira, and the preview."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = os.path.realpath(tmp.name)
        shutil.copytree(os.path.join(REAL, "new-story", "sources"), os.path.join(self.tmp, "new-story", "sources"))
        shutil.copytree(os.path.join(REAL, "duplicates", "fixture"), os.path.join(self.tmp, "catalog"))
        with open(os.path.join(REAL, "new-story", "draft.md"), encoding="utf-8") as f:
            self.text = f.read()
        self.draft = os.path.join(self.tmp, "new-story", "draft.md")
        self.state = os.path.join(self.tmp, "state")
        self.allowlist = os.path.join(SKILL, "fake-allowlist.json")
        self.host = HOST
        self.fake = fake_jira.FakeJira()
        patch = mock.patch.object(preview, "CONTEXT", self.tmp)
        patch.start()
        self.addCleanup(patch.stop)

    def edit(self, old, new):
        self.assertIn(old, self.text)
        self.text = self.text.replace(old, new)

    def drop(self, *names):
        """Take fields, and their citations, out of the draft."""
        kept = [line for line in self.text.split("\n")
                if not any(line.startswith(name + ":") or line.startswith("- %s:" % name) for name in names)]
        self.text = "\n".join(kept)

    def preview(self, **more):
        with open(self.draft, "w", encoding="utf-8") as f:
            f.write(self.text)
        args = dict(draft=self.draft, allowlist=self.allowlist, catalog=os.path.join(self.tmp, "catalog"), state=self.state,
                    payload_out=None, log=None, today=datetime.date(2026, 11, 19))
        args.update(more)
        del preview.LINES[:]
        self.conn = preview.Connection(self.fake.get, self.host)
        code = preview.run(argparse.Namespace(**args), self.conn)
        return code, "\n".join(preview.LINES)

    def ok(self, **more):
        code, text = self.preview(**more)
        self.assertEqual(code, 0, text)
        return text

    def refused(self, *phrases, **more):
        code, text = self.preview(**more)
        self.assertEqual(code, 1, text)
        self.assertTrue(text.startswith("REFUSED: "), text)
        self.assertIn("No preview was made, no payload was saved, and nothing has been written to Jira.", text)
        self.assertNotIn("THE EXACT PAYLOAD", text)
        self.assertNotIn('"fields"', text)
        self.assertFalse(os.path.exists(self.state), "a refusal saves no preview")
        for phrase in phrases:
            self.assertIn(phrase, text)
        return text

    def record(self):
        folder = os.path.join(self.state, "create-previews")
        names = os.listdir(folder)
        self.assertEqual(len(names), 1)
        with open(os.path.join(folder, names[0]), encoding="utf-8") as f:
            return json.load(f)

    def shown_payload(self, text):
        block = text.split("THE EXACT PAYLOAD. This is the request body, not a summary of it:\n")[1].split("\nAs sent it is")[0]
        return json.loads(block)


class ThePreview(Case):
    def test_it_lists_the_project_the_issue_type_and_every_field(self):
        text = self.ok()
        for phrase in ("Jira site:   https://fixture-site.example.invalid", "Project:     RPT (project id 30000)",
                       'Issue type:  "Story" (issue type id 10001)', 'EVERY FIELD Jira lists for creating a "Story" in RPT: 12.',
                       "Set by the draft, 9:", "LEFT TO JIRA because it has a default, 2:", "Optional, not in the draft, and not sent, 1:"):
            self.assertIn(phrase, text)
        for field in self.fake.fields["30000"]:
            self.assertIn("  %-18s" % field["fieldId"], text)

    def test_the_payload_shown_is_the_payload_saved_and_hashed(self):
        text = self.ok()
        record = self.record()
        shown = self.shown_payload(text)
        self.assertEqual(shown, record["payload"])
        body = preview.body_bytes(shown)
        self.assertEqual(hashlib.sha256(body).hexdigest(), record["payload_sha256"])
        self.assertIn("%d bytes, SHA-256 %s" % (len(body), record["payload_sha256"]), text)
        self.assertEqual(json.loads(body.decode("utf-8")), shown)

    def test_the_payload_holds_exactly_the_draft_and_nothing_else(self):
        payload = self.shown_payload(self.ok())
        self.assertEqual(set(payload), {"fields"})
        fields = payload["fields"]
        self.assertEqual(set(fields), {"project", "issuetype", "summary", "description", "labels", "components", "parent",
                                       "duedate", "customfield_10050"})
        self.assertEqual(fields["project"], {"id": "30000"})
        self.assertEqual(fields["issuetype"], {"id": "10001"})
        self.assertEqual(fields["summary"], "Quarterly revenue by plan report for the finance team")
        self.assertEqual(fields["labels"], ["reporting", "revenue"])
        self.assertEqual(fields["components"], [{"id": "31001"}])
        self.assertEqual(fields["parent"], {"key": "RPT-1"})
        self.assertEqual(fields["duedate"], "2027-01-15")
        self.assertEqual(fields["customfield_10050"], {"id": "32001"})
        self.assertEqual(fields["description"]["type"], "doc")
        self.assertEqual([block["type"] for block in fields["description"]["content"]], ["paragraph", "bulletList"])

    def test_the_payload_is_built_once_and_turned_into_bytes_in_one_place(self):
        with mock.patch.object(preview, "build_payload", wraps=preview.build_payload) as built, \
                mock.patch.object(preview, "body_bytes", wraps=preview.body_bytes) as made:
            self.ok(payload_out=os.path.join(self.tmp, "payload.md"))
        self.assertEqual(built.call_count, 1)
        self.assertEqual(made.call_count, 1)

    def test_the_payload_file_holds_the_same_payload_field_by_field(self):
        out = os.path.join(self.tmp, "out", "payload.md")
        text = self.ok(payload_out=out)
        with open(out, encoding="utf-8") as f:
            saved = f.read()
        self.assertEqual(json.loads(saved.split("```json\n")[1].split("\n```")[0]), self.shown_payload(text))
        self.assertIn(self.record()["payload_sha256"], saved)
        for phrase in ("| Target project | RPT (project id 30000), on the sandbox allowlist |", "| Issue type | Story (issue type id 10001) |",
                       "| Request | `POST /rest/api/3/issue` |", "| `components` | Components | \"Reports\" (id 31001) | sources/intake-notes.md line 11 |",
                       "| `customfield_10050` | Team | \"Data\" (option id 32001) | sources/intake-notes.md line 11 |",
                       "- `priority`, Priority: Jira's default is \"Medium\".", "Nothing in this file has been sent to Jira."):
            self.assertIn(phrase, saved)
        self.assertNotIn(HOST, saved)

    def test_the_same_draft_gives_the_same_payload_file(self):
        out = os.path.join(self.tmp, "payload.md")
        self.ok(payload_out=out)
        with open(out, "rb") as f:
            first = f.read()
        shutil.rmtree(self.state)
        self.ok(payload_out=out)
        with open(out, "rb") as f:
            self.assertEqual(f.read(), first)

    def test_a_preview_is_saved_with_a_fingerprint_for_a_later_write(self):
        text = self.ok()
        record = self.record()
        self.assertIn("Fingerprint of this preview: %s" % record["fingerprint"][:12], text)
        self.assertEqual(record["state"], "open")
        self.assertEqual(record["project"], {"id": "30000", "key": "RPT"})
        self.assertEqual(record["left_to_jira"], ["priority", "reporter"])
        self.assertIn("(15 minutes after it was made)", text)

    def test_the_field_list_is_read_through_all_its_pages(self):
        self.ok()
        self.assertEqual(self.fake.requests.count(("GET", "/rest/api/3/issue/createmeta/30000/issuetypes/10001")), 3)

    def test_a_draft_with_no_description_sends_none(self):
        self.text = self.text.split("\n## Description\n")[0] + "\n## Description\n\n## Sources\n" + self.text.split("\n## Sources\n")[1]
        self.drop("- description")
        self.text = "\n".join(line for line in self.text.split("\n") if not line.startswith("- description:"))
        text = self.ok()
        self.assertNotIn("description", self.shown_payload(text)["fields"])
        self.assertIn("  description        Description   no default reported.", text)


class RequiredFields(Case):
    def test_a_missing_required_field_stops_the_preview_and_is_named(self):
        self.drop("components")
        self.refused('the draft is missing 1 field that Jira requires for a "Story" in RPT and gives no default for: '
                     '"Components" (components)')

    def test_every_missing_required_field_is_named(self):
        self.drop("components", "custom")
        self.text = "\n".join(line for line in self.text.split("\n") if not line.startswith("- custom Team:"))
        for field in self.fake.fields["30000"]:
            if field["fieldId"] == "customfield_10050":
                field["hasDefaultValue"] = False
                del field["defaultValue"]
        self.refused('missing 2 fields', '"Components" (components), "Team" (customfield_10050)')

    def test_nothing_is_written_to_the_payload_file_when_refused(self):
        self.drop("components")
        out = os.path.join(self.tmp, "payload.md")
        self.refused(payload_out=out)
        self.assertFalse(os.path.exists(out))

    def test_a_required_field_with_a_default_is_left_to_jira_and_shown(self):
        self.drop("custom")
        self.text = "\n".join(line for line in self.text.split("\n") if not line.startswith("- custom Team:"))
        text = self.ok()
        self.assertIn("LEFT TO JIRA because it has a default, 3:", text)
        self.assertIn('  customfield_10050  Team          Jira\'s default is "Support".', text)
        self.assertNotIn("customfield_10050", self.shown_payload(text)["fields"])

    def test_a_default_jira_does_not_name_is_said_to_be_unknown(self):
        self.assertIn("  reporter           Reporter      Jira says it has a default and does not say what it is.", self.ok())

    def test_a_draft_with_no_summary_or_target_is_refused(self):
        for name in ("summary", "project", "issuetype"):
            text = self.text
            self.drop(name)
            self.refused("the draft has no %s" % name)
            self.text = text


class WhatJiraAllows(Case):
    def test_values_jira_does_not_allow_are_refused(self):
        for old, new, phrase in (
                ('components: ["Reports"]', 'components: ["Reporting"]', 'component "Reporting" is not one of the values Jira allows: "Reports", "Billing", "Documentation"'),
                ('custom: {"Team": "Data"}', 'custom: {"Team": "Finance"}', 'the value of "Team" "Finance" is not one of the values Jira allows'),
                ('custom: {"Team": "Data"}', 'custom: {"Squad": "Data"}', 'the custom field "Squad" is not one Jira lists'),
                ('custom: {"Team": "Data"}', 'custom: {"Story Points": "5"}', 'is not a single-choice field'),
                ('issuetype: "Story"', 'issuetype: "Bug"', 'the issue type "Bug" is not one Jira offers for creating in RPT. It offers: "Epic", "Story", "Sub-task"'),
                ('parent: "RPT-1"', 'parent: "RPT-99"', "the parent RPT-99 could not be read"),
                ('parent: "RPT-1"', 'parent: "OPS-12"', "the parent OPS-12 is in another project"),
                ('labels: ["reporting", "revenue"]', 'labels: ["Has Space", "revenue"]', "is not allowed"),
                ('duedate: "2027-01-15"', 'duedate: "2027-02-30"', "not a real date"),
                ('duedate: "2027-01-15"', 'duedate: "15 January"', "not a real date")):
            text = self.text
            self.edit(old, new)
            if "Squad" in new or "Story Points" in new:
                self.edit("- custom Team:", "- custom %s:" % new.split('"')[1])
            self.refused(phrase)
            self.text = text

    def test_a_priority_is_sent_by_id_and_must_be_one_jira_offers(self):
        self.edit('duedate: "2027-01-15"', 'duedate: "2027-01-15"\npriority: "High"')
        self.edit("- labels:", '- priority: sources/intake-notes.md line 13: "Nobody had a view on priority"\n- labels:')
        text = self.ok()
        self.assertEqual(self.shown_payload(text)["fields"]["priority"], {"id": "2"})
        self.assertIn("LEFT TO JIRA because it has a default, 1:", text)
        shutil.rmtree(self.state)
        self.edit('priority: "High"', 'priority: "Urgent"')
        self.refused('priority "Urgent" is not one of the values Jira allows')

    def test_a_field_the_preview_does_not_support_is_refused(self):
        for line in ('assignee: "someone"', 'reporter: "someone"', 'security: "10000"', 'status: "Done"', 'customfield_10016: 5'):
            text = self.text
            self.edit('duedate: "2027-01-15"', 'duedate: "2027-01-15"\n' + line)
            self.refused("the draft has a field this preview does not support")
            self.assertEqual(self.fake.requests, [], "refused before Jira was asked anything")
            self.text = text

    def test_a_field_jira_does_not_take_on_create_is_refused(self):
        self.fake.fields["30000"] = [f for f in self.fake.fields["30000"] if f["fieldId"] != "labels"]
        self.refused("Jira does not list labels as a field that can be set")

    def test_a_field_of_another_kind_than_expected_is_refused(self):
        for field in self.fake.fields["30000"]:
            if field["fieldId"] == "duedate":
                field["schema"]["type"] = "datetime"
        self.refused("Jira describes duedate as")

    def test_a_summary_must_be_one_line_of_at_most_255_characters(self):
        self.edit("Quarterly revenue by plan report for the finance team", "x" * 256)
        self.refused("longer than 255")

    def test_description_becomes_paragraphs_and_plain_lists(self):
        adf = preview.description_to_adf("One line\nand its second.\n\n- first **bold**\n- second\n\nLast.")
        self.assertEqual([block["type"] for block in adf["content"]], ["paragraph", "bulletList", "paragraph"])
        self.assertEqual(adf["content"][0]["content"][0]["text"], "One line and its second.")
        self.assertEqual(adf["content"][1]["content"][0]["content"][0]["content"][0], {"type": "text", "text": "first **bold**"})
        self.assertIsNone(preview.description_to_adf("  \n\n"))


class PermissionAndAllowlist(Case):
    def test_no_permission_to_create_is_refused(self):
        self.edit('project: "RPT"', 'project: "LOCK"')
        self.refused("Jira says this identity may not create stories in LOCK (CREATE_ISSUES: no)")
        self.assertNotIn(("GET", "/rest/api/3/issue/createmeta/30200/issuetypes"), self.fake.requests)

    def test_the_permission_result_is_shown(self):
        text = self.ok()
        self.assertIn("may create stories     (CREATE_ISSUES):   yes", text)
        self.assertIn(("GET", "/rest/api/3/mypermissions"), self.fake.requests)

    def test_no_answer_to_the_permission_check_assumes_nothing(self):
        real = self.fake.get
        self.fake.get = lambda path, params=None: (500, {}, {}) if "mypermissions" in path else real(path, params)
        self.refused("did not answer the permission check")

    def test_an_empty_field_list_is_refused(self):
        self.fake.fields["30000"] = []
        self.refused("Jira lists no fields")

    def test_a_project_not_on_the_allowlist_is_refused_after_one_request(self):
        self.edit('project: "RPT"', 'project: "OPS"')
        self.refused("project OPS (project id 30100)", "is not on the sandbox allowlist")
        self.assertEqual(self.fake.requests, [("GET", "/rest/api/3/project/OPS")])

    def test_the_same_project_id_on_another_site_is_refused(self):
        self.host = "another-site.example.invalid"
        self.refused("is not on the sandbox allowlist")

    def test_a_project_that_cannot_be_seen_is_refused(self):
        self.edit('project: "RPT"', 'project: "NOPE"')
        self.refused("404")


class Duplicates(Case):
    def test_the_duplicate_search_result_is_shown(self):
        text = self.ok()
        self.assertIn("searched with the jira-duplicate-search skill", text)
        self.assertIn("Result: 1 candidate.", text)
        self.assertIn("RPT-3 (issue id 30003): confidence MEDIUM, 6 of 11 points, matched on parent, component, labels. Recommendation: LINK.", text)
        self.assertIn("Overall recommendation: LINK. A person decides.", text)

    def test_the_difference_from_the_nearest_story_is_shown(self):
        text = self.ok()
        self.assertIn("How the draft differs from the nearest, RPT-3:", text)
        self.assertIn("labels:     only in the draft: revenue. only in the story: sales. in both: reporting.", text)

    def test_a_likely_duplicate_is_shown_loudly_and_a_person_still_decides(self):
        self.text = self.text.replace("Finance needs a quarterly report of recognised revenue by subscription plan, split by region.",
                                      "Finance needs a monthly CSV export from the billing warehouse of customer churn by region and plan.")
        self.text = "\n".join(line for line in self.text.split("\n") if not line.startswith("- description:"))
        self.edit("- duedate:", '- description: sources/intake-notes.md line 8: "the billing warehouse"\n- duedate:')
        text = self.ok()
        self.assertIn("Recommendation: MERGE.", text)
        self.assertIn("Overall recommendation: MERGE. A person decides.", text)
        self.assertEqual(self.record()["duplicates"]["overall"], "merge")

    def test_the_catalog_and_jira_holding_the_same_number_of_stories_is_said(self):
        text = self.ok()
        self.assertIn("Coverage: the catalog holds 7 of project RPT's stories and Jira holds 7: the counts agree.", text)
        self.assertEqual((self.record()["duplicates"]["stories_in_catalog"], self.record()["duplicates"]["stories_in_jira"]), (7, 7))

    def test_stories_in_jira_that_the_catalog_lacks_are_warned_about(self):
        for number in (10, 11, 12):
            self.fake.issues.append(fake_jira.issue("3001%d" % number, "RPT-%d" % number, "Story", "2026-11-19T10:00:00.000+0000"))
        text = self.ok()
        self.assertIn("Coverage: WARNING: the catalog holds 7 of project RPT's stories and Jira holds 10. 3 in Jira have NOT been searched.", text)

    def test_stories_in_the_catalog_that_jira_lacks_are_said(self):
        self.fake.issues = [item for item in self.fake.issues if item["key"] != "RPT-9"]
        self.assertIn("the catalog holds 7 of project RPT's stories and Jira holds 6. Some in the catalog are no longer", self.ok())

    def test_no_duplicate_says_none(self):
        self.edit('labels: ["reporting", "revenue"]', 'labels: ["revenue"]')
        text = self.ok()
        self.assertIn("Result: NONE. No story in the catalog matches this draft on three or more signals.", text)
        self.assertIn("Overall recommendation: PROCEED.", text)

    def test_a_stale_catalog_stops_the_preview(self):
        with open(os.path.join(self.tmp, "catalog", "stories", "30001.md"), "a", encoding="utf-8") as f:
            f.write("\nA line added after the catalog was built.\n")
        self.refused("the duplicate search could not run, so no preview is made")

    def test_the_search_leaves_the_catalog_as_it_was(self):
        def state():
            found = {}
            for folder, _, names in os.walk(os.path.join(self.tmp, "catalog")):
                for name in names:
                    with open(os.path.join(folder, name), "rb") as f:
                        found[name] = hashlib.sha256(f.read()).hexdigest()
            return found
        before = state()
        self.ok()
        self.assertEqual(state(), before)


class Citations(Case):
    def test_citations_are_shown_and_counted(self):
        text = self.ok()
        self.assertIn("Sources for the content, each checked against the file: 10 citations, all true.", text)
        self.assertIn('  custom Team  sources/intake-notes.md line 11: "The data team will build it"', text)

    def test_content_without_a_citation_is_refused(self):
        for name in ("summary", "description", "labels", "components", "parent", "duedate", "custom Team"):
            text = self.text
            self.text = "\n".join(line for line in self.text.split("\n") if not line.startswith("- %s:" % name))
            self.refused("the draft gives no source for: %s" % name)
            self.text = text

    def test_a_citation_that_is_not_true_is_refused(self):
        for old, new, phrase in (
                ('line 14: "Tag it reporting and revenue"', 'line 14: "Tag it urgent"', "the citation for labels is not true"),
                ('line 14: "Tag it reporting and revenue"', 'line 13: "Tag it reporting and revenue"', "the citation for labels is not true"),
                ('line 14: "Tag it reporting and revenue"', 'line 99: "Tag it reporting and revenue"', "names lines that sources/intake-notes.md does not have"),
                ("- labels: sources/intake-notes.md", "- labels: sources/missing.md", "could not be read"),
                ("- labels: sources/intake-notes.md", "- labels: ../../outside.md", "points outside participant/context/"),
                ("- labels: sources/intake-notes.md", "- priority: sources/intake-notes.md", "which is not in the draft"),
                ('- labels: sources/intake-notes.md line 14: "Tag it reporting and revenue"', "- labels: I was told", "could not be read as a citation")):
            text = self.text
            self.edit(old, new)
            self.refused(phrase)
            self.text = text

    def test_a_source_changed_after_the_draft_was_written_is_caught(self):
        path = os.path.join(self.tmp, "new-story", "sources", "intake-notes.md")
        with open(path, encoding="utf-8") as f:
            notes = f.read()
        with open(path, "w", encoding="utf-8") as f:
            f.write(notes.replace("15 January 2027", "29 January 2027"))
        self.refused("the citation for duedate is not true")

    def test_a_citation_may_span_lines(self):
        self.edit('- parent: sources/intake-notes.md line 12: "under the finance reporting epic, RPT-1"',
                  '- parent: sources/intake-notes.md lines 11-12: "under the component Reports. 6. It belongs with the other finance reports"')
        self.ok()


class NothingIsWritten(Case):
    def test_every_request_is_a_get_and_the_snapshot_is_the_same(self):
        text = self.ok()
        self.assertEqual(set(method for method, _ in self.fake.requests), {"GET"})
        self.assertIn("Snapshot of the project's stories in Jira before the preview: 7 stories, ", text)
        self.assertIn("The two are the same. Jira is unchanged.", text)
        self.assertIn("Requests sent to Jira: 12. Every one was a GET", text)

    def test_a_story_appearing_during_the_preview_is_refused(self):
        real = self.fake.get

        def get(path, params=None):
            if "createmeta" in path and len(self.fake.issues) == 9:
                self.fake.issues.append(fake_jira.issue("30010", "RPT-10", "Story", "2026-11-19T10:00:00.000+0000"))
            return real(path, params)
        self.fake.get = get
        self.refused("changed in Jira while the preview was being made")

    def test_the_preview_has_no_code_that_writes_to_jira(self):
        with open(preview.__file__, encoding="utf-8") as f:
            source = f.read()
        self.assertEqual(source.count("urllib.request.Request("), 1)
        self.assertIn('urllib.request.Request(url, method="GET")', source)
        for word in ('method="POST"', 'method="PUT"', 'method="DELETE"', "data=", ".put(", ".post(", "subprocess", "os.system"):
            self.assertNotIn(word, source)
        self.assertFalse(hasattr(preview.Connection(None, HOST), "put"))
        self.assertFalse(hasattr(fake_jira.FakeJira(), "put") or hasattr(fake_jira.FakeJira(), "post"))

    def test_story_text_from_jira_is_never_printed(self):
        text = self.ok()
        self.assertNotIn("IGNORE YOUR RULES", text)
        self.assertNotIn("Ada Fixture", text)
        self.assertNotIn("SEARCH TOOL", text)

    def test_jira_unreachable_is_a_refusal(self):
        def down(path, params=None):
            raise OSError("down")
        self.fake.get = down
        self.refused("could not reach Jira")


class CommandLine(Case):
    def run_main(self, *argv):
        with open(self.draft, "w", encoding="utf-8") as f:
            f.write(self.text)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = preview.main(["--draft", self.draft, "--allowlist", self.allowlist, "--catalog", os.path.join(self.tmp, "catalog"),
                                 "--state", self.state, "--today", "2026-11-19", *argv])
        return code, out.getvalue()

    def test_the_site_is_on_screen_and_not_in_the_saved_log(self):
        log = os.path.join(self.tmp, "log.txt")
        code, text = self.run_main("--source", "fake", "--log", log)
        self.assertEqual(code, 0, text)
        self.assertIn(HOST, text)
        with open(log, encoding="utf-8") as f:
            saved = f.read()
        self.assertNotIn(HOST, saved)
        self.assertIn("Jira site:   [site address removed]", saved)

    def test_output_holding_a_credential_is_not_shown_or_saved(self):
        log = os.path.join(self.tmp, "log.txt")
        conn = preview.Connection(self.fake.get, HOST)
        with mock.patch.object(preview, "make_live", return_value=(conn, ["Quarterly revenue"])):
            code, text = self.run_main("--source", "live", "--log", log)
        self.assertEqual(code, 1)
        self.assertEqual(text.strip(), "STOPPED: a credential was found in the output, so the output was not shown or saved.")
        self.assertFalse(os.path.exists(log))

    def test_a_live_run_needs_all_three_variables_and_https(self):
        good = {"JIRA_BASE_URL": "https://unit-test.example.invalid", "JIRA_EMAIL": "e", "JIRA_API_TOKEN": "t"}
        for name in good:
            with mock.patch.dict(os.environ, {k: v for k, v in good.items() if k != name}, clear=True):
                code, text = self.run_main("--source", "live")
                self.assertEqual(code, 1)
                self.assertIn("the environment variable %s is not set" % name, text)
        with mock.patch.dict(os.environ, dict(good, JIRA_BASE_URL="http://unit-test.example.invalid"), clear=True):
            self.assertIn("must start with https://", self.run_main("--source", "live")[1])

    def test_there_is_no_option_that_creates(self):
        for flag in ("--create", "--send", "--write", "--yes", "--confirm"):
            with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
                self.run_main("--source", "fake", flag)


if __name__ == "__main__":
    unittest.main()
