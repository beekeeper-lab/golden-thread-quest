#!/usr/bin/env python3
"""Records logs/preview-run.txt and logs/invalid-target-run.txt for the trello-create-card-preview quest.

Each block between dashed lines is what a command printed. Commands are
started as a person would start them, against the made-up Trello in
participant/skills/trello-create-card-preview/fake_trello.py. No network is
used and nothing here contacts Trello.

A fake Trello started by a command is gone when the command ends, so two
parts cannot be shown that way: a token that may not write, and a check of
the fake's whole content before and after a preview. For those this script
holds one fake Trello itself and runs the preview against it, and the log
says so.

The state folder, where a READY preview is saved for a later write, is a
temporary folder, shown in the log as STATE.

This script checks for itself. It parses the payload out of what the preview
printed, makes the bytes and their SHA-256 with its own code, and compares
them with the SHA-256 the preview printed, the payload the preview saved and
the payload in payload.md.

If logs/live-preview-run.txt exists (the participant's own read-only run on
their real sandbox board), it is copied unchanged to the end of preview-run.txt.

Run from anywhere:  python3 scripts/record_evidence.py
Exit code 0 if every check came out as expected, 1 if not.
"""
import contextlib
import copy
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ATTEMPT = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(ATTEMPT, "..", "..", "..", ".."))
SKILL = "participant/skills/trello-create-card-preview"
PREVIEW = SKILL + "/preview.py"
INDEX = "participant/skills/trello-build-index/index.py"
BASE = "participant/context/trello/new-card"
BOARDS = BASE + "/fixture/boards"
NOW = "2026-11-20T09:00:00Z"
PLATFORM, SUPPORT, TO_DO = "80b000000000000000000001", "80b000000000000000000002", "81a000000000000000000011"
DUP = "82c000000000000000000201"


