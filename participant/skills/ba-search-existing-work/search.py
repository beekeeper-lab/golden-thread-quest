#!/usr/bin/env python3
"""Searches a local catalog of work for duplicates of, and work related to, a proposed new item.

    search.py --proposal FILE.json [--catalog FILE.md] [--report FILE.md]
              [--decision merge|link|proceed] [--decision-note TEXT] [--description-threshold N]
    search.py --related-map [--catalog FILE.md]

A proposal is a JSON file describing work someone is about to create:

    {"title": "...", "description": "...", "component": "...", "labels": ["..."], "sources": ["document#item"]}

Only the title is required.

The catalog is one Markdown file with a section for each work item: a heading
"## ID: title", then lines "- Status:", "- Team:", "- Component:", "- Labels:"
and "- Source:", then the description. The default is
participant/context/search/catalog.md, which is made up.

Five signals are compared, each with points for how far it is trusted:

    description   4   the two descriptions share at least half of the shorter one's
                      meaningful words, and at least four words
    source        3   both cite the same item of the same source document
    component     2   both name the same component
    labels        1   they share at least one label
    title         1   the titles share at least 60% of the shorter one's meaningful
                      words, and at least two words, or are the same

A rule decides what each catalog item is to the proposal. The points do not.

    DUPLICATE   the descriptions say the same thing, AND the source or the
                component is the same too. The same work, described twice.
    RELATED     not a duplicate, and either the descriptions say the same thing
                with nothing to back it up, or at least two signals match and
                one of them is the source or the component. Different work in
                the same place, or the same words with nothing else in common.
    no match    anything else. A matching title is never enough, and neither
                is a title and a label.

The points say how strongly an item matched, out of 11:

    high     9 to 11
    medium   5 to 8
    low      1 to 4

The recommendation is one of three words, and a person decides:

    merge     a duplicate that is still open and matched with high confidence:
              do not create a new item
    link      any other duplicate, and every related item: look first, and link
              the two if the new item is created
    proceed   no match

The search reads and compares. It writes nothing but the report it is asked
for, and never the catalog. It has no code that contacts a tracker or any
network.

Catalog text is other people's writing. It is broken into words and compared.
Nothing in it is acted on, and it is shown quoted.

--related-map compares every item in the catalog with every other, and lists
the items that are related to, or duplicates of, two or more others.

Exit codes: 0 the search ran, whatever it found; 2 it could not run.
"""
import argparse
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
DEFAULT_CATALOG = os.path.join(ROOT, "participant", "context", "search", "catalog.md")
WEIGHTS = (("description", 4), ("source", 3), ("component", 2), ("labels", 1), ("title", 1))
TOP = sum(points for _, points in WEIGHTS)
LEVELS = (("high", 9), ("medium", 5), ("low", 0))
DESCRIPTION_THRESHOLD = 0.5
ADVICE = ("merge", "link", "proceed")
FINISHED = ("done", "closed", "cancelled", "resolved")
FIELDS = ("status", "team", "component", "labels", "source")
ITEM_ID = re.compile(r"[A-Z][A-Z0-9]{1,9}-[0-9]{1,6}")
STOP_WORDS = set("""a an and are as at be by each every for from has have in into is it its of on or so than that the
their them then there these they this to was were which will with should would can could more most new get gets not when
who our any all one""".split())


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


def place(path):
    relative = os.path.relpath(path, ROOT)
    return path if relative.startswith("..") else relative


# ---------------------------------------------------------------- reading


def split_list(text, separator):
    return [item.strip() for item in text.split(separator) if item.strip()]


