#!/usr/bin/env python3
"""Records logs/preview.txt, confirmation.txt, rerun.txt and recovery.txt for the trello-create-card quest.

Each block between dashed lines is what a command printed. Every command is
started as a person would start it, against the made-up Trello in
participant/skills/trello-create-card/fake_trello_write.py, which is kept in
a file between commands. No network is used and nothing here contacts Trello.

In these recordings the script gives the confirmation, to a made-up Trello,
with the fingerprint it reads out of the preview's output. On the real board
the participant read the preview and typed the confirmation themself. Those
runs are in the logs named live-*.txt, and each is copied unchanged to the
end of the log it belongs to.

Everything a run writes goes in a temporary folder, shown as STATE.

This script checks for itself. It opens the made-up Trello's file before and
after each command and compares the boards, rather than taking the
workflow's word for what was written.

Run from anywhere:  python3 scripts/record_evidence.py
Exit code 0 if every check came out as expected, 1 if not.
"""
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ATTEMPT = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(ATTEMPT, "..", "..", "..", ".."))
SKILL = "participant/skills/trello-create-card"
CREATE = SKILL + "/create.py"
BASE = "participant/context/trello/new-card"
NOW = "2026-11-20T09:00:00Z"
PLATFORM, SUPPORT, TO_DO = "80b000000000000000000001", "80b000000000000000000002", "81a000000000000000000011"
SANDBOX = "6afdf376f8b9111df7e27f99"
WHO = "the participant"

_spec = importlib.util.spec_from_file_location("recorder_fake", os.path.join(ROOT, SKILL, "fake_trello_write.py"))
fake = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fake)


