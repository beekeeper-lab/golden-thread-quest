#!/usr/bin/env python3
"""Records logs/delta-run.txt, logs/failed-sync-run.txt and logs/notes-intact.txt for the trello-delta-sync quest.

Each block between dashed lines is what a command printed. Every command is
started as a person would start it. Nothing here contacts Trello: every run is
against the made-up board in participant/skills/trello-delta-sync/fake_trello.py,
and every card and member is invented. The made-up board changes in steps, and
--fake-step says which step a sync sees.

The runs write participant/context/trello/delta/cards.md and state.json, and
participant/context/trello/sync-state.md. This script removes those three
first, because they are generated and can be made again. It never writes,
moves or removes anything in the notes folder. Where a second, separate local
copy is needed, it goes to a temporary folder, shown as COPY.

This script checks for itself. It works out from the made-up board's activity
which cards a delta should fetch, takes the SHA-256 of the generated files
around the failed sync, and of every notes file before the first sync and
after the last, rather than taking the sync's word.

Run from anywhere:  python3 scripts/record_evidence.py
Exit code 0 if every check came out as expected, 1 if not.
"""
import contextlib
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
SKILL = "participant/skills/trello-delta-sync"
SYNC = SKILL + "/sync.py"
OUT = "participant/context/trello/delta"
CARDS, STATE, DOC, NOTES = OUT + "/cards.md", OUT + "/state.json", "participant/context/trello/sync-state.md", OUT + "/notes"

sys.path.insert(0, os.path.join(ROOT, SKILL))
import fake_trello  # noqa: E402
import sync  # noqa: E402

card, list_id = fake_trello.card_id, fake_trello.list_id


