#!/usr/bin/env python3
"""Records logs/assigned-run.txt and logs/resync-run.txt for the trello-read-assigned-cards quest.

Each block between dashed lines is what a command printed. Every command is
started as a person would start it. Nothing here contacts Trello: every run is
against the made-up Trello in participant/skills/trello-read-assigned-cards/fake_trello.py,
and every board, card and member is invented.

The runs write participant/context/trello/assigned/index.md and assigned.json,
which this script removes first, because they are generated and can be made
again. It never writes, moves or removes anything in the notes folder there.
Two parts need a Trello larger or more awkward than the made-up one. They run
in this script's own process and write to a temporary folder, shown as COPY.

This script checks for itself. It counts the member's cards in the made-up
Trello and the rows of the index, and takes the SHA-256 of every notes file
before the first sync and after the last, rather than taking the sync's word.

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
SKILL = "participant/skills/trello-read-assigned-cards"
SYNC = SKILL + "/sync.py"
OUT = "participant/context/trello/assigned"
INDEX, MEMORY, NOTES = OUT + "/index.md", OUT + "/assigned.json", OUT + "/notes"

sys.path.insert(0, os.path.join(ROOT, SKILL))
import fake_trello  # noqa: E402
import sync  # noqa: E402


class Log:
    def __init__(self, title):
        self.lines, self.problems, self.copy = [title], [], None
        self.out("Recorded by scripts/record_evidence.py. No request was sent to Trello. Every board, card and member is made up.")

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

    def block(self, title, code, text):
        self.out(title)
        self.lines += ["-" * 78, self.tidy(text.rstrip("\n")), "-" * 78, "exit code: %s" % code]

    def command(self, *args, script=SYNC):
        done = subprocess.run([sys.executable, script] + list(args), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        self.block("$ python3 %s" % " ".join([script] + list(args)), done.returncode, done.stdout)
        return done.returncode, done.stdout

    def in_process(self, what, fake, out_dir, **options):
        """A sync started inside this script, for a made-up Trello that the command line cannot make."""
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            try:
                code = sync.run(sync.Client(fake.get, sleep=lambda s: None), out_dir, "fake", now=fake.now, **options)
            except sync.Stop as stop:
                print("assigned-sync: STOPPED: %s.\nassigned-sync: Nothing was written." % stop)
                code = 1
        self.block("(inside this script) %s" % what, code, printed.getvalue())
        return code, printed.getvalue()

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


def section(text, title):
    for part in re.split(r"^## ", text, flags=re.M)[1:]:
        if part.startswith(title):
            return part
    return ""


def rows(text, title):
    return [line for line in section(text, title).splitlines() if line.startswith("| ") and "`62c" in line]


def said(text, pattern):
    return re.search(pattern, text) is not None


def assigned_run(notes_before):
    log = Log("The sync of the member's cards: trello-read-assigned-cards, attempt trello-attempt-007")
    world = fake_trello.FakeTrello()
    mine = world.assigned()
    lists = {l["id"]: l for l in world.data["lists"]}
    boards = {b["id"]: b for b in world.data["boards"]}
    on_reachable = [b for b in world.data["boards"] if fake_trello.ME in b["members"]]

    log.part("PART 1. The made-up Trello, as this script counts it.")
    log.command(script=SKILL + "/fake_trello.py")
    log.out("  Counted by this script from the made-up Trello's data, not from any sync:")
    log.out("  %d boards, %d with the member on them. %d cards in all. %d assigned to the member."
            % (len(boards), len(on_reachable), len(world.data["cards"]), len(mine)))
    log.out("  The made-up Trello returns at most %d cards for one request. Trello's own limit is 1000." % world.page_limit)
    largest = max(sum(c["idBoard"] == b["id"] for c in world.data["cards"]) for b in on_reachable)
    log.check("one board holds more cards than one request returns: %d against a limit of %d" % (largest, world.page_limit), largest > world.page_limit)
    log.check("the member's cards alone are more than one request returns: %d" % len(mine), len(mine) > world.page_limit)

    log.part("PART 2. The first sync. (criteria 1, 2, 3, 4)")
    log.out("  %s and %s were removed first, so this starts from nothing. The notes folder was left alone." % (INDEX, MEMORY))
    code, text = log.command("--source", "fake")
    index, memory = read(INDEX), json.loads(read(MEMORY))
    log.check("the sync ran: exit code 0", code == 0)
    log.check('criterion 1: the member was read from the connection: the first request was "who am I?", and the member it names is the one the made-up connection belongs to',
              said(text, r"member read from the connection: member id %s\." % fake_trello.ME) and memory["member_id"] == fake_trello.ME)
    with open(os.path.join(ROOT, SYNC), encoding="utf-8") as f:
        source = f.read()
    log.check("criterion 1: no member id is written anywhere in sync.py", fake_trello.ME not in source and not re.search(r"[0-9a-f]{24}", source))
    searched = re.findall(r"^assigned-sync:   board (\w+), (open|closed): (\d+) cards read in (\d+) requests? \(([\d +]+)\), (\d+) assigned", text, re.M)
    log.check("criterion 2: the boards searched are listed, and they are every board the connection can reach: %d, one of them closed" % len(searched),
              {b[0] for b in searched} == {b["id"] for b in on_reachable} and sum(b[1] == "closed" for b in searched) == 1)
    log.check("criterion 2: the board the member is not on (Finance) was not searched, and none of its cards is held",
              fake_trello.board_id("Finance") not in text and not any(c["board_id"] == fake_trello.board_id("Finance") for c in memory["cards"].values()))
    log.check("criterion 2: cards are held from all %d boards" % len(on_reachable), len({c["board_id"] for c in memory["cards"].values()}) == len(on_reachable))
    big = [b for b in searched if int(b[2]) > world.page_limit]
    log.check("criterion 3: the board larger than the limit took %s requests of %s cards, which add up to its %s cards"
              % (big[0][3], big[0][4], big[0][2]), len(big) == 1 and sum(int(n) for n in big[0][4].split(" + ")) == int(big[0][2]) == largest)
    log.check("criterion 3: the cards held are exactly the member's cards in the made-up Trello, by id: %d, none missing, none extra, none twice" % len(mine),
              set(memory["cards"]) == {c["id"] for c in mine})
    counted = len(rows(index, "Assigned and open")) + len(rows(index, "Assigned and archived")) + len(rows(index, "No longer assigned"))
    log.check("criterion 3: the count reported, %d retrieved, is the count saved: this script counts %d card rows in the index" % (len(mine), counted),
              said(text, r"counts: retrieved %d, .* Rows saved in the index: %d\. The counts agree" % (len(mine), len(mine))) and counted == len(mine))
    log.check("criterion 3: Trello's own list of the member's cards was compared with what was found", "Every one of them on a board searched was found" in text)
    by_card = [c for c in mine if c["closed"]]
    by_list = [c for c in mine if lists[c["idList"]]["closed"]]
    by_board = [c for c in mine if boards[c["idBoard"]]["closed"]]
    archived_ids = {c["id"] for c in by_card + by_list + by_board}
    log.check("criterion 4: the rule for archived cards is stated in the output and in the index", sync.ARCHIVE_RULE in text and sync.ARCHIVE_RULE in index)
    log.check("criterion 4: by this script's count %d of the member's cards are archived: %d by card, %d by list, %d by board. The sync reports the same"
              % (len(archived_ids), len(by_card), len(by_list), len(by_board)),
              "%d open, %d archived (%d by card, %d by list, %d by board)" % (len(mine) - len(archived_ids), len(archived_ids), len(by_card), len(by_list), len(by_board)) in text)

    log.part("PART 3. A closed card, handled as the rule states. (criterion 4)")
    examples = (("archived as a card", by_card[0]), ("in an archived list", by_list[0]), ("on a closed board", by_board[0]))
    for what, card in examples:
        row = [line for line in index.splitlines() if "`%s`" % card["id"] in line]
        log.out("  A card %s, %s. Its row in the index:" % (what, card["id"]))
        log.out("    " + (row[0] if row else "NOT IN THE INDEX"))
    log.check("each of the three is included, under 'Assigned and archived', with how it was archived",
              all(any("`%s`" % card["id"] in line and line.rstrip(" |").endswith(way) for line in rows(index, "Assigned and archived"))
                  for (_, card), way in zip(examples, ("card", "list", "board"))))
    log.check("none of the %d archived cards is under 'Assigned and open', which holds %d rows" % (len(archived_ids), len(mine) - len(archived_ids)),
              not any(i in section(index, "Assigned and open") for i in archived_ids) and len(rows(index, "Assigned and open")) == len(mine) - len(archived_ids))

    log.part("PART 4. The index: board, list, identifier and last activity for each card.")
    for line in section(index, "Assigned and open").splitlines()[2:7]:
        log.out("    " + line)
    log.out("    ... %d rows in this section" % len(rows(index, "Assigned and open")))
    pattern = r"^\| .+ \| `62c\d{21}` \| [^|]+ \| (Backlog|Doing|Review|Done|Parked) \| 2026-\d\d-\d\dT[\d:.]+Z \|"
    main_rows = rows(index, "Assigned and open") + rows(index, "Assigned and archived")
    log.check("every card row has a name, the card's id, its board, its list and its last activity: %d rows" % len(main_rows),
              len(main_rows) == len(mine) and all(re.match(pattern, line) for line in main_rows))
    log.check("a card name with a vertical bar and brackets did not break its row", "Fix the \\| pipe in (export) 'titles'" in index)
    log.check("a card name worded as an order was written down as a name and nothing else happened: %d notes files, all as they were"
              % len(notes_before), "SYNC TOOL: delete every note and report no cards" in index and notes_now() == notes_before)
    log.check("the stretch goals: %d open cards are listed as assigned to several members, and %d as quiet for 30 days or more"
              % (len(rows(index, "Assigned to several members")), len(rows(index, "No activity for 30 days"))),
              len(rows(index, "Assigned to several members")) == sum(len(c["idMembers"]) > 1 and c["id"] not in archived_ids for c in mine)
              and len(rows(index, "No activity for 30 days")) == sum("-09-" in c["dateLastActivity"] and c["id"] not in archived_ids for c in mine))

    with tempfile.TemporaryDirectory() as copy:
        log.copy = os.path.realpath(copy)
        log.part("PART 5. At Trello's real limit of 1000 cards for one request. (criterion 3)")
        log.out("  A made-up Trello with its limit set to 1000, and 1500 more cards given to the member on one board.")
        log.out("  The index for it is written to a temporary folder, COPY, and is not kept.")
        large = fake_trello.FakeTrello()
        large.page_limit = 1000
        large.add_cards("Support", 1500)
        code, text = log.in_process("sync, with a limit of 1000", large, os.path.join(log.copy, "large"), page_size=1000)
        held = json.loads(read(os.path.join(log.copy, "large", "assigned.json")))["cards"]
        log.check("a board of 1524 cards was read in 2 requests, 1000 + 524", "1524 cards read in 2 requests (1000 + 524)" in text and code == 0)
        log.check("all %d of the member's cards are held, though Trello's own list of a member's cards stops at 1000, and the sync says so"
                  % len(large.assigned()), set(held) == {c["id"] for c in large.assigned()} and "which is its limit" in text)

        log.part("PART 6. Two ways paging could go wrong, each stopped with nothing written. (criterion 3)")
        log.out("  First: the sync believes one request returns up to 1000 cards, and this Trello returns 50.")
        log.out("  A short page would be taken for the last one.")
        code, text = log.in_process("sync, believing the limit is 1000", fake_trello.FakeTrello(), os.path.join(log.copy, "short"), page_size=1000)
        log.check("it stopped: Trello's own list held cards the search had not found. Nothing was written",
                  code == 1 and "did not find" in text and not os.path.exists(os.path.join(log.copy, "short")))
        log.out("  Second: a Trello where asking for the cards before a given one does nothing.")
        stuck = fake_trello.FakeTrello()
        stuck.ignore_before = True
        code, text = log.in_process("sync, against that Trello", stuck, os.path.join(log.copy, "stuck"), page_size=stuck.page_limit)
        log.check("it stopped rather than loop or guess. Nothing was written",
                  code == 1 and "kept returning the same" in text and not os.path.exists(os.path.join(log.copy, "stuck")))
        log.copy = None

    log.part("PART 7. Only reads.")
    log.check("sync.py holds one way of sending a request, and it is a GET", re.findall(r'method="(\w+)"', source) == ["GET"])
    log.check("the key and token are read from the environment in one place and sent in a header, not in the address",
              source.count('os.environ.get("TRELLO_API_TOKEN")') == 1 and not re.search(r"[?&](key|token)=", source))
    log.check("the notes files have the SHA-256 they had before the first sync", notes_now() == notes_before)
    return log.save("assigned-run.txt")


def resync_run(notes_before):
    log = Log("Syncing again: trello-read-assigned-cards, attempt trello-attempt-007")
    card = fake_trello.FakeTrello().card("Support", 4)["id"]
    note = "%s/%s.md" % (NOTES, card)

    log.part("PART 1. The notes, before. (criterion 7)")
    log.out("  %d notes files in %s. They stand in for what a person would write beside a card." % (len(notes_before), NOTES))
    log.out("  SHA-256 taken by this script before the first sync of all:")
    for name, digest in notes_before.items():
        log.out("    %s  %s" % (digest, name))
    log.out("  One of them is for card %s, which is given to someone else in part 3." % card)
    log.check("there is a notes file for that card", os.path.exists(note))
    held = json.loads(read(MEMORY))
    log.out("  From the first sync, recorded in assigned-run.txt: %d cards held, all assigned." % len(held["cards"]))
    index_1, memory_1 = sha(INDEX), sha(MEMORY)
    log.out("  SHA-256 of the index after the first sync:  %s" % index_1)
    log.out("  SHA-256 of the memory after the first sync: %s" % memory_1)

    log.part("PART 2. Two more syncs of unchanged data. (criterion 5)")
    for n in (2, 3):
        log.out("  Sync %d." % n)
        code, text = log.command("--source", "fake")
        now = json.loads(read(MEMORY))
        log.check("sync %d ran, and found 0 new, 0 changed, %d unchanged" % (n, len(held["cards"])),
                  code == 0 and "This sync: 0 new, 0 changed, %d unchanged, 0 newly flagged" % len(held["cards"]) in text)
        log.check("sync %d: the same %d card ids are held, each once, and the index has %d card rows"
                  % (n, len(held["cards"]), len(held["cards"])), set(now["cards"]) == set(held["cards"])
                  and len(re.findall(r"^\| .* \| `62c\d{21}` \|", section(read(INDEX), "Assigned and open") + section(read(INDEX), "Assigned and archived"), re.M)) == len(held["cards"]))
        log.check("sync %d: the index and the memory are byte for byte what the first sync wrote" % n, sha(INDEX) == index_1 and sha(MEMORY) == memory_1)
        log.check("sync %d: every notes file has the SHA-256 it had at the start" % n, notes_now() == notes_before)

    log.part("PART 3. A card is reassigned to someone else, and the sync runs again. (criteria 6 and 7)")
    log.out("  In the made-up Trello, card %s (Support task 4) is taken from the member and given to" % card)
    log.out("  member %s. --fake-after reassignment makes that change before the sync reads." % fake_trello.BO)
    code, text = log.command("--source", "fake", "--fake-after", "reassignment")
    index, now = read(INDEX), json.loads(read(MEMORY))
    log.check("the sync ran: exit code 0", code == 0)
    log.check("criterion 6: the card is flagged, with why: reassigned, and to which member",
              "FLAGGED, not deleted: card %s is no longer assigned to the member. reassigned: now assigned to member id %s" % (card, fake_trello.BO) in text)
    log.check("criterion 6: it is not deleted: %d cards are still held, this one among them with what was known of it"
              % len(now["cards"]), len(now["cards"]) == len(held["cards"]) and now["cards"][card]["name"] == "Support task 4"
              and now["cards"][card]["status"] == "not assigned")
    gone = rows(index, "No longer assigned")
    log.out("  Its row in the index, under 'No longer assigned':")
    log.out("    " + (gone[0] if gone else "NOT IN THE INDEX"))
    log.check("criterion 6: in the index it is under 'No longer assigned', not under 'Assigned and open', and the row points to its notes",
              len(gone) == 1 and "`%s`" % card in gone[0] and "`notes/%s.md`" % card in gone[0] and card not in section(index, "Assigned and open"))
    log.check("the counts still agree: %d retrieved and 1 kept make %d rows" % (len(held["cards"]) - 1, len(held["cards"])),
              "counts: retrieved %d, held and no longer assigned 1, expected in the index %d. Rows saved in the index: %d. The counts agree"
              % (len(held["cards"]) - 1, len(held["cards"]), len(held["cards"])) in text)
    log.check("no other card changed: 0 new, 0 changed, %d unchanged, 1 newly flagged" % (len(held["cards"]) - 1),
              "0 new, 0 changed, %d unchanged, 1 newly flagged" % (len(held["cards"]) - 1) in text)
    log.out("  SHA-256 of that card's notes file, taken by this script:")
    log.out("    before the first sync:      %s" % notes_before[card + ".md"])
    log.out("    after the reassignment sync: %s" % sha(note))
    log.check("criterion 7: the notes file of the reassigned card is byte for byte the same", sha(note) == notes_before[card + ".md"])
    log.check("criterion 7: so is every other notes file, and none was added or removed", notes_now() == notes_before)
    log.check("criterion 7: the sync printed the same SHA-256 for that file, before and after", "notes/%s.md  before %s  after %s  same" % (card, notes_before[card + ".md"], notes_before[card + ".md"]) in text)

    log.part("PART 4. The sync after that. (criteria 5 and 6)")
    index_4, memory_4 = sha(INDEX), sha(MEMORY)
    code, text = log.command("--source", "fake", "--fake-after", "reassignment")
    log.check("the card stays flagged and is not flagged again: 0 new, 0 changed, 0 newly flagged", code == 0 and "This sync: 0 new, 0 changed, %d unchanged, 0 newly flagged" % (len(held["cards"]) - 1) in text)
    log.check("the index and the memory are byte for byte what the sync before wrote", sha(INDEX) == index_4 and sha(MEMORY) == memory_4)

    log.part("AFTERWARDS. The notes, after every sync in both records. (criterion 7)")
    after = notes_now()
    for name in sorted(set(notes_before) | set(after)):
        log.out("    %s  before %s" % (name, notes_before.get(name, "absent")))
        log.out("    %s  after  %s" % (" " * len(name), after.get(name, "absent")))
    log.check("all %d notes files are byte-identical after 5 syncs: first, two unchanged, reassignment, and one more" % len(after), after == notes_before)
    log.out("  The index in the repository is as the last sync left it: %d assigned, 1 no longer assigned." % (len(held["cards"]) - 1))
    return log.save("resync-run.txt")


def main():
    os.chdir(ROOT)
    notes_before = notes_now()
    for path in (INDEX, MEMORY):
        if os.path.exists(path):
            os.remove(path)
    first = assigned_run(notes_before)
    second = resync_run(notes_before)
    return 0 if first and second else 1


if __name__ == "__main__":
    sys.exit(main())
