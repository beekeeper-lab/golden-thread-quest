#!/usr/bin/env python3
"""Searches the local Trello indexes, across boards, for likely duplicates of a proposed card.

    search.py --proposal FILE.json [--boards FOLDER] [--report FILE.md]
              [--decision link|archive-as-duplicate|proceed] [--decision-note TEXT]

A proposal is a JSON file describing a card that someone is about to create:

    {"name": "...", "board": "<board id>", "desc": "...", "labels": ["..."],
     "members": ["<member id>"], "checklist": ["..."], "due": "2026-12-04"}

The name and the board the card would go on are required.

The boards folder holds one folder for each board. Each of those holds
board.json, cards/ and the index of that board, index.md and index.json, as
the trello-build-index skill writes them with the records folder as --out.
The default is participant/context/trello/duplicates/boards/. Every board in
the folder is searched.

The index says which cards exist and holds each card's name, list, labels,
members, due date and state. The description and the checklist items are read
from the card's record, which the index names.

Five signals beyond the name are compared, each with a number of points for
how far it is trusted. The name is compared too, and is the weakest:

    description   4   the two descriptions share at least half of the shorter one's
                      meaningful words, and at least four words
    checklist     3   at least two checklist items are alike, and at least half of
                      the shorter checklist's items
    labels        2   they share a label, by name
    members       2   the same Trello member is on both
    due date      1   the due dates are at most three days apart
    name          1   the names share at least 60% of the shorter one's meaningful
                      words, and at least two words, or are the same

A card is reported as a candidate only when AT LEAST THREE OF THE FIVE
SIGNALS BEYOND THE NAME match. The name never counts towards the three. So a
card with the same name is not a candidate for that, and a card with a
different name is not hidden by it.

A candidate's score is the points of everything that matched, out of 13:

    high     10 to 13
    medium   7 to 9
    low      5 or 6. 5 is the least that three signals can add up to

The recommendation is one of three words, and a person decides:

    proceed               no candidate; or the candidate is archived or complete
    link                  the candidate is on another board; or it is on the same
                          board and the confidence is medium or low
    archive-as-duplicate  the candidate is open, on the board the new card would
                          go on, and the confidence is high

The search reads and compares. It writes nothing but the report it is asked
for. It never changes a record or an index, and it does not rebuild an index
that is stale: it stops and says so. It has no code that contacts Trello or
any network.

Card text is other people's writing. It is broken into words and compared.
Nothing in it is acted on, and it is shown quoted.

Exit codes: 0 the search ran, whatever it found; 2 it could not run.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "participant", "skills", "trello-build-index"))
import index  # noqa: E402

DEFAULT_BOARDS = os.path.join(ROOT, "participant", "context", "trello", "duplicates", "boards")
BEYOND_NAME = (("description", 4), ("checklist", 3), ("labels", 2), ("members", 2), ("due date", 1))
WEIGHTS = BEYOND_NAME + (("name", 1),)
TOP = sum(points for _, points in WEIGHTS)
MIN_SIGNALS = 3
LEVELS = (("high", 10), ("medium", 7), ("low", 0))
DUE_DAYS = 3
ADVICE = ("archive-as-duplicate", "link", "proceed")
STOP_WORDS = set("""a an and are as at be by each every for from has have in into is it its of on or so than that the
their them then there these they this to was were which will with should would can could more most new get gets not""".split())


class Stop(Exception):
    """The search cannot run. The message says why."""


# ---------------------------------------------------------------- words


def words(text):
    """The meaningful words of a text: lowercase, no stop words, a plural 's' removed."""
    found = set()
    for word in re.findall(r"[a-z0-9]+", (text or "").lower()):
        if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
            word = word[:-1]
        if len(word) >= 3 and word not in STOP_WORDS:
            found.add(word)
    return found


def count(number, word):
    return "%d %s%s" % (number, word, "" if number == 1 else "s")


def overlap(a, b):
    """The words two texts share, and that as a share of the shorter one's words."""
    shared = a & b
    return sorted(shared), (len(shared) / min(len(a), len(b)) if a and b else 0.0)


