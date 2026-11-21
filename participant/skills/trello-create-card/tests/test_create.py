"""Tests for the create workflow, create.py. A fake Trello in memory, local files in temporary folders.

Run from the repository root:
    python3 -m unittest discover -s participant/skills/trello-create-card/tests -v
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
import types
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import create  # noqa: E402
from create import pv  # noqa: E402

fake = create.load_fake()
REAL_MAKE_LIVE = create.make_live
NEW_CARD = os.path.join(create.ROOT, "participant", "context", "trello", "new-card")
NOW = "2026-11-20T09:00:00Z"
NAME = "Add a status page link to the app footer"


class Case(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp = os.path.realpath(tmp.name)
        # The draft has to sit under participant/context/ for its citations, so the fixture's own draft is used in place.
        self.draft = os.path.join(self.tmp, "draft.md")
        with open(os.path.join(NEW_CARD, "draft.md"), encoding="utf-8") as f:
            self.draft_text = f.read().replace(": sources/notes.md", ": %s/sources/notes.md" % NEW_CARD)
        self.write_draft(self.draft_text)
        self.link = os.path.join(self.tmp, "linked.md")
        self.state = os.path.join(self.tmp, "state")
        self.result = os.path.join(self.tmp, "result.md")
        self.allowlist = os.path.join(NEW_CARD, "sandbox-allowlist.json")
        self.boards = os.path.join(NEW_CARD, "fixture", "boards")
        self.fake = fake.FakeTrello()
        self.fake.save = lambda path: None
        self.posted = []
        original_post = self.fake.post

        def post(path, params, body):
            self.posted.append(body)
            self.link_when_sent = None
            if os.path.exists(self.link):
                with open(self.link, encoding="utf-8") as f:
                    self.link_when_sent = f.read()
            return original_post(path, params, body)
        self.fake.post = post
        holder = types.SimpleNamespace(FakeTrello=types.SimpleNamespace(open=lambda path: self.fake), TOKEN_PATH=fake.TOKEN_PATH)
        original = create.load_fake
        create.load_fake = lambda: holder
        self.addCleanup(setattr, create, "load_fake", original)

    def write_draft(self, text):
        with open(self.draft, "w", encoding="utf-8") as f:
            f.write(text)

    def run_cmd(self, command, *extra, link=None, source="fake"):
        args = [command, "--source", source, "--fake-file", "unused", "--link", link or self.link]
        if command in ("preview", "confirm"):
            args += ["--draft", self.draft, "--allowlist", self.allowlist, "--boards", self.boards, "--state", self.state, "--now", NOW]
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = create.main(args + list(extra))
        return code, out.getvalue()

    def preview(self):
        code, out = self.run_cmd("preview")
        self.assertEqual(code, 0, out)
        return re.search(r"Fingerprint of this preview: (\w{12})", out).group(1), out

    def confirm(self, code, *extra, by="the participant"):
        return self.run_cmd("confirm", "--fingerprint", code, "--confirmed-by", by, "--result", self.result, *extra)

    def created(self):
        """The cards on the platform board that the fixture does not start with."""
        return [card for card in self.fake.boards[fake.PLATFORM]["cards"] if not card["id"].startswith("82c")]

    def posts(self):
        return [request for request in self.fake.requests if request[0] == "POST"]

    def link_front(self):
        with open(self.link, encoding="utf-8") as f:
            return create.index.front_matter(f.read())

    def refused(self, expect, code_out):
        code, out = code_out
        self.assertEqual(code, 1, out)
        self.assertIn("REFUSED: ", out)
        self.assertIn(expect, out)
        self.assertIn("Nothing has been written to Trello.", out)
        self.assertEqual(self.posts(), [], "a refusal must send no create")
        self.assertEqual(self.created(), [])
        return out


class ThePreview(Case):
    """Criteria 4 and 5."""

    def test_it_shows_the_board_the_list_and_the_exact_change(self):
        _, out = self.preview()
        self.assertIn('Board:  "Made-up platform team board" (board id %s). On the sandbox allowlist: yes.' % fake.PLATFORM, out)
        self.assertIn('List:   "To do" (list id %s). Chosen by id.' % fake.TO_DO, out)
        self.assertIn("The change: one new card would be created, with one request: POST https://api.trello.com/1/cards", out)
        payload = json.loads(out.split("not a summary of it:\n", 1)[1].split("\nAs sent it is", 1)[0])
        self.assertEqual((payload["idList"], payload["pos"], payload["name"]), (fake.TO_DO, "bottom", NAME))

    def test_it_shows_the_tokens_scope_and_expiry_and_the_permission_check(self):
        self.fake.token["dateExpires"] = "2026-11-21T12:00:00.000Z"
        _, out = self.preview()
        self.assertIn("the token's own permissions for boards: read yes, write yes", out)
        self.assertIn("the token expires: 2026-11-21T12:00:00.000Z", out)
        self.assertIn("on the board as: normal. That role may add cards: yes", out)

    def test_it_shows_three_duplicate_checks_and_where_trello_cannot_check(self):
        _, out = self.preview()
        self.assertIn("1. This draft's own link file: there is none", out)
        self.assertIn("2. Asked of Trello, open cards on this board with exactly this name: 0.", out)
        self.assertIn("Result: NONE.", out)
        self.assertIn("Where Trello cannot check: it has no way to refuse a second create of the same card", out)

    def test_it_writes_nothing_to_trello(self):
        before = copy.deepcopy(self.fake.boards)
        _, out = self.preview()
        self.assertEqual(self.fake.boards, before)
        self.assertEqual({request[0] for request in self.fake.requests}, {"GET"})
        self.assertIn("Every one was a GET", out)
        snaps = re.findall(r"Snapshot of the board in Trello (?:before|after) the preview: +(.+)", out)
        self.assertEqual(snaps[0], snaps[1])
        self.assertFalse(os.path.exists(self.link))

    def test_a_preview_has_no_way_to_write(self):
        conn = create.Connection(self.fake.get, None, fake.TOKEN_PATH)
        with self.assertRaises(create.Refused):
            conn.create(b"{}")
        self.assertEqual(self.posts(), [])

    def test_a_token_that_may_not_write_gives_no_fingerprint(self):
        self.fake.token["permissions"][0]["write"] = False
        code, out = self.run_cmd("preview")
        self.assertEqual(code, 3)
        self.assertIn("VERDICT: NOT READY TO WRITE.", out)
        self.assertIn("read yes, write NO", out)
        self.assertNotIn("Fingerprint of this preview", out)
        self.assertFalse(os.path.isdir(os.path.join(self.state, "create-card-previews")))

    def test_an_open_card_with_this_name_on_the_board_is_not_ready(self):
        cards = self.fake.boards[fake.PLATFORM]["cards"]
        cards.append(dict(copy.deepcopy(cards[0]), id=fake.cid(150), name=NAME.upper(), pos=900))
        code, out = self.run_cmd("preview")
        self.assertEqual(code, 3)
        self.assertIn("with exactly this name (card %s)" % fake.cid(150), out)

    def test_a_board_not_on_the_allowlist_is_refused(self):
        self.write_draft(self.draft_text.replace(fake.PLATFORM, fake.SUPPORT).replace(fake.TO_DO, fake.INBOX))
        self.refused("is not on the sandbox allowlist", self.run_cmd("preview"))
        self.assertEqual(self.fake.requests, [])

    def test_two_previews_of_one_draft_have_different_fingerprints(self):
        self.assertNotEqual(self.preview()[0], self.preview()[0])


class TheConfirmation(Case):
    """Criteria 1, 2, 7 and 8."""

    def test_a_confirmed_preview_creates_exactly_one_card(self):
        code, _ = self.preview()
        result, out = self.confirm(code)
        self.assertEqual(result, 0, out)
        self.assertEqual(len(self.posts()), 1)
        self.assertEqual(len(self.created()), 1)
        self.assertIn("CONFIRMATION for preview %s, given by: the participant" % code, out)
        self.assertIn("The confirmation and the write happened in this one run of the command.", out)

    def test_the_bytes_sent_are_the_bytes_whose_sha_the_preview_showed(self):
        code, out = self.preview()
        shown = re.search(r"SHA-256 (\w{64})", out).group(1)
        self.confirm(code)
        self.assertEqual(hashlib.sha256(self.posted[0]).hexdigest(), shown)
        payload = json.loads(out.split("not a summary of it:\n", 1)[1].split("\nAs sent it is", 1)[0])
        self.assertEqual(self.posted[0], pv.body_bytes(payload))

    def test_the_card_created_holds_what_the_payload_sent(self):
        code, _ = self.preview()
        self.confirm(code)
        card, payload = self.created()[0], json.loads(self.posted[0])
        self.assertEqual((card["idList"], card["name"], card["desc"], card["due"], ",".join(card["idLabels"]), ",".join(card["idMembers"])),
                         (payload["idList"], payload["name"], payload["desc"], payload["due"], payload["idLabels"], payload["idMembers"]))
        self.assertEqual(card["pos"], max(c["pos"] for c in self.fake.boards[fake.PLATFORM]["cards"] if c["idList"] == fake.TO_DO))

    def test_the_label_goes_on_in_the_same_one_request(self):
        code, _ = self.preview()
        self.confirm(code)
        self.assertEqual([label["name"] for label in self.created()[0]["labels"]], ["feature"])
        self.assertEqual(len(self.posts()), 1)

    def test_the_link_file_is_written_before_the_create_is_sent(self):
        code, _ = self.preview()
        self.confirm(code)
        front = create.index.front_matter(self.link_when_sent)
        self.assertEqual((front["state"], front["card_id"]), (create.SENT, None))
        before = create.json_block(self.link_when_sent, create.BEFORE_HEADING)
        self.assertEqual(len(before), 6)
        self.assertIn("Do not create it again.", self.link_when_sent)

    def test_the_returned_identifiers_are_written_to_the_link_file(self):
        code, _ = self.preview()
        _, out = self.confirm(code)
        front, card = self.link_front(), self.created()[0]
        self.assertEqual((front["state"], front["card_id"], front["list_id"], front["board_id"], front["short_link"]),
                         (create.CREATED, card["id"], fake.TO_DO, fake.PLATFORM, card["shortLink"]))
        self.assertIn("Written to the link file: the card id %s" % card["id"], out)

    def test_the_card_is_read_back_by_its_id_and_every_field_is_the_same(self):
        code, _ = self.preview()
        _, out = self.confirm(code)
        card = self.created()[0]
        self.assertIn(("GET", "/cards/%s" % card["id"], {"fields": "all"}), self.fake.requests)
        self.assertIn("Result: every field the payload sent reads back the same.", out)
        with open(self.link, encoding="utf-8") as f:
            text = f.read()
        for field in ("idList", "pos", "name", "desc", "due", "idLabels", "idMembers", "idBoard"):
            self.assertRegex(text, r"\| `%s` \| .* \| the same" % field)
        self.assertNotIn("DIFFERENT", text)

    def test_the_result_record_holds_the_ids_the_time_and_the_confirmer(self):
        code, _ = self.preview()
        self.confirm(code, by="A. Tester")
        card = self.created()[0]
        with open(self.result, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("- Board id: %s" % fake.PLATFORM, text)
        self.assertIn("- List id: %s" % fake.TO_DO, text)
        self.assertIn("- Card id: %s" % card["id"], text)
        self.assertIn("Identifier of what was created: the card, Trello card id %s" % card["id"], text)
        self.assertRegex(text, r"- Created at: \d{4}-\d\d-\d\d \d\d:\d\d:\d\d UTC")
        self.assertRegex(text, r"- Confirmed by: A\. Tester, at \d{4}-")
        self.assertIn("- Preview: fingerprint %s" % code, text)

    def test_a_create_is_sent_once_in_a_run(self):
        conn = create.Connection(self.fake.get, self.fake.post, fake.TOKEN_PATH)
        conn.create(b'{"idList":"%s","name":"x"}' % fake.TO_DO.encode())
        with self.assertRaises(create.Refused):
            conn.create(b"{}")
        self.assertEqual(len(self.posts()), 1)


class Refusals(Case):
    """Criteria 4, 6 and 7: nothing is written without a confirmation of this exact preview."""

    def test_no_fingerprint_is_refused(self):
        self.preview()
        self.refused("no confirmation was given", self.run_cmd("confirm", "--confirmed-by", "the participant"))

    def test_no_name_is_refused(self):
        code, _ = self.preview()
        self.refused("gives the name of the person confirming", self.run_cmd("confirm", "--fingerprint", code))

    def test_an_email_address_as_the_name_is_refused(self):
        code, _ = self.preview()
        self.refused("not an email address", self.confirm(code, by="someone@example.invalid"))

    def test_a_fingerprint_no_preview_has_is_refused(self):
        self.preview()
        self.refused("there is no preview with the fingerprint", self.confirm("0123456789ab"))

    def test_something_that_is_not_a_fingerprint_is_refused(self):
        self.preview()
        self.refused("a fingerprint is 12 characters", self.confirm("yes"))

    def test_a_draft_changed_after_the_preview_is_refused_and_the_field_is_named(self):
        code, _ = self.preview()
        self.write_draft(self.draft_text.replace('position: "bottom"', 'position: "top"'))
        self.refused("the change is not the one that was previewed: the payload now differs in pos", self.confirm(code))

    def test_a_draft_edited_without_changing_the_payload_is_refused_too(self):
        code, _ = self.preview()
        self.write_draft(self.draft_text.replace("# Card draft:", "# Card draft, edited:"))
        self.refused("the draft file has been edited since the preview", self.confirm(code))

    def test_a_preview_older_than_the_limit_is_refused(self):
        code, _ = self.preview()
        out = self.refused("this preview is too old. It was made 16 minutes ago and the limit is 15",
                           self.confirm(code, "--pretend-minutes-later", "16"))
        self.assertIn("TEST CLOCK", out)

    def test_a_preview_just_inside_the_limit_is_accepted(self):
        code, _ = self.preview()
        self.assertEqual(self.confirm(code, "--pretend-minutes-later", "14")[0], 0)

    def test_a_board_taken_off_the_allowlist_is_refused(self):
        code, _ = self.preview()
        self.allowlist = os.path.join(self.tmp, "allowlist.json")
        with open(self.allowlist, "w", encoding="utf-8") as f:
            json.dump({"sandbox_boards": [fake.SUPPORT]}, f)
        self.refused("is not on the sandbox allowlist", self.confirm(code))

    def test_a_saved_preview_that_was_altered_is_refused(self):
        code, _ = self.preview()
        path = os.path.join(self.state, "create-card-previews", code + ".json")
        with open(path, encoding="utf-8") as f:
            record = json.load(f)
        record["payload"]["name"] = "Something else"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(record, f)
        self.refused("has been altered since it was made", self.confirm(code))

    def test_a_different_link_file_is_refused(self):
        code, _ = self.preview()
        self.link = os.path.join(self.tmp, "other.md")
        self.refused("not the one the preview was made for", self.confirm(code))

    def test_a_token_that_lost_its_write_scope_since_the_preview_is_refused(self):
        code, _ = self.preview()
        self.fake.token["permissions"][0]["write"] = False
        self.refused("a check that passed at the preview does not pass now", self.confirm(code))

    def test_a_same_name_card_made_since_the_preview_is_refused(self):
        code, _ = self.preview()
        cards = self.fake.boards[fake.PLATFORM]["cards"]
        cards.append(dict(copy.deepcopy(cards[0]), id=fake.cid(150), name=NAME, pos=900))
        code_out = self.confirm(code)
        self.assertEqual(code_out[0], 1)
        self.assertIn("does not pass now", code_out[1])
        self.assertEqual(self.posts(), [])

    def test_a_list_archived_since_the_preview_is_refused(self):
        code, _ = self.preview()
        self.fake.boards[fake.PLATFORM]["lists"][1]["closed"] = True
        self.refused("is archived", self.confirm(code))


class ASecondRun(Case):
    """Criterion 9: running it again creates nothing."""

    def setUp(self):
        super().setUp()
        self.code, _ = self.preview()
        self.assertEqual(self.confirm(self.code)[0], 0)
        self.card = self.created()[0]["id"]

    def again(self, expect, code_out):
        code, out = code_out
        self.assertEqual(code, 1, out)
        self.assertIn(expect, out)
        self.assertEqual(len(self.posts()), 1)
        self.assertEqual(len(self.created()), 1)

    def test_a_second_preview_is_refused_and_names_the_card(self):
        self.again("has already been created in Trello as card %s" % self.card, self.run_cmd("preview"))

    def test_the_same_fingerprint_cannot_be_used_twice(self):
        self.again("A fingerprint is used once", self.confirm(self.code))

    def test_a_second_run_reads_trello_not_at_all_before_refusing(self):
        self.fake.requests.clear()
        self.run_cmd("preview")
        self.assertEqual(self.fake.requests, [])

    def test_without_the_link_file_trello_itself_shows_the_card_and_the_preview_is_not_ready(self):
        code, out = self.run_cmd("preview", link=os.path.join(self.tmp, "another-machine.md"))
        self.assertEqual(code, 3)
        self.assertIn("with exactly this name (card %s)" % self.card, out)
        self.assertNotIn("Fingerprint of this preview", out)
        self.assertEqual(len(self.created()), 1)

    def test_a_link_file_for_another_draft_is_not_reused(self):
        other = os.path.join(self.tmp, "other-draft.md")
        shutil.copy(self.draft, other)
        self.draft = other
        self.again("the link file belongs to another draft", self.run_cmd("preview"))


class WhenTheAnswerIsLost(Case):
    """The second stretch goal, and the quest's reflection: the write happens and the result is not recorded."""

    def lose(self, **knobs):
        self.code, _ = self.preview()
        self.fake.knobs.update(knobs)
        code, out = self.confirm(self.code)
        self.fake.knobs.clear()
        return code, out

    def test_a_lost_answer_is_not_called_a_failure_and_is_not_retried(self):
        code, out = self.lose(lose_answer=True)
        self.assertEqual(code, 2)
        self.assertIn("It is NOT KNOWN whether Trello created the card. It was not sent again", out)
        self.assertEqual(len(self.posts()), 1)
        self.assertEqual(self.link_front()["state"], create.SENT)

    def test_after_a_lost_answer_nothing_creates_again(self):
        self.lose(lose_answer=True)
        for code_out in (self.run_cmd("preview"), self.confirm(self.code)):
            self.assertEqual(code_out[0], 1)
            self.assertRegex(code_out[1], "Run the reconcile command|was confirmed before and a create was sent")
        self.assertEqual(len(self.posts()), 1)
        self.assertEqual(len(self.created()), 1)

    def test_reconcile_finds_the_card_that_was_made_and_links_it(self):
        self.lose(lose_answer=True)
        card = self.created()[0]["id"]
        code, out = self.run_cmd("reconcile", "--result", self.result)
        self.assertEqual(code, 0, out)
        self.assertIn("FOUND exactly one: card %s" % card, out)
        self.assertIn("every field the payload sent reads back the same", out)
        self.assertEqual((self.link_front()["state"], self.link_front()["card_id"]), (create.CREATED, card))
        self.assertEqual(len(self.posts()), 1, "reconcile must not create")
        self.assertEqual(self.run_cmd("verify")[0], 0)

    def test_reconcile_says_not_found_when_the_create_never_arrived(self):
        self.lose(drop_request=True)
        with open(self.link, encoding="utf-8") as f:
            before = f.read()
        code, out = self.run_cmd("reconcile")
        self.assertEqual(code, 1)
        self.assertIn("NOT FOUND.", out)
        self.assertIn("0 were not there before the create was sent", out)
        with open(self.link, encoding="utf-8") as f:
            self.assertEqual(f.read(), before)
        self.assertEqual(self.created(), [])

    def test_reconcile_does_not_take_a_card_that_was_there_before(self):
        cards = self.fake.boards[fake.PLATFORM]["cards"]
        self.code, _ = self.preview()
        payload = None
        self.fake.knobs["drop_request"] = True
        self.confirm(self.code)
        self.fake.knobs.clear()
        payload = json.loads(self.posted[0])
        # an identical card whose id was on the board before the create was sent
        old = dict(copy.deepcopy(cards[0]), name=payload["name"], desc=payload["desc"], due=payload["due"],
                   idLabels=payload["idLabels"].split(","), idMembers=payload["idMembers"].split(","))
        cards[0].update(old)
        code, out = self.run_cmd("reconcile")
        self.assertEqual(code, 1)
        self.assertIn("NOT FOUND.", out)

    def test_reconcile_ignores_a_new_card_that_is_some_other_card(self):
        self.lose(drop_request=True)
        cards = self.fake.boards[fake.PLATFORM]["cards"]
        cards.append(dict(copy.deepcopy(cards[1]), id="6b0000000000000000000abc"))
        code, out = self.run_cmd("reconcile")
        self.assertEqual(code, 1)
        self.assertIn("1 were not there before the create was sent", out)
        self.assertIn("hold what the payload sent (list, name, description, due, labels, members): 0", out)

    def test_reconcile_links_nothing_when_two_new_cards_match(self):
        self.lose(lose_answer=True)
        cards = self.fake.boards[fake.PLATFORM]["cards"]
        cards.append(dict(copy.deepcopy(self.created()[0]), id="6b0000000000000000000abc"))
        code, out = self.run_cmd("reconcile")
        self.assertEqual(code, 1)
        self.assertIn("2 new cards hold what was sent", out)
        self.assertEqual(self.link_front()["state"], create.SENT)

    def test_when_the_card_is_made_and_the_link_file_cannot_be_written_the_id_is_shown_and_nothing_creates_again(self):
        self.code, _ = self.preview()
        calls, original = [], create.write_link

        def failing(*args, **kwargs):
            calls.append(1)
            if len(calls) == 2:  # the first write is the intent, before sending. The second records the card id.
                raise OSError("disk full")
            return original(*args, **kwargs)
        create.write_link = failing
        self.addCleanup(setattr, create, "write_link", original)
        code, out = self.confirm(self.code)
        create.write_link = original
        card = self.created()[0]["id"]
        self.assertEqual(code, 2)
        self.assertIn("the card was created with the card id %s and the link file COULD NOT BE WRITTEN" % card, out)
        self.assertEqual((self.link_front()["state"], self.link_front()["card_id"]), (create.SENT, None))
        self.assertEqual(self.run_cmd("preview")[0], 1)
        self.assertEqual(len(self.posts()), 1)
        code, out = self.run_cmd("reconcile")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.link_front()["card_id"], card)
        self.assertEqual(len(self.created()), 1)

    def test_reconcile_with_nothing_to_reconcile_is_refused(self):
        self.code, _ = self.preview()
        self.confirm(self.code)
        code, out = self.run_cmd("reconcile")
        self.assertEqual(code, 1)
        self.assertIn("There is nothing to reconcile", out)