def read_catalog(path):
    """Every item in the catalog, in the order written. A catalog that cannot be read whole is not searched."""
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        raise Stop("there is no catalog at %s" % place(path))
    except (OSError, UnicodeDecodeError):
        raise Stop("the catalog at %s could not be read" % place(path))
    items, seen = [], set()
    for section in re.split(r"^## ", text, flags=re.M)[1:]:
        heading, _, body = section.partition("\n")
        item_id, colon, title = heading.partition(": ")
        if not colon or not ITEM_ID.fullmatch(item_id.strip()) or not title.strip():
            raise Stop('a heading in the catalog is not "## ID: title": %s. An item that cannot be read could hide a '
                       "duplicate, so nothing is searched" % json.dumps(heading[:60]))
        item_id = item_id.strip()
        if item_id in seen:
            raise Stop("the catalog holds two items with the id %s, so results could not be told apart" % item_id)
        seen.add(item_id)
        item = {"id": item_id, "title": title.strip()}
        lines = body.split("\n")
        rest = 0
        for number, line in enumerate(lines):
            found = re.fullmatch(r"- (\w+): ?(.*)", line.strip())
            if found and found.group(1).lower() in FIELDS:
                if found.group(1).lower() in item:
                    raise Stop("item %s gives its %s twice" % (item_id, found.group(1).lower()))
                item[found.group(1).lower()] = found.group(2).strip()
                rest = number + 1
            elif line.strip() and not found:
                break
        if not item.get("status"):
            raise Stop("item %s has no status, so it is not known whether it is still open" % item_id)
        item["description"] = "\n".join(lines[rest:]).strip()
        item["component"] = item.get("component", "")
        item["team"] = item.get("team", "")
        item["labels"] = split_list(item.get("labels", ""), ",")
        item["sources"] = split_list(item.pop("source", ""), ";")
        item["finished"] = item["status"].lower() in FINISHED
        items.append(item)
    if not items:
        raise Stop("the catalog at %s holds no work item" % place(path))
    return items


