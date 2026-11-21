"""Tests for the cross-board duplicate search, search.py. Local files only, in temporary folders.

Run from the repository root:
    python3 -m unittest discover -s participant/skills/trello-duplicate-search/tests -v
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

FIXTURE = os.path.join(search.ROOT, "participant", "context", "trello", "duplicates")
ONE, TWO = "70b0000000000000000000a1", "70b0000000000000000000a2"
ADA, BO = "5f00000000000000000000a1", "5f00000000000000000000a2"
TEXT = "Send finance a monthly export of customer churn by region and plan from the billing warehouse."
ITEMS = ("Write the churn query", "Schedule the monthly export", "Tell finance where the file lands")


def record(card_id, board, name, desc=TEXT, labels=("finance",), members=(ADA,), checklist=ITEMS, due="2026-12-04T17:00:00.000Z",
           closed=False, done=False, list_id="71a0000000000000000000a1", leave_out=()):
    """One card record in the format trello-card/1, as the card reader writes it."""
    front = {"format": "trello-card/1", "id": card_id, "idBoard": board, "idList": list_id, "name": name, "closed": closed, "pos": 100,
             "due": due, "dueComplete": done, "labels": [{"id": "73e%s%d" % (board[-2:], n), "name": label, "color": "blue"}
                                                         for n, label in enumerate(labels)],
             "idMembers": list(members)}
    for key in leave_out:
        del front[key]
    fence = "````" if "```" in desc else "```"
    body = ["# x", "", "## Description", ""] + ([fence + "text", desc, fence] if desc else ["(empty)"]) + ["", "## Checklists", ""]
    if checklist:
        body += ['### Checklist "To do"', "", "Checklist `74d1`, position `1`. 0 of %d items complete." % len(checklist), ""]
        body += ["- [ ] %s (item `75f%d`, state `incomplete`, position `%d`)" % (json.dumps(item), n, n) for n, item in enumerate(checklist)]
    else:
        body += ["none"]
    body += ["", "## Comments", "", "none", ""]
    return "---\n" + "".join("%s: %s\n" % (key, json.dumps(value)) for key, value in front.items()) + "---\n\n" + "\n".join(body)


class Case(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name
        self.boards = os.path.join(self.tmp, "boards")
        os.makedirs(self.boards)
        self.proposal_path = os.path.join(self.tmp, "proposal.json")

    def board(self, folder, board_id, *cards, lists=None):
        path = os.path.join(self.boards, folder)
        os.makedirs(os.path.join(path, "cards"), exist_ok=True)
        with open(os.path.join(path, "board.json"), "w", encoding="utf-8") as f:
            json.dump({"board": {"id": board_id, "name": "Board " + folder},
                       "lists": lists or [{"id": "71a0000000000000000000a1", "name": "To do", "pos": 1, "closed": False}]}, f)
        for number, text in enumerate(cards, 1):
            with open(os.path.join(path, "cards", "%d.md" % number), "w", encoding="utf-8") as f:
                f.write(text)
        self.rebuild(folder)
        return path

    def rebuild(self, folder):
        path = os.path.join(self.boards, folder)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(index.main(["build", "--records", path, "--out", path]), 0)

    def two_boards(self, *cards_on_two, one=()):
        """Board one, where the proposal goes, and board two, holding the cards under test."""
        self.board("one", ONE, *one)
        self.board("two", TWO, *cards_on_two)

    def use_fixture(self):
        shutil.rmtree(self.boards)
        shutil.copytree(os.path.join(FIXTURE, "boards"), self.boards)

    def propose(self, **fields):
        proposal = {"name": "Monthly churn export for finance", "board": ONE, "desc": TEXT, "labels": ["finance"], "members": [ADA],
                    "checklist": list(ITEMS), "due": "2026-12-04"}
        proposal.update(fields)
        with open(self.proposal_path, "w", encoding="utf-8") as f:
            json.dump({key: value for key, value in proposal.items() if value is not None or key == "due"}, f)
        return self.proposal_path

    def find(self, path=None):
        return search.search(search.read_proposal(path or self.proposal_path), self.boards)

    def run_main(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = search.main(list(args) + ["--boards", self.boards])
        return code, out.getvalue()

    def fixture_proposal(self, name):
        return os.path.join(FIXTURE, "proposals", name)

    def snapshot(self):
        found = {}
        for base, _, names in os.walk(self.boards):
            for name in names:
                with open(os.path.join(base, name), "rb") as f:
                    found[os.path.join(base, name)] = hashlib.sha256(f.read()).hexdigest()
        return found


def ids(found):
    return [c["entry"]["id"][-3:] for c in found]


class TheFixture(Case):
    """The three searches the quest asks for, on the two made-up boards."""

    def setUp(self):
        super().setUp()
        self.use_fixture()

    def test_the_duplicate_with_a_different_name_on_another_board_is_found(self):
        result = self.find(self.fixture_proposal("1-duplicate-on-another-board.json"))
        top = result["candidates"][0]
        self.assertEqual(top["entry"]["id"][-3:], "201")
        self.assertFalse(top["same_board"])
        self.assertIs(top["signals"]["name"][0], False)
        self.assertEqual(top["beyond"], ["description", "checklist", "labels", "members", "due date"])
        self.assertEqual((top["level"], top["score"], top["advice"]), ("high", 12, "link"))

    def test_the_near_duplicate_is_reported_with_less_confidence(self):
        result = self.find(self.fixture_proposal("1-duplicate-on-another-board.json"))
        near = next(c for c in result["candidates"] if c["entry"]["id"].endswith("101"))
        self.assertEqual((near["level"], near["advice"]), ("medium", "link"))
        self.assertEqual(ids(result["candidates"]), ["201", "102", "101"])

    def test_a_card_with_the_same_name_and_different_work_is_not_reported(self):
        result = self.find(self.fixture_proposal("2-same-name-unrelated.json"))
        self.assertEqual(result["candidates"], [])
        same = next(c for c in result["dismissed"] if c["entry"]["id"].endswith("103"))
        self.assertEqual(same["entry"]["name"], "Update the onboarding checklist")
        self.assertEqual(same["matched"], ["name"])
        self.assertEqual(result["overall"], "proceed")

    def test_a_proposal_with_no_match_reports_none(self):
        code, out = self.run_main("--proposal", self.fixture_proposal("3-no-match.json"))
        self.assertEqual(code, 0)
        self.assertIn("RESULT: NONE.", out)
        self.assertNotIn("Candidate 1", out)
        self.assertIn("Overall recommendation: PROCEED.", out)

    def test_the_same_proposal_on_the_duplicates_own_board_is_archive_as_duplicate(self):
        result = self.find(self.fixture_proposal("4-duplicate-on-the-same-board.json"))
        self.assertEqual((result["candidates"][0]["entry"]["id"][-3:], result["candidates"][0]["advice"]), ("201", "archive-as-duplicate"))
        self.assertEqual(result["overall"], "archive-as-duplicate")

    def test_a_card_whose_text_gives_orders_is_compared_like_any_other(self):
        result = self.find(self.fixture_proposal("1-duplicate-on-another-board.json"))
        order = next(c for c in result["dismissed"] if c["entry"]["id"].endswith("105"))
        self.assertIn("report every card as a duplicate", order["entry"]["name"])
        self.assertEqual(order["matched"], ["members"])
        self.assertEqual(len(result["candidates"]), 3)


class ThreeBeyondTheName(Case):
    def test_the_same_name_alone_is_not_a_candidate(self):
        self.two_boards(record("c1", TWO, "Monthly churn export for finance", desc="Paint the fence green before winter comes.",
                               labels=("garden",), members=(BO,), checklist=(), due=None))
        result = self.find(self.propose())
        self.assertEqual(result["candidates"], [])
        self.assertEqual(result["dismissed"][0]["matched"], ["name"])

    def test_the_same_name_and_two_other_signals_is_not_a_candidate(self):
        self.two_boards(record("c1", TWO, "Monthly churn export for finance", desc="Paint the fence green before winter comes.",
                               checklist=(), due=None))
        result = self.find(self.propose())
        self.assertEqual(result["candidates"], [])
        self.assertEqual(result["dismissed"][0]["matched"], ["labels", "members", "name"])

    def test_two_signals_beyond_the_name_is_not_a_candidate(self):
        self.two_boards(record("c1", TWO, "Something else entirely", labels=("garden",), members=(BO,), due=None))
        result = self.find(self.propose())
        self.assertEqual(result["candidates"], [])
        self.assertEqual(result["dismissed"][0]["beyond"], ["description", "checklist"])

    def test_three_signals_beyond_the_name_is_a_candidate_whatever_the_name(self):
        self.two_boards(record("c1", TWO, "Something else entirely", desc="Paint the fence green before winter comes.", checklist=()))
        result = self.find(self.propose())
        self.assertEqual(result["candidates"][0]["beyond"], ["labels", "members", "due date"])
        self.assertEqual((result["candidates"][0]["score"], result["candidates"][0]["level"]), (5, "low"))

    def test_a_card_that_matches_nothing_is_not_listed_at_all(self):
        self.two_boards(record("c1", TWO, "Paint the fence", desc="Paint the fence green before winter comes.", labels=("garden",),
                               members=(BO,), checklist=("Buy paint",), due="2027-03-01T09:00:00.000Z"))
        result = self.find(self.propose())
        self.assertEqual((result["candidates"], result["dismissed"], result["searched"]), ([], [], 1))


class AcrossBoards(Case):
    def test_every_board_in_the_folder_is_searched(self):
        self.board("one", ONE, record("c1", ONE, "Unrelated", desc="Paint the fence.", labels=(), members=(), checklist=(), due=None))
        self.board("two", TWO, record("c2", TWO, "Churn numbers for the finance team"))
        self.board("three", "70b0000000000000000000a3", record("c3", "70b0000000000000000000a3", "Finance wants churn monthly"))
        result = self.find(self.propose())
        self.assertEqual(result["searched"], 3)
        self.assertEqual(sorted(c["board"]["folder"] for c in result["candidates"]), ["three", "two"])

    def test_a_label_is_matched_by_name_because_its_id_differs_on_each_board(self):
        self.two_boards(record("c1", TWO, "Other", desc="Paint the fence.", labels=("Finance",), checklist=(), due=None))
        result = self.find(self.propose())
        self.assertIs(result["dismissed"][0]["signals"]["labels"][0], True)

    def test_the_board_the_card_would_go_on_must_be_searched(self):
        self.two_boards(record("c1", TWO, "Other"))
        code, out = self.run_main("--proposal", self.propose(board="70b0000000000000000000ff"))
        self.assertEqual(code, 2)
        self.assertIn("not among the boards searched", out)

    def test_a_folder_that_is_not_a_board_stops_the_search(self):
        self.two_boards(record("c1", TWO, "Other"))
        os.makedirs(os.path.join(self.boards, "stray"))
        code, out = self.run_main("--proposal", self.propose())
        self.assertEqual(code, 2)
        self.assertIn("A board left out could hide a duplicate", out)

    def test_the_same_board_in_two_folders_stops_the_search(self):
        self.two_boards(record("c1", TWO, "Other"))
        shutil.copytree(os.path.join(self.boards, "two"), os.path.join(self.boards, "two-again"))
        self.rebuild("two-again")
        code, out = self.run_main("--proposal", self.propose())
        self.assertEqual(code, 2)
        self.assertIn("hold the same board", out)


class EachSignal(Case):
    def one(self, proposal=None, **card):
        self.two_boards(record("c1", TWO, card.pop("name", "Other"), **card))
        proposal = search.read_proposal(self.propose(**(proposal or {})))
        board = next(b for b in search.read_boards(self.boards) if b["folder"] == "two")
        entry = board["cards"][0]
        return search.compare(proposal, entry, search.read_record(os.path.join(board["path"], "cards", entry["file"])))

    def test_description_needs_four_shared_words(self):
        signals = self.one({"desc": "Export churn monthly."}, desc="Monthly churn export, please.")
        self.assertIs(signals["description"][0], False)

    def test_description_needs_half_of_the_shorter_one(self):
        long_one = "finance monthly export customer " + " ".join("word%d" % n for n in range(20))
        signals = self.one({"desc": long_one}, desc="finance monthly export customer " + " ".join("other%d" % n for n in range(20)))
        self.assertIs(signals["description"][0], False)

    def test_a_short_proposal_matches_a_long_description(self):
        signals = self.one({"desc": "Monthly export of customer churn for finance."}, desc=TEXT + " " + " ".join("extra%d" % n for n in range(30)))
        self.assertIs(signals["description"][0], True)

    def test_one_alike_checklist_item_is_not_enough(self):
        signals = self.one(checklist=("Write the churn query", "Buy paint", "Wash the brushes"))
        self.assertIs(signals["checklist"][0], False)

    def test_two_alike_items_and_half_of_the_shorter_checklist_matches(self):
        signals = self.one(checklist=("Write the churn query", "Schedule the monthly export", "Buy paint", "Wash the brushes"))
        self.assertIs(signals["checklist"][0], True)

    def test_two_alike_items_under_half_of_the_shorter_checklist_does_not_match(self):
        five = ["Write the churn query", "Schedule the monthly export", "Alpha beta gamma", "Delta epsilon zeta", "Eta theta iota"]
        signals = self.one({"checklist": five}, checklist=five[:2] + ["Buy green paint", "Wash every brush", "Mend broken gate", "Sweep stone path"])
        self.assertIs(signals["checklist"][0], False)

    def test_a_checklist_item_with_quotes_in_it_is_read(self):
        signals = self.one({"checklist": ['Write the "churn" query', "Schedule the monthly export"]},
                           checklist=('Write the "churn" query', "Schedule the monthly export"))
        self.assertIs(signals["checklist"][0], True)

    def test_a_label_with_no_name_is_not_compared(self):
        signals = self.one(labels=("",))
        self.assertIsNone(signals["labels"][0])

    def test_members_match_on_the_same_member_id(self):
        self.assertIs(self.one(members=(BO, ADA))["members"][0], True)

    def test_members_do_not_match_on_different_ids(self):
        self.assertIs(self.one(members=(BO,))["members"][0], False)

    def test_due_dates_three_days_apart_match(self):
        self.assertIs(self.one(due="2026-12-07T23:00:00.000Z")["due date"][0], True)

    def test_due_dates_four_days_apart_do_not_match(self):
        self.assertIs(self.one(due="2026-12-08T01:00:00.000Z")["due date"][0], False)

    def test_what_one_side_lacks_is_not_comparable_and_is_not_a_match(self):
        signals = self.one({"desc": "", "labels": [], "members": [], "checklist": [], "due": None})
        self.assertEqual([signals[name][0] for name, _ in search.BEYOND_NAME], [None] * 5)

    def test_what_the_card_lacks_is_not_comparable(self):
        signals = self.one(name="Monthly churn export for finance", desc="", labels=(), members=(), checklist=(), due=None)
        self.assertEqual([signals[name][0] for name, _ in search.BEYOND_NAME], [None] * 5)

    def test_a_record_with_no_labels_field_is_still_compared_on_the_rest(self):
        signals = self.one(leave_out=("labels",))
        self.assertIsNone(signals["labels"][0])
        self.assertIn("no labels field", signals["labels"][1])
        self.assertIs(signals["members"][0], True)

    def test_a_description_holding_a_code_fence_is_read_whole(self):
        text = "Send finance a monthly export.\n```\nselect churn from billing warehouse by region\n```\nGroup by customer plan."
        signals = self.one({"desc": text}, desc=text)
        self.assertIn("100%", signals["description"][1])
        self.assertIn("warehouse", signals["description"][1])

    def test_names_alike_in_other_words_order_match(self):
        self.assertIs(self.one(name="Finance export: churn, monthly")["name"][0], True)


class Confidence(unittest.TestCase):
    def judged(self, *matched, same_board=False, finished=None):
        signals = {name: (name in matched, "") for name, _ in search.WEIGHTS}
        return search.judge(signals, same_board, finished)[2:]

    def test_the_least_three_signals_can_score_is_low(self):
        self.assertEqual(self.judged("labels", "members", "due date"), (5, "low", "link"))

    def test_six_is_low_and_seven_is_medium(self):
        self.assertEqual(self.judged("labels", "members", "due date", "name")[:2], (6, "low"))
        self.assertEqual(self.judged("checklist", "labels", "members")[:2], (7, "medium"))

    def test_nine_is_medium_and_ten_is_high(self):
        self.assertEqual(self.judged("description", "checklist", "labels")[:2], (9, "medium"))
        self.assertEqual(self.judged("description", "checklist", "labels", "name")[:2], (10, "high"))

    def test_everything_matching_is_thirteen(self):
        self.assertEqual(self.judged(*[name for name, _ in search.WEIGHTS])[:2], (13, "high"))
        self.assertEqual(search.TOP, 13)

    def test_the_name_adds_a_point_but_never_makes_a_third_signal(self):
        self.assertEqual(self.judged("description", "checklist", "name"), (8, None, None))

    def test_high_on_another_board_is_link(self):
        self.assertEqual(self.judged("description", "checklist", "labels", "members")[2], "link")

    def test_high_and_open_on_the_same_board_is_archive_as_duplicate(self):
        self.assertEqual(self.judged("description", "checklist", "labels", "members", same_board=True)[2], "archive-as-duplicate")

    def test_medium_or_low_on_the_same_board_is_link(self):
        self.assertEqual(self.judged("checklist", "labels", "members", same_board=True)[2], "link")
        self.assertEqual(self.judged("labels", "members", "due date", same_board=True)[2], "link")

    def test_a_finished_card_is_proceed_on_any_board(self):
        for same_board in (True, False):
            self.assertEqual(self.judged("description", "checklist", "labels", "members", same_board=same_board, finished="archived")[2], "proceed")


class Finished(Case):
    def advice(self, **card):
        lists = [{"id": "71a0000000000000000000a1", "name": "To do", "pos": 1, "closed": False},
                 {"id": "71a0000000000000000000a9", "name": "Dropped", "pos": 2, "closed": True}]
        self.board("one", ONE, record("c1", ONE, "Churn for finance", **card), lists=lists)
        candidate = self.find(self.propose())["candidates"][0]
        return candidate["advice"], candidate["finished"]

    def test_an_open_card_on_the_same_board_is_archive_as_duplicate(self):
        self.assertEqual(self.advice(), ("archive-as-duplicate", None))

    def test_an_archived_card_is_proceed(self):
        self.assertEqual(self.advice(closed=True), ("proceed", "archived"))

    def test_a_card_on_an_archived_list_is_proceed(self):
        self.assertEqual(self.advice(list_id="71a0000000000000000000a9"), ("proceed", "on an archived list"))

    def test_a_card_marked_complete_is_proceed(self):
        self.assertEqual(self.advice(done=True), ("proceed", "marked complete"))

    def test_the_overall_recommendation_is_the_most_cautious_one(self):
        self.board("one", ONE, record("c1", ONE, "Churn for finance", closed=True), record("c2", ONE, "Churn again"))
        self.board("two", TWO, record("c3", TWO, "Churn elsewhere"))
        result = self.find(self.propose())
        self.assertEqual(sorted(c["advice"] for c in result["candidates"]), ["archive-as-duplicate", "link", "proceed"])
        self.assertEqual(result["overall"], "archive-as-duplicate")


class StaleIndex(Case):
    def setUp(self):
        super().setUp()
        self.two_boards(record("c1", TWO, "Churn for finance"))
        self.propose()
        self.card = os.path.join(self.boards, "two", "cards", "1.md")

    def stopped(self):
        before = self.snapshot()
        code, out = self.run_main("--proposal", self.proposal_path)
        self.assertEqual(code, 2)
        self.assertIn("does not match its records", out)
        self.assertIn("Nothing was searched", out)
        self.assertNotIn("Candidate", out)
        self.assertEqual(self.snapshot(), before, "a stale index must not be rebuilt by the search")

    def test_a_changed_record_stops_the_search(self):
        with open(self.card, "a", encoding="utf-8") as f:
            f.write("\nA line added after the index was built.\n")
        self.stopped()

    def test_an_added_record_stops_the_search(self):
        with open(os.path.join(self.boards, "two", "cards", "2.md"), "w", encoding="utf-8") as f:
            f.write(record("c2", TWO, "Added later"))
        self.stopped()

    def test_a_hand_edited_index_stops_the_search(self):
        path = os.path.join(self.boards, "two", "index.json")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        with open(path, "w", encoding="utf-8") as f:
            f.write(text.replace("Churn for finance", "Edited by hand"))
        self.stopped()

    def test_a_missing_index_stops_the_search(self):
        os.remove(os.path.join(self.boards, "one", "index.json"))
        self.stopped()

    def test_after_a_rebuild_the_search_runs(self):
        with open(self.card, "a", encoding="utf-8") as f:
            f.write("\nA line added.\n")
        self.rebuild("two")
        self.assertEqual(self.run_main("--proposal", self.proposal_path)[0], 0)


class NothingChanges(Case):
    def setUp(self):
        super().setUp()
        self.use_fixture()
        self.proposal = self.fixture_proposal("1-duplicate-on-another-board.json")

    def test_a_search_leaves_every_index_and_record_as_it_was(self):
        before = self.snapshot()
        code, out = self.run_main("--proposal", self.proposal, "--report", os.path.join(self.tmp, "report.md"))
        self.assertEqual(code, 0)
        self.assertEqual(self.snapshot(), before)
        self.assertIn("unchanged. All %d files" % len(before), out)

    def test_the_index_hashes_printed_are_the_real_ones(self):
        _, out = self.run_main("--proposal", self.proposal)
        with open(os.path.join(self.boards, "support-team", "index.json"), "rb") as f:
            self.assertIn(hashlib.sha256(f.read()).hexdigest(), out)

    def test_a_report_cannot_be_written_inside_the_boards_folder(self):
        before = self.snapshot()
        code, out = self.run_main("--proposal", self.proposal, "--report", os.path.join(self.boards, "support-team", "index.md"))
        self.assertEqual(code, 2)
        self.assertIn("cannot be written inside the boards folder", out)
        self.assertEqual(self.snapshot(), before)

    def test_without_report_no_file_is_written_anywhere(self):
        listed = sorted(os.listdir(self.tmp))
        self.run_main("--proposal", self.proposal)
        self.assertEqual(sorted(os.listdir(self.tmp)), listed)

    def test_two_searches_print_the_same(self):
        self.assertEqual(self.run_main("--proposal", self.proposal), self.run_main("--proposal", self.proposal))


class Proposals(Case):
    def setUp(self):
        super().setUp()
        self.two_boards(record("c1", TWO, "Other"))

    def refused(self, text, expect):
        with open(self.proposal_path, "w", encoding="utf-8") as f:
            f.write(text)
        code, out = self.run_main("--proposal", self.proposal_path)
        self.assertEqual(code, 2)
        self.assertIn(expect, out)

    def test_a_proposal_needs_a_name(self):
        self.refused(json.dumps({"board": ONE, "name": "  "}), "needs a name")

    def test_a_proposal_needs_a_board(self):
        self.refused(json.dumps({"name": "x"}), "the id of the board")

    def test_an_unknown_name_is_refused(self):
        self.refused(json.dumps({"name": "x", "board": ONE, "run": "rm"}), "only these names")

    def test_a_due_date_must_be_a_date(self):
        self.refused(json.dumps({"name": "x", "board": ONE, "due": "next week"}), "YYYY-MM-DD")

    def test_a_file_that_is_not_json_is_refused(self):
        self.refused("name: x", "not JSON")

    def test_a_missing_file_is_refused(self):
        code, out = self.run_main("--proposal", os.path.join(self.tmp, "absent.json"))
        self.assertEqual((code, "no proposal file" in out), (2, True))

    def test_a_name_and_a_board_are_enough(self):
        with open(self.proposal_path, "w", encoding="utf-8") as f:
            json.dump({"name": "Other", "board": ONE}, f)
        code, out = self.run_main("--proposal", self.proposal_path)
        self.assertEqual(code, 0)
        self.assertIn("RESULT: NONE.", out)


class Report(Case):
    def setUp(self):
        super().setUp()
        self.use_fixture()
        self.proposal = self.fixture_proposal("1-duplicate-on-another-board.json")
        self.report = os.path.join(self.tmp, "report.md")

    def written(self, *args):
        code, out = self.run_main("--proposal", self.proposal, "--report", self.report, *args)
        self.assertEqual(code, 0)
        with open(self.report, encoding="utf-8") as f:
            return f.read(), out

    def test_every_candidate_has_signals_confidence_and_one_of_the_three_recommendations(self):
        text, _ = self.written()
        parts = text.split("\n### Candidate ")[1:]
        self.assertEqual(len(parts), 3)
        for part in parts:
            self.assertGreaterEqual(len(re.findall(r"^\| (?:Description|Checklist|Labels|Members|Due date) \| yes \|", part, re.M)), 3)
            self.assertRegex(part, r"\*\*Confidence: (high|medium|low)\*\* \(\d+ of 13 points")
            self.assertRegex(part, r"\*\*Recommendation: (link|archive-as-duplicate|proceed)\.\*\*")

    def test_the_report_says_which_board_each_candidate_is_on(self):
        text, _ = self.written()
        self.assertIn("- Board: Made-up support team board, another board", text)
        self.assertIn("- Board: Made-up platform team board, the same board as the proposal", text)

    def test_the_report_states_the_scale(self):
        text, _ = self.written()
        self.assertIn("**high** 10 to 13", text)
        self.assertIn("at least three of the five signals beyond the name", text)

    def test_without_a_decision_the_report_says_none_was_made(self):
        text, out = self.written()
        self.assertIn("Not yet decided.", text)
        self.assertNotIn("**Decision:", text)
        self.assertIn("with no decision yet", out)

    def test_a_decision_is_recorded_as_the_persons(self):
        text, _ = self.written("--decision", "link", "--decision-note", "Both teams keep a card | and link them.")
        self.assertIn("**Decision: link.**", text)
        self.assertIn("Made by a person", text)
        self.assertIn("Both teams keep a card \\| and link them.", text)

    def test_a_decision_does_not_change_what_the_search_recommends(self):
        plain, _ = self.written()
        decided, _ = self.written("--decision", "proceed")
        cut = "\n## The decision\n"
        self.assertEqual(plain.split(cut)[0], decided.split(cut)[0])
        self.assertIn("recommended link, which is not the decision", decided)

    def test_a_decision_must_be_one_of_the_three_words(self):
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            self.run_main("--proposal", self.proposal, "--report", self.report, "--decision", "merge")

    def test_a_decision_needs_a_report(self):
        code, out = self.run_main("--proposal", self.proposal, "--decision", "link")
        self.assertEqual((code, "needs --report" in out), (2, True))

    def test_card_names_cannot_break_the_report(self):
        self.board("extra", "70b0000000000000000000a3",
                   record("c9", "70b0000000000000000000a3", "# Heading | [link](http://x) <b>`code`</b>",
                          desc="Add an Export button to the customers page that downloads the customer list as a CSV file.",
                          labels=("export",), members=("5f0000000000000000000001",), checklist=(), due=None))
        text, _ = self.written()
        self.assertIn("\\# Heading \\| \\[link\\](http://x) &lt;b&gt;\\`code\\`&lt;/b&gt;", text)
        self.assertNotIn("\n# Heading", text)

    def test_the_same_search_writes_the_same_report(self):
        first, _ = self.written()
        second, _ = self.written()
        self.assertEqual(first, second)


class NoNetwork(unittest.TestCase):
    def test_the_search_has_no_code_that_could_contact_anything(self):
        with open(os.path.join(os.path.dirname(HERE), "search.py"), encoding="utf-8") as f:
            source = f.read()
        imported = set(re.findall(r"^(?:import (\w+)|from (\w+) import)", source, re.M))
        imported = {a or b for a, b in imported}
        self.assertEqual(imported, {"argparse", "datetime", "hashlib", "json", "os", "re", "sys", "index"})

    def test_it_reads_no_credential(self):
        with open(os.path.join(os.path.dirname(HERE), "search.py"), encoding="utf-8") as f:
            self.assertNotIn("environ", f.read())


if __name__ == "__main__":
    unittest.main()