class WhenTrelloAnswersOtherwise(Case):
    def answer(self, **knobs):
        code, _ = self.preview()
        self.fake.knobs.update(knobs)
        result = self.confirm(code)
        self.fake.knobs.clear()
        return code, result

    def test_a_refusal_from_trello_that_made_no_card_removes_the_link_file(self):
        fingerprint, (code, out) = self.answer(post_status=400)
        self.assertEqual(code, 1)
        self.assertIn("Trello answered 400 to the create and made no card", out)
        self.assertIn("No card was created.", out)
        self.assertFalse(os.path.exists(self.link))
        self.assertEqual(self.created(), [])
        again = self.confirm(fingerprint)
        self.assertEqual(again[0], 1)
        self.assertIn("It cannot be used again", again[1])
        self.assertEqual(len(self.posts()), 1)

    def test_a_server_error_is_not_taken_as_nothing_made(self):
        _, (code, out) = self.answer(post_status=500)
        self.assertEqual(code, 2)
        self.assertIn("it is not certain that no card was made", out)
        self.assertEqual(self.link_front()["state"], create.SENT)

    def test_a_card_that_reads_back_differently_needs_a_person(self):
        _, (code, out) = self.answer(alter={"due": "2026-12-12T17:00:00.000Z"})
        self.assertEqual(code, 2)
        self.assertIn("does not read back as it was sent", out)
        self.assertIn("NOT ALL THE SAME: due", self.link_front()["comparison"])
        self.assertEqual(len(self.created()), 1)

    def test_a_card_made_in_another_list_is_caught_by_the_read_back(self):
        _, (code, out) = self.answer(wrong_list=fake.DOING)
        self.assertEqual(code, 2)
        self.assertIn("NOT ALL THE SAME: idList", self.link_front()["comparison"])

    def test_a_description_trello_altered_is_caught(self):
        _, (code, out) = self.answer(alter={"desc": "Customers ask support."})
        self.assertEqual(code, 2)
        self.assertIn("NOT ALL THE SAME: desc", self.link_front()["comparison"])

    def test_a_label_trello_dropped_is_caught(self):
        _, (code, out) = self.answer(alter={"idLabels": []})
        self.assertEqual(code, 2)
        self.assertIn("NOT ALL THE SAME: idLabels", self.link_front()["comparison"])


