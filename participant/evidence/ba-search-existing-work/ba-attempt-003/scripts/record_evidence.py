#!/usr/bin/env python3
"""Records logs/search-run.txt for the ba-search-existing-work quest.

Each block between dashed lines is what a command printed. Every command is
started as a person would start it. Only local files are used: no tracker is
contacted, and every work item, team and source in the catalog is made up.

Parts 1 to 6 run on the catalog in the repository,
participant/context/search/catalog.md, and write nothing there. Part 7 spoils
a catalog, so it runs on a copy in a temporary folder, shown as COPY.

This script checks for itself. It counts the catalog's sections and takes the
catalog's SHA-256 before the first search and after the last, rather than
taking the search's word that nothing changed.

Run from anywhere:  python3 scripts/record_evidence.py
Exit code 0 if every check came out as expected, 1 if not.
"""
import hashlib
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ATTEMPT = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(ATTEMPT, "..", "..", "..", ".."))
SEARCH = "participant/skills/ba-search-existing-work/search.py"
BASE = "participant/context/search"
CATALOG = BASE + "/catalog.md"
REPORT = BASE + "/report.md"
DUPLICATE, NO_MATCH = BASE + "/proposals/1-duplicate.json", BASE + "/proposals/2-no-match.json"


class Log:
    def __init__(self):
        self.lines, self.problems, self.copy = [], [], None

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

    def command(self, *args, show=True):
        done = subprocess.run([sys.executable, SEARCH] + list(args), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        text = self.tidy(done.stdout.rstrip("\n"))
        if show:
            self.out("$ python3 %s %s" % (SEARCH, self.tidy(" ".join(args))))
            self.lines += ["-" * 78, text, "-" * 78, "exit code: %d" % done.returncode]
        return done.returncode, text


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def matches(text):
    """{item id: (kind, the lines of that match)} from what a search printed."""
    found = {}
    for block in re.split(r"\n(?=Match \d+: )", text.split("\nLooked at and NOT")[0].split("\nOverall recommendation")[0])[1:]:
        kind, item = re.match(r"Match \d+: (\w+), ([\w-]+)\.", block).groups()
        found[item] = (kind, block)
    return found


def main():
    os.chdir(ROOT)
    log = Log()
    log.out("The search for existing work: ba-search-existing-work, attempt ba-attempt-003")
    log.out("Recorded by scripts/record_evidence.py. Local files only. No tracker was contacted. Every work item is made up.")

    log.part("PART 1. The catalog: %s." % CATALOG)
    with open(CATALOG, encoding="utf-8") as f:
        catalog = f.read()
    sections = re.findall(r"^## ([A-Z]+-\d+): ", catalog, re.M)
    before = sha(CATALOG)
    log.out("  Counted by this script: %d sections, each one work item. %d different ids." % (len(sections), len(set(sections))))
    log.out("  SHA-256 taken by this script before any search: %s" % before)
    log.check("the catalog holds at least fifteen work items: %d" % len(sections), len(sections) >= 15 and len(set(sections)) == len(sections))
    log.check("it holds the true duplicate (WRK-101), the near duplicate (WRK-106), related items (WRK-102, 103, 104) and an item "
              "with nearly the proposal's title for different work (WRK-105)", {"WRK-%d" % n for n in range(101, 107)} <= set(sections))

    log.part("PART 2. A proposed duplicate. (criteria 1, 2, 3, 5, 7)")
    code, text = log.command("--proposal", DUPLICATE)
    found = matches(text)
    true = found.get("WRK-101", ("", ""))
    log.check("the search ran: exit code 0", code == 0)
    log.check("criterion 3: the true duplicate, WRK-101, is found and labelled DUPLICATE, first of the matches", list(found)[:1] == ["WRK-101"] and true[0] == "DUPLICATE")
    log.check("its title shares no meaningful word with the proposal's: the title line says no, 0 shared words",
              bool(re.search(r"^    title +no +0 shared words", true[1], re.M)))
    log.check("criterion 1: it was matched on more than the title: description, source, component and labels",
              len(re.findall(r"^    (description|source|component|labels) +MATCHED", true[1], re.M)) == 4)
    log.check("criterion 2: every match lists all five fields, each MATCHED with its points or not, and how strongly",
              len(found) == 5 and all(len(re.findall(r"^    (?:description|source|component|labels|title) +(?:MATCHED \+\d|no|-) +\S", block, re.M)) == 5
                                      and re.search(r"strength: (HIGH|MEDIUM|LOW) \(\d+ of 11 points", block) for _, block in found.values()))
    log.check("how strongly a description matched is a number: 96% for the true duplicate, 48% for WRK-102, which needs 50%",
              "96% of the shorter description" in true[1] and "48% of the shorter description" in found.get("WRK-102", ("", ""))[1])
    log.check("criterion 3: the related items, WRK-102, WRK-103 and WRK-104, are each labelled RELATED, not duplicate",
              [found.get(item, ("",))[0] for item in ("WRK-102", "WRK-103", "WRK-104")] == ["RELATED"] * 3)
    log.check("criterion 7: each match says why it is that kind, by the rule", all(re.search(r"^  why (duplicate|related): .+\.$", block, re.M) for _, block in found.values()))
    log.check("the near duplicate, WRK-106, is a DUPLICATE of MEDIUM strength, and is cancelled, so it is LINK and not merge",
              found.get("WRK-106", ("",))[0] == "DUPLICATE" and "strength: MEDIUM" in found["WRK-106"][1] and "recommendation: LINK." in found["WRK-106"][1])
    words = set(re.findall(r"recommendation: ([A-Z]+)\.", text))
    log.check("criterion 5: the recommendations given are among merge, link and proceed: %s" % ", ".join(sorted(words)), words == {"MERGE", "LINK"})
    log.check("criterion 5: only the open, high-strength duplicate is MERGE, and the related items are all LINK",
              "recommendation: MERGE." in true[1] and all("recommendation: LINK." in block for kind, block in found.values() if kind == "RELATED"))
    log.check("criterion 5: the search says a person decides", "A person decides whether to merge, link or proceed." in text)
    log.check("the item with nearly the same title, WRK-105, is not a match: the title is alike and nothing else is",
              "WRK-105" not in found and bool(re.search(r'WRK-105, "Export the customer list": matched on title only\.', text)))
    log.check("the item whose text gives orders, WRK-116, is not obeyed: the result is not 'proceed', and it matched on component only",
              "Overall recommendation: MERGE." in text and bool(re.search(r"WRK-116, .*: matched on component only\.", text)))

    log.part("PART 3. A proposed new item with no match. (criterion 4)")
    code, text = log.command("--proposal", NO_MATCH)
    log.check("the search ran: exit code 0", code == 0)
    log.check("it reports no match, in those words", "RESULT: NO MATCH. No item in the catalog is a duplicate of this proposal or related to it." in text)
    log.check("it does not offer the closest item as a guess: no match is listed, and no catalog item is named at all",
              not matches(text) and "WRK-" not in text and "The closest items are not offered as a guess." in text)
    log.check("all %d items were compared" % len(sections), "%d work items." % len(sections) in text)
    log.check("the overall recommendation is PROCEED", "Overall recommendation: PROCEED." in text)

    log.part("PART 4. The catalog is unchanged. (criterion 6)")
    after = sha(CATALOG)
    log.out("  SHA-256 taken again by this script after the searches: %s" % after)
    with open(CATALOG, encoding="utf-8") as f:
        log.check("the catalog has the SHA-256 it had before the first search, and is the same text", after == before and f.read() == catalog)
    log.check("each search printed that same SHA-256 as its own before-and-after", "SHA-256 before and after: %s" % before in text)
    log.check("no file was added beside the catalog by the searches", sorted(os.listdir(BASE)) == sorted(set(os.listdir(BASE)) | {"catalog.md", "proposals"}))

    log.part("PART 5. The first stretch goal: the description threshold, and its effect on this catalog.")
    log.out("The same proposed duplicate, searched at six thresholds. 50% is the one used everywhere else.")
    log.out("")
    log.out("  threshold   WRK-101          WRK-106          WRK-102          WRK-103   WRK-104   duplicates  related")
    table = {}
    for percent in (30, 45, 50, 60, 80, 90):
        _, text = log.command("--proposal", DUPLICATE, "--description-threshold", str(percent), show=False)
        found = matches(text)
        kinds = {item: found.get(item, ("no match",))[0].lower() for item in ("WRK-101", "WRK-106", "WRK-102", "WRK-103", "WRK-104")}
        table[percent] = kinds
        log.out("  %-11s %-16s %-16s %-16s %-9s %-9s %-11d %d" % ("%d%%" % percent, kinds["WRK-101"], kinds["WRK-106"], kinds["WRK-102"],
                                                                 kinds["WRK-103"], kinds["WRK-104"],
                                                                 sum(1 for k, _ in found.values() if k == "DUPLICATE"),
                                                                 sum(1 for k, _ in found.values() if k == "RELATED")))
    log.out("")
    log.check("the true duplicate is a duplicate at every threshold tried", all(table[p]["WRK-101"] == "duplicate" for p in table))
    log.check("lowered to 45%, the borderline item WRK-102 (48%) turns from related into a duplicate: a false duplicate",
              table[50]["WRK-102"] == "related" and table[45]["WRK-102"] == "duplicate")
    log.check("raised to 90%, the near duplicate WRK-106 (83%) turns from a duplicate into related: a missed one",
              table[80]["WRK-106"] == "duplicate" and table[90]["WRK-106"] == "related")
    log.check("the items that are related for other reasons, WRK-103 and WRK-104, do not move",
              all(table[p]["WRK-103"] == "related" and table[p]["WRK-104"] == "related" for p in table))

    log.part("PART 6. The second stretch goal: items in the catalog that are related to several others.")
    code, text = log.command("--related-map")
    log.check("the map ran and changed nothing: exit code 0, and the catalog's SHA-256 is still the same", code == 0 and sha(CATALOG) == before)
    log.check("three items match two or more others", "TWO OR MORE others: 3." in text)
    log.check("it shows the catalog already holds the same work twice: WRK-101 and WRK-106", "WRK-101 and WRK-106" in text)

    with tempfile.TemporaryDirectory() as tmp:
        log.copy = os.path.realpath(tmp)
        copy = os.path.join(log.copy, "catalog.md")
        log.part("PART 7. On a copy: a catalog that cannot be read whole is not searched.")
        with open(copy, "w", encoding="utf-8") as f:
            f.write(catalog + "\n## WRK-101: A second item with an id already used\n\n- Status: open\n\nSomething else.\n")
        log.out("A copy of the catalog was given a second item with the id WRK-101.")
        code, text = log.command("--proposal", DUPLICATE, "--catalog", copy)
        log.check("the search stopped rather than guess: exit code 2", code == 2 and "two items with the id WRK-101" in text and "Nothing was searched" in text)
        log.copy = None

    log.part("AFTERWARDS. The report in the repository, %s." % REPORT)
    if os.path.exists(REPORT):
        with open(REPORT, encoding="utf-8") as f:
            report = f.read()
        parts = report.split("\n### Match ")[1:]
        log.out("  The report was written by the participant's own run of the search, with their decision given as --decision.")
        log.check("it holds %d matches for the one proposed item" % len(parts), len(parts) >= 1)
        log.check("each match lists the five fields, whether each matched, and how strongly",
                  all(len(re.findall(r"^\| (?:Description|Source|Component|Labels|Title) \| (?:yes|no|not comparable) \| \d \| .+ \|$", part, re.M)) == 5 for part in parts))
        log.check("each match has a strength of high, medium or low, with its points out of 11",
                  all(re.search(r"\*\*Strength: (high|medium|low)\*\* \(\d+ of 11 points", part) for part in parts))
        log.check("each recommendation is merge, link or proceed", all(re.search(r"\*\*Recommendation: (merge|link|proceed)\.\*\*", part) for part in parts))
        decided = re.search(r"^\*\*Decision: (merge|link|proceed)\.\*\*$", report, re.M)
        log.check("a person's decision is recorded: %s" % (decided.group(1) if decided else "NONE YET"), bool(decided))
        log.check("the catalog is still as it was before the first search", sha(CATALOG) == before)
    else:
        log.out("  There is no report yet. The participant writes it with their own run of the search, giving their decision.")
        log.check("the report exists", False)

    count = sum(1 for line in log.lines if re.match(r"  (ok  |FAIL) ", line))
    log.out()
    log.out("RESULT: %s" % ("ALL CHECKS PASSED. %d checks." % count if not log.problems else "%d OF %d CHECKS FAILED." % (len(log.problems), count)))
    os.makedirs(os.path.join(ATTEMPT, "logs"), exist_ok=True)
    with open(os.path.join(ATTEMPT, "logs", "search-run.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(log.lines) + "\n")
    print(log.lines[-1])
    for problem in log.problems:
        print("  FAILED: " + problem)
    return 0 if not log.problems else 1


if __name__ == "__main__":
    sys.exit(main())