def read_proposal(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        raise Stop("there is no proposal file at the path given")
    except ValueError:
        raise Stop("the proposal file is not JSON")
    allowed = {"title", "description", "component", "labels", "sources"}
    if not isinstance(data, dict) or not set(data) <= allowed:
        raise Stop("a proposal has only these names: %s" % ", ".join(sorted(allowed)))
    title = data.get("title")
    if not isinstance(title, str) or not title.strip():
        raise Stop("a proposal needs a title")
    lists = {}
    for name in ("labels", "sources"):
        value = data.get(name) or []
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            raise Stop("in a proposal, %s is a list of text" % name)
        lists[name] = [item.strip() for item in value if item.strip()]
    description, component = data.get("description") or "", data.get("component") or ""
    if not isinstance(description, str) or not isinstance(component, str):
        raise Stop("in a proposal, the description and the component are text")
    return {"id": None, "title": title.strip(), "description": description, "component": component.strip(),
            "labels": lists["labels"], "sources": lists["sources"]}


def sha_of(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


# ---------------------------------------------------------------- comparing


def low(items):
    return set(item.strip().lower() for item in items if item.strip())


def compare(proposal, item, threshold=DESCRIPTION_THRESHOLD):
    """The five signals for one item: {name: (matched, detail)}. matched is True, False or None for 'cannot compare'."""
    signals = {}

    def cannot(which, proposal_has, what):
        signals[which] = (None, "cannot compare: %s has %s" % ("the proposal" if not proposal_has else "the item", what))

    mine, theirs = words(proposal["description"]), words(item["description"])
    if not mine or not theirs:
        cannot("description", mine, "no description")
    else:
        shared, share = overlap(mine, theirs)
        signals["description"] = (len(shared) >= 4 and share >= threshold,
                                  "%s, %d%% of the shorter description's %d (needs %d%%)"
                                  % (count(len(shared), "shared word"), round(share * 100), min(len(mine), len(theirs)), round(threshold * 100)))

    if not proposal["sources"] or not item["sources"]:
        cannot("source", proposal["sources"], "no cited source")
    else:
        shared = sorted(low(proposal["sources"]) & low(item["sources"]))
        documents = sorted(set(s.split("#")[0] for s in low(proposal["sources"])) & set(s.split("#")[0] for s in low(item["sources"])))
        signals["source"] = (bool(shared), "the same item of the same document: " + ", ".join(shared) if shared else
                             "the same document, a different item of it: " + ", ".join(documents) if documents else "no document in common")

    if not proposal["component"] or not item["component"]:
        cannot("component", proposal["component"], "no component")
    else:
        same = proposal["component"].lower() == item["component"].lower()
        signals["component"] = (same, "both %s" % json.dumps(item["component"]) if same else
                                "%s here, %s there" % (json.dumps(proposal["component"]), json.dumps(item["component"])))

    if not proposal["labels"] or not item["labels"]:
        cannot("labels", proposal["labels"], "no label")
    else:
        shared = sorted(low(proposal["labels"]) & low(item["labels"]))
        signals["labels"] = (bool(shared), "shared: " + ", ".join(shared) if shared else "none shared")

    mine, theirs = words(proposal["title"]), words(item["title"])
    shared, share = overlap(mine, theirs)
    signals["title"] = (bool(mine) and (mine == theirs or (len(shared) >= 2 and share >= 0.6)),
                        "%s, %d%% of the shorter title" % (count(len(shared), "shared word"), round(share * 100)))
    return signals


def judge(signals, finished):
    """(matched signals, points, kind, confidence, recommendation). kind is "duplicate", "related" or None."""
    matched = [name for name, _ in WEIGHTS if signals[name][0] is True]
    score = sum(points for name, points in WEIGHTS if name in matched)
    said_the_same = "description" in matched
    backed_up = "source" in matched or "component" in matched
    if said_the_same and backed_up:
        kind = "duplicate"
    elif said_the_same or (len(matched) >= 2 and backed_up):
        kind = "related"
    else:
        return matched, score, None, None, None
    level = next(name for name, least in LEVELS if score >= least)
    advice = "merge" if kind == "duplicate" and level == "high" and not finished else "link"
    return matched, score, kind, level, advice


def why_kind(found):
    """One sentence: why this item is a duplicate, or related, by the rule."""
    matched = found["matched"]
    if found["kind"] == "duplicate":
        backing = " and ".join(name for name in ("source", "component") if name in matched)
        return "the descriptions say the same thing, and the %s %s the same too" % (backing, "are" if " and " in backing else "is")
    if "description" in matched:
        return "the descriptions say the same thing, but neither the source nor the component is the same, so nothing backs it up"
    return ("%s match, but the descriptions do not say the same thing: it is different work in the same place"
            % " and ".join(name for name in matched))


def why_advice(found):
    if found["advice"] == "merge":
        return "Do not create a new item. This is the same work and it is still open. Add anything new to it"
    if found["kind"] == "duplicate" and found["item"]["finished"]:
        return ("This looks like the same work, and it is %s. Look at why before creating. If the new item is still needed, "
                "create it and link the two" % found["item"]["status"].lower())
    if found["kind"] == "duplicate":
        return ("This may be the same work. Look at it before creating. If the new item is still needed, create it and link "
                "the two")
    return "This is different work that touches the same thing. If the new item is created, link the two so that both are seen together"


# ---------------------------------------------------------------- the search


def search(proposal, items, threshold=DESCRIPTION_THRESHOLD):
    matches, dismissed = [], []
    for item in items:
        if proposal.get("id") and item["id"] == proposal["id"]:
            continue
        signals = compare(proposal, item, threshold)
        matched, score, kind, level, advice = judge(signals, item["finished"])
        found = {"item": item, "signals": signals, "matched": matched, "score": score, "kind": kind, "level": level, "advice": advice}
        if kind:
            matches.append(found)
        elif matched:
            dismissed.append(found)
    matches.sort(key=lambda m: (m["kind"] != "duplicate", -m["score"], m["item"]["id"]))
    overall = min((m["advice"] for m in matches), key=ADVICE.index) if matches else "proceed"
    return {"searched": len(items), "matches": matches, "dismissed": dismissed, "overall": overall, "threshold": threshold}


def quote(text):
    return json.dumps(" ".join(str(text).split()), ensure_ascii=False)


def only(found):
    text = "matched on %s only" % " and ".join(found["matched"])
    if found["matched"] == ["title"]:
        return text + ". The title is alike and nothing else is"
    if set(found["matched"]) <= {"title", "labels"}:
        return text + ". Neither says what the work is or where it is"
    return text


def tally(result):
    duplicates = sum(1 for m in result["matches"] if m["kind"] == "duplicate")
    return duplicates, len(result["matches"]) - duplicates


def lines_for(proposal, result, catalog_path):
    """What the search found, as plain lines for the screen."""
    duplicates, related = tally(result)
    out = ["SEARCH FOR EXISTING WORK. Reads one local file, and changes nothing.",
           "Proposed item: %s" % quote(proposal["title"]),
           "  component: %s. labels: %s. sources: %s." % (proposal["component"] or "none", ", ".join(proposal["labels"]) or "none",
                                                           ", ".join(proposal["sources"]) or "none"),
           "Catalog searched: %s, %s." % (place(catalog_path), count(result["searched"], "work item")),
           "Signals and points: %s." % ", ".join("%s %d" % item for item in WEIGHTS),
           "DUPLICATE: the descriptions say the same thing, and the source or the component is the same too.",
           "RELATED:   not a duplicate, and the descriptions say the same thing, or two signals match and one is the source",
           "           or the component.",
           "Strength:  high 9 to %d points, medium 5 to 8, low 1 to 4. Descriptions match at %d%% of the shorter one's words."
           % (TOP, round(result["threshold"] * 100)), ""]
    if not result["matches"]:
        out += ["RESULT: NO MATCH. No item in the catalog is a duplicate of this proposal or related to it.",
                "The closest items are not offered as a guess. Any that matched on something are listed below, with why they",
                "do not count."]
    else:
        out += ["RESULT: %s, %s related." % (count(duplicates, "duplicate"), related)]
    for number, m in enumerate(result["matches"], 1):
        item = m["item"]
        out += ["",
                "Match %d: %s, %s. Status: %s. Team: %s." % (number, m["kind"].upper(), item["id"], item["status"], item["team"] or "not given"),
                "  title: %s" % quote(item["title"]),
                "  why %s: %s." % (m["kind"], why_kind(m)),
                "  strength: %s (%d of %d points, %d of 5 signals matched)" % (m["level"].upper(), m["score"], TOP, len(m["matched"]))]
        for name, points in WEIGHTS:
            state, detail = m["signals"][name]
            out.append("    %-12s %-10s %s" % (name, "MATCHED +%d" % points if state else ("no" if state is False else "-"), detail))
        out += ["  recommendation: %s. %s." % (m["advice"].upper(), why_advice(m))]
    if result["dismissed"]:
        out += ["", "Looked at and NOT reported, because by the rule they are neither duplicates nor related:"]
        out += ["  %s, %s: %s." % (m["item"]["id"], quote(m["item"]["title"]), only(m)) for m in result["dismissed"]]
    out += ["",
            "Overall recommendation: %s." % result["overall"].upper(),
            "This is a recommendation. A person decides whether to merge, link or proceed. The search has created, merged,",
            "linked and changed nothing."]
    return [line.rstrip() for line in out]


def md(text):
    """Text from the catalog or a proposal, made safe to sit in Markdown as plain text on one line."""
    text = " ".join(str(text).split()).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    for ch in "\\`*_[]|#~":
        text = text.replace(ch, "\\" + ch)
    return text


def markdown_for(proposal, result, catalog_path, decision=None, note=None):
    """The same findings as a Markdown report, with the person's decision if one was given."""
    duplicates, related = tally(result)
    out = ["# Search report: existing work for one proposed item", "",
           "> Written by `participant/skills/ba-search-existing-work/search.py`. It reports and recommends. A person",
           "> decides. Titles and words from the catalog are other people's writing, shown as text.", "",
           "## The proposed item", "",
           "- Title: %s" % md(proposal["title"]),
           "- Component: %s" % (md(proposal["component"]) or "none"),
           "- Labels: %s" % (", ".join(md(x) for x in proposal["labels"]) or "none"),
           "- Sources: %s" % (", ".join(md(x) for x in proposal["sources"]) or "none"), "",
           "## How it was searched", "",
           "%s in `%s` were compared on five signals." % (count(result["searched"], "work item").capitalize(), place(catalog_path)), "",
           "| Signal | Points | It matches when |", "|---|---|---|",
           "| Description | 4 | the descriptions share at least %d%% of the shorter one's meaningful words, and at least four |" % round(result["threshold"] * 100),
           "| Source | 3 | both cite the same item of the same source document |",
           "| Component | 2 | both name the same component |",
           "| Labels | 1 | they share at least one label |",
           "| Title | 1 | the titles share at least 60% of the shorter one's meaningful words, and at least two, or are the same |", "",
           "A rule, not the points, decides what an item is to the proposal:", "",
           "- **Duplicate**: the descriptions say the same thing, and the source or the component is the same too.",
           "- **Related**: not a duplicate, and either the descriptions say the same thing with nothing to back it up, or at",
           "  least two signals match and one of them is the source or the component.",
           "- **No match**: anything else. A matching title is never enough.", "",
           "The points say how strongly an item matched, out of %d: **high** 9 to %d, **medium** 5 to 8, **low** 1 to 4." % (TOP, TOP), "",
           "## Result: %s" % ("%s, %d related" % (count(duplicates, "duplicate"), related) if result["matches"] else "no match"), ""]
    if not result["matches"]:
        out += ["No item in the catalog is a duplicate of this proposal or related to it. The closest items are not offered as",
                "a guess.", ""]
    for number, m in enumerate(result["matches"], 1):
        item = m["item"]
        out += ["### Match %d: %s, `%s`" % (number, m["kind"], item["id"]), "",
                "- Title: %s" % md(item["title"]),
                "- Status: %s. Team: %s" % (md(item["status"]), md(item["team"]) or "not given"),
                "- **%s**, because %s." % (m["kind"].capitalize(), why_kind(m)),
                "- **Strength: %s** (%d of %d points, %d of 5 signals matched)" % (m["level"], m["score"], TOP, len(m["matched"])),
                "- **Recommendation: %s.** %s." % (m["advice"], why_advice(m)), "",
                "| Field | Matched | Points | How strongly |", "|---|---|---|---|"]
        for name, points in WEIGHTS:
            state, detail = m["signals"][name]
            out.append("| %s | %s | %s | %s |" % (name.capitalize(), "yes" if state else ("no" if state is False else "not comparable"),
                                                  points if state else 0, md(detail)))
        out.append("")
    out += ["## Looked at and not reported", ""]
    out += ["- `%s`, %s: %s." % (m["item"]["id"], md(m["item"]["title"]), only(m)) for m in result["dismissed"]] or ["No other item matched on any signal."]
    out += ["", "## The search's overall recommendation: %s" % result["overall"], "",
            "The search has created, merged, linked and changed nothing.", "",
            "## The decision", ""]
    if decision:
        out += ["**Decision: %s.**" % decision, "",
                "Made by a person and given to the search with `--decision`. The search did not choose it. The search",
                "recommended %s, which %s the decision." % (result["overall"], "is" if decision == result["overall"] else "is not")]
        if note:
            out += ["", "The person's note: %s" % md(note)]
    else:
        out += ["Not yet decided. A person decides whether to merge, link or proceed, and records it by running the search",
                "again with `--decision`."]
    return "\n".join(out) + "\n"


def related_map(items, threshold=DESCRIPTION_THRESHOLD):
    """Every item against every other. Returns {item id: [(other id, kind), ...]} for items with any match."""
    found = {}
    for item in items:
        result = search(item, items, threshold)
        if result["matches"]:
            found[item["id"]] = [(m["item"]["id"], m["kind"]) for m in result["matches"]]
    return found


def map_lines(items, catalog_path, threshold):
    found = related_map(items, threshold)
    several = {key: value for key, value in found.items() if len(value) >= 2}
    titles = {item["id"]: item["title"] for item in items}
    out = ["RELATED MAP. Every item in the catalog compared with every other. Reads one local file, and changes nothing.",
           "Catalog: %s, %s. %d of them match at least one other." % (place(catalog_path), count(len(items), "work item"), len(found)), "",
           "Items that are related to, or duplicates of, TWO OR MORE others: %d." % len(several)]
    for key in sorted(several, key=lambda k: (-len(several[k]), k)):
        out.append("  %s, %s: %s" % (key, quote(titles[key]), "; ".join("%s (%s)" % pair for pair in several[key])))
    pairs = sorted(set(tuple(sorted((key, other))) + (kind,) for key, value in found.items() for other, kind in value if kind == "duplicate"))
    out += ["", "Pairs already in the catalog that are duplicates of each other by the rule: %d." % len(pairs)]
    out += ["  %s and %s" % (a, b) for a, b, _ in pairs]
    out += ["", "This is a list for a person to read. Nothing has been merged, linked or changed."]
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description="Search a local catalog of work for duplicates of, and work related to, a proposed item.")
    parser.add_argument("--proposal", help="the JSON file describing the proposed item")
    parser.add_argument("--related-map", action="store_true", help="compare every catalog item with every other instead")
    parser.add_argument("--catalog", default=DEFAULT_CATALOG, help="the catalog, one Markdown file")
    parser.add_argument("--report", help="also write the findings here, as Markdown")
    parser.add_argument("--decision", choices=ADVICE, help="the decision a person has made, to record in the report")
    parser.add_argument("--decision-note", help="the person's reason, to record with the decision")
    parser.add_argument("--description-threshold", type=int, metavar="N",
                        help="the share of the shorter description's words that must be shared, as a whole number from 10 to 100. The default is 50")
    args = parser.parse_args(argv)
    catalog = os.path.abspath(args.catalog)
    try:
        if bool(args.proposal) == args.related_map:
            raise Stop("give either --proposal FILE or --related-map")
        if (args.decision or args.decision_note) and not args.report:
            raise Stop("a decision is recorded in a report, so --decision needs --report")
        if args.decision_note and not args.decision:
            raise Stop("a note goes with a decision, so --decision-note needs --decision")
        if args.description_threshold is not None and not 10 <= args.description_threshold <= 100:
            raise Stop("--description-threshold is a whole number from 10 to 100")
        threshold = args.description_threshold / 100 if args.description_threshold is not None else DESCRIPTION_THRESHOLD
        if args.report and os.path.exists(args.report) and os.path.samefile(args.report, catalog):
            raise Stop("the report cannot be written over the catalog, which the search does not change")
        proposal = read_proposal(args.proposal) if args.proposal else None
        before = sha_of(catalog) if os.path.isfile(catalog) else None
        items = read_catalog(catalog)
        if proposal:
            result = search(proposal, items, threshold)
            lines = lines_for(proposal, result, catalog)
        else:
            lines = map_lines(items, catalog, threshold)
        after = sha_of(catalog)
    except Stop as stop:
        print("STOPPED: %s." % stop)
        print("Nothing was searched and nothing was changed.")
        return 2
    print("\n".join(lines))
    print("")
    if after != before:
        print("WARNING: the catalog is not as it was before the search.")
        return 2
    print("Catalog after the search: unchanged. SHA-256 before and after: %s" % before)
    if args.report:
        os.makedirs(os.path.dirname(os.path.abspath(args.report)), exist_ok=True)
        with open(args.report, "w", encoding="utf-8") as f:
            f.write(markdown_for(proposal, result, catalog, args.decision, args.decision_note))
        print("Report written: %s%s" % (place(os.path.abspath(args.report)),
                                        ", with the person's decision: %s" % args.decision if args.decision else ", with no decision yet"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
