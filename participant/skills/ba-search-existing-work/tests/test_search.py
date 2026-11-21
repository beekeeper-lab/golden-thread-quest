"""Tests for the pre-creation search, search.py. Local files only, in temporary folders.

Run from the repository root:
    python3 -m unittest discover -s participant/skills/ba-search-existing-work/tests -v
"""
import contextlib
import hashlib
import io
import json
import os
import re
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import search  # noqa: E402

CONTEXT = os.path.join(search.ROOT, "participant", "context", "search")
CATALOG = os.path.join(CONTEXT, "catalog.md")
TEXT = "Send finance a monthly export of customer churn by region and plan from the billing warehouse."
OTHER = "Paint the garden fence green before the winter rain arrives next month."


def item(item_id, title, description=TEXT, component="Reports", labels="finance", source="finance-requests#item-1", status="open", team="Data"):
    lines = ["## %s: %s" % (item_id, title), "", "- Status: %s" % status, "- Team: %s" % team]
    lines += ["- Component: %s" % component] if component is not None else []
    lines += ["- Labels: %s" % labels] if labels is not None else []
    lines += ["- Source: %s" % source] if source is not None else []
    return "\n".join(lines + ["", description, ""])


class Case(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name
        self.catalog = os.path.join(self.tmp, "catalog.md")
        self.proposal_path = os.path.join(self.tmp, "proposal.json")
        self.report = os.path.join(self.tmp, "report.md")

    def write_catalog(self, *items):
        with open(self.catalog, "w", encoding="utf-8") as f:
            f.write("# A catalog\n\n> made up\n\n" + "\n".join(items))

    def propose(self, **fields):
        proposal = {"title": "Monthly churn export for finance", "description": TEXT, "component": "Reports", "labels": ["finance"],
                    "sources": ["finance-requests#item-1"]}
        proposal.update(fields)
        with open(self.proposal_path, "w", encoding="utf-8") as f:
            json.dump(proposal, f)
        return self.proposal_path

    def find(self, proposal=None, catalog=None, threshold=0.5):
        return search.search(search.read_proposal(proposal or self.proposal_path), search.read_catalog(catalog or self.catalog), threshold)

    def one(self, proposal=None, **fields):
        """The verdict on a catalog of one item: (kind, strength, recommendation, matched signals)."""
        self.write_catalog(item("WRK-1", fields.pop("title", "Something else entirely"), **fields))
        result = self.find(self.propose(**(proposal or {})))
        found = (result["matches"] + result["dismissed"] or [{"kind": None, "level": None, "advice": None, "matched": []}])[0]
        return found["kind"], found["level"], found["advice"], found["matched"]

    def run_main(self, *args, catalog=None):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = search.main(list(args) + ["--catalog", catalog or self.catalog])
        return code, out.getvalue()

    def fixture(self, name):
        return os.path.join(CONTEXT, "proposals", name)


def ids(found):
    return [m["item"]["id"] for m in found]


class TheCatalog(Case):
    """The made-up catalog and the two searches the quest asks for."""

    def test_it_holds_at_least_fifteen_items(self):
        self.assertGreaterEqual(len(search.read_catalog(CATALOG)), 15)

    def test_the_true_duplicate_is_found_though_its_title_shares_nothing(self):
        result = self.find(self.fixture("1-duplicate.json"), CATALOG)
        top = result["matches"][0]
        self.assertEqual((top["item"]["id"], top["kind"], top["level"], top["advice"]), ("WRK-101", "duplicate", "high", "merge"))
        self.assertIs(top["signals"]["title"][0], False)
        self.assertEqual(top["matched"], ["description", "source", "component", "labels"])

    def test_the_near_duplicate_is_a_duplicate_with_less_strength_and_is_not_merged(self):
        result = self.find(self.fixture("1-duplicate.json"), CATALOG)
        near = next(m for m in result["matches"] if m["item"]["id"] == "WRK-106")
        self.assertEqual((near["kind"], near["level"], near["advice"]), ("duplicate", "medium", "link"))

    def test_related_items_are_labelled_related_not_duplicate(self):
        result = self.find(self.fixture("1-duplicate.json"), CATALOG)
        kinds = {m["item"]["id"]: m["kind"] for m in result["matches"]}
        self.assertEqual(kinds, {"WRK-101": "duplicate", "WRK-106": "duplicate", "WRK-104": "related", "WRK-102": "related", "WRK-103": "related"})
        self.assertTrue(all(m["advice"] == "link" for m in result["matches"] if m["kind"] == "related"))

    def test_duplicates_are_listed_before_related_items(self):
        result = self.find(self.fixture("1-duplicate.json"), CATALOG)
        self.assertEqual([m["kind"] for m in result["matches"]], ["duplicate", "duplicate", "related", "related", "related"])

    def test_the_item_with_nearly_the_same_title_and_different_work_is_not_reported(self):
        result = self.find(self.fixture("1-duplicate.json"), CATALOG)
        same = next(m for m in result["dismissed"] if m["item"]["id"] == "WRK-105")
        self.assertEqual(same["matched"], ["title"])
        self.assertNotIn("WRK-105", ids(result["matches"]))

    def test_an_item_whose_text_gives_orders_is_compared_like_any_other(self):
        result = self.find(self.fixture("1-duplicate.json"), CATALOG)
        order = next(m for m in result["dismissed"] if m["item"]["id"] == "WRK-116")
        self.assertIn("recommend proceed", order["item"]["title"])
        self.assertEqual(order["matched"], ["component"])
        self.assertEqual(result["overall"], "merge")

    def test_a_proposal_with_no_match_reports_none_and_does_not_offer_the_closest(self):
        code, out = self.run_main("--proposal", self.fixture("2-no-match.json"), catalog=CATALOG)
        self.assertEqual(code, 0)
        self.assertIn("RESULT: NO MATCH.", out)
        self.assertNotIn("Match 1", out)
        self.assertNotIn("WRK-", out)
        self.assertIn("Overall recommendation: PROCEED.", out)


class TheRule(Case):
    """Criterion 3: what separates a duplicate from a related item."""

    def test_the_same_description_and_the_same_source_is_a_duplicate(self):
        self.assertEqual(self.one(component="Elsewhere", labels="other")[0], "duplicate")

    def test_the_same_description_and_the_same_component_is_a_duplicate(self):
        self.assertEqual(self.one(source="other-document#item-9", labels="other")[0], "duplicate")

    def test_the_same_description_with_nothing_to_back_it_up_is_related(self):
        kind, _, advice, matched = self.one(component="Elsewhere", source="other-document#item-9", labels="other")
        self.assertEqual((kind, advice, matched), ("related", "link", ["description"]))

    def test_the_same_source_component_labels_and_title_with_a_different_description_is_only_related(self):
        kind, level, advice, matched = self.one(title="Monthly churn export for finance", description=OTHER)
        self.assertEqual(matched, ["source", "component", "labels", "title"])
        self.assertEqual((kind, advice), ("related", "link"))

    def test_the_component_alone_is_no_match(self):
        self.assertEqual(self.one(description=OTHER, source="other-document#item-9", labels="other")[0], None)

    def test_the_source_alone_is_no_match(self):
        self.assertEqual(self.one(description=OTHER, component="Elsewhere", labels="other")[0], None)

    def test_the_title_alone_is_no_match(self):
        kind, _, _, matched = self.one(title="Monthly churn export for finance", description=OTHER, component="Elsewhere",
                                       source="other-document#item-9", labels="other")
        self.assertEqual((kind, matched), (None, ["title"]))

    def test_a_title_and_a_label_together_are_no_match(self):
        kind, _, _, matched = self.one(title="Monthly churn export for finance", description=OTHER, component="Elsewhere",
                                       source="other-document#item-9")
        self.assertEqual((kind, matched), (None, ["labels", "title"]))

    def test_a_component_and_a_label_are_related(self):
        self.assertEqual(self.one(description=OTHER, source="other-document#item-9")[0], "related")

    def test_an_item_that_matches_nothing_is_not_listed_at_all(self):
        self.write_catalog(item("WRK-1", "Paint the fence", description=OTHER, component="Garden", labels="outdoors", source="garden-plan#row-1"))
        result = self.find(self.propose())
        self.assertEqual((result["matches"], result["dismissed"], result["searched"]), ([], [], 1))


class EachSignal(Case):
    def signals(self, proposal=None, **fields):
        self.write_catalog(item("WRK-1", fields.pop("title", "Other"), **fields))
        return search.compare(search.read_proposal(self.propose(**(proposal or {}))), search.read_catalog(self.catalog)[0])

    def test_a_description_needs_four_shared_words(self):
        self.assertIs(self.signals({"description": "Export churn monthly."}, description="Monthly churn export, please.")["description"][0], False)

    def test_a_description_needs_half_of_the_shorter_one(self):
        base = "finance monthly export customer "
        signals = self.signals({"description": base + " ".join("word%d" % n for n in range(20))},
                               description=base + " ".join("other%d" % n for n in range(20)))
        self.assertIs(signals["description"][0], False)

    def test_a_short_proposal_matches_a_long_description(self):
        signals = self.signals({"description": "Monthly export of customer churn for finance."},
                               description=TEXT + " " + " ".join("extra%d" % n for n in range(30)))
        self.assertIs(signals["description"][0], True)

    def test_how_strongly_a_description_matched_is_stated(self):
        self.assertRegex(self.signals()["description"][1], r"^\d+ shared words, 100% of the shorter description's \d+ \(needs 50%\)$")

    def test_the_same_document_and_a_different_item_is_not_the_same_source(self):
        signals = self.signals(source="finance-requests#item-2")
        self.assertIs(signals["source"][0], False)
        self.assertIn("the same document, a different item", signals["source"][1])

    def test_one_shared_source_among_several_is_enough(self):
        self.assertIs(self.signals(source="other#a; finance-requests#item-1")["source"][0], True)

    def test_components_match_whatever_the_letter_case(self):
        self.assertIs(self.signals(component="reports")["component"][0], True)

    def test_labels_match_on_one_shared_label(self):
        self.assertIs(self.signals(labels="other, Finance")["labels"][0], True)

    def test_what_the_proposal_lacks_is_not_comparable_and_is_not_a_match(self):
        signals = self.signals({"description": "", "component": "", "labels": [], "sources": []})
        self.assertEqual([signals[name][0] for name in ("description", "source", "component", "labels")], [None] * 4)

    def test_what_the_item_lacks_is_not_comparable(self):
        signals = self.signals(description="", component=None, labels=None, source=None)
        self.assertEqual([signals[name][0] for name in ("description", "source", "component", "labels")], [None] * 4)
        self.assertIn("the item has no cited source", signals["source"][1])

    def test_titles_alike_in_another_order_match(self):
        self.assertIs(self.signals(title="Finance export: churn, monthly")["title"][0], True)


class Strength(unittest.TestCase):
    def judged(self, *matched, finished=False):
        return search.judge({name: (name in matched, "") for name, _ in search.WEIGHTS}, finished)[1:]

    def test_points_add_up_to_eleven(self):
        self.assertEqual(self.judged(*[name for name, _ in search.WEIGHTS])[:3], (11, "duplicate", "high"))
        self.assertEqual(search.TOP, 11)

    def test_nine_is_high_and_eight_is_medium(self):
        self.assertEqual(self.judged("description", "source", "component")[:3], (9, "duplicate", "high"))
        self.assertEqual(self.judged("description", "source", "labels")[:3], (8, "duplicate", "medium"))

    def test_five_is_medium_and_four_is_low(self):
        self.assertEqual(self.judged("source", "component")[:3], (5, "related", "medium"))
        self.assertEqual(self.judged("source", "labels")[:3], (4, "related", "low"))

    def test_points_never_make_a_duplicate_without_the_description(self):
        self.assertEqual(self.judged("source", "component", "labels", "title")[:3], (7, "related", "medium"))

    def test_an_open_duplicate_with_high_strength_is_merge(self):
        self.assertEqual(self.judged("description", "source", "component")[3], "merge")

    def test_a_finished_duplicate_is_link(self):
        self.assertEqual(self.judged("description", "source", "component", finished=True)[3], "link")

    def test_a_duplicate_with_medium_strength_is_link(self):
        self.assertEqual(self.judged("description", "component")[3], "link")

    def test_a_related_item_is_never_merge(self):
        self.assertEqual(self.judged("source", "component", "labels", "title")[3], "link")


class Recommendation(Case):
    def test_done_closed_and_cancelled_items_count_as_finished(self):
        for status in ("Done", "closed", "Cancelled", "resolved"):
            self.assertEqual(self.one(status=status)[2], "link", status)

    def test_an_item_in_progress_is_still_open(self):
        self.assertEqual(self.one(status="In progress")[2], "merge")

    def test_the_overall_recommendation_is_the_most_cautious_one(self):
        self.write_catalog(item("WRK-1", "A"), item("WRK-2", "B", description=OTHER))
        result = self.find(self.propose())
        self.assertEqual(sorted(m["advice"] for m in result["matches"]), ["link", "merge"])
        self.assertEqual(result["overall"], "merge")

    def test_no_match_is_proceed(self):
        self.write_catalog(item("WRK-1", "A", description=OTHER, component="Garden", labels="outdoors", source="garden#1"))
        self.assertEqual(self.find(self.propose())["overall"], "proceed")


class TheThreshold(Case):
    """The first stretch goal."""

    def kinds(self, percent):
        result = search.search(search.read_proposal(self.fixture("1-duplicate.json")), search.read_catalog(CATALOG), percent / 100)
        return {m["item"]["id"]: m["kind"] for m in result["matches"]}

    def test_a_lower_threshold_turns_the_borderline_related_item_into_a_duplicate(self):
        self.assertEqual(self.kinds(50)["WRK-102"], "related")
        self.assertEqual(self.kinds(45)["WRK-102"], "duplicate")

    def test_a_higher_threshold_loses_the_near_duplicate(self):
        self.assertEqual(self.kinds(80)["WRK-106"], "duplicate")
        self.assertEqual(self.kinds(90)["WRK-106"], "related")

    def test_the_true_duplicate_survives_every_threshold_tried(self):
        for percent in (30, 50, 70, 90):
            self.assertEqual(self.kinds(percent)["WRK-101"], "duplicate")

    def test_the_threshold_given_is_shown_in_the_output(self):
        _, out = self.run_main("--proposal", self.fixture("1-duplicate.json"), "--description-threshold", "45", catalog=CATALOG)
        self.assertIn("Descriptions match at 45% of the shorter one's words.", out)
        self.assertIn("(needs 45%)", out)

    def test_a_threshold_outside_ten_to_a_hundred_is_refused(self):
        for value in ("5", "150"):
            code, out = self.run_main("--proposal", self.fixture("1-duplicate.json"), "--description-threshold", value, catalog=CATALOG)
            self.assertEqual((code, "whole number from 10 to 100" in out), (2, True))


class TheRelatedMap(Case):
    """The second stretch goal."""

    def test_an_item_related_to_two_others_is_listed_with_them(self):
        self.write_catalog(item("WRK-1", "Hub", description=OTHER), item("WRK-2", "Spoke A", description="Mend the broken gate hinge on the east side today."),
                           item("WRK-3", "Spoke B", description="Order twelve new chairs for the upstairs meeting room."),
                           item("WRK-4", "Loner", description="Plan", component="Garden", labels="outdoors", source="garden#1"))
        found = search.related_map(search.read_catalog(self.catalog))
        self.assertEqual(found["WRK-1"], [("WRK-2", "related"), ("WRK-3", "related")])
        self.assertNotIn("WRK-4", found)

    def test_an_item_is_not_compared_with_itself(self):
        self.write_catalog(item("WRK-1", "Only one"))
        self.assertEqual(search.related_map(search.read_catalog(self.catalog)), {})

    def test_the_command_lists_them_and_changes_nothing(self):
        before = search.sha_of(CATALOG)
        code, out = self.run_main("--related-map", catalog=CATALOG)
        self.assertEqual(code, 0)
        self.assertIn("TWO OR MORE others: 3.", out)
        self.assertRegex(out, r"WRK-101, .*WRK-106 \(duplicate\); WRK-104 \(related\)")
        self.assertEqual(search.sha_of(CATALOG), before)

    def test_a_proposal_and_the_map_together_are_refused(self):
        code, out = self.run_main("--proposal", self.fixture("1-duplicate.json"), "--related-map", catalog=CATALOG)
        self.assertEqual((code, "give either" in out), (2, True))


class NothingChanges(Case):
    """Criterion 6."""

    def test_the_catalog_is_byte_for_byte_the_same_after_a_search(self):
        with open(CATALOG, "rb") as f:
            before = f.read()
        code, out = self.run_main("--proposal", self.fixture("1-duplicate.json"), "--report", self.report, catalog=CATALOG)
        with open(CATALOG, "rb") as f:
            self.assertEqual(f.read(), before)
        self.assertIn("unchanged. SHA-256 before and after: %s" % hashlib.sha256(before).hexdigest(), out)

    def test_a_report_cannot_be_written_over_the_catalog(self):
        self.write_catalog(item("WRK-1", "A"))
        before = search.sha_of(self.catalog)
        code, out = self.run_main("--proposal", self.propose(), "--report", self.catalog)
        self.assertEqual(code, 2)
        self.assertIn("cannot be written over the catalog", out)
        self.assertEqual(search.sha_of(self.catalog), before)

    def test_without_report_no_file_is_written(self):
        self.write_catalog(item("WRK-1", "A"))
        self.propose()
        listed = sorted(os.listdir(self.tmp))
        self.run_main("--proposal", self.proposal_path)
        self.assertEqual(sorted(os.listdir(self.tmp)), listed)

    def test_two_searches_print_the_same(self):
        args = ("--proposal", self.fixture("1-duplicate.json"))
        self.assertEqual(self.run_main(*args, catalog=CATALOG), self.run_main(*args, catalog=CATALOG))

    def test_the_search_has_no_code_that_could_contact_anything(self):
        with open(os.path.join(os.path.dirname(HERE), "search.py"), encoding="utf-8") as f:
            source = f.read()
        imported = {a or b for a, b in re.findall(r"^(?:import (\w+)|from (\w+) import)", source, re.M)}
        self.assertEqual(imported, {"argparse", "hashlib", "json", "os", "re", "sys"})
        self.assertNotIn("os.environ", source)


class AwkwardCatalogs(Case):
    def stopped(self, expect, *items):
        self.write_catalog(*items)
        code, out = self.run_main("--proposal", self.propose())
        self.assertEqual(code, 2, out)
        self.assertIn(expect, out)
        self.assertIn("Nothing was searched", out)

    def test_two_items_with_one_id_stop_the_search(self):
        self.stopped("two items with the id WRK-1", item("WRK-1", "A"), item("WRK-1", "B"))

    def test_a_heading_that_is_not_an_id_and_a_title_stops_the_search(self):
        self.stopped('is not "## ID: title"', item("WRK-1", "A"), "## Just a heading\n\ntext\n")

    def test_an_item_with_no_status_stops_the_search(self):
        self.stopped("has no status", item("WRK-1", "A").replace("- Status: open\n", ""))

    def test_an_empty_catalog_stops_the_search(self):
        with open(self.catalog, "w", encoding="utf-8") as f:
            f.write("# Nothing here\n")
        code, out = self.run_main("--proposal", self.propose())
        self.assertEqual((code, "holds no work item" in out), (2, True))

    def test_a_missing_catalog_stops_the_search(self):
        code, out = self.run_main("--proposal", self.propose(), catalog=os.path.join(self.tmp, "absent.md"))
        self.assertEqual((code, "there is no catalog" in out), (2, True))

    def test_a_description_of_several_paragraphs_is_read_whole(self):
        self.write_catalog(item("WRK-1", "A", description="Send finance a monthly export.\n\nOf customer churn by region and plan.\n\nFrom the billing warehouse."))
        self.assertIn("warehouse", search.read_catalog(self.catalog)[0]["description"])
        self.assertEqual(self.find(self.propose())["matches"][0]["kind"], "duplicate")

    def test_a_line_in_a_description_that_looks_like_a_field_is_not_taken_as_one(self):
        self.write_catalog(item("WRK-1", "A", description="Send finance the export.\n\n- Status: done\n- Component: Garden"))
        found = search.read_catalog(self.catalog)[0]
        self.assertEqual((found["status"], found["component"]), ("open", "Reports"))


class Proposals(Case):
    def setUp(self):
        super().setUp()
        self.write_catalog(item("WRK-1", "A"))

    def refused(self, text, expect):
        with open(self.proposal_path, "w", encoding="utf-8") as f:
            f.write(text)
        code, out = self.run_main("--proposal", self.proposal_path)
        self.assertEqual(code, 2)
        self.assertIn(expect, out)

    def test_a_proposal_needs_a_title(self):
        self.refused(json.dumps({"description": "x"}), "needs a title")

    def test_an_unknown_name_is_refused(self):
        self.refused(json.dumps({"title": "x", "run": "rm"}), "only these names")

    def test_a_file_that_is_not_json_is_refused(self):
        self.refused("title: x", "not JSON")

    def test_a_title_alone_is_enough_to_search(self):
        with open(self.proposal_path, "w", encoding="utf-8") as f:
            json.dump({"title": "Something"}, f)
        code, out = self.run_main("--proposal", self.proposal_path)
        self.assertEqual(code, 0)
        self.assertIn("RESULT: NO MATCH.", out)


class Report(Case):
    def written(self, *args):
        code, out = self.run_main("--proposal", self.fixture("1-duplicate.json"), "--report", self.report, *args, catalog=CATALOG)
        self.assertEqual(code, 0)
        with open(self.report, encoding="utf-8") as f:
            return f.read(), out

    def test_every_match_has_its_fields_how_strongly_a_strength_and_one_of_the_three_recommendations(self):
        text, _ = self.written()
        parts = text.split("\n### Match ")[1:]
        self.assertEqual(len(parts), 5)
        for part in parts:
            self.assertEqual(len(re.findall(r"^\| (?:Description|Source|Component|Labels|Title) \| (?:yes|no|not comparable) \| \d \| .+ \|$", part, re.M)), 5)
            self.assertRegex(part, r"\*\*Strength: (high|medium|low)\*\* \(\d+ of 11 points")
            self.assertRegex(part, r"\*\*Recommendation: (merge|link|proceed)\.\*\*")
            self.assertRegex(part, r"- \*\*(Duplicate|Related)\*\*, because ")

    def test_the_report_says_why_each_kind(self):
        text, _ = self.written()
        self.assertIn("**Duplicate**, because the descriptions say the same thing, and the source and component are the same too.", text)
        self.assertIn("**Related**, because source and labels match, but the descriptions do not say the same thing", text)

    def test_the_report_states_the_rule(self):
        text, _ = self.written()
        self.assertIn("A rule, not the points, decides", text)
        self.assertIn("A matching title is never enough.", text)

    def test_without_a_decision_the_report_says_none_was_made(self):
        text, out = self.written()
        self.assertIn("Not yet decided.", text)
        self.assertNotIn("**Decision:", text)
        self.assertIn("with no decision yet", out)

    def test_a_decision_is_recorded_as_the_persons_and_changes_nothing_else(self):
        plain, _ = self.written()
        decided, _ = self.written("--decision", "link", "--decision-note", "Ask the other team | first.")
        cut = "\n## The decision\n"
        self.assertEqual(plain.split(cut)[0], decided.split(cut)[0])
        self.assertIn("**Decision: link.**", decided)
        self.assertIn("recommended merge, which is not the decision", decided)
        self.assertIn("Ask the other team \\| first.", decided)

    def test_a_decision_must_be_one_of_the_three_words(self):
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            self.run_main("--proposal", self.fixture("1-duplicate.json"), "--report", self.report, "--decision", "archive", catalog=CATALOG)

    def test_a_decision_needs_a_report(self):
        code, out = self.run_main("--proposal", self.fixture("1-duplicate.json"), "--decision", "link", catalog=CATALOG)
        self.assertEqual((code, "needs --report" in out), (2, True))

    def test_catalog_titles_cannot_break_the_report(self):
        self.write_catalog(item("WRK-1", "# Heading | [link](http://x) <b>`code`</b>"))
        code, _ = self.run_main("--proposal", self.propose(), "--report", self.report)
        with open(self.report, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("\\# Heading \\| \\[link\\](http://x) &lt;b&gt;\\`code\\`&lt;/b&gt;", text)
        self.assertNotIn("\n# Heading", text)

    def test_the_no_match_report_says_no_match(self):
        code, _ = self.run_main("--proposal", self.fixture("2-no-match.json"), "--report", self.report, catalog=CATALOG)
        with open(self.report, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("## Result: no match", text)
        self.assertIn("overall recommendation: proceed", text)
        self.assertNotIn("### Match", text)


if __name__ == "__main__":
    unittest.main()