class Log:
    def __init__(self, title):
        self.lines, self.problems, self.state = [title], [], None

    def out(self, text=""):
        self.lines.append(text)

    def part(self, text):
        self.lines += ["", "=" * 78, text]

    def check(self, label, ok):
        self.lines.append("  %-4s %s" % ("ok" if ok else "FAIL", label))
        if not ok:
            self.problems.append(label)

    def tidy(self, text):
        return text.replace(self.state, "STATE") if self.state else text

    def block(self, text, code):
        self.lines += ["-" * 78, self.tidy(text.rstrip("\n")), "-" * 78, "exit code: %d" % code]

    def command(self, script, *args):
        self.out("$ python3 %s %s" % (script, self.tidy(" ".join(args))))
        done = subprocess.run([sys.executable, script] + list(args), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        self.block(done.stdout, done.returncode)
        return done.returncode, self.tidy(done.stdout)

    def preview(self, draft, *extra):
        return self.command(PREVIEW, "--source", "fake", "--draft", draft, "--allowlist", BASE + "/sandbox-allowlist.json",
                            "--boards", BOARDS, "--state", self.state, "--now", NOW, *extra)

    def finish(self, name):
        count = sum(1 for line in self.lines if re.match(r"  (ok  |FAIL) ", line))
        self.lines += ["", "RESULT: %s" % ("ALL CHECKS PASSED. %d checks." % count if not self.problems
                                           else "%d OF %d CHECKS FAILED." % (len(self.problems), count))]
        os.makedirs(os.path.join(ATTEMPT, "logs"), exist_ok=True)
        with open(os.path.join(ATTEMPT, "logs", name), "w", encoding="utf-8") as f:
            f.write("\n".join(self.lines) + "\n")
        print("%s  %s" % (name, self.lines[-1]))
        for problem in self.problems:
            print("  FAILED: " + problem)
        return not self.problems


def hashes(folder):
    found = {}
    for base, _, names in os.walk(folder):
        for name in names:
            with open(os.path.join(base, name), "rb") as f:
                found[os.path.relpath(os.path.join(base, name), folder)] = hashlib.sha256(f.read()).hexdigest()
    return found


def printed_payload(text):
    block = text.split("THE EXACT PAYLOAD. This is the request body, not a summary of it:\n", 1)[1].split("\nAs sent it is", 1)[0]
    return json.loads(block)


def own_sha(payload):
    """The bytes a write would send and their SHA-256, made here and not by the preview."""
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return len(body), hashlib.sha256(body).hexdigest()


def saved_previews(state):
    folder = os.path.join(state, "card-previews")
    found = []
    for name in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
        with open(os.path.join(folder, name), encoding="utf-8") as f:
            found.append(json.load(f))
    return found


def in_process(log, trello, draft, state, label):
    """Runs the preview inside this script against a fake Trello this script holds."""
    sys.path.insert(0, os.path.join(ROOT, SKILL))
    import fake_trello
    import preview
    original = fake_trello.FakeTrello
    fake_trello.FakeTrello = lambda: trello
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            code = preview.main(["--source", "fake", "--draft", draft, "--allowlist", BASE + "/sandbox-allowlist.json", "--boards", BOARDS,
                                 "--state", state, "--now", NOW])
    finally:
        fake_trello.FakeTrello = original
    log.out("Run inside this script, against a fake Trello this script holds, %s:" % label)
    log.out("  preview.py --source fake --draft %s (the same options as above)" % draft)
    log.block(out.getvalue(), code)
    return code, log.tidy(out.getvalue())


def preview_run(tmp):
    log = Log("The preview of a new card: trello-create-card-preview, attempt trello-attempt-005")
    log.out("Recorded by scripts/record_evidence.py. A made-up Trello in memory and local files only. No Trello was contacted.")
    log.state = os.path.join(tmp, "state")

    log.part("PART 1. The local indexes the duplicate search reads match their records.")
    before_indexes = hashes(BOARDS)
    for name in sorted(os.listdir(BOARDS)):
        code, _ = log.command(INDEX, "check", "--records", "%s/%s" % (BOARDS, name), "--out", "%s/%s" % (BOARDS, name))
        log.check("the index of %s is exactly what a build from its records would write" % name, code == 0)

    log.part("PART 2. The preview of the draft, %s/draft.md. (criteria 1, 2, 4, 5, 6, 7)" % BASE)
    code, text = log.preview(BASE + "/draft.md", "--payload-out", BASE + "/payload.md")
    log.check("the preview was made and is READY: exit code 0", code == 0 and "VERDICT: READY TO WRITE." in text)
    log.check("criterion 1: the list is named by its id, and Trello says it belongs to the stated board",
              "(list id %s). Chosen by id. Trello says it belongs to board %s, the stated board: yes. Archived: no." % (TO_DO, PLATFORM) in text)
    log.check("the board's first list by position is the archived one, and it is not the list used",
              'by position: "Old ideas" (ARCHIVED), "To do"' in text)
    log.check("criterion 2: the label and the member were each found on the board",
              "each found on the board before being put in the payload: 1 label, 1 member." in text)
    payload = printed_payload(text)
    log.check("criterion 5: the payload shown holds the list and the position: idList %s, pos %s" % (payload.get("idList"), json.dumps(payload.get("pos"))),
              payload.get("idList") == TO_DO and payload.get("pos") == "bottom")
    log.check("where in the list is shown: number 4 of 4 open cards, after card ...103", "number 4 of 4 open cards" in text and "after:  card 82c000000000000000000103" in text)
    log.check("criterion 4: the permission check is in the preview, with Trello's answers",
              "PERMISSION CHECK, asked of Trello" in text and "That role may add cards: yes" in text and "read yes, write yes" in text)
    log.check("criterion 4: the duplicate result is in the preview: NONE, recommendation PROCEED",
              "DUPLICATE SEARCH:" in text and "Result: NONE." in text and "overall recommendation: PROCEED" in text)
    log.check("criterion 7: six citations are shown, each with its file and line", len(re.findall(r"^  \w+ +sources/notes\.md lines? [\d-]+: \"", text, re.M)) == 6)
    snaps = re.findall(r"Snapshot of the board in Trello (?:before|after) the preview: +(.+)", text)
    log.check("criterion 6: the board snapshot is the same before and after: %s" % (snaps[0] if snaps else "?"), len(snaps) == 2 and snaps[0] == snaps[1])
    sent = re.findall(r"^  (\w+) /", text, re.M)
    log.check("criterion 6: all %d requests were GET" % len(sent), bool(sent) and set(sent) == {"GET"})
    log.check("the request that holds the token is listed without it", "GET /tokens/[the token]" in text and "faketoken" not in text)

    log.part("PART 3. Is the payload shown the payload a write would send? Checked by this script, with its own code. (criterion 5)")
    size, digest = own_sha(payload)
    log.out("  The payload parsed out of the text above, turned into bytes here: %d bytes, SHA-256 %s" % (size, digest))
    log.check("that is the size and SHA-256 the preview printed", "%d bytes, SHA-256 %s" % (size, digest) in text)
    saved = saved_previews(log.state)
    log.check("one preview was saved in STATE for a later write", len(saved) == 1)
    log.check("the payload saved there is the payload shown, and its saved SHA-256 is the same",
              len(saved) == 1 and saved[0]["payload"] == payload and saved[0]["payload_sha256"] == digest and saved[0]["payload_bytes"] == size)
    log.check("the saved preview names the request, the board and the list",
              len(saved) == 1 and (saved[0]["request"], saved[0]["board"], saved[0]["list"]) == ("POST https://api.trello.com/1/cards", PLATFORM, TO_DO))
    with open(BASE + "/payload.md", encoding="utf-8") as f:
        payload_md = f.read()
    in_file = json.loads(payload_md.split("```json\n", 1)[1].split("\n```", 1)[0])
    log.check("the payload in %s/payload.md is the same payload, with the same SHA-256" % BASE, in_file == payload and digest in payload_md)
    log.check("payload.md lists the fields one by one, with idList and pos", "| `idList` | %s |" % TO_DO in payload_md and '| `pos` | "bottom" |' in payload_md)
    with open(BASE + "/draft.md", encoding="utf-8") as f:
        draft = f.read()
    log.check("every value in the payload is in the draft, or is the board's id for a label the draft names",
              all(json.dumps(payload[key]) in draft for key in ("idList", "pos", "name", "due", "idMembers"))
              and payload["desc"] in draft and '"feature" (label id %s)' % payload["idLabels"] in text)

    log.part("PART 4. A draft that duplicates a card on another board. Valid, and NOT READY until a person decides. (criterion 4)")
    code, text = log.preview(BASE + "/not-ready/duplicate.md")
    log.check("a preview was made and is NOT READY: exit code 3", code == 3 and "VERDICT: NOT READY TO WRITE. 1 reason:" in text)
    log.check("the candidate is shown with its board, confidence and recommendation",
              "card %s, open, on ANOTHER board: confidence MEDIUM, 9 of 13 points" % DUP in text and "Recommendation: LINK." in text)
    log.check("the payload is still shown, so a person can see the card they are deciding about", "THE EXACT PAYLOAD" in text and printed_payload(text)["pos"] == "top")
    log.check("nothing more was saved for a later write", len(saved_previews(log.state)) == 1)
    code, text = log.preview(BASE + "/decided/duplicate.md")
    log.check("the same draft with a decision recorded about that card is READY: exit code 0",
              code == 0 and "The draft records a person's decision: LINK, made about card %s." % DUP in text and "VERDICT: READY TO WRITE." in text)

    log.part("PART 5. A token that may read and may not write. Valid, and NOT READY. (criterion 4)")
    sys.path.insert(0, os.path.join(ROOT, SKILL))
    import fake_trello
    trello = fake_trello.FakeTrello()
    trello.token["permissions"][0]["write"] = False
    code, text = in_process(log, trello, BASE + "/draft.md", log.state, "whose token has read and not write")
    log.check("a preview was made and is NOT READY: exit code 3", code == 3 and "VERDICT: NOT READY TO WRITE." in text)
    log.check("the permission check says so: read yes, write NO", "read yes, write NO" in text)
    log.check("the reason is given", "may read boards and may not write to them" in text)
    log.check("the payload is the same one as in part 2", own_sha(printed_payload(text))[1] == digest)

    log.part("PART 6. The board is unchanged. Checked by this script on a fake Trello it holds. (criterion 6)")
    trello = fake_trello.FakeTrello()
    before = copy.deepcopy((trello.boards, trello.token, trello.me))
    code, text = in_process(log, trello, BASE + "/draft.md", os.path.join(tmp, "state-2"), "unchanged from the fixture")
    cards = sum(len(board["cards"]) for board in trello.boards.values())
    lists = sum(len(board["lists"]) for board in trello.boards.values())
    log.out("  The fake Trello holds %d boards, %d lists and %d cards. This script copied all of it before the preview." % (len(trello.boards), lists, cards))
    log.check("the preview ran and is READY", code == 0)
    log.check("the fake received %d requests, and every one was a GET" % len(trello.requests),
              bool(trello.requests) and {method for method, _, _ in trello.requests} == {"GET"})
    log.check("every board, list, card, label, membership and the token record are exactly as they were before the preview",
              (trello.boards, trello.token, trello.me) == before)
    log.check("the local indexes and records are unchanged too: all %d files have the SHA-256 they had in part 1" % len(before_indexes),
              hashes(BOARDS) == before_indexes)
    log.check("the fake Trello has no function but get", [name for name in dir(trello) if not name.startswith("_") and callable(getattr(trello, name))] == ["get"])

    live = os.path.join(ATTEMPT, "logs", "live-preview-run.txt")
    if os.path.exists(live):
        log.part("THE SAME ON THE REAL SANDBOX BOARD. The participant's own read-only run, copied unchanged from logs/live-preview-run.txt.")
        with open(live, encoding="utf-8") as f:
            log.lines += f.read().rstrip("\n").split("\n")
    return log.finish("preview-run.txt")


def invalid_target_run(tmp):
    log = Log("Previews that are refused: trello-create-card-preview, attempt trello-attempt-005")
    log.out("Recorded by scripts/record_evidence.py. A made-up Trello in memory and local files only. No Trello was contacted.")
    log.out("Each draft below is %s/draft.md with one line changed, made by scripts/make_fixture.py. The draft as it is" % BASE)
    log.out("previews as READY: that run is part 2 of logs/preview-run.txt.")
    log.state = os.path.join(tmp, "state-refused")
    out_file = os.path.join(log.state, "payload-refused.md")
    cases = [
        ("list-on-another-board.md", "The list exists, on another board. (criteria 1 and 3)",
         ["is not on the stated board", "Trello says the list belongs to board %s" % SUPPORT]),
        ("missing-list.md", "No list has this id. (criterion 3)", ["the list 81a000000000000000000099 does not exist (Trello answered 404)"]),
        ("archived-list.md", "The list is the archived one, the first on the board by position: the quest's scenario. (criterion 1)",
         ['"Old ideas", is archived', "would not be seen on the board"]),
        ("unknown-label.md", "A label the board does not have. (criteria 2 and 3)",
         ['the label "urgent" does not exist on board %s' % PLATFORM, '"bug", "docs", "export", "feature"']),
        ("member-not-on-board.md", "A member who is not on the board. (criterion 2)", ["is not a member of board %s" % PLATFORM]),
    ]
    for number, (name, title, expect) in enumerate(cases, 1):
        log.part("PART %d. %s" % (number, title))
        with open(os.path.join(BASE, "refused", name), encoding="utf-8") as f:
            log.out("  %s" % next(line for line in f.read().split("\n") if line.startswith("> Made from draft.md"))[2:])
        code, text = log.preview("%s/refused/%s" % (BASE, name), "--payload-out", out_file)
        log.check("the preview was refused: exit code 1", code == 1 and text.startswith("REFUSED: "))
        for piece in expect:
            log.check("the reason says: %s" % piece, piece in text)
        log.check("the reason names what does exist, so the draft can be put right",
                  "open lists are" in text or "named labels are" in text or "which has 3" in text)
        log.check("no payload was shown, none was saved for a write, and no payload file was written",
                  "idList" not in text and "PAYLOAD" not in text and not saved_previews(log.state) and not os.path.exists(out_file))
    return log.finish("invalid-target-run.txt")


def main():
    os.chdir(ROOT)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = os.path.realpath(tmp)
        first = preview_run(tmp)
        second = invalid_target_run(tmp)
    return 0 if first and second else 1


if __name__ == "__main__":
    sys.exit(main())