class Log:
    def __init__(self, title):
        self.lines, self.problems, self.copy = [title], [], None
        self.out("Recorded by scripts/record_evidence.py. No request was sent to Trello. Every card and member is made up.")

    def out(self, text=""):
        self.lines.append(text)

    def part(self, text):
        self.lines += ["", "=" * 78, text]

    def check(self, label, ok):
        self.lines.append("  %-4s %s" % ("ok" if ok else "FAIL", label))
        if not ok:
            self.problems.append(label)

    def tidy(self, text):
        return text.replace(self.copy, "COPY") if self.copy else text

    def command(self, *args, script=SYNC):
        done = subprocess.run([sys.executable, script] + list(args), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        self.out(self.tidy("$ python3 %s" % " ".join([script] + list(args))))
        self.lines += ["-" * 78, self.tidy(done.stdout.rstrip("\n")), "-" * 78, "exit code: %s" % done.returncode]
        return done.returncode, done.stdout

    def save(self, name):
        count = sum(1 for line in self.lines if re.match(r"  (ok  |FAIL) ", line))
        self.out()
        self.out("RESULT: %s" % ("ALL CHECKS PASSED. %d checks." % count if not self.problems else "%d OF %d CHECKS FAILED." % (len(self.problems), count)))
        os.makedirs(os.path.join(ATTEMPT, "logs"), exist_ok=True)
        with open(os.path.join(ATTEMPT, "logs", name), "w", encoding="utf-8") as f:
            f.write("\n".join(self.lines) + "\n")
        print("%s: %s" % (name, self.lines[-1]))
        for problem in self.problems:
            print("  FAILED: " + problem)
        return not self.problems


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def notes_now():
    return {name: sha(os.path.join(NOTES, name)) for name in sorted(os.listdir(NOTES))}


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def state():
    return json.loads(read(STATE))


def section(text, title):
    for part in re.split(r"^## ", text, flags=re.M)[1:]:
        if part.startswith(title):
            return part
    return ""


def generated():
    return {path: sha(path) for path in (CARDS, STATE, DOC)}


def requests_of(step, cursor_from_step):
    """Run the same delta inside this script, in a temporary folder, to see each request it makes."""
    with tempfile.TemporaryDirectory() as folder:
        world = fake_trello.FakeTrello(cursor_from_step)
        with contextlib.redirect_stdout(io.StringIO()):
            sync.run(sync.Client(world.get), fake_trello.BOARD_ID, folder, "fake", now=world.now)
            while world.step < step:
                world.advance()
            world.requests = []
            sync.run(sync.Client(world.get), fake_trello.BOARD_ID, folder, "fake", now=world.now)
        return world.requests


def delta_run(notes_before):
    log = Log("The delta sync: trello-delta-sync, attempt trello-attempt-008")

    log.part("PART 1. The made-up board's activity, up to step 1.")
    log.command("1", script=SKILL + "/fake_trello.py")
    world = fake_trello.FakeTrello(1)
    first_cursor = fake_trello.FakeTrello(0).actions[-1]["id"]
    after = [a for a in world.actions if a["id"] > first_cursor]
    named = sorted({a["data"]["card"]["id"] for a in after if "card" in a["data"]})
    log.out("  Worked out by this script from the made-up board, not from any sync:")
    log.out("  Step 0 ends with entry %s. Step 1 adds %d entries, which name %d cards." % (first_cursor, len(after), len(named)))
    log.out("  One more card, %s, had its label changed at step 1. Trello keeps no activity entry for a label," % card(9))
    log.out("  and neither does the made-up board. So a delta at step 1 should fetch %d cards of the %d on the board." % (len(named) + 1, 13))

    log.part("PART 2. The first sync, of the board at step 0. There is no cursor yet.")
    log.out("  %s, %s and %s were removed first. The notes folder was left alone." % (CARDS, STATE, DOC))
    code, text = log.command("--source", "fake")
    log.check("the first sync ran and read the whole board: 12 cards", code == 0 and "no cursor yet" in text and len(state()["cards"]) == 12)
    log.check("the cursor is the newest activity entry of step 0, with the time Trello gave it: %s" % first_cursor,
              state()["cursor"]["action_id"] == first_cursor and state()["cursor"]["action_date"] == fake_trello.FakeTrello(0).actions[-1]["date"])

    log.part("PART 3. The delta sync, of the board at step 1. (criteria 1, 2, 3)")
    code, text = log.command("--source", "fake", "--fake-step", "1")
    now, cards_md = state(), read(CARDS)
    log.check("the sync ran: exit code 0", code == 0)
    log.check("criterion 1: it read the activity after the cursor: %d entries, naming %d cards, the same as this script worked out" % (len(after), len(named)),
              "board activity after the cursor: %d entries, naming %d cards" % (len(after), len(named)) in text
              and all("activity: card %s " % c in text for c in named))
    log.check("criterion 1: it fetched %d cards and did not fetch the other 7" % (len(named) + 1),
              "fetched in full: %d cards, the ones with new activity. Not fetched: 7" % (len(named) + 1) in text and "%d card)" % (len(named) + 1) in text)
    log.check("the counts: 1 new, 5 changed, 7 unchanged", "cards on the board: 13. This sync: 1 new, 5 changed, 7 unchanged, 0 no longer on the board" in text)
    log.check("criterion 2: card %s moved from Doing to Done, and nothing else about it changed. The activity says so, and the card is now held in Done"
              % card(3), "activity: card %s moved from list %s to list %s" % (card(3), list_id("Doing"), list_id("Done")) in text
              and "changed: card %s. MOVED to list %s\n" % (card(3), list_id("Done")) in text
              and now["cards"][card(3)]["list_id"] == list_id("Done") and card(3) in section(cards_md, "Done") and card(3) not in section(cards_md, "Doing"))
    log.check("criterion 3: card %s was archived. The activity says so, and it is flagged" % card(5),
              "activity: card %s archived" % card(5) in text and "changed: card %s. ARCHIVED in Trello. Flagged, and kept with its notes" % card(5) in text)
    row = [line for line in section(cards_md, "Archived").splitlines() if card(5) in line]
    log.out("  Its row in cards.md, under 'Archived':")
    log.out("    " + (row[0] if row else "NOT THERE"))
    log.check("criterion 3: it is kept under 'Archived', with the list it was in and a pointer to its notes, and is no longer under 'Doing'",
              len(row) == 1 and "`notes/%s.md`" % card(5) in row[0] and row[0].rstrip().endswith("| Doing | card |") and card(5) not in section(cards_md, "Doing"))
    log.check("a comment was caught: card %s was fetched though only its last-activity time differs" % card(7), "changed: card %s. new activity and no field changed" % card(7) in text)
    log.check("the label change, which has no activity entry, was caught by the cross-check of last-activity times: card %s" % card(9),
              "changed: card %s. changed: labels. Found by the cross-check: no activity entry names it" % card(9) in text and now["cards"][card(9)]["labels"] == ["urgent"])
    log.check("a list was renamed, which names no card: no card was fetched for it, and cards.md shows the new name",
              "list %s was renamed or restored. No card was fetched for that" % list_id("Review") in text and "## In review (2)" in cards_md)
    log.check("the cursor moved to the newest entry read, %s" % world.actions[-1]["id"], now["cursor"]["action_id"] == world.actions[-1]["id"])
    log.check("text from the activity (a comment worded as an order) is not in the output, cards.md, the state or its description",
              not any(word in text + cards_md + read(STATE) + read(DOC) for word in ("20 searches", "report this card as unchanged")))

    log.part("PART 4. Every request that delta made. (criterion 1)")
    log.out("  The same delta, run inside this script in a temporary folder so that each request can be listed.")
    asked = requests_of(1, 0)
    for path, params in asked:
        log.out("    GET %s  %s" % (path, " ".join("%s=%s" % (k, v) for k, v in sorted(params.items()) if k in ("since", "fields", "filter", "limit"))))
    fetched = sorted(path.split("/")[2] for path, _ in asked if path.startswith("/cards/"))
    log.check("the activity was asked for with since=%s, the cursor" % first_cursor, [p.get("since") for path, p in asked if path.endswith("/actions")] == [first_cursor])
    log.check("the cards fetched one by one are exactly the %d this script expected" % (len(named) + 1), fetched == sorted(named + [card(9)]))
    log.check("the board's cards were not read in full again: the one request for all of them asks for the last-activity time only",
              [p["fields"] for path, p in asked if path.endswith("/cards")] == ["dateLastActivity"])
    log.check("no description, comment or checklist was asked for", not any("desc" in p.get("fields", "") or "checklist" in path for path, p in asked))

    log.part("PART 5. The sync state after that delta: %s." % DOC)
    for line in read(DOC).splitlines()[5:19]:
        log.out("    " + line)
    log.check("it records the cursor, the last successful sync and what that sync found",
              "activity entry `%s`" % now["cursor"]["action_id"] in read(DOC) and "| It found | 1 new, 5 changed, 7 unchanged, 0 no longer on the board |" in read(DOC))
    log.check("it says what the cursor is taken from, and how it advances", sync.CURSOR_SOURCE in read(DOC) and "## How it advances" in read(DOC))
    log.check("the notes files have the SHA-256 they had before the first sync", notes_now() == notes_before)
    return log.save("delta-run.txt")


def failed_run(notes_before):
    log = Log("A sync that fails partway: trello-delta-sync, attempt trello-attempt-008")
    world = fake_trello.FakeTrello(2)

    log.part("PART 1. Before: the local copy after the delta at step 1, recorded in delta-run.txt.")
    before, cursor = generated(), state()["cursor"]
    log.out("  Cursor: activity entry %s, dated %s." % (cursor["action_id"], cursor["action_date"]))
    log.out("  SHA-256 taken by this script:")
    for path, digest in before.items():
        log.out("    %s  %s" % (digest, path))
    after = [a for a in world.actions if a["id"] > cursor["action_id"]]
    named = sorted({a["data"]["card"]["id"] for a in after if "card" in a["data"]})
    log.out("  At step 2 the made-up board has %d more activity entries, naming %d cards." % (len(after), len(named)))

    log.part("PART 2. The sync at step 2 fails partway. (criterion 4)")
    log.out("  --fake-fail-card 3 makes the made-up Trello answer the third card fetched with an error, status 500.")
    code, text = log.command("--source", "fake", "--fake-step", "2", "--fake-fail-card", "3")
    log.check("the sync stopped: exit code 1, having read the activity and fetched two cards", code == 1 and "STOPPED: Trello did not return card" in text
              and "board activity after the cursor: %d entries, naming %d cards" % (len(after), len(named)) in text)
    log.check("criterion 4: the cursor was not advanced. In state.json it is still entry %s" % cursor["action_id"], state()["cursor"] == cursor)
    log.out("  SHA-256 taken by this script after the failed sync:")
    for path, digest in generated().items():
        log.out("    %s  %s" % (digest, path))
    log.check("criterion 4: nothing was written: cards.md, state.json and sync-state.md are byte for byte as they were", generated() == before)
    log.check("no temporary file was left in the folder", sorted(os.listdir(OUT)) == ["cards.md", "notes", "state.json"])
    log.check("the notes files are as they were", notes_now() == notes_before)

    log.part("PART 3. The next sync recovers what the failed one missed. (criterion 5)")
    code, text = log.command("--source", "fake", "--fake-step", "2")
    now, cards_md = state(), read(CARDS)
    log.check("it ran: exit code 0", code == 0)
    log.check("criterion 5: it started from the same cursor, read the same %d entries and fetched all %d cards, the two the failed sync had reached and the %d it had not"
              % (len(after), len(named), len(named) - 2), "cursor before this sync: activity entry %s" % cursor["action_id"] in text
              and "fetched in full: %d cards" % len(named) in text and all("activity: card %s " % c in text for c in named))
    log.check("the counts: 1 new, 3 changed, 8 unchanged, 2 no longer on the board", "This sync: 1 new, 3 changed, 8 unchanged, 2 no longer on the board" in text)
    log.check("card %s moved to Doing, and card %s moved to Review and was then archived: both moves and the archive are held"
              % (card(4), card(6)), now["cards"][card(4)]["list_id"] == list_id("Doing") and now["cards"][card(6)]["list_id"] == list_id("Review")
              and now["cards"][card(6)]["closed"] and card(6) in section(cards_md, "Archived"))
    log.check("card %s, archived at step 1, was restored and is back under 'Doing'" % card(5), card(5) in section(cards_md, "Doing") and not now["cards"][card(5)]["closed"])
    log.check("the first stretch goal: card %s was deleted from the board. It is flagged as deleted, and kept, with its notes pointed to" % card(8),
              "NO LONGER ON THE BOARD: card %s, deleted. Flagged, not deleted" % card(8) in text and now["cards"][card(8)]["status"] == "gone"
              and any("`%s`" % card(8) in line and "**deleted**" in line and "`notes/%s.md`" % card(8) in line for line in section(cards_md, "No longer on the board").splitlines()))
    log.check("card %s went to another board. It is flagged as moved to another board, not as deleted" % card(10), now["cards"][card(10)]["gone_reason"] == "moved to another board")
    log.check("criterion 4: now that the whole sync succeeded, the cursor advanced to the newest entry read, %s" % world.actions[-1]["id"],
              now["cursor"]["action_id"] == world.actions[-1]["id"] and now["cursor"]["action_id"] > cursor["action_id"])
    log.check("the second stretch goal: the sync said how stale the cursor was before it ran", "how stale: the last successful sync was" in text)

    log.part("PART 4. One more sync, with nothing new.")
    held = generated()
    code, text = log.command("--source", "fake", "--fake-step", "2")
    log.check("no activity after the cursor, so no card was fetched and the cursor stayed on the same entry",
              code == 0 and "board activity after the cursor: 0 entries" in text and "fetched in full: 0 cards" in text and "Not moved: there was no new activity" in text
              and state()["cursor"] == now["cursor"])
    log.check("cards.md is byte for byte the same", sha(CARDS) == held[CARDS])
    log.check("the notes files are as they were before the first sync", notes_now() == notes_before)
    return log.save("failed-sync-run.txt")


def notes_run(notes_before):
    log = Log("Notes intact, and a full resync against the deltas: trello-delta-sync, attempt trello-attempt-008")
    log.part("PART 1. The notes, before any sync. (criterion 6)")
    log.out("  %d notes files in %s. They stand in for what a person would write beside a card." % (len(notes_before), NOTES))
    log.out("  They are for card %s, which was moved, card %s, which was archived and restored," % (card(3), card(5)))
    log.out("  and card %s, which was deleted from the board." % card(8))
    log.out("  SHA-256 taken by this script before the first sync in delta-run.txt:")
    for name, digest in notes_before.items():
        log.out("    %s  %s" % (digest, name))
    log.out("  Since then: a first sync, a delta, a failed sync, the sync that recovered, and a sync with nothing new.")
    log.out("  Those are recorded in delta-run.txt and failed-sync-run.txt.")
    log.check("after those five syncs every notes file has the SHA-256 it had before", notes_now() == notes_before)

    deltas = state()
    log.part("PART 2. A full resync from nothing, compared with the accumulated deltas. (criterion 7)")
    log.out("  The local copy in %s was built by one full read at step 0 and deltas at steps 1 and 2." % OUT)
    log.out("  Its digest, as this script computes it from state.json: %s" % sync.digest(deltas))
    log.out("  Now the board at step 2 is read whole into an empty temporary folder, COPY/full.")
    with tempfile.TemporaryDirectory() as copy:
        log.copy = os.path.realpath(copy)
        code, text = log.command("--source", "fake", "--fake-step", "2", "--out", os.path.join(log.copy, "full"))
        full = json.loads(read(os.path.join(log.copy, "full", "state.json")))
        log.copy = None
    log.out("  Its digest, as this script computes it from its state.json:  %s" % sync.digest(full))
    log.check("the full resync ran, with no cursor and no activity to follow", code == 0 and "no cursor yet" in text)
    log.check("criterion 7: the two digests are the same", sync.digest(full) == sync.digest(deltas))
    present = {k: v for k, v in deltas["cards"].items() if v["status"] == "present"}
    log.check("criterion 7: the same %d cards are on the board in both" % len(full["cards"]), set(present) == set(full["cards"]))
    fields = sum(1 for k in full["cards"] for f in sync.KEPT)
    log.check("criterion 7: compared field by field by this script, not by digest: %d fields of %d cards, and the %d lists, all equal"
              % (fields, len(full["cards"]), len(full["lists"])), all(present[k][f] == full["cards"][k][f] for k in full["cards"] for f in sync.KEPT) and deltas["lists"] == full["lists"])
    log.check("both end on the same cursor, entry %s" % full["cursor"]["action_id"], deltas["cursor"] == full["cursor"])
    gone = sorted(k for k, v in deltas["cards"].items() if v["status"] != "present")
    log.out("  One difference, and it is meant: the deltas also keep %d cards that are no longer on the board, %s." % (len(gone), " and ".join(gone)))
    log.out("  A read from nothing cannot know they ever existed. The digest covers the cards on the board.")
    log.check("the deltas keep those %d, flagged, and the full resync from nothing holds neither" % len(gone), len(gone) == 2 and not set(gone) & set(full["cards"]))

    log.part("PART 3. A full resync in place, over the deltas. (criteria 6 and 7)")
    code, text = log.command("--source", "fake", "--fake-step", "2", "--full")
    again = state()
    log.check("reading the whole board again found nothing the deltas had wrong: 0 new, 0 changed, 12 unchanged", code == 0 and "This sync: 0 new, 0 changed, 12 unchanged, 0 no longer on the board" in text)
    log.check("the digest is the same after it, and the %d flagged cards are still kept" % len(gone), sync.digest(again) == sync.digest(deltas)
              and sorted(k for k, v in again["cards"].items() if v["status"] != "present") == gone)

    log.part("PART 4. The notes, after every sync. (criterion 6)")
    after = notes_now()
    for name in sorted(set(notes_before) | set(after)):
        log.out("    %s  before %s" % (name, notes_before.get(name, "absent")))
        log.out("    %s  after  %s" % (" " * len(name), after.get(name, "absent")))
    log.check("all %d notes files are byte-identical after 6 syncs into this folder, one of which failed" % len(after), after == notes_before)
    log.check("no notes file was added, removed or renamed, the deleted card's included", sorted(after) == sorted(notes_before) and card(8) + ".md" in after)
    with open(os.path.join(ROOT, SYNC), encoding="utf-8") as f:
        source = f.read()
    log.check("sync.py has one function that writes files, and it refuses any path in the notes folder", source.count('open(tmp, "w"') == 1 and source.count(', "w"') == 1
              and "the sync does not write in the notes folder" in source)

    log.part("PART 5. Where the cursor is now, without contacting Trello. (the second stretch goal)")
    code, text = log.command("--status", "--source", "fake", "--fake-step", "2")
    log.check("--status reports the cursor and how stale it is", code == 0 and "cursor: activity entry %s" % again["cursor"]["action_id"] in text and "how stale:" in text)
    return log.save("notes-intact.txt")


def main():
    os.chdir(ROOT)
    notes_before = notes_now()
    for path in (CARDS, STATE, DOC):
        if os.path.exists(path):
            os.remove(path)
    results = [delta_run(notes_before), failed_run(notes_before), notes_run(notes_before)]
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