class Verify(Case):
    """Criterion 3: the local file is matched to the Trello card by identifier afterwards."""

    def setUp(self):
        super().setUp()
        code, _ = self.preview()
        self.confirm(code)
        self.card = self.created()[0]

    def test_it_matches_by_card_id_and_finds_every_field_the_same(self):
        code, out = self.run_cmd("verify")
        self.assertEqual(code, 0, out)
        self.assertIn("Matched to Trello by card id %s: found." % self.card["id"], out)
        self.assertIn("Result: every field the payload sent reads back the same.", out)

    def test_it_writes_nothing_to_trello(self):
        self.run_cmd("verify")
        self.assertEqual(len(self.posts()), 1)

    def test_a_card_that_was_renamed_and_moved_is_still_the_same_card(self):
        self.card["name"], self.card["idList"] = "Renamed by someone", fake.DOING
        code, out = self.run_cmd("verify")
        self.assertEqual(code, 3)
        self.assertIn("Matched to Trello by card id %s: found." % self.card["id"], out)
        self.assertIn("THE CARD NO LONGER READS AS IT WAS SENT. It is the same card, by its id.", out)
        self.assertIn("NOT ALL THE SAME: idList, name", self.link_front()["comparison"])

    def test_a_card_no_longer_last_in_its_list_is_reported(self):
        cards = self.fake.boards[fake.PLATFORM]["cards"]
        cards.append(dict(copy.deepcopy(cards[0]), id=fake.cid(150), pos=self.card["pos"] + 10))
        code, out = self.run_cmd("verify")
        self.assertEqual(code, 3)
        self.assertIn("NOT ALL THE SAME: pos", self.link_front()["comparison"])

    def test_a_deleted_card_is_reported_and_the_link_file_is_left(self):
        self.fake.boards[fake.PLATFORM]["cards"].remove(self.card)
        before = self.link_front()
        code, out = self.run_cmd("verify")
        self.assertEqual(code, 1)
        self.assertIn("Trello answered 404 for card %s" % self.card["id"], out)
        self.assertEqual(self.link_front(), before)

    def test_a_file_that_is_not_a_link_is_left_alone(self):
        with open(self.link, "w", encoding="utf-8") as f:
            f.write("# my own notes\n")
        code, out = self.run_cmd("verify")
        self.assertEqual(code, 1)
        self.assertIn("is not a link this workflow wrote", out)


