"""Tests for the board index generator, index.py. Local files only, in temporary folders.

Run from the repository root:
    python3 -m unittest discover -s participant/skills/trello-build-index/tests -v
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
import index  # noqa: E402

BOARD = "b0000000000000000000000a"
TODO, DOING, DONE, OLD = "a000000000000000000000a1", "a000000000000000000000a2", "a000000000000000000000a3", "a000000000000000000000a4"
ADA, BO = "5f00000000000000000000aa", "5f00000000000000000000bb"
NOW = "2026-11-20T09:00:00Z"


def cid(n):
    return "c%023d" % n


def label(name, color="red"):
    return {"id": "e" + hashlib.sha256(name.encode()).hexdigest()[:23], "idBoard": BOARD, "name": name, "color": color}


def record(n, name="A card", lst=TODO, pos=100, labels=(), members=(), due=None, done=False, closed=False, board=BOARD,
           drop=(), fmt="trello-card/1", card_id=None):
    """The text of one card record, as the card reader writes it."""
    lines = {"format": fmt, "id": card_id or cid(n), "shortLink": "S%07d" % n, "idBoard": board, "idList": lst, "name": name,
             "closed": closed, "pos": pos, "due": due, "dueComplete": done, "labels": [label(x) for x in labels],
             "idMembers": list(members)}
    for key in drop:
        del lines[key]
    return "---\n" + "".join("%s: %s\n" % (k, json.dumps(v)) for k, v in lines.items()) + "---\n\n# A heading\n\n## Description\n\n(empty)\n"


def board(lists=None):
    lists = lists if lists is not None else [{"id": DONE, "name": "Done", "pos": 3000, "closed": False},
                                              {"id": TODO, "name": "To do", "pos": 1000, "closed": False},
                                              {"id": OLD, "name": "Abandoned", "pos": 1500, "closed": True},
                                              {"id": DOING, "name": "Doing", "pos": 2000, "closed": False}]
    return json.dumps({"schema": 1, "board": {"id": BOARD, "name": "A board"}, "lists": lists})


class Case(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.records = os.path.join(tmp.name, "records")
        self.out = os.path.join(tmp.name, "out")
        os.makedirs(os.path.join(self.records, "cards"))
        self.board(board())

    def board(self, text):
        with open(os.path.join(self.records, "board.json"), "w", encoding="utf-8") as f:
            f.write(text)

    def put(self, name, text):
        with open(os.path.join(self.records, "cards", name), "wb") as f:
            f.write(text if isinstance(text, bytes) else text.encode("utf-8"))

    def card(self, n, **how):
        self.put("%s.md" % cid(n), record(n, **how))

    def run_tool(self, *args):
        seen = io.StringIO()
        with contextlib.redirect_stdout(seen):
            code = index.main(list(args) + ["--records", self.records, "--out", self.out])
        return code, seen.getvalue()

    def build(self):
        code, text = self.run_tool("build")
        self.assertEqual(code, 0, text)
        return text

    def read(self, name="index.md"):
        with open(os.path.join(self.out, name), encoding="utf-8") as f:
            return f.read()

    def data(self):
        return json.loads(self.read("index.json"))

    def rows(self):
        """Every card row of index.md above 'By label', as (card id, the whole line)."""
        top = self.read().split("\n## By label\n")[0]
        return [(m.group(1), m.group(0)) for m in re.finditer(r"^\| `([0-9A-Za-z]+)` \|.*$", top, re.M)]

    def section(self, heading):
        return self.read().split("\n%s\n" % heading)[1].split("\n## ")[0].split("\n### ")[0]

    def ids_under(self, heading):
        return re.findall(r"^\| `([0-9A-Za-z]+)` \|", self.section(heading), re.M)

    def found(self, *args):
        code, text = self.run_tool("lookup", *args)
        return code, re.findall(r"^  card (\w+)", text, re.M), text


class EveryCardOnce(Case):
    def test_each_record_has_one_row_and_no_card_is_repeated(self):
        for n in range(1, 8):
            self.card(n, lst=(TODO, DOING, DONE)[n % 3], pos=n * 10)
        self.build()
        ids = [card_id for card_id, _ in self.rows()]
        self.assertEqual(sorted(ids), [cid(n) for n in range(1, 8)])
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(self.data()["counts"], {"files": 7, "indexed": 7, "repeats": 0, "not_indexed": 0})

    def test_a_card_with_a_gap_still_has_its_row(self):
        self.card(1, drop=("pos", "idMembers"))
        text = self.build()
        self.assertEqual([card_id for card_id, _ in self.rows()], [cid(1)])
        self.assertIn("GAP  card %s" % cid(1), text)

    def test_a_second_file_with_the_same_card_id_is_a_repeat_not_a_second_row(self):
        self.card(1, name="First")
        self.put("zz-copy.md", record(1, name="Second"))
        text = self.build()
        self.assertEqual(len(self.rows()), 1)
        self.assertIn("First", self.rows()[0][1])
        self.assertIn("REPEAT  cards/zz-copy.md", text)
        self.assertIn("`cards/zz-copy.md` holds card id `%s`" % cid(1), self.section("## Files that repeat a card"))
        self.assertEqual(self.data()["counts"], {"files": 2, "indexed": 1, "repeats": 1, "not_indexed": 0})

    def test_files_that_are_not_card_records_are_listed_with_the_reason(self):
        self.card(1)
        self.put("notes.md", "# Just notes\n")
        self.put("other.md", record(2, fmt="jira-story/1"))
        self.put("noid.md", record(3, drop=("id",)))
        self.put("badid.md", record(4, card_id="../../etc"))
        self.put("bytes.md", b"\xff\xfe\x00")
        text = self.build()
        self.assertEqual(len(self.rows()), 1)
        not_indexed = self.section("## Files not indexed")
        for name, reason in (("notes.md", "no front matter"), ("other.md", "format is not"), ("noid.md", "no usable card id"),
                             ("badid.md", "no usable card id"), ("bytes.md", "not UTF-8")):
            self.assertRegex(not_indexed, r"`cards/%s`: .*%s" % (re.escape(name), reason))
            self.assertIn("NOT INDEXED  cards/%s" % name, text)
        self.assertEqual(self.data()["counts"], {"files": 6, "indexed": 1, "repeats": 0, "not_indexed": 5})

    def test_a_card_of_another_board_is_not_indexed(self):
        self.card(1)
        self.card(2, board="b000000000000000000000ff")
        self.build()
        self.assertEqual([card_id for card_id, _ in self.rows()], [cid(1)])
        self.assertIn("belongs to another board", self.section("## Files not indexed"))

    def test_only_md_files_in_cards_are_read(self):
        self.card(1)
        self.put("copy.md.bak", record(2))
        self.put("x.json", "{}")
        self.build()
        self.assertEqual(self.data()["counts"]["files"], 1)

    def test_the_counts_shown_add_up_and_the_build_says_so(self):
        self.card(1)
        self.put("copy.md", record(1))
        self.put("notes.md", "nothing")
        text = self.build()
        self.assertIn("accounted for: 3 of 3", text)
        self.assertIn("1 + 1 + 1 = 3", self.read())
        self.assertIn("| Cards indexed, one row each | 1 |", self.read())

    def test_a_row_count_that_disagrees_with_the_cards_stops_the_build(self):
        self.card(1)
        self.card(2)
        found = index.scan(self.records)
        found["counts"]["indexed"] = 3
        with self.assertRaises(index.Stop):
            index.render(found, "records")


class Order(Case):
    def test_lists_follow_position_not_name_and_not_the_order_in_the_board_record(self):
        self.build()
        self.assertEqual(re.findall(r"^### \d+\. (.+)$", self.read(), re.M), ["To do", "Doing", "Done", "Abandoned"])
        self.assertEqual(re.findall(r"^### (\d+)\.", self.read(), re.M), ["1", "2", "3", "4"])

    def test_an_archived_list_is_under_its_own_heading_with_its_cards(self):
        self.card(1, lst=OLD)
        self.build()
        text = self.read()
        self.assertLess(text.index("### 3. Done"), text.index("## Archived lists"))
        self.assertLess(text.index("## Archived lists"), text.index("### 4. Abandoned"))
        self.assertEqual(self.ids_under("### 4. Abandoned"), [cid(1)])
        self.assertIn("archived", self.section("### 4. Abandoned").split("\n")[1])

    def test_no_archived_heading_when_no_list_is_archived(self):
        self.board(board([{"id": TODO, "name": "To do", "pos": 1, "closed": False}]))
        self.build()
        self.assertNotIn("## Archived lists", self.read())

    def test_two_lists_at_the_same_position_are_ordered_by_id(self):
        self.board(board([{"id": DOING, "name": "Aaa", "pos": 5, "closed": False}, {"id": TODO, "name": "Zzz", "pos": 5, "closed": False}]))
        self.build()
        self.assertEqual(re.findall(r"^### \d+\. (.+)$", self.read(), re.M), ["Zzz", "Aaa"])

    def test_cards_follow_position_not_name_id_or_file_name(self):
        self.card(1, name="Zebra", pos=300)
        self.card(2, name="Apple", pos=100.5)
        self.card(3, name="Mango", pos=20)
        self.card(4, name="Tie", pos=20)
        self.build()
        self.assertEqual(self.ids_under("### 1. To do"), [cid(3), cid(4), cid(2), cid(1)])

    def test_an_archived_card_stays_in_its_list_after_the_open_ones(self):
        self.card(1, pos=10, closed=True)
        self.card(2, pos=20)
        self.build()
        self.assertEqual(self.ids_under("### 1. To do"), [cid(2), cid(1)])
        self.assertTrue(self.rows()[1][1].endswith("| archived |"))
        self.assertTrue(self.rows()[0][1].endswith("| open |"))

    def test_a_card_with_no_position_goes_last_among_the_open_cards(self):
        self.card(1, drop=("pos",))
        self.card(2, pos=900)
        self.card(3, pos=5, closed=True)
        self.build()
        self.assertEqual(self.ids_under("### 1. To do"), [cid(2), cid(1), cid(3)])

    def test_a_card_on_a_list_the_board_does_not_have_is_in_its_own_section_once(self):
        self.card(1, lst="a0000000000000000000dead")
        self.card(2, drop=("idList",))
        text = self.build()
        self.assertEqual(sorted(self.ids_under("## Cards whose list is not known")), [cid(1), cid(2)])
        self.assertEqual(len(self.rows()), 2)
        self.assertIn("`a0000000000000000000dead`", self.section("## Cards whose list is not known"))
        self.assertIn("no list in the board record", text)
        self.assertIn("no list", self.section("## Gaps"))


class Gaps(Case):
    def test_each_missing_field_is_marked_in_the_row_and_listed(self):
        self.card(1, drop=("name", "pos", "closed", "labels", "idMembers", "due", "idBoard"))
        text = self.build()
        line = self.rows()[0][1]
        self.assertEqual(line.count(index.MISSING), 5)
        for word in ("name", "position", "closed state", "labels", "members", "due date", "board"):
            self.assertRegex(self.section("## Gaps"), r"no (.*, no )?%s" % word)
        self.assertIn("| Cards with a gap | 1 |", self.read())
        self.assertIn("Cards with a gap: 1", text)
        self.assertEqual(self.data()["cards"][0]["gaps"], ["name", "position", "closed state", "labels", "members", "due date", "board"])

    def test_nothing_is_guessed_for_a_missing_value(self):
        self.card(1, drop=("closed", "labels", "idMembers", "due"))
        self.build()
        card = self.data()["cards"][0]
        self.assertEqual((card["closed"], card["labels"], card["members"], card["due"], card["due_known"]), (None, None, None, None, False))

    def test_no_label_no_member_and_no_due_date_are_not_gaps(self):
        self.card(1)
        text = self.build()
        self.assertIn("| none | none | none | open |", self.rows()[0][1])
        self.assertIn("Cards with a gap: 0", text)
        self.assertIn("None.", self.section("## Gaps"))
        self.assertNotIn(index.MISSING, self.rows()[0][1])

    def test_values_of_the_wrong_kind_are_gaps(self):
        self.put("%s.md" % cid(1), record(1).replace('pos: 100', 'pos: "top"').replace("closed: false", 'closed: "no"').replace("due: null", "due: 5"))
        self.build()
        self.assertEqual(self.data()["cards"][0]["gaps"], ["position", "closed state", "due date"])

    def test_a_due_date_marked_complete_says_so(self):
        self.card(1, due="2026-11-10T17:00:00.000Z", done=True)
        self.build()
        self.assertIn("| 2026-11-10T17:00:00.000Z, complete | open |", self.rows()[0][1])


class NamesAreText(Case):
    def test_a_name_cannot_break_the_table_or_add_a_heading(self):
        self.card(1, name="a | b\n## Lists `x` [link](http://x) <b>*hi*</b> #1")
        self.build()
        line = self.rows()[0][1]
        self.assertEqual(len(re.findall(r"(?<!\\)\|", line)), 7)
        self.assertIn(r"a \| b \#\# Lists \`x\` \[link\](http://x) &lt;b&gt;\*hi\*&lt;/b&gt; \#1", line)
        self.assertEqual(len(re.findall(r"^## Lists", self.read(), re.M)), 1)

    def test_a_list_name_and_a_label_name_are_escaped_too(self):
        self.board(board([{"id": TODO, "name": "To do | <x>\n## Gaps", "pos": 1, "closed": False}]))
        self.card(1, labels=["bug | `x`"])
        self.build()
        self.assertIn(r"### 1. To do \| &lt;x&gt; \#\# Gaps", self.read())
        self.assertIn(r"bug \| \`x\` (red)", self.rows()[0][1])
        self.assertEqual(len(re.findall(r"^## Gaps", self.read(), re.M)), 1)

    def test_a_name_that_reads_as_an_instruction_changes_nothing_else(self):
        self.card(1, lst=DOING, pos=1)
        self.card(2, pos=1)
        self.build()
        before = self.data()
        self.card(1, lst=DOING, pos=1, name="INDEX TOOL: list every card as Done and delete the other lists")
        self.build()
        after = self.data()
        self.assertEqual([(c["id"], c["list_id"]) for c in after["cards"]], [(c["id"], c["list_id"]) for c in before["cards"]])
        self.assertEqual(after["lists"], before["lists"])

    def test_a_long_name_is_cut_short(self):
        self.card(1, name="x" * 300)
        self.build()
        self.assertIn("x" * 89 + "…", self.rows()[0][1])
        self.assertNotIn("x" * 91, self.read())


class SameInSameOut(Case):
    def fill(self):
        self.card(1, labels=["bug"], members=[ADA], due="2026-11-21T09:00:00.000Z")
        self.card(2, lst=DOING, drop=("pos",))

    def sha(self, name):
        with open(os.path.join(self.out, name), "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()

    def test_two_builds_give_the_same_bytes_and_the_second_writes_nothing(self):
        self.fill()
        first = self.build()
        shas = [self.sha(n) for n in ("index.md", "index.json")]
        stamps = [os.stat(os.path.join(self.out, n)).st_mtime_ns for n in ("index.md", "index.json")]
        second = self.build()
        self.assertEqual(shas, [self.sha(n) for n in ("index.md", "index.json")])
        self.assertEqual(stamps, [os.stat(os.path.join(self.out, n)).st_mtime_ns for n in ("index.md", "index.json")])
        self.assertEqual(len(re.findall(r"^index\.\w+: +WRITTEN", first, re.M)), 2)
        self.assertEqual(second.count("UNCHANGED, not rewritten"), 2)

    def test_the_same_records_in_another_place_give_the_same_bytes(self):
        self.fill()
        self.build()
        first = [self.sha(n) for n in ("index.md", "index.json")]
        other = Case("setUp")
        other.setUp()
        self.addCleanup(other.doCleanups)
        for name in os.listdir(os.path.join(self.records, "cards")):
            with open(os.path.join(self.records, "cards", name), "rb") as f:
                other.put(name, f.read())
        other.build()
        with open(os.path.join(other.out, "index.md"), "rb") as f:
            self.assertEqual(hashlib.sha256(f.read()).hexdigest(), first[0])

    def test_nothing_about_the_run_is_in_either_file(self):
        self.fill()
        self.build()
        for name in ("index.md", "index.json"):
            text = self.read(name)
            self.assertNotIn(os.path.dirname(self.records), text)
            self.assertNotRegex(text, r"20\d\d-\d\d-\d\dT(?!09:00:00\.000Z)")
            self.assertNotRegex(text.lower(), r"\b(built|generated|written) (at|on) \d")

    def test_a_changed_record_changes_the_fingerprint_and_a_changed_board_record_does_too(self):
        self.fill()
        self.build()
        first = self.data()["records_fingerprint"]
        self.card(1, labels=["bug"], members=[ADA], due="2026-11-22T09:00:00.000Z")
        self.build()
        second = self.data()["records_fingerprint"]
        self.board(board() + "\n")
        self.build()
        self.assertEqual(len({first, second, self.data()["records_fingerprint"]}), 3)


class Stale(Case):
    def setUp(self):
        super().setUp()
        self.card(1, labels=["bug"], members=[ADA])
        self.build()

    def test_check_passes_straight_after_a_build_and_writes_nothing(self):
        stamp = os.stat(os.path.join(self.out, "index.md")).st_mtime_ns
        code, text = self.run_tool("check")
        self.assertEqual(code, 0, text)
        self.assertEqual(os.stat(os.path.join(self.out, "index.md")).st_mtime_ns, stamp)
        self.assertEqual(sorted(os.listdir(self.out)), ["index.json", "index.md"])

    def test_check_fails_when_a_card_is_added_changed_or_removed(self):
        self.card(2)
        self.assertEqual(self.run_tool("check")[0], 1)
        self.build()
        self.card(2, name="Renamed")
        self.assertEqual(self.run_tool("check")[0], 1)
        self.build()
        os.remove(os.path.join(self.records, "cards", "%s.md" % cid(2)))
        code, text = self.run_tool("check")
        self.assertEqual(code, 1)
        self.assertIn("The records are the source of truth", text)

    def test_check_fails_when_the_board_record_changes(self):
        self.board(board([{"id": TODO, "name": "Renamed", "pos": 1, "closed": False}]))
        self.assertEqual(self.run_tool("check")[0], 1)

    def test_check_fails_when_either_index_file_is_edited_by_hand_or_is_gone(self):
        for name in ("index.md", "index.json"):
            good = self.read(name)
            with open(os.path.join(self.out, name), "w", encoding="utf-8") as f:
                f.write(good.replace("A card", "A card, edited"))
            code, text = self.run_tool("check")
            self.assertEqual(code, 1, name)
            self.assertIn("%s is not what" % name, text)
            self.build()
        os.remove(os.path.join(self.out, "index.json"))
        self.assertEqual(self.run_tool("check")[0], 1)

    def test_a_lookup_refuses_a_stale_index_and_names_no_card(self):
        self.card(2, labels=["bug"])
        code, ids, text = self.found("--label", "bug")
        self.assertEqual((code, ids), (1, []))
        self.assertIn("CHECK FAILED", text)
        self.assertIn("No answer is given", text)

    def test_a_lookup_refuses_an_edited_index_json(self):
        with open(os.path.join(self.out, "index.json"), "w", encoding="utf-8") as f:
            f.write(self.read("index.json").replace(TODO, DONE))
        code, ids, _ = self.found("--list", "Done")
        self.assertEqual((code, ids), (1, []))

    def test_the_header_says_what_the_file_is(self):
        head = self.read().split("## What this index was built from")[0]
        self.assertIn("This file is generated. Do not edit it by hand.", head)
        self.assertIn("are the source of truth, not this", head)
        self.assertIn("`records/cards/`", head)
        self.assertIn("`records/board.json`", head)
        self.assertIn(index.REBUILD, head)
        self.assertRegex(self.read(), r"\| Fingerprint of the records \| `[0-9a-f]{64}` \|")
        self.assertIn("source of truth", self.data()["note"])


class Lookup(Case):
    def setUp(self):
        super().setUp()
        self.card(1, pos=20, labels=["bug"], members=[ADA], due="2026-11-21T09:00:00.000Z")
        self.card(2, pos=10, labels=["bug", "Urgent"], members=[ADA, BO], due="2026-11-27T09:00:00.000Z")
        self.card(3, lst=DOING, labels=["feature"], members=[BO], due="2026-11-27T09:00:01.000Z")
        self.card(4, lst=DONE, due="2026-11-22T09:00:00.000Z", done=True)
        self.card(5, lst=DONE, pos=200, due="2026-11-23T09:00:00.000Z", closed=True)
        self.card(6, lst=DOING, pos=500, due="2026-11-20T08:59:59.000Z", labels=["bugfix"])
        self.card(7, lst="a0000000000000000000dead", drop=("idMembers",))
        self.build()

    def test_by_list_name_gives_that_list_only_in_board_order(self):
        self.assertEqual(self.found("--list", "To do")[:2], (0, [cid(2), cid(1)]))
        self.assertEqual(self.found("--list", "to DO")[1], [cid(2), cid(1)])
        self.assertEqual(self.found("--list", "Done")[1], [cid(4), cid(5)])

    def test_by_list_id(self):
        self.assertEqual(self.found("--list", DOING)[1], [cid(3), cid(6)])

    def test_part_of_a_list_name_finds_nothing(self):
        code, ids, text = self.found("--list", "Do")
        self.assertEqual((code, ids), (1, []))
        self.assertIn("no list with that name or id", text)

    def test_an_empty_list_is_found_and_holds_nothing(self):
        code, ids, text = self.found("--list", "Abandoned")
        self.assertEqual((code, ids), (1, []))
        self.assertIn("Found: 0 of 7 cards.", text)

    def test_by_label_is_the_whole_name_in_any_capitals(self):
        self.assertEqual(self.found("--label", "bug")[:2], (0, [cid(2), cid(1)]))
        self.assertEqual(self.found("--label", "URGENT")[1], [cid(2)])
        self.assertEqual(self.found("--label", "nothing")[:2], (1, []))

    def test_by_member_is_the_exact_id(self):
        self.assertEqual(self.found("--member", BO)[:2], (0, [cid(2), cid(3)]))
        self.assertEqual(self.found("--member", ADA[:-1])[:2], (1, []))

    def test_a_lookup_says_where_the_record_is_and_shows_a_gap(self):
        text = self.found("--list", "To do")[2]
        self.assertIn("record: cards/%s.md" % cid(2), text)
        self.assertIn("answered from index.json", text)
        self.assertRegex(text, r"It was last written (under a minute|\d+ \w+) ago")
        code, text = self.run_tool("lookup", "--member", "nobody")
        self.assertNotIn("GAP", text)
        self.assertEqual(index.cmd_check(self.records, self.out, quiet=True), 0)

    def test_due_within_seven_days_counts_from_the_clock_given(self):
        code, ids, text = self.found("--due-within-days", "7", "--now", NOW)
        self.assertEqual((code, ids), (0, [cid(1), cid(2)]))
        self.assertIn("from 2026-11-20T09:00:00Z to 2026-11-27T09:00:00Z", text)
        self.assertNotIn("computer's clock", text)
        self.assertEqual(self.found("--due-within-days", "7", "--now", "2026-11-21T09:00:01Z")[1], [cid(2), cid(3)])
        self.assertEqual(self.found("--due-within-days", "1", "--now", NOW)[1], [cid(1)])

    def test_due_leaves_out_complete_archived_and_overdue_cards(self):
        ids = self.found("--due-within-days", "30", "--now", NOW)[1]
        self.assertEqual(ids, [cid(1), cid(2), cid(3)])

    def test_due_with_no_clock_given_says_it_used_the_computers(self):
        self.assertIn("counted from the computer's clock", self.found("--due-within-days", "7")[2])

    def test_a_clock_value_that_cannot_be_read_stops_the_run(self):
        code, text = self.run_tool("lookup", "--due-within-days", "7", "--now", "tomorrow")
        self.assertEqual(code, 2)
        self.assertIn("STOPPED", text)

    def test_the_views_by_label_and_member_in_the_index_agree_with_the_rows(self):
        labels, members = self.section("## By label"), self.section("## By member")
        self.assertRegex(labels, r"- \*\*bug \(red\)\*\* \(2\): .*%s.*%s" % (cid(2), cid(1)))
        self.assertRegex(labels, r"- \*\*no label\*\* \(3\)")
        self.assertRegex(members, r"- \*\*`%s`\*\* \(2\)" % BO)
        self.assertRegex(members, r"- \*\*no member\*\* \(3\)")
        self.assertNotIn(cid(7), members)


class BoardRecord(Case):
    def stopped(self, why):
        code, text = self.run_tool("build")
        self.assertEqual(code, 2, text)
        self.assertIn(why, text)
        self.assertFalse(os.path.exists(self.out))

    def test_no_board_record_stops_the_build(self):
        os.remove(os.path.join(self.records, "board.json"))
        self.stopped("there is no board record")

    def test_a_board_record_that_is_not_json_stops_the_build(self):
        self.board("{")
        self.stopped("is not JSON")

    def test_a_board_record_with_no_lists_stops_the_build(self):
        self.board(json.dumps({"board": {"id": BOARD}}))
        self.stopped("does not hold a board and its lists")

    def test_a_list_with_no_position_stops_the_build(self):
        self.board(board([{"id": TODO, "name": "To do", "closed": False}]))
        self.stopped("no id or no position")

    def test_the_same_list_twice_stops_the_build(self):
        self.board(board([{"id": TODO, "name": "A", "pos": 1}, {"id": TODO, "name": "B", "pos": 2}]))
        self.stopped("same list id twice")

    def test_no_cards_folder_stops_the_build(self):
        os.rmdir(os.path.join(self.records, "cards"))
        self.stopped("no cards folder")

    def test_an_empty_cards_folder_gives_an_index_with_no_rows(self):
        self.build()
        self.assertEqual(self.rows(), [])
        self.assertIn("0 + 0 + 0 = 0", self.read())


class NoNetwork(unittest.TestCase):
    def test_the_generator_has_no_code_that_reaches_a_network(self):
        with open(index.__file__, encoding="utf-8") as f:
            code = f.read()
        for word in ("urllib", "http.client", "socket", "requests", "subprocess", "os.environ", "getenv"):
            self.assertNotIn(word, code.split('"""', 2)[2])


if __name__ == "__main__":
    unittest.main()
