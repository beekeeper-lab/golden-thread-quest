"""Tests for the card-creation preview, preview.py. A fake Trello in memory, local files in temporary folders.

Run from the repository root:
    python3 -m unittest discover -s participant/skills/trello-create-card-preview/tests -v
"""
import contextlib
import copy
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
import preview  # noqa: E402
import fake_trello as fake  # noqa: E402
from preview import index  # noqa: E402

NEW_CARD = os.path.join(preview.ROOT, "participant", "context", "trello", "new-card")
NOTES = os.path.join(NEW_CARD, "sources", "notes.md")
NOW = "2026-11-20T09:00:00Z"
STATUS = {"name": "Add a status page link to the app footer",
          "description": "Customers ask support whether the service is down before checking anything.\n\n- Use the existing footer component",
          "sources": {"name": (7, "add a status page link to the app footer"),
                      "description": (8, "customers ask support whether the service is down"),
                      "labels": (10, "It is a feature"), "members": (11, "member 5f0000000000000000000012"),
                      "due": (12, "Friday 11 December 2026")}}
EXPORT = {"name": "Export the customer list as CSV",
          "description": "Admins keep asking support for their customer list. Add an Export button on the customers page that downloads the "
                         "customer list as a CSV file with the account name, plan and signup date columns. Stream the download so large "
                         "accounts do not time out.",
          "sources": {"name": (16, "export the customer list as CSV"), "description": (17, "admins keep asking support"),
                      "labels": (19, "Label it export"), "members": (19, "member 5f0000000000000000000012"), "due": (19, "Friday 4 December 2026")}}


def draft_text(content=STATUS, sources=None, description=None, **fields):
    front = {"format": "trello-card-draft/1", "board": fake.PLATFORM, "list": fake.TO_DO, "position": "bottom", "name": content["name"],
             "labels": ["feature"], "members": [fake.BO], "due": "2026-12-11T17:00:00.000Z"}
    front.update(fields)
    front = {key: value for key, value in front.items() if value is not None}
    cited = dict(content["sources"]) if sources is None else sources
    described = content["description"] if description is None else description
    wanted = [key for key in ("name", "labels", "members", "due") if front.get(key)] + (["description"] if described else [])
    lines = ["- %s: %s line %d: %s" % (key, NOTES, cited[key][0], json.dumps(cited[key][1])) for key in wanted if key in cited]
    return ("---\n" + "".join("%s: %s\n" % (key, json.dumps(value)) for key, value in front.items()) + "---\n\n# Draft\n\n## Description\n\n"
            + described + "\n\n## Sources\n\n" + "\n".join(lines) + "\n")


class Case(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = tmp.name
        self.state = os.path.join(self.tmp, "state")
        self.boards = os.path.join(self.tmp, "boards")
        shutil.copytree(os.path.join(NEW_CARD, "fixture", "boards"), self.boards)
        self.allowlist = os.path.join(NEW_CARD, "sandbox-allowlist.json")
        self.payload_out = os.path.join(self.tmp, "payload.md")
        self.fake = fake.FakeTrello()
        original = fake.FakeTrello
        fake.FakeTrello = lambda: self.fake
        self.addCleanup(setattr, fake, "FakeTrello", original)

    def run_preview(self, text=None, *extra, **fields):
        path = os.path.join(self.tmp, "draft.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(draft_text(**fields) if text is None else text)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = preview.main(["--source", "fake", "--draft", path, "--allowlist", self.allowlist, "--boards", self.boards,
                                 "--state", self.state, "--now", NOW, "--payload-out", self.payload_out] + list(extra))
        return code, out.getvalue()

    def saved(self):
        folder = os.path.join(self.state, "card-previews")
        found = []
        for name in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
            with open(os.path.join(folder, name), encoding="utf-8") as f:
                found.append(json.load(f))
        return found

    def refused(self, expect, text=None, **fields):
        code, out = self.run_preview(text, **fields)
        self.assertEqual(code, 1, out)
        self.assertTrue(out.startswith("REFUSED: "), out)
        self.assertIn(expect, out)
        self.assertNotIn("PAYLOAD", out)
        self.assertNotIn("idList", out)
        self.assertEqual(self.saved(), [])
        self.assertFalse(os.path.exists(self.payload_out))
        return out

    def not_ready(self, expect, **fields):
        code, out = self.run_preview(**fields)
        self.assertEqual(code, 3, out)
        self.assertIn("VERDICT: NOT READY TO WRITE.", out)
        self.assertIn(expect, out)
        self.assertIn("THE EXACT PAYLOAD", out)
        self.assertEqual(self.saved(), [], "a preview that is not ready must not be saved for a write")
        return out

    def ready(self, **fields):
        code, out = self.run_preview(**fields)
        self.assertEqual(code, 0, out)
        self.assertIn("VERDICT: READY TO WRITE.", out)
        return out

    def printed_payload(self, out):
        block = out.split("THE EXACT PAYLOAD. This is the request body, not a summary of it:\n", 1)[1].split("\nAs sent it is", 1)[0]
        return json.loads(block)


