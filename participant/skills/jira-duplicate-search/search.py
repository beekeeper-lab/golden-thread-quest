#!/usr/bin/env python3
"""Searches the local Jira catalog for likely duplicates of a proposed new item.

    search.py --proposal FILE.json [--catalog FOLDER] [--report FILE.md] [--today YYYY-MM-DD]

A proposal is a JSON file describing work that someone is about to create:

    {"title": "...", "description": "...", "labels": ["..."], "components": ["..."], "parent": "RPT-1"}

Only the title is required. `parent` is the key or the issue id of the parent
story, or null.

The catalog folder holds catalog.json and a stories/ folder of records, as
the jira-build-index skill writes them. The default is
participant/context/jira/. The catalog says which stories exist. What each
story holds is read from its record, because the records are the source of
truth.

Five signals are compared, each with a number of points for how far it is
trusted:

    description   4   the two descriptions share at least half of the shorter one's
                      meaningful words, and at least four words
    parent        3   both sit under the same parent story
    component     2   both name the same component
    labels        1   they share at least one label
    title         1   the titles share at least 60% of the shorter one's meaningful
                      words, and at least two words, or are the same

A story is reported as a candidate only when at least three signals match.
So a matching title can never make a candidate by itself. A candidate's score
is the sum of its matched signals' points, out of 11:

    high     8 to 11
    medium   5 to 7
    low      4, the least that three signals can add up to

The recommendation is one of three words, and a person decides:

    merge     high, and the existing story is open: do not create a new one
    link      high and the existing story is finished, or medium: look first,
              and link the two if the new one is created
    proceed   low, or no candidate: create it

The search reads and compares. It writes nothing but the report it is asked
for. It never changes a record or the catalog, and it does not rebuild a
catalog that is stale: it stops and says so. It has no code that contacts
Jira or any network.

Story text is other people's writing. It is broken into words and compared.
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
sys.path.insert(0, os.path.join(ROOT, "participant", "skills", "jira-build-index"))
import index  # noqa: E402

DEFAULT_CATALOG = os.path.join(ROOT, "participant", "context", "jira")
WEIGHTS = (("description", 4), ("parent", 3), ("component", 2), ("labels", 1), ("title", 1))
MIN_SIGNALS = 3
LEVELS = (("high", 8), ("medium", 5), ("low", 0))
FINISHED = ("done", "closed", "resolved")
STOP_WORDS = set("""a an and are as at be by each every for from has have in into is it its of on or so than that the
their them then there these they this to was were which will with should would can could more most new get gets""".split())


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


# ---------------------------------------------------------------- reading


def read_proposal(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise Stop("there is no proposal file at the path given")
    except ValueError:
        raise Stop("the proposal file is not JSON")
    allowed = {"title", "description", "labels", "components", "parent"}
    if not isinstance(data, dict) or not set(data) <= allowed:
        raise Stop("a proposal has only these names: %s" % ", ".join(sorted(allowed)))
    title = data.get("title")
    if not isinstance(title, str) or not title.strip():
        raise Stop("a proposal needs a title")
    lists = {}
    for name in ("labels", "components"):
        value = data.get(name) or []
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise Stop("in a proposal, %s is a list of text" % name)
        lists[name] = value
    description, parent = data.get("description") or "", data.get("parent")
    if not isinstance(description, str) or not (parent is None or isinstance(parent, str)):
        raise Stop("in a proposal, the description is text and the parent is a key, an id or null")
    return {"title": title.strip(), "description": description, "labels": lists["labels"],
            "components": lists["components"], "parent": (parent or "").strip() or None}


def read_story(path):
    """What the search compares, read from one record."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    front = index.front_matter(text) or {}

    def names(value):
        return [item["name"] if isinstance(item, dict) else item for item in value
                if isinstance(item, str) or (isinstance(item, dict) and isinstance(item.get("name"), str))] \
            if isinstance(value, list) else []
    body = text.split("\n## Description\n", 1)[1] if "\n## Description\n" in text else ""
    body = body.split("\n## Preserved fields\n", 1)[0].strip()
    parent = front.get("parent") if isinstance(front.get("parent"), dict) else {}
    status = front.get("status") if isinstance(front.get("status"), dict) else {}
    category = status.get("statusCategory") if isinstance(status.get("statusCategory"), dict) else {}

    def day(value):
        return value[:10] if isinstance(value, str) and re.match(r"\d{4}-\d\d-\d\d", value) else None
    return {"description": "" if body == "(empty)" else body,
            "labels": names(front.get("labels")), "components": names(front.get("components")),
            "parent_id": parent.get("id") if isinstance(parent.get("id"), str) else None,
            "parent_key": parent.get("key") if isinstance(parent.get("key"), str) else None,
            "finished": (category.get("key") == "done" or str(status.get("name", "")).lower() in FINISHED
                         or isinstance(front.get("resolution"), dict)),
            "created": day(front.get("created")), "updated": day(front.get("updated"))}