class Compare(unittest.TestCase):
    def rows(self, payload, card, others=None):
        card = dict({"id": "c1", "idList": "L", "idBoard": "B", "closed": False, "pos": 5, "name": "n"}, **card)
        rows, good, _ = create.compare(dict({"idList": "L", "name": "n", "pos": "bottom"}, **payload), card, "B", [card] + (others or []))
        return good, {row[0]: row[3] for row in rows}

    def test_top_means_first_among_the_open_cards(self):
        other = {"id": "c2", "idList": "L", "closed": False, "pos": 9}
        self.assertTrue(self.rows({"pos": "top"}, {}, [other])[0])
        self.assertFalse(self.rows({"pos": "bottom"}, {}, [other])[0])

    def test_an_archived_card_below_does_not_count(self):
        self.assertTrue(self.rows({"pos": "bottom"}, {}, [{"id": "c2", "idList": "L", "closed": True, "pos": 9}])[0])

    def test_a_number_position_must_read_back_as_that_number(self):
        self.assertTrue(self.rows({"pos": 5}, {})[0])
        self.assertFalse(self.rows({"pos": 6}, {})[0])

    def test_the_same_instant_written_differently_is_the_same_due(self):
        self.assertTrue(self.rows({"due": "2026-12-11T17:00:00.000Z"}, {"due": "2026-12-11T17:00:00.000Z"})[0])
        self.assertFalse(self.rows({"due": "2026-12-11T17:00:00.000Z"}, {"due": None})[0])

    def test_something_on_the_card_that_was_never_sent_is_a_difference(self):
        good, verdicts = self.rows({}, {"desc": "added by something else"})
        self.assertFalse(good)
        self.assertIn("DIFFERENT", verdicts["desc"])

    def test_a_card_on_another_board_is_a_difference(self):
        self.assertFalse(self.rows({}, {"idBoard": "other"})[0])

    def test_labels_are_compared_as_a_set(self):
        self.assertTrue(self.rows({"idLabels": "a,b"}, {"idLabels": ["b", "a"]})[0])
        self.assertFalse(self.rows({"idLabels": "a,b"}, {"idLabels": ["a"]})[0])