class TheTarget(Case):
    """Criterion 1: the list is chosen by identifier and belongs to the stated board."""

    def test_a_good_draft_is_ready_and_names_the_list_by_id(self):
        out = self.ready()
        self.assertIn('List:   "To do" (list id %s). Chosen by id.' % fake.TO_DO, out)
        self.assertIn("belongs to board %s, the stated board: yes" % fake.PLATFORM, out)

    def test_a_list_given_by_name_is_refused(self):
        self.refused("by its Trello id", list="To do")

    def test_a_board_given_by_name_is_refused(self):
        self.refused("by its Trello id", board="Made-up platform team board")

    def test_a_list_on_another_board_is_refused(self):
        out = self.refused("is not on the stated board", list=fake.INBOX)
        self.assertIn("Trello says the list belongs to board %s" % fake.SUPPORT, out)

    def test_a_list_that_does_not_exist_is_refused(self):
        self.refused("does not exist", list=fake.lid(99))

    def test_an_archived_list_is_refused(self):
        out = self.refused("is archived", list=fake.OLD_IDEAS)
        self.assertIn("would not be seen", out)

    def test_the_first_list_by_position_is_the_archived_one_and_is_never_picked(self):
        first = min(self.fake.boards[fake.PLATFORM]["lists"], key=lambda row: row["pos"])
        self.assertTrue(first["closed"])
        self.assertEqual(self.printed_payload(self.ready())["idList"], fake.TO_DO)

    def test_a_board_not_on_the_allowlist_is_refused_before_trello_is_asked(self):
        self.refused("is not on the sandbox allowlist", board=fake.SUPPORT, list=fake.INBOX, labels=None, members=None)
        self.assertEqual(self.fake.requests, [])

    def test_a_closed_board_is_refused(self):
        self.fake.boards[fake.PLATFORM]["closed"] = True
        self.refused("is closed")

    def test_a_board_the_token_cannot_see_is_refused(self):
        self.fake.fail["/boards/%s" % fake.PLATFORM] = 404
        self.refused("is not visible to this token")

    def test_a_rejected_token_is_refused_with_the_reason(self):
        self.fake.fail["/members/me"] = 401
        self.refused("rejected the key or the token")