def folder_hashes(folder, records):
    """SHA-256 of both catalog files and of every record, to show afterwards that none changed."""
    found = {}
    for path in [os.path.join(folder, "catalog.md"), os.path.join(folder, "catalog.json")] + \
            sorted(os.path.join(records, name) for name in os.listdir(records)):
        if os.path.isfile(path):
            with open(path, "rb") as f:
                found[os.path.relpath(path, folder)] = hashlib.sha256(f.read()).hexdigest()
    return found


# ---------------------------------------------------------------- comparing


def low(items):
    return set(item.lower() for item in items)


def compare(proposal, entry, story):
    """The five signals for one story: {name: (matched, detail)}. matched is True, False or None for 'cannot compare'."""
    signals = {}
    mine, theirs = words(proposal["description"]), words(story["description"])
    if not mine or not theirs:
        signals["description"] = (None, "cannot compare: %s has no description" % ("the proposal" if not mine else "the story"))
    else:
        shared, share = overlap(mine, theirs)
        signals["description"] = (len(shared) >= 4 and share >= 0.5,
                                  "%s, %d%% of the shorter description%s"
                                  % (count(len(shared), "shared word"), round(share * 100), ": " + ", ".join(shared) if shared else ""))
    if not proposal["parent"] or not (story["parent_id"] or story["parent_key"]):
        signals["parent"] = (None, "cannot compare: %s has no parent" % ("the proposal" if not proposal["parent"] else "the story"))
    else:
        same = proposal["parent"] == story["parent_id"] or proposal["parent"].lower() == (story["parent_key"] or "").lower()
        signals["parent"] = (same, "%s parent, %s" % ("the same" if same else "a different", story["parent_key"] or story["parent_id"]))
    for name, key in (("component", "components"), ("labels", "labels")):
        if not proposal[key] or not story[key]:
            signals[name] = (None, "cannot compare: %s has none" % ("the proposal" if not proposal[key] else "the story"))
        else:
            shared = sorted(low(proposal[key]) & low(story[key]))
            signals[name] = (bool(shared), "shared: " + ", ".join(shared) if shared else "none shared")
    mine, theirs = words(proposal["title"]), words(entry["title"] or "")
    shared, share = overlap(mine, theirs)
    same = bool(mine) and (mine == theirs or (len(shared) >= 2 and share >= 0.6))
    signals["title"] = (same, "%s, %d%% of the shorter title%s"
                        % (count(len(shared), "shared word"), round(share * 100), ": " + ", ".join(shared) if shared else ""))
    return signals


def judge(signals, finished):
    matched = [name for name, _ in WEIGHTS if signals[name][0] is True]
    score = sum(points for name, points in WEIGHTS if name in matched)
    if len(matched) < MIN_SIGNALS:
        return matched, score, None, None
    level = next(name for name, least in LEVELS if score >= least)
    if level == "high":
        advice = "link" if finished else "merge"
    else:
        advice = "link" if level == "medium" else "proceed"
    return matched, score, level, advice


WHY = {"merge": "do not create a new story. This looks like the same work, and it is still open. Add anything new to it",
       "link": "look at this story before creating. If the new one is still needed, create it and link the two",
       "proceed": "create the new story. This one is in the same area and is probably different work"}


def age(day, today):
    if not day:
        return "not recorded"
    days = (today - datetime.date.fromisoformat(day)).days
    return "%s, %d day%s before %s" % (day, days, "" if days == 1 else "s", today.isoformat())


# ---------------------------------------------------------------- the search


def search(proposal, folder, today):
    records = os.path.join(folder, "stories")
    try:
        files = index.render(index.scan(records), "stories")
    except index.Stop as stop:
        raise Stop(str(stop))
    if index.matches(folder, files):
        raise Stop("the catalog in %s does not match its records, so it is not searched. Rebuild it with the "
                   "jira-build-index skill, then search again. This search does not change a catalog" % index.place(folder))
    with open(os.path.join(folder, "catalog.json"), encoding="utf-8") as f:
        entries = json.load(f)["entries"]
    candidates, dismissed = [], []
    for entry in entries:
        story = read_story(os.path.join(records, entry["file"]))
        signals = compare(proposal, entry, story)
        matched, score, level, advice = judge(signals, story["finished"])
        found = {"entry": entry, "story": story, "signals": signals, "matched": matched, "score": score,
                 "level": level, "advice": advice}
        if level:
            candidates.append(found)
        elif matched:
            dismissed.append(found)
    candidates.sort(key=lambda c: (-c["score"], int(c["entry"]["id"])))
    order = ("merge", "link", "proceed")
    overall = min((c["advice"] for c in candidates), key=order.index) if candidates else "proceed"
    return {"searched": len(entries), "candidates": candidates, "dismissed": dismissed, "overall": overall, "today": today}