class Log:
    def __init__(self, title, tmp):
        self.lines, self.problems, self.tmp = [title], [], tmp
        self.out("Recorded by scripts/record_evidence.py against a made-up Trello kept in a file. No Trello was contacted.")

    def out(self, text=""):
        self.lines.append(text)

    def part(self, text):
        self.lines += ["", "=" * 78, text]

    def check(self, label, ok):
        self.lines.append("  %-4s %s" % ("ok" if ok else "FAIL", label))
        if not ok:
            self.problems.append(label)

    def tidy(self, text):
        return text.replace(self.tmp, "STATE")

    def command(self, *args):
        self.out("$ python3 %s %s" % (CREATE, self.tidy(" ".join('"%s"' % a if " " in a else a for a in args))))
        done = subprocess.run([sys.executable, CREATE] + list(args), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        self.lines += ["-" * 78, self.tidy(done.stdout.rstrip("\n")), "-" * 78, "exit code: %d" % done.returncode]
        return done.returncode, self.tidy(done.stdout)

    def append_live(self, name, title):
        path = os.path.join(ATTEMPT, "logs", name)
        if os.path.exists(path):
            self.part("%s The participant's own run on the real sandbox board, copied unchanged from logs/%s." % (title, name))
            with open(path, encoding="utf-8") as f:
                self.lines += f.read().rstrip("\n").split("\n")

    def finish(self, name):
        count = sum(1 for line in self.lines if re.match(r"  (ok  |FAIL) ", line))
        self.lines += ["", "RESULT: %s" % ("ALL CHECKS PASSED. %d checks." % count if not self.problems
                                           else "%d OF %d CHECKS FAILED." % (len(self.problems), count))]
        os.makedirs(os.path.join(ATTEMPT, "logs"), exist_ok=True)
        with open(os.path.join(ATTEMPT, "logs", name), "w", encoding="utf-8") as f:
            f.write("\n".join(self.lines) + "\n")
        print("%-18s %s" % (name, self.lines[-1]))
        for problem in self.problems:
            print("  FAILED: " + problem)
        return not self.problems


class World:
    """One made-up Trello in a file, with its own state folder and link file."""

    def __init__(self, tmp, name, draft=BASE + "/draft.md", allowlist=BASE + "/sandbox-allowlist.json", setup=None):
        self.folder = os.path.join(tmp, name)
        os.makedirs(self.folder)
        self.fake_file, self.link = os.path.join(self.folder, "fake-trello.json"), os.path.join(self.folder, "linked.md")
        self.state, self.result = os.path.join(self.folder, "state"), os.path.join(self.folder, "result.md")
        self.draft, self.allowlist = draft, allowlist
        trello = fake.FakeTrello()
        if setup:
            setup(trello)
        trello.save(self.fake_file)

    def common(self, command):
        args = [command, "--source", "fake", "--fake-file", self.fake_file, "--link", self.link]
        if command in ("preview", "confirm"):
            args += ["--draft", self.draft, "--allowlist", self.allowlist, "--boards", BASE + "/fixture/boards", "--state", self.state, "--now", NOW]
        return args

    def boards(self):
        with open(self.fake_file, encoding="utf-8") as f:
            return json.load(f)["boards"]

    def knobs(self, **knobs):
        with open(self.fake_file, encoding="utf-8") as f:
            data = json.load(f)
        data["knobs"] = knobs
        with open(self.fake_file, "w", encoding="utf-8") as f:
            json.dump(data, f)

    def new_cards(self):
        return [card for board in self.boards().values() for card in board["cards"] if not card["id"].startswith("82c")]

    def saved_previews(self):
        folder = os.path.join(self.state, "create-card-previews")
        return sorted(os.listdir(folder)) if os.path.isdir(folder) else []


def fingerprint_in(text):
    found = re.search(r"Fingerprint of this preview: (\w{12})", text)
    return found.group(1) if found else ""


def payload_in(text):
    return json.loads(text.split("not a summary of it:\n", 1)[1].split("\nAs sent it is", 1)[0])


def posts_in(text):
    return len(re.findall(r"^  POST /", text, re.M))


def temp_draft(folder):
    """A copy of the draft that can be edited, with its citations pointing at the real notes."""
    path = os.path.join(folder, "draft.md")
    with open(BASE + "/draft.md", encoding="utf-8") as f:
        text = f.read().replace(": sources/notes.md", ": %s/%s/sources/notes.md" % (ROOT, BASE))
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def preview_log(tmp):
    log = Log("The workflow stopping at a preview: trello-create-card, attempt trello-attempt-006", tmp)
    world = World(tmp, "preview", setup=lambda t: t.token.update(dateExpires="2026-11-21T12:00:00.000Z"))
    log.part("PART 1. The preview of %s/draft.md. (criteria 4 and 5)" % BASE)
    before = world.boards()
    code, text = log.command(*world.common("preview"))
    payload = payload_in(text)
    log.check("the workflow stopped at a preview: exit code 0, and the verdict is READY", code == 0 and "VERDICT: READY TO WRITE." in text)
    log.check("it shows the board and the list, each by id", 'Board:  "Made-up platform team board" (board id %s)' % PLATFORM in text
              and '(list id %s). Chosen by id.' % TO_DO in text)
    log.check("it shows the exact change: one new card, one POST, and the payload with its list and position",
              "one new card would be created, with one request: POST https://api.trello.com/1/cards" in text
              and payload["idList"] == TO_DO and payload["pos"] == "bottom")
    log.check("it shows the token's write scope and its expiry", "read yes, write yes" in text and "the token expires: 2026-11-21T12:00:00.000Z" in text)
    log.check("it shows the permission check: may this member add cards to this board", "on the board as: normal. That role may add cards: yes" in text)
    log.check("it shows three duplicate checks: the link file, asked of Trello, and the local indexes",
              all(piece in text for piece in ("1. This draft's own link file", "2. Asked of Trello, open cards on this board with exactly this name: 0", "Result: NONE.")))
    log.check("it states where Trello cannot check", "Where Trello cannot check: it has no way to refuse a second create of the same card" in text)
    log.check("it gives a fingerprint and an expiry: %s" % fingerprint_in(text), bool(fingerprint_in(text)) and "(15 minutes after it was made)" in text)
    snaps = re.findall(r"Snapshot of the board in Trello (?:before|after) the preview: +(.+)", text)
    log.check("its own snapshot of the board is the same before and after: %s" % (snaps[0] if snaps else "?"), len(snaps) == 2 and snaps[0] == snaps[1])
    sent = re.findall(r"^  (\w+) /", text, re.M)
    log.check("all %d requests were GET" % len(sent), bool(sent) and set(sent) == {"GET"})
    log.out("  Checked by this script, from the made-up Trello's own file:")
    log.check("every board, list and card in the made-up Trello is exactly as it was before the preview", world.boards() == before)
    log.check("no link file was written, so nothing claims a card exists", not os.path.exists(world.link))

    log.part("PART 2. A token that may read and may not write. There is then nothing to confirm. (criterion 5)")
    world = World(tmp, "read-only", setup=lambda t: t.token["permissions"][0].update(write=False))
    code, text = log.command(*world.common("preview"))
    log.check("the preview is NOT READY: exit code 3", code == 3 and "VERDICT: NOT READY TO WRITE." in text)
    log.check("it says why: the token may read and may not write", "read yes, write NO" in text and "may not write to them" in text)
    log.check("it gives no fingerprint and saves no preview, so no confirmation can be given", not fingerprint_in(text) and not world.saved_previews())
    log.append_live("live-preview.txt", "THE REAL PREVIEW.")
    return log.finish("preview.txt")


def confirmation_log(tmp):
    log = Log("The approved run, and four refusals: trello-create-card, attempt trello-attempt-006", tmp)
    log.out("In these recordings the script gives the confirmation. On the real board the participant typed it.")
    world = World(tmp, "approved")
    log.part("PART 1. The approved run: a preview, then a confirmation naming its fingerprint. (criteria 1, 2, 4, 7, 8)")
    code, text = log.command(*world.common("preview"))
    fingerprint, payload = fingerprint_in(text), payload_in(text)
    shown = re.search(r"SHA-256 (\w{64})", text).group(1)
    log.check("after the preview the made-up Trello holds no new card", code == 0 and not world.new_cards())
    log.out("The fingerprint %s is read from the preview above and given with the confirmation." % fingerprint)
    code, text = log.command(*world.common("confirm"), "--fingerprint", fingerprint, "--confirmed-by", WHO, "--result", world.result)
    cards = world.new_cards()
    log.check("the card was created: exit code 0", code == 0 and "CREATED in Trello: one card." in text)
    log.check("the confirmation names the preview's fingerprint and who gave it", "CONFIRMATION for preview %s, given by: %s" % (fingerprint, WHO) in text)
    log.check("the confirmation and the write were in one run of the command: it lists exactly one POST", posts_in(text) == 1
              and "The confirmation and the write happened in this one run" in text)
    log.check("before writing it checked again that the payload has the SHA-256 the preview showed", "has the SHA-256 of the previewed one, %s: ok" % shown in text)
    log.check("the link file was written before the create was sent", "Written to the link file before sending" in text
              and text.index("Written to the link file before sending") < text.index("CREATED in Trello"))
    log.out("  Checked by this script, from the made-up Trello's own file:")
    log.check("exactly one card exists that was not there before", len(cards) == 1)
    card = cards[0] if cards else {}
    log.check("criterion 1: that card holds the previewed payload field for field: list, name, description, due, label, member",
              bool(card) and (card["idList"], card["name"], card["desc"], card["due"], ",".join(card["idLabels"]), ",".join(card["idMembers"]))
              == (payload["idList"], payload["name"], payload["desc"], payload["due"], payload["idLabels"], payload["idMembers"]))
    log.check("and it is last in its list, which is what \"bottom\" asked for",
              bool(card) and card["pos"] == max(c["pos"] for c in world.boards()[PLATFORM]["cards"] if c["idList"] == TO_DO and not c["closed"]))
    with open(world.link, encoding="utf-8") as f:
        link = f.read()
    log.check("criterion 2: the link file holds the card id, the list id and the board id Trello returned",
              bool(card) and all('%s: "%s"' % pair in link for pair in (("card_id", card["id"]), ("list_id", TO_DO), ("board_id", PLATFORM))))
    log.check("the workflow's own read-back found every field the same", "Result: every field the payload sent reads back the same." in text and "DIFFERENT" not in link)
    with open(world.result, encoding="utf-8") as f:
        result = f.read()
    log.out("The result record it saved:")
    log.lines += ["-" * 78, log.tidy(result.rstrip("\n")), "-" * 78]
    log.check("criterion 8: the result record holds the board, list and card ids, what was created, the time and the confirmer",
              bool(card) and all(piece in result for piece in ("Board id: %s" % PLATFORM, "List id: %s" % TO_DO, "Card id: %s" % card["id"],
                                                               "Identifier of what was created: the card, Trello card id %s" % card["id"],
                                                               "Created at: 20", "Confirmed by: %s, at 20" % WHO)))

    def refusal(number, title, world, args, expect):
        before = world.boards()
        code, text = log.command(*args)
        log.check("refused: exit code 1", code == 1 and "REFUSED: " in text)
        log.check("the reason: %s" % expect, expect in text)
        log.check("nothing was written: no POST was sent, and the made-up Trello is exactly as it was", posts_in(text) == 0 and world.boards() == before and not world.new_cards())

    log.part("PART 2. Refusal 1 of 4: a missing confirmation. (criteria 4 and 7)")
    world = World(tmp, "missing")
    log.command(*world.common("preview"))
    refusal(1, "", world, world.common("confirm"), "no confirmation was given")

    log.part("PART 3. Refusal 2 of 4: the change differs from the preview. (criterion 7)")
    folder = os.path.join(tmp, "differs-draft")
    os.makedirs(folder)
    world = World(tmp, "differs", draft=temp_draft(folder))
    code, text = log.command(*world.common("preview"))
    with open(world.draft, encoding="utf-8") as f:
        draft = f.read()
    with open(world.draft, "w", encoding="utf-8") as f:
        f.write(draft.replace('position: "bottom"', 'position: "top"'))
    log.out('After the preview, the draft was edited: position "bottom" became position "top".')
    refusal(2, "", world, world.common("confirm") + ["--fingerprint", fingerprint_in(text), "--confirmed-by", WHO],
            "the change is not the one that was previewed: the payload now differs in pos")

    log.part("PART 4. Refusal 3 of 4: a preview older than the stated limit of 15 minutes. (criterion 7)")
    world = World(tmp, "too-old")
    code, text = log.command(*world.common("preview"))
    log.out("The workflow's clock is moved 16 minutes on with its tests-only option. The output says so.")
    refusal(3, "", world, world.common("confirm") + ["--fingerprint", fingerprint_in(text), "--confirmed-by", WHO, "--pretend-minutes-later", "16"],
            "this preview is too old. It was made 16 minutes ago and the limit is 15")

    log.part("PART 5. Refusal 4 of 4: a board that is not on the sandbox allowlist. (criterion 6)")
    log.out("First, a draft for the made-up support board, which the allowlist leaves out. It is refused at the preview.")
    folder = os.path.join(tmp, "support-draft")
    os.makedirs(folder)
    path = temp_draft(folder)
    with open(path, encoding="utf-8") as f:
        draft = f.read()
    with open(path, "w", encoding="utf-8") as f:
        f.write(draft.replace(PLATFORM, SUPPORT).replace(TO_DO, "81a000000000000000000021").replace('labels: ["feature"]\n', "").replace('members: ["5f0000000000000000000012"]\n', ""))
    with open(path, encoding="utf-8") as f:
        kept = [line for line in f.read().split("\n") if not line.startswith(("- labels:", "- members:"))]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(kept))
    world = World(tmp, "not-allowed", draft=path)
    refusal(4, "", world, world.common("preview"), "board %s is not on the sandbox allowlist" % SUPPORT)
    log.check("no preview was saved, so there is no fingerprint to confirm", not world.saved_previews())
    log.out("")
    log.out("Second, a board that is taken off the allowlist after a preview was made. It is refused at the confirmation.")
    allow = os.path.join(tmp, "allowlist-without-the-board.json")
    with open(allow, "w", encoding="utf-8") as f:
        json.dump({"sandbox_boards": [SANDBOX]}, f)
    world = World(tmp, "taken-off")
    code, text = log.command(*world.common("preview"))
    world.allowlist = allow
    refusal(4, "", world, world.common("confirm") + ["--fingerprint", fingerprint_in(text), "--confirmed-by", WHO],
            "board %s is not on the sandbox allowlist" % PLATFORM)
    log.append_live("live-confirmation-refused.txt", "A REAL REFUSAL, NOT PLANNED: the confirm command was first run with the placeholder word still where the fingerprint goes.")
    log.append_live("live-confirmation-missing.txt", "A SECOND REAL REFUSAL, NOT PLANNED: the confirm command was then run with an empty fingerprint.")
    log.append_live("live-confirmation.txt", "THE REAL APPROVED RUN, with the fingerprint typed by the participant.")
    return log.finish("confirmation.txt")