class LabelsAndMembers(Case):
    """Criterion 2: labels and members are chosen from those that exist."""

    def test_a_label_is_sent_as_the_id_the_board_gives_it(self):
        wanted = next(row["id"] for row in self.fake.boards[fake.PLATFORM]["labels"] if row["name"] == "feature")
        self.assertEqual(self.printed_payload(self.ready())["idLabels"], wanted)

    def test_two_labels_are_joined_in_the_drafts_order(self):
        ids = {row["name"]: row["id"] for row in self.fake.boards[fake.PLATFORM]["labels"]}
        payload = self.printed_payload(self.ready(labels=["docs", "bug"], sources=dict(STATUS["sources"])))
        self.assertEqual(payload["idLabels"], "%s,%s" % (ids["docs"], ids["bug"]))

    def test_an_unknown_label_is_refused_and_the_real_ones_are_named(self):
        out = self.refused('the label "urgent" does not exist', labels=["feature", "urgent"])
        self.assertIn('"bug", "docs", "export", "feature"', out)

    def test_a_label_of_another_board_is_refused(self):
        self.refused('the label "billing" does not exist', labels=["billing"])

    def test_a_label_name_must_match_exactly(self):
        self.refused('the label "Feature" does not exist', labels=["Feature"])

    def test_two_labels_with_one_name_are_refused(self):
        self.fake.boards[fake.PLATFORM]["labels"].append({"id": fake.label_id(fake.PLATFORM, 9), "name": "feature", "color": "red"})
        self.refused("2 labels named")

    def test_a_member_who_is_not_on_the_board_is_refused(self):
        self.refused("is not a member of board", members=[fake.DEE])

    def test_a_member_given_by_name_is_refused(self):
        self.refused("must be a list of different Trello ids", members=["Bo"])

    def test_a_draft_with_no_labels_or_members_sends_neither_field(self):
        payload = self.printed_payload(self.ready(labels=None, members=None))
        self.assertEqual(sorted(payload), ["desc", "due", "idList", "name", "pos"])


class ThePayload(Case):
    """Criterion 5: the preview contains the exact payload, including list and position."""

    def test_the_payload_holds_the_list_and_the_position(self):
        payload = self.printed_payload(self.ready())
        self.assertEqual((payload["idList"], payload["pos"]), (fake.TO_DO, "bottom"))

    def test_the_payload_is_exactly_the_draft(self):
        self.assertEqual(self.printed_payload(self.ready()),
                         {"idList": fake.TO_DO, "pos": "bottom", "name": STATUS["name"], "desc": STATUS["description"],
                          "due": "2026-12-11T17:00:00.000Z", "idLabels": fake.label_id(fake.PLATFORM, 3), "idMembers": fake.BO})

    def test_the_description_is_sent_as_written_line_breaks_included(self):
        self.assertIn("\n\n- Use the existing footer component", self.printed_payload(self.ready())["desc"])

    def test_the_printed_payload_the_saved_payload_and_the_payload_file_are_the_same(self):
        out = self.ready()
        saved = self.saved()[0]
        with open(self.payload_out, encoding="utf-8") as f:
            in_file = json.loads(f.read().split("```json\n", 1)[1].split("\n```", 1)[0])
        self.assertEqual(self.printed_payload(out), saved["payload"])
        self.assertEqual(in_file, saved["payload"])

    def test_the_sha_shown_is_the_sha_of_the_bytes_a_write_would_send(self):
        out = self.ready()
        saved = self.saved()[0]
        body = preview.body_bytes(saved["payload"])
        digest = hashlib.sha256(body).hexdigest()
        self.assertIn("%d bytes, SHA-256 %s" % (len(body), digest), out)
        self.assertEqual((saved["payload_sha256"], saved["payload_bytes"]), (digest, len(body)))

    def test_the_bytes_are_compact_json_with_names_in_order(self):
        body = preview.body_bytes({"pos": "top", "idList": "x", "name": "é"}).decode("utf-8")
        self.assertEqual(body, '{"idList":"x","name":"é","pos":"top"}')

    def test_the_payload_is_built_once(self):
        calls, original = [], preview.build_payload

        def counted(*args):
            calls.append(1)
            return original(*args)
        preview.build_payload = counted
        self.addCleanup(setattr, preview, "build_payload", original)
        self.ready()
        self.assertEqual(len(calls), 1)

    def test_two_previews_of_one_draft_give_the_same_bytes(self):
        first = re.search(r"SHA-256 (\w+)", self.ready()).group(1)
        self.fake = fake.FakeTrello()
        self.state = os.path.join(self.tmp, "state-2")  # two identical previews in one second share a fingerprint
        self.assertEqual(re.search(r"SHA-256 (\w+)", self.ready(position="bottom")).group(1), first)

    def test_a_number_position_is_sent_as_the_number(self):
        self.assertEqual(self.printed_payload(self.ready(position=150))["pos"], 150)

    def test_a_draft_with_no_position_is_refused(self):
        self.refused("There is no default", position=None)

    def test_a_position_that_is_not_top_bottom_or_above_zero_is_refused(self):
        for position in ("middle", 0, -5, True):
            self.refused("There is no default", position=position)

    def test_the_saved_preview_names_the_request_the_board_and_the_list(self):
        self.ready()
        saved = self.saved()[0]
        self.assertEqual((saved["request"], saved["board"], saved["list"], saved["state"]),
                         ("POST https://api.trello.com/1/cards", fake.PLATFORM, fake.TO_DO, "open"))
        self.assertRegex(saved["expires_at"], r"^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d UTC$")