def quote(text):
    return json.dumps(" ".join(str(text).split()))


def lines_for(proposal, result, folder):
    """What the search found, as plain lines for the screen."""
    out = ["DUPLICATE SEARCH. Reads local files only, and changes none.",
           "Proposed item: %s" % quote(proposal["title"]),
           "  labels: %s. components: %s. parent: %s." % (", ".join(proposal["labels"]) or "none",
                                                           ", ".join(proposal["components"]) or "none", proposal["parent"] or "none"),
           "Catalog searched: %s, %d stories. It matches its records." % (index.place(folder), result["searched"]),
           "Signals and points: %s. A candidate needs at least %d matched signals."
           % (", ".join("%s %d" % item for item in WEIGHTS), MIN_SIGNALS),
           "Confidence: high 8 to 11 points, medium 5 to 7, low 4.", ""]
    if not result["candidates"]:
        out += ["RESULT: NONE. No story in the catalog matches this proposal on three or more signals."]
    else:
        out += ["RESULT: %d candidate%s." % (len(result["candidates"]), "" if len(result["candidates"]) == 1 else "s")]
    for number, c in enumerate(result["candidates"], 1):
        entry = c["entry"]
        out += ["",
                "Candidate %d: %s (issue id %s), status %s%s" % (number, entry["key"] or index.MISSING, entry["id"],
                                                                 entry["status"] or index.MISSING, ", finished" if c["story"]["finished"] else ", open"),
                "  title: %s" % quote(entry["title"] or ""),
                "  confidence: %s (%d of 11 points, %d of 5 signals matched)" % (c["level"].upper(), c["score"], len(c["matched"]))]
        for name, points in WEIGHTS:
            state, detail = c["signals"][name]
            out.append("    %-12s %-10s %s" % (name, "MATCHED +%d" % points if state else ("no" if state is False else "-"), detail))
        out += ["  created: %s" % age(c["story"]["created"], result["today"]),
                "  last updated: %s" % age(c["story"]["updated"], result["today"]),
                "  recommendation: %s. %s." % (c["advice"].upper(), WHY[c["advice"]][0].upper() + WHY[c["advice"]][1:]),
                "  record: stories/%s" % entry["file"]]
    if result["dismissed"]:
        out += ["", "Looked at and NOT reported as duplicates, because fewer than %d signals matched:" % MIN_SIGNALS]
        for c in result["dismissed"]:
            out.append("  %s (issue id %s): matched on %s only. %s"
                       % (c["entry"]["key"] or index.MISSING, c["entry"]["id"], " and ".join(c["matched"]),
                          "The title is the same and nothing else is." if c["matched"] == ["title"] else ""))
    out += ["",
            "Overall recommendation: %s." % result["overall"].upper(),
            "This is a recommendation. A person decides whether to merge, link or proceed. The search has created,",
            "linked and changed nothing."]
    return [line.rstrip() for line in out]


def md(text):
    """Text from a record or a proposal, made safe to sit in Markdown as plain text on one line."""
    text = " ".join(str(text).split()).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    for ch in "\\`*_[]|#~":
        text = text.replace(ch, "\\" + ch)
    return text


