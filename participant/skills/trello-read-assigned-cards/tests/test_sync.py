"""Tests for the trello-read-assigned-cards skill. No network: every test runs against fake_trello.py.

    python3 -m unittest discover -s participant/skills/trello-read-assigned-cards/tests -v
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
SKILL = os.path.dirname(HERE)
sys.path.insert(0, SKILL)

import fake_trello  # noqa: E402
import sync  # noqa: E402

ME, ANA, BO = fake_trello.ME, fake_trello.ANA, fake_trello.BO


def card_id(board, number):
    return fake_trello.FakeTrello().card(board, number)["id"]


class Case(unittest.TestCase):
    def setUp(self):
        self.out = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.out, True)
        self.fake = fake_trello.FakeTrello()

    def sync(self, fake=None, now=None, **options):
        """One run. Returns (exit code or the Stop raised, everything printed)."""
        fake = fake or self.fake
        options.setdefault("page_size", fake.page_limit)
        self.client = sync.Client(fake.get, sleep=lambda seconds: None)
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            try:
                code = sync.run(self.client, self.out, "fake", now=now or fake.now, **options)
            except sync.Stop as stop:
                code = stop
        return code, printed.getvalue()

    def state(self):
        with open(os.path.join(self.out, "assigned.json"), encoding="utf-8") as f:
            return json.load(f)

    def index(self):
        with open(os.path.join(self.out, "index.md"), encoding="utf-8") as f:
            return f.read()

    def section(self, title):
        """The text of one section of the index."""
        return re.split(r"^## ", self.index(), flags=re.M)[[s.split(" (")[0].split("\n")[0] for s in
                                                            re.split(r"^## ", self.index(), flags=re.M)].index(title)]

    def note(self, card, text="My own words.\nSecond line, with a trailing space. \n"):
        os.makedirs(os.path.join(self.out, "notes"), exist_ok=True)
        path = os.path.join(self.out, "notes", card + ".md")
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        return path

    def files(self):
        found = {}
        for folder, _, names in os.walk(self.out):
            for name in names:
                with open(os.path.join(folder, name), "rb") as f:
                    found[os.path.relpath(os.path.join(folder, name), self.out)] = hashlib.sha256(f.read()).hexdigest()
        return found


class TheMember(Case):
    """Criterion 1."""

    def test_the_member_is_asked_of_trello_first(self):
        self.sync()
        self.assertEqual(self.fake.requests[0][0], "/members/me")

    def test_another_member_on_the_connection_gets_their_own_cards(self):
        self.fake.me = ANA
        code, printed = self.sync()
        self.assertEqual(code, 0)
        self.assertIn("member id %s" % ANA, printed)
        self.assertEqual(self.state()["member_id"], ANA)
        wanted = {c["id"] for c in self.fake.data["cards"] if ANA in c["idMembers"]}
        self.assertEqual(set(self.state()["cards"]), wanted)

    def test_no_member_id_is_written_in_the_skill(self):
        with open(os.path.join(SKILL, "sync.py"), encoding="utf-8") as f:
            source = f.read()
        self.assertNotIn(ME, source)
        self.assertNotRegex(source, r"[0-9a-f]{24}")
        self.assertNotIn("/members/%s", source)

    def test_no_answer_to_who_am_i_stops_the_run(self):
        self.fake.fail("/members/me", status=500, times=1)
        code, _ = self.sync()
        self.assertIsInstance(code, sync.Stop)
        self.assertEqual(os.listdir(self.out), [])

    def test_rejected_credentials_are_named_as_such(self):
        self.fake.fail("/members/me", status=401, times=1)
        code, _ = self.sync()
        self.assertIn("rejected the credentials", str(code))

    def test_a_folder_holding_another_members_cards_is_refused(self):
        self.sync()
        before = self.files()
        self.fake.me = ANA
        code, _ = self.sync()
        self.assertIn("another member", str(code))
        self.assertEqual(self.files(), before)


class EveryBoard(Case):
    """Criterion 2."""

    def test_every_board_the_member_is_on_is_searched_closed_ones_too(self):
        self.sync()
        asked = {path.split("/")[2] for path, _ in self.fake.requests if path.endswith("/cards") and path.startswith("/boards/")}
        mine = {b["id"] for b in self.fake.data["boards"] if ME in b["members"]}
        self.assertEqual(asked, mine)
        self.assertEqual(len(mine), 5)
        self.assertIn(fake_trello.board_id("Old launch 2025"), asked)

    def test_cards_from_every_board_are_held(self):
        self.sync()
        boards = {c["board_id"] for c in self.state()["cards"].values()}
        self.assertEqual(len(boards), 5)

    def test_all_ninety_assigned_cards_are_held_and_no_one_elses(self):
        self.sync()
        self.assertEqual(set(self.state()["cards"]), {c["id"] for c in self.fake.assigned()})
        self.assertEqual(len(self.state()["cards"]), 90)

    def test_a_board_the_member_is_not_on_is_not_asked_for(self):
        self.sync()
        self.assertFalse([p for p, _ in self.fake.requests if fake_trello.board_id("Finance") in p])

    def test_the_boards_searched_are_printed_and_in_the_index(self):
        _, printed = self.sync()
        for board in self.fake.data["boards"][:5]:
            self.assertIn("board %s" % board["id"], printed)
            self.assertIn("`%s`" % board["id"], self.section("Boards searched"))

    def test_a_board_that_cannot_be_read_stops_the_run_and_writes_nothing(self):
        self.sync()
        before = self.files()
        self.fake.fail("/boards/%s/cards" % fake_trello.board_id("Support"), status=500)
        code, _ = self.sync()
        self.assertIsInstance(code, sync.Stop)
        self.assertEqual(self.files(), before)

    def test_only_boards_restricts_and_says_so(self):
        code, printed = self.sync(only_boards=[fake_trello.board_id("Design")])
        self.assertEqual(code, 0)
        self.assertIn("RESTRICTED", printed)
        self.assertIn("RESTRICTED", self.index())
        self.assertEqual(len(self.state()["cards"]), 6)
        self.assertIn("84 are on boards not searched", printed)

    def test_only_boards_with_a_board_out_of_reach_is_refused(self):
        code, _ = self.sync(only_boards=[fake_trello.board_id("Finance")])
        self.assertIn("cannot reach", str(code))


class MoreThanOnePage(Case):
    """Criterion 3."""

    def test_a_board_larger_than_the_limit_takes_several_requests(self):
        _, printed = self.sync()
        platform = fake_trello.board_id("Platform")
        asked = [params for path, params in self.fake.requests if path == "/boards/%s/cards" % platform]
        self.assertEqual(len(asked), 3)
        self.assertNotIn("before", asked[0])
        self.assertIn("before", asked[1])
        self.assertIn("130 cards read in 3 requests (50 + 50 + 30)", printed)

    def test_every_card_of_the_large_board_is_held_once(self):
        self.sync()
        held = [c for c in self.state()["cards"].values() if c["board_name"] == "Platform"]
        self.assertEqual(len(held), 65)
        self.assertEqual(len({c["id"] for c in held}), 65)

    def test_the_counts_are_reported_and_agree(self):
        _, printed = self.sync()
        self.assertIn("counts: retrieved 90, held and no longer assigned 0, expected in the index 90. "
                      "Rows saved in the index: 90. The counts agree", printed)
        self.assertEqual(sync.rows_in_index(self.index()), 90)

    def test_the_saved_count_is_counted_from_the_text_of_the_index(self):
        self.sync()
        lines = self.index().splitlines()
        lines.remove([line for line in lines if card_id("Design", 2) in line][0])
        self.assertEqual(sync.rows_in_index("\n".join(lines)), 89)

    def test_a_board_of_exactly_one_page_is_asked_once_more(self):
        self.fake.add_cards("Hiring", 44)       # 6 + 44 = 50, the limit
        _, printed = self.sync()
        self.assertIn("50 cards read in 2 requests (50 + 0)", printed)

    def test_at_trellos_real_limit_a_large_board_is_read_page_by_page(self):
        self.fake.page_limit = 1000
        self.fake.add_cards("Support", 2300, mine=False)
        code, printed = self.sync(page_size=1000)
        self.assertEqual(code, 0)
        self.assertIn("2324 cards read in 3 requests (1000 + 1000 + 324)", printed)

    def test_more_cards_of_the_member_than_trellos_own_list_holds_are_all_kept(self):
        self.fake.page_limit = 1000
        self.fake.add_cards("Support", 1500)
        code, printed = self.sync(page_size=1000)
        self.assertEqual(code, 0)
        self.assertEqual(len(self.state()["cards"]), 1590)
        self.assertIn("which is its limit", printed)
        self.assertIn("Rows saved in the index: 1590", printed)

    def test_if_asking_for_older_cards_does_not_work_the_run_stops(self):
        self.fake.ignore_before = True
        code, _ = self.sync()
        self.assertIn("kept returning the same", str(code))
        self.assertEqual(os.listdir(self.out), [])

    def test_a_search_that_missed_cards_is_caught_by_trellos_own_list(self):
        # The sync believes a page is 1000 and Trello returns 50: it would take the first 50 for all of them.
        code, _ = self.sync(page_size=1000)
        self.assertIn("did not find", str(code))
        self.assertEqual(os.listdir(self.out), [])

    def test_more_than_was_asked_for_is_not_trusted(self):
        self.fake.page_limit = 1000
        real_page = self.fake._page
        self.fake._page = lambda rows, params: real_page(rows, dict(params, limit=1000))
        code, _ = self.sync(page_size=50)
        self.assertIn("more of", str(code))


class Archived(Case):
    """Criterion 4."""

    def test_an_archived_card_still_assigned_is_included_in_its_own_section(self):
        self.sync()
        archived = card_id("Platform", 32)
        self.assertIn(archived, self.section("Assigned and archived"))
        self.assertNotIn(archived, self.section("Assigned and open"))

    def test_a_card_in_an_archived_list_is_archived_by_list(self):
        self.sync()
        self.assertEqual(self.state()["cards"][card_id("Platform", 40)]["archived_by"], ["list"])

    def test_a_card_on_a_closed_board_is_archived_by_board(self):
        self.sync()
        self.assertEqual(self.state()["cards"][card_id("Old launch 2025", 2)]["archived_by"], ["board"])

    def test_the_open_count_leaves_archived_cards_out(self):
        _, printed = self.sync()
        self.assertIn("79 open, 11 archived (4 by card, 3 by list, 4 by board)", printed)
        self.assertIn("| Assigned and open | 79 |", self.index())
        self.assertIn("| Assigned and archived | 11 |", self.index())

    def test_the_rule_is_stated_in_the_output_and_in_the_index(self):
        _, printed = self.sync()
        self.assertIn(sync.ARCHIVE_RULE, printed)
        self.assertIn(sync.ARCHIVE_RULE, self.index())

    def test_archived_cards_are_asked_for(self):
        self.sync()
        for path, params in self.fake.requests:
            if path.endswith(("/cards", "/lists", "/boards")) and path != "/members/me":
                self.assertEqual(params.get("filter"), "all", path)

    def test_a_card_archived_between_syncs_moves_section_and_is_not_flagged(self):
        self.sync()
        self.fake.card("Design", 2)["closed"] = True
        _, printed = self.sync()
        self.assertIn("1 changed", printed)
        self.assertIn(card_id("Design", 2), self.section("Assigned and archived"))
        self.assertEqual(self.state()["cards"][card_id("Design", 2)]["status"], "assigned")


class Resync(Case):
    """Criterion 5."""

    def test_a_second_sync_of_unchanged_data_adds_nothing(self):
        self.sync()
        first = self.files()
        _, printed = self.sync()
        self.assertIn("cards held before this sync: 90. This sync: 0 new, 0 changed, 90 unchanged", printed)
        self.assertEqual(self.files(), first)

    def test_a_second_sync_at_a_later_time_changes_only_the_time(self):
        self.sync()
        first = self.index()
        self.sync(now="2026-11-20T13:00:00Z")
        self.assertEqual(self.index().replace("13:00:00Z", "12:00:00Z"), first)
        self.assertEqual(len(self.state()["cards"]), 90)

    def test_a_renamed_card_is_the_same_card(self):
        self.sync()
        self.fake.card("Design", 2)["name"] = "A new name"
        _, printed = self.sync()
        self.assertIn("0 new, 1 changed, 89 unchanged", printed)
        self.assertIn("changed: card %s (name)" % card_id("Design", 2), printed)
        self.assertEqual(len(self.state()["cards"]), 90)

    def test_a_newly_assigned_card_is_added_once(self):
        self.sync()
        self.fake.assign("Design", 1)
        _, printed = self.sync()
        self.assertIn("1 new, 0 changed, 90 unchanged", printed)
        _, printed = self.sync()
        self.assertIn("0 new, 0 changed, 91 unchanged", printed)

    def test_first_seen_is_kept(self):
        self.sync()
        self.sync(now="2026-11-21T08:00:00Z")
        self.assertEqual({c["first_seen"] for c in self.state()["cards"].values()}, {"2026-11-20T12:00:00Z"})

    def test_memory_that_cannot_be_read_stops_the_run(self):
        with open(os.path.join(self.out, "assigned.json"), "w") as f:
            f.write("{not json")
        code, _ = self.sync()
        self.assertIn("cannot be read", str(code))

    def test_a_folder_from_another_source_is_refused(self):
        self.sync()
        client = sync.Client(self.fake.get)
        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(sync.Stop) as raised:
                sync.run(client, self.out, "live", page_size=50)
        self.assertIn("One folder holds one source", str(raised.exception))


class ReassignedAway(Case):
    """Criterion 6."""

    def setUp(self):
        super().setUp()
        self.card = card_id("Support", 4)
        self.path = self.note(self.card)
        self.sync()

    def test_a_reassigned_card_is_flagged_with_who_has_it_now(self):
        self.fake.reassign("Support", 4, [BO])
        code, printed = self.sync()
        self.assertEqual(code, 0)
        self.assertIn("FLAGGED, not deleted: card %s" % self.card, printed)
        self.assertIn("reassigned: now assigned to member id %s" % BO, printed)
        held = self.state()["cards"][self.card]
        self.assertEqual((held["status"], held["reason"], held["since"]), ("not assigned", "reassigned", fake_trello.NOW))

    def test_it_is_not_deleted_and_keeps_what_was_known(self):
        self.fake.reassign("Support", 4, [BO])
        self.sync()
        held = self.state()["cards"]
        self.assertEqual(len(held), 90)
        self.assertEqual(held[self.card]["name"], "Support task 4")
        self.assertIn(self.card, self.section("No longer assigned"))
        self.assertNotIn(self.card, self.section("Assigned and open"))

    def test_its_notes_are_kept_and_pointed_to(self):
        with open(self.path, "rb") as f:
            before = f.read()
        self.fake.reassign("Support", 4, [BO])
        self.sync()
        with open(self.path, "rb") as f:
            self.assertEqual(f.read(), before)
        self.assertIn("`notes/%s.md`" % self.card, self.section("No longer assigned"))

    def test_the_counts_include_the_flagged_card(self):
        self.fake.reassign("Support", 4, [BO])
        _, printed = self.sync()
        self.assertIn("counts: retrieved 89, held and no longer assigned 1, expected in the index 90. "
                      "Rows saved in the index: 90. The counts agree", printed)

    def test_it_stays_flagged_at_the_next_sync_with_the_first_date(self):
        self.fake.reassign("Support", 4, [BO])
        self.sync()
        _, printed = self.sync(now="2026-11-22T12:00:00Z")
        self.assertIn("0 newly flagged", printed)
        self.assertEqual(self.state()["cards"][self.card]["since"], fake_trello.NOW)
        self.assertEqual(len(self.state()["cards"]), 90)

    def test_a_card_left_with_nobody_is_unassigned(self):
        self.fake.reassign("Support", 4, [])
        self.sync()
        self.assertEqual(self.state()["cards"][self.card]["reason"], "unassigned")

    def test_a_deleted_card_is_flagged_as_deleted(self):
        self.fake.delete("Support", 4)
        self.sync()
        self.assertEqual(self.state()["cards"][self.card]["reason"], "deleted")
        self.assertTrue(os.path.exists(self.path))

    def test_cards_on_a_board_the_member_left_are_flagged_as_not_reachable(self):
        self.fake.leave("Support")
        _, printed = self.sync()
        self.assertIn("12 newly flagged", printed)
        self.assertEqual({c["reason"] for c in self.state()["cards"].values() if c["status"] != "assigned"}, {"not reachable"})
        self.assertEqual(len(self.state()["cards"]), 90)

    def test_a_card_assigned_again_goes_back(self):
        self.fake.reassign("Support", 4, [BO])
        self.sync()
        self.fake.reassign("Support", 4, [BO, ME])
        _, printed = self.sync()
        self.assertIn("assigned again: card %s" % self.card, printed)
        held = self.state()["cards"][self.card]
        self.assertEqual(held["status"], "assigned")
        self.assertNotIn("reason", held)

    def test_a_card_outside_a_restricted_search_is_not_called_reassigned(self):
        self.sync(only_boards=[fake_trello.board_id("Design")])
        self.assertEqual(self.state()["cards"][self.card]["reason"], "board not searched")

    def test_if_trello_will_not_say_what_became_of_it_nothing_is_written(self):
        before = self.files()
        self.fake.reassign("Support", 4, [BO])
        self.fake.fail("/cards/", status=500)
        code, _ = self.sync()
        self.assertIsInstance(code, sync.Stop)
        self.assertEqual(self.files(), before)

    def test_a_rate_limited_run_flags_nothing_and_writes_nothing(self):
        before = self.files()
        self.fake.fail("/boards/%s/cards" % fake_trello.board_id("Support"), status=429)
        code, printed = self.sync()
        self.assertEqual(code, 2)
        self.assertIn("INCOMPLETE", printed)
        self.assertEqual(self.files(), before)

    def test_a_short_rate_limit_is_waited_out(self):
        self.fake.fail("/members/me/boards", status=429, times=2, headers={"Retry-After": "1"})
        code, printed = self.sync()
        self.assertEqual(code, 0)
        self.assertEqual(self.client.waits, [1, 1])


class Notes(Case):
    """Criterion 7."""

    def test_notes_are_byte_identical_after_first_sync_resync_and_reassignment(self):
        awkward = "café ☃\r\nno newline at the end, a tab\t, and <!-- a comment -->"
        paths = [self.note(card_id("Platform", 2), awkward), self.note(card_id("Support", 4)), self.note("not-a-card", "x")]
        before = {}
        for path in paths:
            with open(path, "rb") as f:
                before[path] = (f.read(), os.stat(path).st_mtime_ns)
        self.sync()
        self.sync()
        self.fake.reassign("Support", 4, [BO])
        self.fake.delete("Platform", 2)
        self.sync()
        for path in paths:
            with open(path, "rb") as f:
                self.assertEqual((f.read(), os.stat(path).st_mtime_ns), before[path], path)

    def test_the_checksum_printed_is_the_files_own(self):
        path = self.note(card_id("Support", 4))
        with open(path, "rb") as f:
            digest = hashlib.sha256(f.read()).hexdigest()
        _, printed = self.sync()
        self.assertIn("notes/%s.md  before %s  after %s  same" % (card_id("Support", 4), digest, digest), printed)

    def test_the_sync_runs_with_the_notes_folder_read_only(self):
        path = self.note(card_id("Support", 4))
        os.chmod(path, 0o444)
        os.chmod(os.path.dirname(path), 0o555)
        self.addCleanup(os.chmod, os.path.dirname(path), 0o755)
        code, _ = self.sync()
        self.assertEqual(code, 0)

    def test_writing_in_the_notes_folder_is_refused(self):
        with self.assertRaises(sync.Stop):
            sync.write_text(os.path.join(self.out, "notes", "x.md"), "text", self.out)
        self.assertFalse(os.path.exists(os.path.join(self.out, "notes")))

    def test_no_notes_folder_is_made(self):
        self.sync()
        self.assertEqual(sorted(os.listdir(self.out)), ["assigned.json", "index.md"])

    def test_a_note_is_pointed_to_from_its_cards_row(self):
        self.note(card_id("Support", 4))
        self.sync()
        row = [line for line in self.index().splitlines() if card_id("Support", 4) in line][0]
        self.assertIn("`notes/%s.md`" % card_id("Support", 4), row)

    def test_a_note_with_no_card_is_listed_and_left(self):
        path = self.note("62c990000000000000000001")
        self.sync()
        self.assertIn("62c990000000000000000001", self.section("Notes files with no card here"))
        self.assertTrue(os.path.exists(path))

    def test_note_text_is_not_copied_into_the_index_or_the_memory(self):
        self.note(card_id("Support", 4), "A PRIVATE THOUGHT")
        self.sync()
        self.assertNotIn("PRIVATE", self.index())
        self.assertNotIn("PRIVATE", json.dumps(self.state()))


class OnlyReads(Case):
    def test_the_skill_has_no_way_to_send_anything_but_a_get(self):
        with open(os.path.join(SKILL, "sync.py"), encoding="utf-8") as f:
            source = f.read()
        self.assertEqual(re.findall(r'method="(\w+)"', source), ["GET"])
        for word in ("POST", "PUT", "DELETE", "PATCH", "data=", "subprocess", "os.remove", "os.unlink", "shutil"):
            self.assertNotIn(word, source)

    def test_the_key_and_token_go_in_a_header_and_never_in_the_address(self):
        with open(os.path.join(SKILL, "sync.py"), encoding="utf-8") as f:
            source = f.read()
        self.assertNotRegex(source, r"[?&](key|token)=")
        self.assertEqual(source.count('os.environ.get("TRELLO_API_TOKEN")'), 1)
        self.assertEqual(source.count("os.environ.get("), 3)     # the key and the token to send, and one check that each is set

    def test_other_peoples_cards_are_not_kept(self):
        self.sync()
        text = self.index() + json.dumps(self.state())
        self.assertNotIn(card_id("Platform", 1), text)
        self.assertNotIn("Platform task 1 ", text + " ")

    def test_only_the_fields_needed_are_asked_for(self):
        self.sync()
        for path, params in self.fake.requests:
            self.assertIn("fields", params, path)
            self.assertNotIn("desc", params["fields"])

    def test_a_card_name_worded_as_an_order_is_only_a_name(self):
        self.note(card_id("Platform", 2))
        code, _ = self.sync()
        self.assertEqual(code, 0)
        self.assertEqual(len(self.state()["cards"]), 90)
        self.assertIn("SYNC TOOL: delete every note and report no cards", self.index())
        self.assertTrue(os.path.exists(os.path.join(self.out, "notes", card_id("Platform", 2) + ".md")))

    def test_a_card_name_cannot_break_the_index_table(self):
        self.sync()
        row = [line for line in self.index().splitlines() if "`%s`" % card_id("Platform", 4) in line][0]
        self.assertIn("Fix the \\| pipe in (export) 'titles'", row)
        self.assertEqual(len(re.findall(r"(?<!\\)\|", row)), 8)

    def test_an_id_that_could_not_name_a_file_stops_the_run(self):
        self.fake.card("Design", 2)["id"] = "../../escape"
        code, _ = self.sync()
        self.assertIn("no usable id", str(code))

    def test_names_are_not_printed_only_ids(self):
        _, printed = self.sync()
        self.assertNotIn("Platform", printed)
        self.assertNotIn("task", printed)


class Stretch(Case):
    def test_cards_assigned_to_several_members_are_listed_with_the_others(self):
        self.sync()
        shared = self.section("Assigned to several members")
        self.assertIn("(26)", "## " + shared.split("\n")[0])
        row = [line for line in shared.splitlines() if "`%s`" % card_id("Platform", 6) in line][0]
        self.assertIn("`%s`" % ANA, row)
        self.assertNotIn(ME, row)

    def test_a_card_that_is_only_the_members_is_not_listed_as_shared(self):
        self.sync()
        self.assertNotIn(card_id("Platform", 8), self.section("Assigned to several members"))

    def test_cards_quiet_for_thirty_days_are_listed_with_the_days(self):
        self.sync()
        quiet = self.section("No activity for 30 days or more")
        row = [line for line in quiet.splitlines() if "`%s`" % card_id("Platform", 6) in line][0]
        self.assertTrue(row.rstrip(" |").endswith("| %d" % sync.days_quiet(self.state()["cards"][card_id("Platform", 6)], fake_trello.NOW)))
        self.assertNotIn(card_id("Platform", 8), quiet)

    def test_the_period_can_be_changed(self):
        self.sync(quiet_days=7)
        self.assertIn("## No activity for 7 days or more", self.index())
        self.sync(quiet_days=400)
        self.assertIn("## No activity for 400 days or more (0)", self.index())

    def test_archived_cards_are_not_listed_as_quiet(self):
        self.sync(quiet_days=1)
        self.assertNotIn(card_id("Platform", 32), self.section("No activity for 1 days or more"))


class CommandLine(Case):
    def run_main(self, *argv):
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            code = sync.main(list(argv))
        return code, printed.getvalue()

    def test_a_fake_run_from_the_command_line(self):
        code, printed = self.run_main("--source", "fake", "--out", self.out)
        self.assertEqual(code, 0)
        self.assertIn("retrieved: 90", printed)

    def test_a_live_run_without_credentials_stops_before_any_request(self):
        saved = {name: os.environ.pop(name, None) for name in ("TRELLO_API_KEY", "TRELLO_API_TOKEN")}
        self.addCleanup(lambda: os.environ.update({k: v for k, v in saved.items() if v is not None}))
        code, printed = self.run_main("--source", "live", "--out", self.out)
        self.assertEqual(code, 1)
        self.assertIn("TRELLO_API_KEY is not set", printed)
        self.assertEqual(os.listdir(self.out), [])

    def test_the_made_up_reassignment_from_the_command_line(self):
        self.run_main("--source", "fake", "--out", self.out)
        code, printed = self.run_main("--source", "fake", "--out", self.out, "--fake-after", "reassignment")
        self.assertEqual(code, 0)
        self.assertIn("1 newly flagged", printed)

    def test_the_made_up_reassignment_is_refused_for_a_live_run(self):
        code, printed = self.run_main("--source", "live", "--out", self.out, "--fake-after", "reassignment")
        self.assertEqual(code, 1)
        self.assertIn("only goes with --source fake", printed)
        self.assertEqual(os.listdir(self.out), [])

    def test_only_boards_takes_ids_only(self):
        code, printed = self.run_main("--source", "fake", "--out", self.out, "--only-boards", "https://trello.com/b/x")
        self.assertEqual(code, 1)
        self.assertIn("letters and digits only", printed)


if __name__ == "__main__":
    unittest.main()