class WhereInTheList(Case):
    def placed(self, **fields):
        return self.ready(**fields).split("WHERE IN THE LIST.", 1)[1].split("\n\n", 1)[0]

    def test_bottom_is_after_the_last_open_card(self):
        text = self.placed()
        self.assertIn("number 4 of 4 open cards", text)
        self.assertIn("after:  card %s, at position 300" % fake.cid(103), text)
        self.assertIn("before: nothing. It would be last.", text)

    def test_top_is_before_the_first_open_card_and_the_archived_card_is_not_counted(self):
        text = self.placed(position="top")
        self.assertIn("number 1 of 4 open cards", text)
        self.assertIn("before: card %s, at position 100" % fake.cid(101), text)
        self.assertNotIn(fake.cid(104), text)

    def test_a_number_falls_between_the_cards_either_side(self):
        text = self.placed(position=150)
        self.assertIn("number 2 of 4 open cards", text)
        self.assertIn("after:  card %s" % fake.cid(101), text)
        self.assertIn("before: card %s" % fake.cid(102), text)

    def test_a_number_another_card_already_has_is_said_not_to_be_known(self):
        self.assertIn("in a way this preview does not know", self.placed(position=200))

    def test_an_empty_list_is_said_to_be_empty(self):
        self.assertIn("no open card now", self.placed(list=fake.DONE))

    def test_no_card_name_from_trello_is_printed(self):
        out = self.ready()
        for row in self.fake.boards[fake.PLATFORM]["cards"]:
            self.assertNotIn(row["name"], out)


class Permission(Case):
    """Criterion 4: the permission check appears in the preview."""

    def test_the_check_is_shown_when_the_write_would_be_allowed(self):
        out = self.ready()
        self.assertIn("PERMISSION CHECK, asked of Trello", out)
        self.assertIn("on the board as: normal. That role may add cards: yes", out)
        self.assertIn("read yes, write yes", out)

    def test_a_read_only_token_is_not_ready_and_the_payload_is_still_shown(self):
        self.fake.token["permissions"][0]["write"] = False
        out = self.not_ready("may read boards and may not write to them")
        self.assertIn("read yes, write NO", out)

    def test_an_observer_is_not_ready(self):
        self.fake.me = fake.CY
        self.not_ready("an observer of the board")

    def test_someone_not_on_the_board_is_not_ready(self):
        self.fake.me = fake.DEE
        self.not_ready("not an active member of the board")

    def test_a_deactivated_member_is_not_ready(self):
        self.fake.boards[fake.PLATFORM]["memberships"][0]["deactivated"] = True
        self.not_ready("not an active member of the board")

    def test_when_trello_does_not_give_the_tokens_permissions_writing_is_not_assumed(self):
        self.fake.fail[fake.TOKEN_PATH] = 404
        out = self.not_ready("it is not assumed that it may write")
        self.assertIn("May it write: NOT KNOWN", out)

    def test_a_token_scoped_to_another_board_only_is_not_ready(self):
        self.fake.token["permissions"][0]["idModel"] = fake.SUPPORT
        self.not_ready("may not write")

    def test_two_reasons_are_both_listed(self):
        self.fake.token["permissions"][0]["write"] = False
        self.fake.me = fake.CY
        self.assertIn("2 reasons:", self.not_ready("an observer"))

    def test_the_payload_file_of_a_preview_that_is_not_ready_says_so(self):
        self.fake.token["permissions"][0]["write"] = False
        self.not_ready("may not write")
        with open(self.payload_out, encoding="utf-8") as f:
            self.assertIn("NOT READY TO WRITE:", f.read())