def markdown_for(proposal, result):
    """The same findings as a Markdown report."""
    esc = md
    out = ["# Duplicate search report", "",
           "> Written by `participant/skills/jira-duplicate-search/search.py`. It reports and recommends. A person",
           "> decides. Story titles and words are other people's writing, shown as text.", "",
           "## The proposed item", "",
           "- Title: %s" % esc(proposal["title"]),
           "- Labels: %s" % (", ".join(esc(x) for x in proposal["labels"]) or "none"),
           "- Components: %s" % (", ".join(esc(x) for x in proposal["components"]) or "none"),
           "- Parent: %s" % (esc(proposal["parent"]) if proposal["parent"] else "none"), "",
           "## How it was searched", "",
           "%d stories in the catalog were compared on five signals. Ages are counted to %s."
           % (result["searched"], result["today"].isoformat()), "",
           "| Signal | Points | It matches when |", "|---|---|---|",
           "| Description | 4 | the descriptions share at least half of the shorter one's meaningful words, and at least four |",
           "| Parent | 3 | both sit under the same parent story |",
           "| Component | 2 | both name the same component |",
           "| Labels | 1 | they share at least one label |",
           "| Title | 1 | the titles share at least 60% of the shorter one's meaningful words, and at least two, or are the same |", "",
           "A story is a candidate only when at least three signals match. Confidence is the points of the matched",
           "signals, out of 11: **high** 8 to 11, **medium** 5 to 7, **low** 4, the least three signals can add up to.", "",
           "## Result: %s" % ("%d candidate%s" % (len(result["candidates"]), "" if len(result["candidates"]) == 1 else "s")
                              if result["candidates"] else "none"), ""]
    if not result["candidates"]:
        out += ["No story in the catalog matches this proposal on three or more signals.", ""]
    for number, c in enumerate(result["candidates"], 1):
        entry = c["entry"]
        out += ["### Candidate %d: %s (issue id %s)" % (number, esc(entry["key"] or index.MISSING), entry["id"]), "",
                "- Title: %s" % esc(entry["title"] or ""),
                "- Status: %s, %s" % (esc(entry["status"] or index.MISSING), "finished" if c["story"]["finished"] else "open"),
                "- **Confidence: %s** (%d of 11 points, %d of 5 signals matched)" % (c["level"], c["score"], len(c["matched"])),
                "- **Recommendation: %s.** %s." % (c["advice"], WHY[c["advice"]][0].upper() + WHY[c["advice"]][1:]),
                "- Created: %s" % age(c["story"]["created"], result["today"]),
                "- Last updated: %s" % age(c["story"]["updated"], result["today"]),
                "- Record: `stories/%s`" % entry["file"], "",
                "| Signal | Matched | Points | Detail |", "|---|---|---|---|"]
        for name, points in WEIGHTS:
            state, detail = c["signals"][name]
            out.append("| %s | %s | %s | %s |" % (name.capitalize(), "yes" if state else ("no" if state is False else "not comparable"),
                                                  points if state else 0, esc(detail)))
        out.append("")
    out += ["## Looked at and not reported", ""]
    out += ["- %s (issue id %s): matched on %s only%s" % (esc(c["entry"]["key"] or index.MISSING), c["entry"]["id"], " and ".join(c["matched"]),
                                                          ". The title is the same and nothing else is." if c["matched"] == ["title"] else ".")
            for c in result["dismissed"]] or ["No other story matched on any signal."]
    out += ["", "Fewer than three signals matched for each of these, so none is reported as a duplicate.", "",
            "## Overall recommendation: %s" % result["overall"], "",
            "A person decides whether to merge, link or proceed. The search has created, linked and changed nothing."]
    return "\n".join(out) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description="Search the local Jira catalog for likely duplicates of a proposed item.")
    parser.add_argument("--proposal", required=True, help="the JSON file describing the proposed item")
    parser.add_argument("--catalog", default=DEFAULT_CATALOG, help="the folder holding catalog.json and stories/")
    parser.add_argument("--report", help="also write the findings here, as Markdown")
    parser.add_argument("--today", help="the date ages are counted to, YYYY-MM-DD. The default is today")
    args = parser.parse_args(argv)
    folder = os.path.abspath(args.catalog)
    try:
        try:
            today = datetime.date.fromisoformat(args.today) if args.today else datetime.date.today()
        except ValueError:
            raise Stop("--today must be a date written YYYY-MM-DD")
        if args.report and os.path.commonpath([os.path.abspath(args.report), folder]) == folder and \
                os.path.basename(args.report) in ("catalog.md", "catalog.json"):
            raise Stop("the report cannot be written over the catalog")
        proposal = read_proposal(args.proposal)
        if not os.path.isdir(os.path.join(folder, "stories")):
            raise Stop("there is no stories folder in %s" % index.place(folder))
        before = folder_hashes(folder, os.path.join(folder, "stories"))
        result = search(proposal, folder, today)
        after = folder_hashes(folder, os.path.join(folder, "stories"))
    except Stop as stop:
        print("STOPPED: %s." % stop)
        print("Nothing was searched and nothing was changed.")
        return 2
    print("\n".join(lines_for(proposal, result, folder)))
    print("")
    if after == before:
        print("Catalog and records after the search: unchanged. All %d files have the SHA-256 they had before." % len(before))
        print("  catalog.md   %s" % before.get("catalog.md"))
        print("  catalog.json %s" % before.get("catalog.json"))
    else:
        print("WARNING: a catalog or record file is not as it was before the search.")
        return 2
    if args.report:
        text = markdown_for(proposal, result)
        os.makedirs(os.path.dirname(os.path.abspath(args.report)), exist_ok=True)
        with open(args.report, "w", encoding="utf-8") as f:
            f.write(text)
        print("Report written: %s" % index.place(os.path.abspath(args.report)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