def rerun_log(tmp):
    log = Log("Running the approved workflow a second time: trello-create-card, attempt trello-attempt-006", tmp)
    world = World(tmp, "rerun")
    log.part("PART 1. The first run, for reference: a preview and its confirmation create one card.")
    code, text = log.command(*world.common("preview"))
    fingerprint = fingerprint_in(text)
    log.command(*world.common("confirm"), "--fingerprint", fingerprint, "--confirmed-by", WHO, "--result", world.result)
    cards = world.new_cards()
    log.check("one card exists that was not there before", len(cards) == 1)
    card = cards[0]["id"] if cards else "?"
    after_first = world.boards()

    log.part("PART 2. The same workflow again: the preview. (criterion 9)")
    code, text = log.command(*world.common("preview"))
    log.check("refused: exit code 1, and it names the card this draft became", code == 1 and "has already been created in Trello as card %s" % card in text)
    log.check("no request at all was sent to Trello", "Requests sent" not in text and posts_in(text) == 0)

    log.part("PART 3. The same confirmation again, with the same fingerprint. (criteria 7 and 9)")
    code, text = log.command(*world.common("confirm"), "--fingerprint", fingerprint, "--confirmed-by", WHO)
    log.check("refused: a fingerprint is used once", code == 1 and "A fingerprint is used once" in text)
    log.out("  Checked by this script, from the made-up Trello's own file:")
    log.check("the made-up Trello is exactly as the first run left it: still one new card, none repeated", world.boards() == after_first and len(world.new_cards()) == 1)

    log.part("PART 4. The local file is matched to the card by its id. (criterion 3)")
    code, text = log.command(*world.common("verify"))
    log.check("the card was found by its card id and every field reads back the same",
              code == 0 and "Matched to Trello by card id %s: found." % card in text and "Result: every field the payload sent reads back the same." in text)
    log.check("verify sent no write", posts_in(text) == 0 and world.boards() == after_first)

    log.part("PART 5. The limit, stated: without the link file, Trello itself would not stop a second card.")
    log.out("The same draft is previewed with a different link file, as on a machine that never had the first one.")
    world.link = os.path.join(world.folder, "another-machine.md")
    code, text = log.command(*world.common("preview"))
    log.check("the preview is NOT READY: Trello shows an open card with exactly this name, and names it",
              code == 3 and "with exactly this name (card %s)" % card in text and not fingerprint_in(text))
    log.check("still one new card", len(world.new_cards()) == 1)
    log.out("  What this does not stop: a second card under a different name, made from a different draft or by hand.")
    log.out("  Trello has no way to refuse a second create. A person would notice it on the board, and in the duplicate")
    log.out("  search of the next preview once the local index is rebuilt.")
    log.append_live("live-rerun.txt", "THE REAL SECOND RUN: the preview again.")
    log.append_live("live-rerun-confirm.txt", "THE REAL SECOND RUN: the same confirmation again, with the same fingerprint.")
    log.append_live("live-verify.txt", "THE REAL MATCH BY IDENTIFIER, some time after the create.")
    return log.finish("rerun.txt")