class Duplicates(Case):
    """Criterion 4: the duplicate result appears in the preview."""

    def export(self, **fields):
        return dict(dict(content=EXPORT, labels=["export"], due="2026-12-04T17:00:00.000Z", position="top"), **fields)

    def test_no_duplicate_is_reported_as_none(self):
        out = self.ready()
        self.assertIn("DUPLICATE SEARCH:", out)
        self.assertIn("Result: NONE.", out)
        self.assertIn("overall recommendation: PROCEED", out)

    def test_a_likely_duplicate_on_another_board_is_shown_and_the_preview_is_not_ready(self):
        out = self.not_ready("the draft records no person's decision about it", **self.export())
        self.assertIn("card %s, open, on ANOTHER board: confidence MEDIUM" % fake.cid(201), out)
        self.assertIn("Recommendation: LINK.", out)

    def test_a_recorded_decision_that_covers_the_candidate_makes_it_ready(self):
        out = self.ready(**self.export(duplicate_decision="link", duplicate_candidates=[fake.cid(201)]))
        self.assertIn("The draft records a person's decision: LINK, made about card %s." % fake.cid(201), out)
        self.assertEqual(self.saved()[0]["duplicates"]["decision"], "link")

    def test_a_decision_about_a_different_card_does_not_cover_the_candidate(self):
        self.not_ready("which the decision recorded in the draft does not cover",
                       **self.export(duplicate_decision="proceed", duplicate_candidates=[fake.cid(101)]))

    def test_a_decision_with_no_cards_named_covers_nothing(self):
        self.not_ready("does not cover", **self.export(duplicate_decision="proceed"))

    def test_a_decision_to_archive_as_duplicate_means_the_card_is_not_created(self):
        self.not_ready("this card is not to be created",
                       **self.export(duplicate_decision="archive-as-duplicate", duplicate_candidates=[fake.cid(201)]))

    def test_a_decision_that_is_not_one_of_the_three_words_is_refused(self):
        self.refused("duplicate_decision must be one of", duplicate_decision="merge")

    def test_candidates_with_no_decision_are_refused(self):
        self.refused("records no duplicate_decision", duplicate_candidates=[fake.cid(201)])

    def test_an_index_that_does_not_match_its_records_refuses_the_preview(self):
        with open(os.path.join(self.boards, "support-team", "cards", fake.cid(201) + ".md"), "a", encoding="utf-8") as f:
            f.write("\nchanged\n")
        self.refused("the duplicate search could not run")

    def test_a_board_missing_from_the_local_indexes_refuses_the_preview(self):
        shutil.rmtree(os.path.join(self.boards, "platform-team"))
        self.refused("not among the boards searched")

    def test_cards_in_trello_that_the_index_lacks_are_warned_about(self):
        cards = self.fake.boards[fake.PLATFORM]["cards"]
        cards.append(dict(copy.deepcopy(cards[0]), id=fake.cid(150), pos=900))
        out = self.ready()
        self.assertIn("WARNING: the index of this board holds 6 cards and Trello holds 7. 1 in Trello have NOT been searched.", out)

    def test_counts_that_agree_are_said_to_agree(self):
        self.assertIn("holds 6 cards and Trello holds 6: the counts agree", self.ready())