def alike(a, b, least_share=0.6, least_words=2):
    """Whether two short texts, such as two names or two checklist items, say the same thing."""
    mine, theirs = words(a), words(b)
    shared, share = overlap(mine, theirs)
    return bool(mine) and (mine == theirs or (len(shared) >= least_words and share >= least_share))


def day(value):
    """The calendar day of a due date, or None."""
    if not isinstance(value, str) or not re.match(r"\d{4}-\d\d-\d\d($|T)", value):
        return None
    try:
        return datetime.date.fromisoformat(value[:10])
    except ValueError:
        return None


# ---------------------------------------------------------------- reading


def read_proposal(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise Stop("there is no proposal file at the path given")
    except ValueError:
        raise Stop("the proposal file is not JSON")
    allowed = {"name", "board", "desc", "labels", "members", "checklist", "due"}
    if not isinstance(data, dict) or not set(data) <= allowed:
        raise Stop("a proposal has only these names: %s" % ", ".join(sorted(allowed)))
    for key in ("name", "board"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise Stop("a proposal needs a name, and the id of the board the card would go on")
    lists = {}
    for key in ("labels", "members", "checklist"):
        value = data.get(key) or []
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise Stop("in a proposal, %s is a list of text" % key)
        lists[key] = [item for item in value if item.strip()]
    desc, due = data.get("desc") or "", data.get("due")
    if not isinstance(desc, str):
        raise Stop("in a proposal, the description is text")
    if due is not None and day(due) is None:
        raise Stop("in a proposal, the due date is written YYYY-MM-DD, or is null")
    return {"name": data["name"].strip(), "board": data["board"].strip(), "desc": desc, "labels": lists["labels"],
            "members": lists["members"], "checklist": lists["checklist"], "due": due}


def read_record(path):
    """The description and the checklist items of one card, from its record. Text only."""
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except (OSError, UnicodeDecodeError):
        raise Stop("the card record %s, which its index names, could not be read" % index.place(path))
    body = text.split("\n## Description\n", 1)[1] if "\n## Description\n" in text else ""
    lines = body.strip("\n").split("\n")
    desc = ""
    if lines and re.fullmatch(r"`{3,}\w*", lines[0]):
        fence = lines[0].rstrip("abcdefghijklmnopqrstuvwxyz")
        desc = "\n".join(lines[1:lines.index(fence, 1)]) if fence in lines[1:] else ""
    items = []
    section = body.split("\n## Checklists\n", 1)[1].split("\n## Comments\n", 1)[0] if "\n## Checklists\n" in body else ""
    for found in re.findall(r'^- \[.\] ("(?:[^"\\]|\\.)*") \(item `', section, re.M):
        try:
            items.append(json.loads(found))
        except ValueError:
            pass
    return {"desc": desc, "checklist": [item for item in items if isinstance(item, str)]}


def read_boards(folder):
    """Every board in the boards folder, with its index, after checking the index matches its records."""
    if not os.path.isdir(folder):
        raise Stop("there is no boards folder at %s" % index.place(folder))
    names = sorted(name for name in os.listdir(folder) if os.path.isdir(os.path.join(folder, name)))
    if not names:
        raise Stop("the boards folder %s holds no board" % index.place(folder))
    boards = []
    for name in names:
        path = os.path.join(folder, name)
        try:
            files = index.render(index.scan(path), name)
        except index.Stop as stop:
            raise Stop("the board folder %s cannot be searched: %s. A board left out could hide a duplicate, so no board "
                       "is searched" % (index.place(path), stop))
        if index.matches(path, files):
            raise Stop("the index in %s does not match its records, so nothing is searched. Rebuild it with the "
                       "trello-build-index skill, then search again. This search does not change an index" % index.place(path))
        with open(os.path.join(path, "index.json"), encoding="utf-8") as f:
            data = json.load(f)
        if data["board"]["id"] in [board["id"] for board in boards]:
            raise Stop("two folders in %s hold the same board, %s" % (index.place(folder), data["board"]["id"]))
        boards.append({"folder": name, "path": path, "id": data["board"]["id"], "name": data["board"]["name"],
                       "lists": {item["id"]: item for item in data["lists"]}, "cards": data["cards"],
                       "fingerprint": data["records_fingerprint"]})
    return boards


def folder_hashes(folder):
    """SHA-256 of every file under the boards folder, to show afterwards that none changed."""
    found = {}
    for base, _, names in os.walk(folder):
        for name in names:
            path = os.path.join(base, name)
            with open(path, "rb") as f:
                found[os.path.relpath(path, folder)] = hashlib.sha256(f.read()).hexdigest()
    return found


# ---------------------------------------------------------------- comparing


def low(items):
    return set(item.strip().lower() for item in items if item.strip())


def compare(proposal, entry, record):
    """The six signals for one card: {name: (matched, detail)}. matched is True, False or None for 'cannot compare'."""
    signals = {}

    def cannot(which, proposal_has, what):
        signals[which] = (None, "cannot compare: %s has %s" % ("the proposal" if not proposal_has else "the card", what))

    mine, theirs = words(proposal["desc"]), words(record["desc"])
    if not mine or not theirs:
        cannot("description", mine, "no description")
    else:
        shared, share = overlap(mine, theirs)
        signals["description"] = (len(shared) >= 4 and share >= 0.5,
                                  "%s, %d%% of the shorter description%s"
                                  % (count(len(shared), "shared word"), round(share * 100), ": " + ", ".join(shared) if shared else ""))

    if not proposal["checklist"] or not record["checklist"]:
        cannot("checklist", proposal["checklist"], "no checklist items")
    else:
        short, long_ = sorted((proposal["checklist"], record["checklist"]), key=len)
        same = sum(1 for item in short if any(alike(item, other) for other in long_))
        signals["checklist"] = (same >= 2 and same * 2 >= len(short),
                                "%d of the shorter checklist's %s alike" % (same, count(len(short), "item")))

    labels = None if entry["labels"] is None else [label["name"] for label in entry["labels"] if label.get("name")]
    if not proposal["labels"] or not labels:
        cannot("labels", proposal["labels"], "no named label" if labels is not None else "no labels field in its record")
    else:
        shared = sorted(low(proposal["labels"]) & low(labels))
        signals["labels"] = (bool(shared), "shared: " + ", ".join(shared) if shared else "none shared")

    if not proposal["members"] or not entry["members"]:
        cannot("members", proposal["members"], "no member" if entry["members"] is not None else "no members field in its record")
    else:
        shared = sorted(set(proposal["members"]) & set(entry["members"]))
        signals["members"] = (bool(shared), "%s shared" % count(len(shared), "member") if shared else "none shared")

    mine, theirs = day(proposal["due"]), day(entry["due"])
    if mine is None or theirs is None:
        cannot("due date", mine, "no due date")
    else:
        apart = abs((mine - theirs).days)
        signals["due date"] = (apart <= DUE_DAYS, "%s apart: %s and %s" % (count(apart, "day"), mine.isoformat(), theirs.isoformat()))

    if not entry["name"]:
        cannot("name", True, "no name in its record")
    else:
        shared, share = overlap(words(proposal["name"]), words(entry["name"]))
        signals["name"] = (alike(proposal["name"], entry["name"]),
                           "%s, %d%% of the shorter name%s"
                           % (count(len(shared), "shared word"), round(share * 100), ": " + ", ".join(shared) if shared else ""))
    return signals


def judge(signals, same_board, finished):
    """(matched beyond the name, all matched, score, confidence, recommendation). The last two are None for no candidate."""
    beyond = [name for name, _ in BEYOND_NAME if signals[name][0] is True]
    matched = [name for name, _ in WEIGHTS if signals[name][0] is True]
    score = sum(points for name, points in WEIGHTS if name in matched)
    if len(beyond) < MIN_SIGNALS:
        return beyond, matched, score, None, None
    level = next(name for name, least in LEVELS if score >= least)
    if finished:
        advice = "proceed"
    elif same_board and level == "high":
        advice = "archive-as-duplicate"
    else:
        advice = "link"
    return beyond, matched, score, level, advice


def why(advice, finished):
    if advice == "archive-as-duplicate":
        return ("This is the same work, open, on the board the new card would go on. Do not keep two cards. If the new "
                "card is created anyway, one of the two is archived as a duplicate")
    if advice == "link":
        return ("Look at this card before creating. If the new card is still needed, create it and link the two, so that "
                "both teams know. Nothing on the other card is changed")
    return "This earlier card is %s. Create the new card if the work is needed again, and name this card in it" % finished


# ---------------------------------------------------------------- the search


def search(proposal, folder):
    boards = read_boards(folder)
    if proposal["board"] not in [board["id"] for board in boards]:
        raise Stop("the proposal is for board %s, which is not among the boards searched. The board a card would go on has "
                   "to be searched" % proposal["board"][:32])
    candidates, dismissed, searched = [], [], 0
    for board in boards:
        for entry in board["cards"]:
            searched += 1
            record = read_record(os.path.join(board["path"], "cards", entry["file"]))
            signals = compare(proposal, entry, record)
            in_list = board["lists"].get(entry["list_id"])
            finished = ("archived" if entry["closed"] is True else "on an archived list" if in_list and in_list["closed"]
                        else "marked complete" if entry["due_complete"] else None)
            same_board = board["id"] == proposal["board"]
            beyond, matched, score, level, advice = judge(signals, same_board, finished)
            found = {"entry": entry, "board": board, "list": in_list["name"] if in_list else index.MISSING, "signals": signals,
                     "beyond": beyond, "matched": matched, "score": score, "level": level, "advice": advice,
                     "finished": finished, "same_board": same_board}
            if level:
                candidates.append(found)
            elif matched:
                dismissed.append(found)
    candidates.sort(key=lambda c: (-c["score"], c["entry"]["id"]))
    overall = min((c["advice"] for c in candidates), key=ADVICE.index) if candidates else "proceed"
    return {"boards": boards, "searched": searched, "candidates": candidates, "dismissed": dismissed, "overall": overall}


def quote(text):
    return json.dumps(" ".join(str(text).split()), ensure_ascii=False)


def where(c):
    return "%s board %s, list %s" % ("the SAME" if c["same_board"] else "ANOTHER", quote(c["board"]["name"]), quote(c["list"]))


def state(c):
    return c["finished"] or "open"


def only(c):
    """Why a card that matched something is not a candidate."""
    text = "matched on %s only" % " and ".join(c["matched"])
    if c["matched"] == ["name"]:
        return text + ". The name is alike and nothing else is"
    if "name" in c["matched"]:
        return text + ". Beyond the name that is %s, and three are needed" % count(len(c["beyond"]), "signal")
    return text


def lines_for(proposal, result, folder):
    """What the search found, as plain lines for the screen."""
    board = next(b for b in result["boards"] if b["id"] == proposal["board"])
    out = ["DUPLICATE SEARCH ACROSS BOARDS. Reads local files only, and changes none.",
           "Proposed card: %s" % quote(proposal["name"]),
           "  for the board: %s" % quote(board["name"]),
           "  labels: %s. members: %d. checklist items: %d. due: %s." % (", ".join(proposal["labels"]) or "none", len(proposal["members"]),
                                                                         len(proposal["checklist"]), proposal["due"] or "none"),
           "Boards searched: %d, in %s. Each index matches its records." % (len(result["boards"]), index.place(folder))]
    out += ["  %s: %s, records fingerprint %s" % (quote(b["name"]), count(len(b["cards"]), "card"), b["fingerprint"][:16]) for b in result["boards"]]
    out += ["Cards compared: %d." % result["searched"],
            "Signals and points: %s. A candidate needs at least %d matched signals BEYOND THE NAME."
            % (", ".join("%s %d" % item for item in WEIGHTS), MIN_SIGNALS),
            "Confidence: high 10 to %d points, medium 7 to 9, low 5 or 6." % TOP, ""]
    if not result["candidates"]:
        out += ["RESULT: NONE. No card on any board searched matches this proposal on three or more signals beyond the name."]
    else:
        out += ["RESULT: %s." % count(len(result["candidates"]), "candidate")]
    for number, c in enumerate(result["candidates"], 1):
        entry = c["entry"]
        out += ["",
                "Candidate %d: card %s, %s" % (number, entry["id"], state(c)),
                "  name: %s" % quote(entry["name"] or index.MISSING),
                "  on: %s" % where(c),
                "  confidence: %s (%d of %d points; %d of 5 signals beyond the name matched)" % (c["level"].upper(), c["score"], TOP, len(c["beyond"]))]
        for name, points in WEIGHTS:
            matched, detail = c["signals"][name]
            out.append("    %-12s %-10s %s" % (name, "MATCHED +%d" % points if matched else ("no" if matched is False else "-"), detail))
        out += ["  recommendation: %s. %s." % (c["advice"].upper(), why(c["advice"], c["finished"])),
                "  record: %s/cards/%s" % (c["board"]["folder"], entry["file"])]
    if result["dismissed"]:
        out += ["", "Looked at and NOT reported as duplicates, because fewer than %d signals beyond the name matched:" % MIN_SIGNALS]
        out += ["  card %s, %s, on %s: %s." % (c["entry"]["id"], quote(c["entry"]["name"] or index.MISSING), quote(c["board"]["name"]), only(c))
                for c in result["dismissed"]]
    out += ["",
            "Overall recommendation: %s." % result["overall"].upper(),
            "This is a recommendation. A person decides whether to link, archive as a duplicate or proceed. The search has",
            "created, linked, archived and changed nothing."]
    return [line.rstrip() for line in out]


def md(text):
    """Text from a record or a proposal, made safe to sit in Markdown as plain text on one line."""
    text = " ".join(str(text).split()).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    for ch in "\\`*_[]|#~":
        text = text.replace(ch, "\\" + ch)
    return text


def markdown_for(proposal, result, decision=None, note=None):
    """The same findings as a Markdown report, with the person's decision if one was given."""
    board = next(b for b in result["boards"] if b["id"] == proposal["board"])
    out = ["# Duplicate search report", "",
           "> Written by `participant/skills/trello-duplicate-search/search.py`. It reports and recommends. A person",
           "> decides. Card names and words are other people's writing, shown as text.", "",
           "## The proposed card", "",
           "- Name: %s" % md(proposal["name"]),
           "- For the board: %s" % md(board["name"]),
           "- Labels: %s" % (", ".join(md(x) for x in proposal["labels"]) or "none"),
           "- Members: %s" % (", ".join("`%s`" % md(x) for x in proposal["members"]) or "none"),
           "- Checklist items: %d" % len(proposal["checklist"]),
           "- Due: %s" % (proposal["due"] or "none"), "",
           "## How it was searched", "",
           "%d cards on %d boards were compared, from the index of each board. Each index matched its records."
           % (result["searched"], len(result["boards"])), ""]
    out += ["- %s: %s, records fingerprint `%s`" % (md(b["name"]), count(len(b["cards"]), "card"), b["fingerprint"][:16]) for b in result["boards"]]
    out += ["",
            "| Signal | Points | It matches when |", "|---|---|---|",
            "| Description | 4 | the descriptions share at least half of the shorter one's meaningful words, and at least four |",
            "| Checklist | 3 | at least two checklist items are alike, and at least half of the shorter checklist's items |",
            "| Labels | 2 | they share a label, by name |",
            "| Members | 2 | the same Trello member is on both |",
            "| Due date | 1 | the due dates are at most three days apart |",
            "| Name | 1 | the names share at least 60% of the shorter one's meaningful words, and at least two, or are the same |", "",
            "A card is a candidate only when **at least three of the five signals beyond the name** match. The name never",
            "counts towards the three. Confidence is the points of everything that matched, out of %d: **high** 10 to %d," % (TOP, TOP),
            "**medium** 7 to 9, **low** 5 or 6. 5 is the least that three signals can add up to.", "",
            "## Result: %s" % (count(len(result["candidates"]), "candidate") if result["candidates"] else "none"), ""]
    if not result["candidates"]:
        out += ["No card on any board searched matches this proposal on three or more signals beyond the name.", ""]
    for number, c in enumerate(result["candidates"], 1):
        entry = c["entry"]
        out += ["### Candidate %d: card `%s`" % (number, entry["id"]), "",
                "- Name: %s" % md(entry["name"] or index.MISSING),
                "- Board: %s, %s" % (md(c["board"]["name"]), "the same board as the proposal" if c["same_board"] else "another board"),
                "- List: %s. State: %s" % (md(c["list"]), state(c)),
                "- **Confidence: %s** (%d of %d points; %d of 5 signals beyond the name matched)" % (c["level"], c["score"], TOP, len(c["beyond"])),
                "- **Recommendation: %s.** %s." % (c["advice"], why(c["advice"], c["finished"])),
                "- Record: `%s/cards/%s`" % (c["board"]["folder"], entry["file"]), "",
                "| Signal | Matched | Points | Detail |", "|---|---|---|---|"]
        for name, points in WEIGHTS:
            matched, detail = c["signals"][name]
            out.append("| %s | %s | %s | %s |" % (name.capitalize(), "yes" if matched else ("no" if matched is False else "not comparable"),
                                                  points if matched else 0, md(detail)))
        out.append("")
    out += ["## Looked at and not reported", ""]
    out += ["- Card `%s`, %s, on %s: %s." % (c["entry"]["id"], md(c["entry"]["name"] or index.MISSING), md(c["board"]["name"]), only(c))
            for c in result["dismissed"]] or ["No other card matched on any signal."]
    if result["dismissed"]:
        out += ["", "Fewer than three signals beyond the name matched for each of these, so none is reported as a duplicate."]
    out += ["", "## The search's overall recommendation: %s" % result["overall"], "",
            "The search has created, linked, archived and changed nothing.", "",
            "## The decision", ""]
    if decision:
        out += ["**Decision: %s.**" % decision, "",
                "Made by a person and given to the search with `--decision`. The search did not choose it. The search",
                "recommended %s, which %s the decision." % (result["overall"], "is" if decision == result["overall"] else "is not")]
        if note:
            out += ["", "The person's note: %s" % md(note)]
    else:
        out += ["Not yet decided. A person decides whether to link, archive as a duplicate or proceed, and records it by",
                "running the search again with `--decision`."]
    return "\n".join(out) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Search the local Trello indexes, across boards, for likely duplicates of a proposed card.")
    parser.add_argument("--proposal", required=True, help="the JSON file describing the proposed card")
    parser.add_argument("--boards", default=DEFAULT_BOARDS, help="the folder holding one folder for each board")
    parser.add_argument("--report", help="also write the findings here, as Markdown")
    parser.add_argument("--decision", choices=ADVICE, help="the decision a person has made, to record in the report")
    parser.add_argument("--decision-note", help="the person's reason, to record with the decision")
    args = parser.parse_args(argv)
    folder = os.path.abspath(args.boards)
    try:
        if (args.decision or args.decision_note) and not args.report:
            raise Stop("a decision is recorded in a report, so --decision needs --report")
        if args.decision_note and not args.decision:
            raise Stop("a note goes with a decision, so --decision-note needs --decision")
        if args.report and os.path.commonpath([os.path.abspath(args.report), folder]) == folder:
            raise Stop("the report cannot be written inside the boards folder, which the search does not change")
        proposal = read_proposal(args.proposal)
        if not os.path.isdir(folder):
            raise Stop("there is no boards folder at %s" % index.place(folder))
        before = folder_hashes(folder)
        result = search(proposal, folder)
        after = folder_hashes(folder)
    except Stop as stop:
        print("STOPPED: %s." % stop)
        print("Nothing was searched and nothing was changed.")
        return 2
    print("\n".join(lines_for(proposal, result, folder)))
    print("")
    if after != before:
        print("WARNING: a file in the boards folder is not as it was before the search.")
        return 2
    print("Indexes and records after the search: unchanged. All %d files have the SHA-256 they had before." % len(before))
    for board in result["boards"]:
        for name in ("index.md", "index.json"):
            print("  %-26s %s" % ("%s/%s" % (board["folder"], name), before[os.path.join(board["folder"], name)]))
    if args.report:
        text = markdown_for(proposal, result, args.decision, args.decision_note)
        os.makedirs(os.path.dirname(os.path.abspath(args.report)), exist_ok=True)
        with open(args.report, "w", encoding="utf-8") as f:
            f.write(text)
        print("Report written: %s%s" % (index.place(os.path.abspath(args.report)),
                                        ", with the person's decision: %s" % args.decision if args.decision else ", with no decision yet"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