class Credentials(Case):
    KEY, TOKEN = "k" * 32, fake.TOKEN_PATH.split("/")[-1]

    def setUp(self):
        super().setUp()
        original = create.make_live
        create.make_live = lambda may_write: (create.Connection(self.fake.get, self.fake.post if may_write else None, fake.TOKEN_PATH),
                                              [self.KEY, self.TOKEN])
        self.addCleanup(setattr, create, "make_live", original)

    def test_the_token_is_never_in_the_output_the_link_file_or_the_result(self):
        code, out = self.run_cmd("preview", source="live")
        fingerprint = re.search(r"Fingerprint of this preview: (\w{12})", out).group(1)
        code, more = self.run_cmd("confirm", "--fingerprint", fingerprint, "--confirmed-by", "the participant", "--result", self.result, source="live")
        self.assertEqual(code, 0, more)
        self.assertIn("GET /tokens/[the token]", more)
        self.assertIn("searched for the API key and the token: neither found", more)
        texts = [out, more]
        for path in (self.link, self.result):
            with open(path, encoding="utf-8") as f:
                texts.append(f.read())
        for text in texts:
            self.assertNotIn(self.TOKEN, text)
            self.assertNotIn(self.KEY, text)

    def test_if_the_token_would_appear_nothing_is_shown(self):
        self.fake.boards[fake.PLATFORM]["lists"][1]["name"] = "To do " + self.TOKEN
        code, out = self.run_cmd("preview", source="live")
        self.assertEqual(code, 1)
        self.assertTrue(out.startswith("STOPPED: the key or the token was found"))
        self.assertNotIn(self.TOKEN, out)

    def test_the_real_write_function_sends_nothing_but_the_creation_of_a_card(self):
        os.environ["TRELLO_API_KEY"], os.environ["TRELLO_API_TOKEN"] = "not-a-real-key", "not-a-real-value"
        self.addCleanup(os.environ.pop, "TRELLO_API_KEY")
        self.addCleanup(os.environ.pop, "TRELLO_API_TOKEN")
        conn, _ = REAL_MAKE_LIVE(True)
        for path, params, body in (("/boards", None, b"{}"), ("/cards/abc", None, b"{}"), ("/cards", {"x": 1}, b"{}"), ("/cards", None, "{}")):
            with self.assertRaises(create.Refused):
                conn._post(path, params, body)
        self.assertIsNone(REAL_MAKE_LIVE(False)[0]._post)


if __name__ == "__main__":
    unittest.main()