def recovery_log(tmp):
    log = Log("When the create is sent and its answer is lost: trello-create-card, attempt trello-attempt-006", tmp)
    log.out("This cannot be made to happen on real Trello on purpose, so it is recorded against the made-up Trello only.")
    world = World(tmp, "lost")
    log.part("PART 1. The card is created and the answer never arrives.")
    code, text = log.command(*world.common("preview"))
    fingerprint = fingerprint_in(text)
    world.knobs(lose_answer=True)
    log.out("The made-up Trello is told to create the card and then drop the connection.")
    code, text = log.command(*world.common("confirm"), "--fingerprint", fingerprint, "--confirmed-by", WHO)
    world.knobs()
    log.check("the workflow does not call it a failure or a success: exit code 2, NOT KNOWN", code == 2 and "It is NOT KNOWN whether Trello created the card" in text)
    log.check("it sent the create once and did not send it again", posts_in(text) == 1 and len(world.new_cards()) == 1)
    with open(world.link, encoding="utf-8") as f:
        link = f.read()
    log.check("the link file, written before sending, says a create was sent and its result is not recorded", 'state: "create sent, result not recorded"' in link)

    log.part("PART 2. Nothing will create it again.")
    code, text = log.command(*world.common("preview"))
    log.check("a new preview is refused and says to reconcile", code == 1 and "Run the reconcile command before anything else" in text)
    code, text = log.command(*world.common("confirm"), "--fingerprint", fingerprint, "--confirmed-by", WHO)
    log.check("the old fingerprint is refused", code == 1 and posts_in(text) == 0)
    log.check("still exactly one new card", len(world.new_cards()) == 1)

    log.part("PART 3. Reconcile finds the card, links it and compares it. It writes nothing to Trello.")
    before = world.boards()
    code, text = log.command(*world.common("reconcile"), "--result", world.result)
    card = world.new_cards()[0]["id"]
    log.check("it found exactly one card that was not on the board before and holds what was sent", code == 0 and "FOUND exactly one: card %s" % card in text)
    log.check("the card reads back the same as the payload", "Result: every field the payload sent reads back the same." in text)
    log.check("reconcile sent no write and changed nothing in Trello", posts_in(text) == 0 and world.boards() == before)
    with open(world.link, encoding="utf-8") as f:
        log.check("the link file now holds the card id", 'card_id: "%s"' % card in f.read())

    log.part("PART 4. The other case: the create never reached Trello.")
    world = World(tmp, "dropped")
    code, text = log.command(*world.common("preview"))
    fingerprint = fingerprint_in(text)
    world.knobs(drop_request=True)
    log.out("The made-up Trello is told to drop the connection before it sees the create.")
    code, text = log.command(*world.common("confirm"), "--fingerprint", fingerprint, "--confirmed-by", WHO)
    world.knobs()
    log.check("the workflow cannot tell this from part 1, and says the same: exit code 2, NOT KNOWN", code == 2 and "It is NOT KNOWN" in text)
    code, text = log.command(*world.common("reconcile"))
    log.check("reconcile says NOT FOUND, creates nothing and leaves the link file for a person", code == 1 and "NOT FOUND." in text and not world.new_cards())

    log.part("PART 5. Trello refuses the create outright.")
    world = World(tmp, "refused")
    code, text = log.command(*world.common("preview"))
    world.knobs(post_status=400)
    code, text = log.command(*world.common("confirm"), "--fingerprint", fingerprint_in(text), "--confirmed-by", WHO)
    world.knobs()
    log.check("it looked at the board before believing the refusal, found no new card, and removed the link file",
              code == 1 and "made no card" in text and "The board holds no card that was not there before" in text and not os.path.exists(world.link))
    return log.finish("recovery.txt")


def main():
    os.chdir(ROOT)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = os.path.realpath(tmp)
        results = [preview_log(tmp), confirmation_log(tmp), rerun_log(tmp), recovery_log(tmp)]
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