class NothingIsWritten(Case):
    """Criterion 6: running the preview changes nothing in Trello."""

    def test_every_request_is_a_get(self):
        self.ready()
        self.assertTrue(self.fake.requests)
        self.assertEqual({method for method, _, _ in self.fake.requests}, {"GET"})

    def test_the_fake_trello_holds_exactly_what_it_held_before(self):
        before = copy.deepcopy((self.fake.boards, self.fake.token, self.fake.me))
        self.ready()
        self.assertEqual((self.fake.boards, self.fake.token, self.fake.me), before)

    def test_the_preview_shows_the_board_snapshot_before_and_after_and_they_match(self):
        out = self.ready()
        before = re.search(r"before the preview: (.+)", out).group(1)
        after = re.search(r"after the preview:  (.+)", out).group(1)
        self.assertEqual(before, after)
        self.assertIn("4 lists, 6 cards", before)

    def test_every_request_sent_is_listed(self):
        out = self.ready()
        self.assertEqual(len(re.findall(r"^  GET /", out, re.M)), len(self.fake.requests))
        self.assertIn("Requests sent to Trello: %d." % len(self.fake.requests), out)

    def test_a_board_that_changes_during_the_preview_refuses_it(self):
        def move(path):
            if path.endswith("/memberships"):
                self.fake.boards[fake.PLATFORM]["cards"][0]["pos"] = 999
        self.fake.after = move
        self.refused("changed in Trello while the preview was being made")

    def test_the_snapshot_notices_a_list_being_archived(self):
        def archive(path):
            if path.endswith("/memberships"):
                self.fake.boards[fake.PLATFORM]["lists"][2]["closed"] = True
        self.fake.after = archive
        self.refused("changed in Trello while the preview was being made")

    def test_the_preview_has_no_code_of_its_own_that_sends_anything(self):
        with open(os.path.join(os.path.dirname(HERE), "preview.py"), encoding="utf-8") as f:
            source = f.read()
        imported = {a or b for a, b in re.findall(r"^\s*(?:import (\w+)|from (\w+) import)", source, re.M)}
        self.assertEqual(imported, {"argparse", "datetime", "hashlib", "json", "os", "re", "sys", "search", "card", "fake_trello"})
        self.assertNotIn("urllib", source)
        self.assertEqual([name for name in dir(preview.Connection) if not name.startswith("_")], ["get", "token"])

    def test_the_approved_reader_it_uses_for_a_live_run_sends_get_only(self):
        with open(os.path.join(preview.ROOT, "participant", "skills", "trello-read-card", "card.py"), encoding="utf-8") as f:
            source = f.read()
        self.assertEqual(re.findall(r'method="(\w+)"', source), ["GET"])
        self.assertNotIn("data=", source)

    def test_the_local_indexes_are_unchanged(self):
        def snapshot():
            found = {}
            for base, _, names in os.walk(self.boards):
                for name in names:
                    with open(os.path.join(base, name), "rb") as f:
                        found[os.path.join(base, name)] = f.read()
            return found
        before = snapshot()
        self.ready()
        self.assertEqual(snapshot(), before)


class Sources(Case):
    """Criterion 7: source citations are included."""

    def test_each_citation_is_shown_with_its_file_and_line(self):
        out = self.ready()
        self.assertIn("SOURCES for the content, each checked against the file: 5 citations, all true.", out)
        self.assertRegex(out, r'name +\S+notes\.md line 7: "add a status page link to the app footer"')

    def test_the_payload_file_gives_a_source_for_each_field_of_content(self):
        self.ready()
        with open(self.payload_out, encoding="utf-8") as f:
            text = f.read()
        for key in ("name", "desc", "due", "idLabels", "idMembers"):
            self.assertRegex(text, r"\| `%s` \| .* \| .*notes\.md line" % key)
        self.assertIn("| `idList` | %s | the draft's target |" % fake.TO_DO, text)

    def test_content_with_no_citation_is_refused(self):
        sources = dict(STATUS["sources"])
        del sources["due"]
        self.refused("the draft gives no source for: due", sources=sources)

    def test_a_quotation_that_is_not_on_the_line_is_refused(self):
        self.refused("is not true", sources=dict(STATUS["sources"], name=(7, "add a dark mode toggle")))

    def test_a_quotation_on_another_line_is_refused(self):
        self.refused("is not true", sources=dict(STATUS["sources"], name=(8, "add a status page link to the app footer")))

    def test_a_source_outside_the_context_folder_is_refused(self):
        outside = os.path.join(self.tmp, "notes.md")
        shutil.copy(NOTES, outside)
        self.refused("points outside participant/context/", text=draft_text().replace(NOTES, outside))

    def test_a_citation_for_something_not_in_the_draft_is_refused(self):
        text = draft_text(due=None) + '- due: %s line 12: "Friday 11 December 2026"\n' % NOTES
        self.refused("which is not in the draft", text=text)


