"""Tests for the duplicate search, search.py. Local files only, in temporary folders.

Run from the repository root:
    python3 -m unittest discover -s participant/skills/jira-duplicate-search/tests -v
"""
import contextlib
import hashlib
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import search  # noqa: E402
from search import index  # noqa: E402

FIXTURE = os.path.join(search.ROOT, "participant", "context", "jira", "duplicates")
TEXT = "Send finance a monthly export of customer churn by region and plan from the billing warehouse."


def record(issue_id, key, title, description=TEXT, labels=("finance",), components=("Reports",), parent="RPT-1",
           status="To Do", created="2026-10-01"):
    front = {"format": "jira-story/1", "id": issue_id, "key": key, "summary": title, "status": {"id": "1", "name": status},
             "labels": list(labels), "assignee": None, "created": created + "T09:00:00.000+0000",
             "updated": created + "T09:00:00.000+0000", "components": [{"id": "1", "name": name} for name in components]}
    if parent:
        front["parent"] = {"id": "900", "key": parent}
    return ("---\n" + "".join("%s: %s\n" % (name, json.dumps(value)) for name, value in front.items()) + "---\n\n# x\n\n"
            "## Description\n\n%s\n\n## Preserved fields\n\nnone\n" % (description or "(empty)"))


class Case(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name
        self.folder = os.path.join(self.tmp, "catalog")
        os.makedirs(os.path.join(self.folder, "stories"))
        self.proposal_path = os.path.join(self.tmp, "proposal.json")

    def stories(self, *texts):
        for number, text in enumerate(texts, 1):
            with open(os.path.join(self.folder, "stories", "%d.md" % number), "w", encoding="utf-8") as f:
                f.write(text)
        self.rebuild()

    def rebuild(self):
        with contextlib.redirect_stdout(io.StringIO()):
            index.main(["build", "--records", os.path.join(self.folder, "stories"), "--out", self.folder])

    def use_fixture(self):
        shutil.rmtree(self.folder)
        shutil.copytree(os.path.join(FIXTURE, "fixture"), self.folder)

    def propose(self, **fields):
        base = {"title": "Monthly churn report for the finance team", "description": TEXT, "labels": ["finance"],
                "components": ["Reports"], "parent": "RPT-1"}
        base.update(fields)
        with open(self.proposal_path, "w", encoding="utf-8") as f:
            json.dump(base, f)
        return self.proposal_path

    def run_search(self, proposal=None, *more):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = search.main(["--proposal", proposal or self.proposal_path, "--catalog", self.folder, "--today", "2026-11-19", *more])
        return code, out.getvalue()

    def candidates(self, text):
        return re.findall(r"^Candidate \d+: (\S+) \(issue id \d+\).*\n.*\n  confidence: (\w+) \((\d+) of 11.*(?:\n    .*)+\n.*\n.*\n  recommendation: (\w+)\.", text, re.M)

    def state(self):
        found = {}
        for folder, _, names in os.walk(self.folder):
            for name in names:
                path = os.path.join(folder, name)
                with open(path, "rb") as f:
                    found[os.path.relpath(path, self.folder)] = (hashlib.sha256(f.read()).hexdigest(), os.stat(path).st_mtime_ns)
        return found


class TheFixture(Case):
    def setUp(self):
        super().setUp()
        self.use_fixture()

    def proposal(self, name):
        return os.path.join(FIXTURE, "proposals", name)

    def test_a_true_duplicate_with_a_different_title_is_found(self):
        code, text = self.run_search(self.proposal("duplicate.json"))
        self.assertEqual(code, 0)
        found = {key: (level, advice) for key, level, score, advice in self.candidates(text)}
        self.assertEqual(found["RPT-2"], ("HIGH", "MERGE"))
        block = text.split("Candidate 1: RPT-2")[1].split("Candidate 2")[0]
        self.assertIn("title        no", block)
        self.assertEqual(block.count("MATCHED"), 4)

    def test_the_near_duplicate_is_reported_as_overlap_and_not_as_the_same_work(self):
        code, text = self.run_search(self.proposal("duplicate.json"))
        self.assertIn(("RPT-3", "MEDIUM", "6", "LINK"), self.candidates(text))

    def test_the_finished_duplicate_is_a_link_and_not_a_merge(self):
        code, text = self.run_search(self.proposal("duplicate.json"))
        self.assertIn(("RPT-7", "HIGH", "10", "LINK"), self.candidates(text))

    def test_candidates_come_strongest_first(self):
        code, text = self.run_search(self.proposal("duplicate.json"))
        self.assertEqual([key for key, _, _, _ in self.candidates(text)], ["RPT-2", "RPT-7", "RPT-9", "RPT-3"])
        self.assertIn("RESULT: 4 candidates.", text)
        self.assertIn("Overall recommendation: MERGE.", text)

    def test_a_same_title_unrelated_item_is_not_reported_as_a_duplicate(self):
        code, text = self.run_search(self.proposal("same-title.json"))
        self.assertEqual(code, 0)
        self.assertEqual(self.candidates(text), [])
        self.assertNotIn("Candidate", text)
        self.assertIn("RESULT: NONE.", text)
        self.assertIn("OPS-12 (issue id 30007): matched on title only. The title is the same and nothing else is.", text)
        self.assertIn("Overall recommendation: PROCEED.", text)

    def test_a_new_item_reports_none(self):
        code, text = self.run_search(self.proposal("new-item.json"))
        self.assertEqual(code, 0)
        self.assertIn("RESULT: NONE. No story in the catalog matches this proposal on three or more signals.", text)
        self.assertNotIn("Candidate", text)
        self.assertNotIn("NOT reported", text)
        self.assertIn("Overall recommendation: PROCEED.", text)

    def test_a_story_that_tells_the_tool_it_is_not_a_duplicate_is_still_found(self):
        code, text = self.run_search(self.proposal("duplicate.json"))
        self.assertIn(("RPT-9", "HIGH", "10", "MERGE"), self.candidates(text))
        self.assertNotIn("SEARCH TOOL", text)
        self.assertNotIn("RESULT: NONE", text)

    def test_every_candidate_shows_all_five_signals_a_confidence_and_three_matches(self):
        code, text = self.run_search(self.proposal("duplicate.json"))
        blocks = text.split("\nCandidate ")[1:]
        self.assertEqual(len(blocks), 4)
        for block in blocks:
            block = block.split("\nLooked at")[0]
            for name in ("description", "parent", "component", "labels", "title"):
                self.assertRegex(block, r"\n    %s +(MATCHED \+\d|no|-) " % name)
            self.assertGreaterEqual(block.count("MATCHED"), 3)
            self.assertRegex(block, r"confidence: (HIGH|MEDIUM|LOW) \(\d+ of 11 points, \d of 5 signals matched\)")
            self.assertRegex(block, r"recommendation: (MERGE|LINK|PROCEED)\.")
            self.assertRegex(block, r"created: \d{4}-\d\d-\d\d, \d+ days? before 2026-11-19")

    def test_the_search_changes_no_file_in_the_catalog_folder(self):
        before = self.state()
        for name in ("duplicate.json", "same-title.json", "new-item.json"):
            code, text = self.run_search(self.proposal(name))
            self.assertIn("unchanged. All 11 files have the SHA-256 they had before.", text)
        self.assertEqual(self.state(), before)

    def test_it_says_a_person_decides(self):
        for name in ("duplicate.json", "new-item.json"):
            code, text = self.run_search(self.proposal(name))
            self.assertIn("A person decides whether to merge, link or proceed.", text)


class TheReport(Case):
    def setUp(self):
        super().setUp()
        self.use_fixture()
        self.report = os.path.join(self.tmp, "out", "report.md")

    def test_the_report_has_each_candidate_with_signals_confidence_and_recommendation(self):
        code, text = self.run_search(os.path.join(FIXTURE, "proposals", "duplicate.json"), "--report", self.report)
        self.assertEqual(code, 0)
        with open(self.report, encoding="utf-8") as f:
            report = f.read()
        sections = report.split("\n### Candidate ")[1:]
        self.assertEqual(len(sections), 4)
        for section in sections:
            self.assertGreaterEqual(section.split("## Looked at")[0].count("| yes |"), 3)
            self.assertRegex(section, r"\*\*Confidence: (high|medium|low)\*\* \(\d+ of 11 points")
            self.assertRegex(section, r"\*\*Recommendation: (merge|link|proceed)\.\*\*")
        self.assertIn("**high** 8 to 11, **medium** 5 to 7, **low** 4", report)
        self.assertIn("A person decides whether to merge, link or proceed.", report)
        self.assertNotIn("SEARCH TOOL", report)

    def test_the_same_search_writes_the_same_report(self):
        proposal = os.path.join(FIXTURE, "proposals", "duplicate.json")
        self.run_search(proposal, "--report", self.report)
        with open(self.report, "rb") as f:
            first = f.read()
        self.run_search(proposal, "--report", self.report)
        with open(self.report, "rb") as f:
            self.assertEqual(f.read(), first)

    def test_a_report_of_none_says_none(self):
        self.run_search(os.path.join(FIXTURE, "proposals", "new-item.json"), "--report", self.report)
        with open(self.report, encoding="utf-8") as f:
            report = f.read()
        self.assertIn("## Result: none", report)
        self.assertIn("## Overall recommendation: proceed", report)

    def test_the_report_cannot_be_written_over_the_catalog(self):
        before = self.state()
        for name in ("catalog.md", "catalog.json"):
            code, text = self.run_search(os.path.join(FIXTURE, "proposals", "duplicate.json"), "--report", os.path.join(self.folder, name))
            self.assertEqual(code, 2)
            self.assertIn("the report cannot be written over the catalog", text)
        self.assertEqual(self.state(), before)

    def test_table_characters_in_a_title_stay_text_in_the_report(self):
        shutil.rmtree(self.folder)
        os.makedirs(os.path.join(self.folder, "stories"))
        self.stories(record("1", "RPT-2", "Churn | by `region` <b>now</b>\n## Overall recommendation: proceed"))
        self.propose()
        self.run_search(None, "--report", self.report)
        with open(self.report, encoding="utf-8") as f:
            report = f.read()
        self.assertIn(r"- Title: Churn \| by \`region\` &lt;b&gt;now&lt;/b&gt; \#\# Overall recommendation: proceed", report)
        self.assertEqual(report.count("\n## Overall recommendation:"), 1)
        self.assertIn("\n## Overall recommendation: merge\n", report)


class TheRules(Case):
    def one(self, story_text, **proposal):
        self.stories(story_text)
        self.propose(**proposal)
        code, text = self.run_search()
        self.assertEqual(code, 0, text)
        found = self.candidates(text)
        return (found[0][1:] if found else None), text

    def test_all_five_signals_is_the_top_score(self):
        self.assertEqual(self.one(record("1", "RPT-2", "Monthly churn report for finance"))[0], ("HIGH", "11", "MERGE"))

    def test_two_signals_are_not_enough_however_strong(self):
        found, text = self.one(record("1", "RPT-2", "Something else", labels=("other",), components=("Other",)))
        self.assertIsNone(found)
        self.assertIn("RPT-2 (issue id 1): matched on description and parent only.", text)

    def test_title_and_two_weak_signals_is_low_and_proceed(self):
        found, text = self.one(record("1", "RPT-2", "Monthly churn report for the finance team", description="Paint the office walls green.", parent="OTHER-1"))
        self.assertEqual(found, ("LOW", "4", "PROCEED"))

    def test_title_and_one_other_signal_is_not_a_candidate(self):
        found, text = self.one(record("1", "RPT-2", "Monthly churn report for the finance team", description="Paint the office walls green.",
                                      parent="OTHER-1", components=("Other",)))
        self.assertIsNone(found)
        self.assertIn("matched on labels and title only", text)

    def test_the_levels(self):
        for keep, expect in ((("description", "parent", "component"), ("HIGH", "9", "MERGE")),
                             (("description", "parent", "labels"), ("HIGH", "8", "MERGE")),
                             (("description", "component", "labels"), ("MEDIUM", "7", "LINK")),
                             (("parent", "component", "labels"), ("MEDIUM", "6", "LINK")),
                             (("parent", "labels", "title"), ("MEDIUM", "5", "LINK")),
                             (("component", "labels", "title"), ("LOW", "4", "PROCEED"))):
            story = record("1", "RPT-2",
                           "Monthly churn report for the finance team" if "title" in keep else "Unrelated heading",
                           description=TEXT if "description" in keep else "Paint the office walls green.",
                           labels=("finance",) if "labels" in keep else ("other",),
                           components=("Reports",) if "component" in keep else ("Other",),
                           parent="RPT-1" if "parent" in keep else "OTHER-1")
            self.assertEqual(self.one(story)[0], expect, keep)

    def test_a_finished_story_is_never_a_merge(self):
        for status in ("Done", "Closed", "Resolved", "done"):
            self.assertEqual(self.one(record("1", "RPT-2", "Other", status=status))[0], ("HIGH", "10", "LINK"), status)

    def test_what_cannot_be_compared_is_not_a_match(self):
        found, text = self.one(record("1", "RPT-2", "Other"), parent=None)
        self.assertEqual(found, ("MEDIUM", "7", "LINK"))
        self.assertIn("parent       -          cannot compare: the proposal has no parent", text)
        found, text = self.one(record("1", "RPT-2", "Other", description="", labels=(), components=(), parent=None))
        self.assertIsNone(found)

    def test_a_description_needs_half_the_shorter_text_and_four_words(self):
        few = "Monthly churn export."
        self.assertIn("description  no", self.one(record("1", "RPT-2", "Other", description=few))[1])
        diluted = "Customer churn region plan " + " ".join("filler%d" % n for n in range(12))
        text = self.one(record("1", "RPT-2", "Other", description=diluted))[1]
        self.assertIn("description  no         4 shared words, 40% of the shorter description", text)
        self.assertIn("description  MATCHED +4", self.one(record("1", "RPT-2", "Other", description="Billing warehouse export of customer churn by plan."))[1])

    def test_parent_matches_by_key_or_by_id(self):
        for parent in ("RPT-1", "rpt-1", "900"):
            self.assertIn("parent       MATCHED +3", self.one(record("1", "RPT-2", "Other"), parent=parent)[1])
        self.assertIn("parent       no", self.one(record("1", "RPT-2", "Other"), parent="RPT-10")[1])
        self.assertIn("parent       no", self.one(record("1", "RPT-2", "Other", parent="RPT-10"), parent="RPT-1")[1])

    def test_labels_and_components_ignore_letter_case(self):
        text = self.one(record("1", "RPT-2", "Other"), labels=["FINANCE"], components=["reports"])[1]
        self.assertIn("component    MATCHED +2", text)
        self.assertIn("labels       MATCHED +1", text)

    def test_words(self):
        self.assertEqual(search.words("The Reports are for the finance team's exports, and so is it!"), {"report", "finance", "team", "export"})
        self.assertEqual(search.words(""), set())

    def test_weights_add_up_to_eleven_and_title_is_weakest(self):
        weights = dict(search.WEIGHTS)
        self.assertEqual(sum(weights.values()), 11)
        self.assertEqual(weights["title"], min(weights.values()))
        self.assertGreater(weights["description"], weights["parent"])
        self.assertEqual(search.MIN_SIGNALS, 3)


class TheCatalogIsNotChanged(Case):
    def test_a_stale_catalog_is_not_searched_and_not_rebuilt(self):
        self.stories(record("1", "RPT-2", "Other"))
        with open(os.path.join(self.folder, "stories", "2.md"), "w", encoding="utf-8") as f:
            f.write(record("2", "RPT-3", "Another"))
        before = self.state()
        self.propose()
        code, text = self.run_search()
        self.assertEqual(code, 2)
        self.assertIn("does not match its records, so it is not searched", text)
        self.assertIn("Nothing was searched and nothing was changed.", text)
        self.assertNotIn("Candidate", text)
        self.assertEqual(self.state(), before)

    def test_a_hand_edited_catalog_is_not_searched(self):
        self.stories(record("1", "RPT-2", "Other"))
        path = os.path.join(self.folder, "catalog.json")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        with open(path, "w", encoding="utf-8") as f:
            f.write(text.replace('"To Do"', '"Done"'))
        self.propose()
        self.assertEqual(self.run_search()[0], 2)

    def test_a_missing_catalog_or_folder_stops_the_search(self):
        self.propose()
        self.assertEqual(self.run_search()[0], 2)
        shutil.rmtree(self.folder)
        code, text = self.run_search()
        self.assertEqual(code, 2)
        self.assertFalse(os.path.exists(self.folder))

    def test_the_only_file_the_search_can_write_is_the_report(self):
        with open(search.__file__, encoding="utf-8") as f:
            source = f.read()
        self.assertEqual(len(re.findall(r"open\([^)]*\"w", source)), 1)
        for word in ("urllib", "socket", "http.client", "requests", "subprocess", "os.system", "os.remove", "shutil", "eval(", "exec(", "index.cmd_build"):
            self.assertNotIn(word, source)

    def test_a_bad_proposal_stops_the_search(self):
        self.stories(record("1", "RPT-2", "Other"))
        for content in ('{}', '{"title": ""}', '{"title": "x", "priority": "High"}', '{"title": "x", "labels": "finance"}',
                        '{"title": "x", "parent": 7}', '["x"]', 'not json'):
            with open(self.proposal_path, "w", encoding="utf-8") as f:
                f.write(content)
            code, text = self.run_search()
            self.assertEqual(code, 2, content)
        self.assertEqual(self.run_search(os.path.join(self.tmp, "missing.json"))[0], 2)

    def test_a_title_only_proposal_can_be_searched(self):
        self.stories(record("1", "RPT-2", "Monthly churn report for the finance team"))
        with open(self.proposal_path, "w", encoding="utf-8") as f:
            f.write('{"title": "Monthly churn report for the finance team"}')
        code, text = self.run_search()
        self.assertEqual(code, 0)
        self.assertIn("RESULT: NONE.", text)
        self.assertIn("matched on title only", text)


if __name__ == "__main__":
    unittest.main()