class TheDraft(Case):
    def test_a_field_the_preview_does_not_know_is_refused(self):
        self.refused("does not support", text=draft_text().replace('position: "bottom"', 'position: "bottom"\nidBoard: "x"'))

    def test_a_file_that_is_not_a_draft_is_refused(self):
        self.refused("is not a card draft", text="# Just notes\n")

    def test_a_due_time_that_is_not_real_is_refused(self):
        for due in ("2026-12-11", "2026-13-40T17:00:00.000Z", "next Friday"):
            self.refused("is not a real time", due=due)

    def test_a_due_time_in_the_past_is_refused(self):
        self.refused("A new card is not created already overdue", due="2026-11-19T17:00:00.000Z")

    def test_a_name_with_only_spaces_is_refused(self):
        self.refused("no usable name", name="   ")

    def test_a_draft_with_no_description_sends_none(self):
        self.assertNotIn("desc", self.printed_payload(self.ready(description="")))


class Credentials(Case):
    KEY, TOKEN = "k" * 32, fake.TOKEN_PATH.split("/")[-1]

    def live(self):
        original = preview.make_live
        preview.make_live = lambda: (preview.Connection(self.fake.get, fake.TOKEN_PATH), [self.KEY, self.TOKEN])
        self.addCleanup(setattr, preview, "make_live", original)
        path = os.path.join(self.tmp, "draft.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(draft_text())
        self.log = os.path.join(self.tmp, "log.txt")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = preview.main(["--source", "live", "--draft", path, "--allowlist", self.allowlist, "--boards", self.boards,
                                 "--state", self.state, "--now", NOW, "--payload-out", self.payload_out, "--log", self.log])
        return code, out.getvalue()

    def test_the_token_is_in_a_request_path_and_is_never_shown_or_saved(self):
        code, out = self.live()
        self.assertEqual(code, 0, out)
        self.assertTrue(any(self.TOKEN in path for _, path, _ in self.fake.requests))
        self.assertIn("GET /tokens/[the token]", out)
        self.assertIn("searched for the API key and the token: neither found", out)
        texts = [out, json.dumps(self.saved())]
        for path in (self.log, self.payload_out):
            with open(path, encoding="utf-8") as f:
                texts.append(f.read())
        for text in texts:
            self.assertNotIn(self.TOKEN, text)
            self.assertNotIn(self.KEY, text)

    def test_if_the_token_would_appear_nothing_is_shown_or_saved(self):
        self.fake.boards[fake.PLATFORM]["lists"][1]["name"] = "To do " + self.TOKEN
        code, out = self.live()
        self.assertEqual(code, 1)
        self.assertTrue(out.startswith("STOPPED: the key or the token was found"))
        self.assertNotIn(self.TOKEN, out)
        self.assertEqual(self.saved(), [])
        self.assertFalse(os.path.exists(self.payload_out))
        self.assertFalse(os.path.exists(self.log))

    def test_the_preview_reads_no_credential_itself(self):
        with open(os.path.join(os.path.dirname(HERE), "preview.py"), encoding="utf-8") as f:
            self.assertNotIn("os.environ", f.read())


if __name__ == "__main__":
    unittest.main()
