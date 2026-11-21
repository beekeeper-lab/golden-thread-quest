#!/usr/bin/env python3
"""Records logs/review-run.txt for the ba-detect-ambiguity quest.

Each block between dashed lines is what the checker printed, started as a
person would start it. Only local files are read. The requirements set is
made up.

What this script can and cannot record. The review itself, deciding which
words fail and why, was done by an assistant reading the requirements, and
is in participant/context/ambiguity/findings.md. No script made those
judgments. This script records four things about them:

  1  the checker run on the findings, which prints every finding and every
     requirement left unflagged with the reason it is sound;
  2  the checker refusing copies of the findings that have been spoiled;
  3  the findings set beside the answer key of the separate assistant that
     wrote the requirements, which the reviewer opened only after the review;
  4  the types that independent readers gave the findings when the types
     had been removed.

Parts 3 and 4 are worked out here from the files in review/, by this
script's own reading of them.

Run from anywhere:  python3 scripts/record_evidence.py
Exit code 0 if every check came out as expected, 1 if not.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ATTEMPT = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(ATTEMPT, "..", "..", "..", ".."))
REL = os.path.relpath(ATTEMPT, ROOT)
CHECK = "participant/skills/requirements-review/check.py"
REQUIREMENTS = "participant/context/ambiguity/requirements.md"
FINDINGS = "participant/context/ambiguity/findings.md"
TYPES = ("contradictory", "untestable", "incomplete", "vague")
LINES, PROBLEMS = [], []


def out(text=""):
    LINES.append(text)


def part(text):
    LINES.extend(["", "=" * 78, text])


def check(label, ok):
    LINES.append("  %-4s %s" % ("ok" if ok else "FAIL", label))
    if not ok:
        PROBLEMS.append(label)


def run(*args, hide=None):
    shown = " ".join(args).replace(hide, "COPY") if hide else " ".join(args)
    out("$ python3 %s %s" % (CHECK, shown))
    done = subprocess.run([sys.executable, CHECK] + list(args), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    text = done.stdout.rstrip("\n").replace(hide, "COPY") if hide else done.stdout.rstrip("\n")
    LINES.extend(["-" * 78, text, "-" * 78, "exit code: %d" % done.returncode])
    return done.returncode, text


def review_types():
    """{finding: (requirements, type)} read from findings.md by this script."""
    with open(FINDINGS, encoding="utf-8") as f:
        text = f.read()
    found = {}
    for block in re.split(r"\n## (?=F-\d+)", text.split("\n## Unflagged")[0])[1:]:
        name = block.split("\n")[0].strip()
        reqs = re.findall(r"(?:REQ|NFR)-\d+", re.search(r"- Requirement: (.*)", block).group(1))
        found[name] = (reqs, re.search(r"- Type: (\w+)", block).group(1))
    unflagged = re.findall(r"^- ((?:REQ|NFR)-\d+): ", text.split("\n## Unflagged")[1].split("\n## ")[0], re.M)
    return found, unflagged


def key_intent():
    """{requirement: (SOUND or DEFECTIVE, type or None, trap?)} read from the author's answer key."""
    with open(os.path.join(REL, "review", "answer-key.md"), encoding="utf-8") as f:
        text = f.read()
    found = {}
    for req, verdict, rest in re.findall(r"^### ((?:REQ|NFR)-\d+): (SOUND|DEFECTIVE)(.*)$", text, re.M):
        kind = re.search(r"(CONTRADICTORY|UNTESTABLE|INCOMPLETE|VAGUE)", rest)
        found[req] = (verdict, kind.group(1).lower() if kind else None, "TRAP" in rest)
    return found


def reader_types(name):
    """{finding: (type, how it was reached)} as an independent reader gave it, read from a table in review/."""
    path = os.path.join(REL, "review", name)
    if not os.path.exists(path):
        return None
    found = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            cells = [cell.strip().lower() for cell in line.split("|")]
            if len(cells) > 4 and re.fullmatch(r"f-\d+", cells[1]):
                given = [cell for cell in cells[2:] if cell in TYPES or cell.startswith("not settled")]
                last = cells[-2]
                how = "not settled" if last.startswith("not settled") else "assumed" if last.startswith("assumed") else \
                    "settled" if last.startswith("settled") else "-"
                found[cells[1].upper()] = (given[0] if given else "?", how)
    return found


def main():
    os.chdir(ROOT)
    os.makedirs(REL + "/logs", exist_ok=True)
    out("Running the review, and the requirements it left unflagged: ba-detect-ambiguity, attempt ba-attempt-002")
    out("Recorded by scripts/record_evidence.py. Each block between dashed lines is what the checker printed.")
    out("Only local files are read. The requirements set is made up, so nothing is redacted.")
    out("The judgments in the review were made by an assistant reading the requirements. No script made them.")

    part("PART 1. The review as it stands: every finding, and every requirement left unflagged with why it is sound.")
    code, text = run()
    findings, unflagged = review_types()
    check("the review keeps all seven of its rules, exit code 0", code == 0 and "RESULT: THE REVIEW KEEPS ALL ITS RULES." in text)
    check("each of the %d findings names one of the four types (criterion 1)" % len(findings), all(kind in TYPES for _, kind in findings.values()))
    check("all four types are used: %s" % ", ".join("%s %d" % (t, sum(1 for _, k in findings.values() if k == t)) for t in TYPES),
          all(any(k == t for _, k in findings.values()) for t in TYPES))
    check("the two contradictions each cite two requirements, and one of them spans the two documents (criterion 4)",
          sorted(sorted(r) for r, k in findings.values() if k == "contradictory") == [["NFR-04", "REQ-14"], ["REQ-04", "REQ-12"]])
    check("%d requirements are listed as unflagged, each with a reason (criterion 5)" % len(unflagged), len(unflagged) == 10
          and all(re.search(r"^  %s +\S.{20,}" % r, text, re.M) for r in unflagged))
    check("every one of the 20 requirements is accounted for exactly once", "10 with a finding + 10 unflagged = 20 of 20 requirements." in text)
    check("every finding asks a question", text.count("        asks: ") == len(findings) and all(line.rstrip().endswith("?") for line in text.split("\n") if line.startswith("        asks: ")))

    part("PART 2. The checker refusing a review that breaks a rule.\n"
         "Each time, one thing is changed in a copy of the findings in a temporary folder, shown as COPY.")
    with open(FINDINGS, encoding="utf-8") as f:
        good = f.read()
    spoiled = [
        ("a quoted word is changed, so the words quoted are no longer in the requirement", '- Words: "shortly before"', '- Words: "soon before"', "rule 2: F-05 quotes words that are not in REQ-06"),
        ("a finding's question is replaced by wording for the requirement", "- Question: How long before a booking's start time is the reminder email to be sent?",
         "- Question: It should read 30 minutes before the start. Agreed?", "rule 6: F-05 offers wording in place of a question"),
        ("a sound requirement is dropped from the unflagged list", "- REQ-07: the five things", "- the five things", "REQ-07 has no finding and is not listed as unflagged"),
        ("a contradiction names only one of its two requirements", "- Requirement: REQ-14 and NFR-04", "- Requirement: REQ-14", "rule 4: F-02 is a contradiction and names 1 requirement"),
        ("a finding is given two types at once", "- Type: vague\n- Words: \"shortly before\"", "- Type: vague or incomplete\n- Words: \"shortly before\"", "rule 1: F-05 does not name one of the four types"),
    ]
    with tempfile.TemporaryDirectory() as tmp:
        for what, old, new, expect in spoiled:
            path = os.path.join(tmp, "findings.md")
            with open(path, "w", encoding="utf-8") as f:
                f.write(good.replace(old, new, 1))
            out("")
            out("Changed: %s." % what)
            done = subprocess.run([sys.executable, CHECK, "--findings", path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            said = [line.strip() for line in done.stdout.split("\n") if line.strip().startswith("rule ")]
            LINES.extend(["    " + line for line in said] + ["    exit code: %d" % done.returncode])
            check("refused, naming the rule", old in good and done.returncode == 1 and any(expect in line for line in said))

    part("PART 3. The findings beside the author's answer key.\n"
         "The requirements were written by a separate assistant, which also wrote a key saying which it meant to be\n"
         "sound and which defective. The reviewer wrote down a first pass and a second look before opening it.\n"
         "The key is in review/answer-key.md. This table is worked out by this script from the two files.")
    key = key_intent()
    by_req = {}
    for name, (reqs, kind) in findings.items():
        for req in reqs:
            by_req.setdefault(req, []).append((name, kind))
    out("  %-7s %-26s %s" % ("", "the author meant", "the review"))
    planted = agreed = traps = traps_left = 0
    extra, missed = [], []
    for req in sorted(key, key=lambda r: (r[:3] == "NFR", int(r.split("-")[1]))):
        verdict, kind, trap = key[req]
        mine = by_req.get(req, [])
        out("  %-7s %-26s %s" % (req, ("sound, a trap" if trap else "sound") if verdict == "SOUND" else "defective, " + kind,
                                 "unflagged" if not mine else "; ".join("%s %s" % item for item in mine)))
        if verdict == "DEFECTIVE":
            planted += 1
            agreed += 1 if any(k == kind for _, k in mine) else 0
            if not mine:
                missed.append(req)
            extra += [(n, req, k) for n, k in mine if k != kind]
        else:
            traps += 1 if trap else 0
            traps_left += 1 if trap and not mine else 0
            extra += [(n, req, k) for n, k in mine]
    out("")
    check("the key covers all 20 requirements: %d meant as defective and %d as sound" % (planted, len(key) - planted), len(key) == 20)
    check("every requirement the author meant as defective has a finding of the same type: %d of %d" % (agreed, planted), agreed == planted and not missed)
    check("every trap, a sound requirement made to look suspicious, was left unflagged: %d of %d" % (traps_left, traps), traps_left == traps and traps > 0)
    out("  Findings the author did not plant: %s." % ("; ".join("%s on %s (%s)" % item for item in sorted(set(extra))) or "none"))
    check("there is one, F-09 on REQ-13, and it is listed and not hidden", sorted(set(req for _, req, _ in extra)) == ["REQ-13"])
    check("every requirement the author meant as sound is unflagged: %d of %d" % (sum(1 for r in key if key[r][0] == "SOUND" and r not in by_req), len(key) - planted),
          all(r not in by_req for r in key if key[r][0] == "SOUND"))
    out("  The review as first handed in had a second finding the author did not plant: F-11 on NFR-01, which the")
    out("  author meant as sound. It was withdrawn after review, because its type could not be reproduced. Part 4")
    out("  has the record of that.")
    out("  The author, the reviewer and the independent readers are assistants of the same kind. Agreement between")
    out("  them shows the review is consistent. It does not show the review is right.")

    part("PART 4. The types given by independent readers (criterion 7).\n"
         "Each was a fresh assistant given the requirements and the findings with the Type, Also considered and\n"
         "Effort lines removed, and nothing else. Their reports, and the file each was given, are in review/.\n"
         "This table is worked out by this script from those reports and from findings.md.")
    WITHDRAWN = {"F-11": "incomplete"}  # the type the review gave it before it was withdrawn
    earlier = dict({name: kind for name, (_, kind) in findings.items()}, **WITHDRAWN)
    names = sorted(earlier, key=lambda n: int(n.split("-")[1]))
    files = ["independent-read.md", "independent-read-2.md", "independent-read-3.md", "independent-read-4.md", "independent-read-5.md"]
    readers = [reader_types(name) for name in files]
    out("  s = settled by the written words alone. a = reached by assuming something unwritten. n = not settled.")
    out("  %-6s %-24s %-14s %-17s %-17s %-17s %s" % ("", "the review", "reader 1", "reader 2", "reader 3", "reader 4", "reader 5"))
    for name in names:
        cells = []
        for number, reader in enumerate(readers):
            if reader is None:
                cells.append("(not run)")
            elif name not in reader:
                cells.append("not given")
            else:
                kind, how = reader[name]
                cells.append(kind if number == 0 else "not settled" if kind.startswith("not settled") else "%s, %s" % (kind, how[0]))
        out("  %-6s %-24s %-14s %-17s %-17s %-17s %s" % (name, earlier[name] + (", withdrawn" if name in WITHDRAWN else ""), cells[0], cells[1], cells[2], cells[3], cells[4]))
    out("")
    out("  Reader 1 had the definitions as first agreed and was free to fill gaps. It matched all ten, and said five")
    out("  were close calls settled by three assumptions of its own. Those were written into the definitions.")
    out("  Readers 2 to 5 were told to assume nothing and to say so when the written words did not decide a case.")
    notes = {1: "Given the three clarifications.",
             2: "Given two more sentences, added to settle F-11. They did not settle it.",
             3: "Given a rule the reviewer of the first hand-in suggested. F-11 matched, by an assumption, and F-06 came unsettled.",
             4: "Given the definitions reader 3 had, and nine findings: the rule was taken out again and F-11 withdrawn."}
    for number in (1, 2, 3, 4):
        reader = readers[number]
        if reader is None:
            continue
        given = [name for name in names if name in reader]
        same = [name for name in given if reader[name][0] == earlier[name]]
        hows = [reader[name][1] for name in given]
        out("")
        out("  Reader %d. %s" % (number + 1, notes[number]))
        out("  It gave %d of %d findings the review's type: %d settled, %d by an assumption, %d not settled."
            % (len(same), len(given), hows.count("settled"), hows.count("assumed"), hows.count("not settled")))
        for name in given:
            if name not in same:
                out("  NOT REPRODUCED by reader %d: %s. The review says %s. The reader says: %s." % (number + 1, name, earlier[name], reader[name][0]))
        check("reader %d's report has a row for every finding it was given, and the rows are compared as written" % (number + 1),
              sorted(given) == sorted(name for name in names if number < 4 or name not in WITHDRAWN))
    last = readers[4]
    out("")
    if last is None:
        out("  Reader 5 has not been run. WHETHER THE NINE TYPES CAN BE REPRODUCED IS NOT YET SHOWN.")
        PROBLEMS.append("reader 5 not run")
    else:
        same = [name for name in findings if last.get(name, ("",))[0] == findings[name][1]]
        check("reader 5 was given the findings file as it now stands, nine findings, and gave every one the review's type: %d of %d"
              % (len(same), len(findings)), len(same) == len(findings) and sorted(last) == sorted(findings))
        hows = [last[name][1] for name in findings if name in last]
        out("  Of those, %d were settled by the written words alone and %d by an assumption, which the findings file names"
            % (hows.count("settled"), hows.count("assumed")))
        out("  as a judgment the definitions leave open.")
    out("")
    out("RESULT: %s" % ("%d CHECK(S) FAILED" % len(PROBLEMS) if PROBLEMS else
                        "ALL CHECKS PASSED."))
    with open(os.path.join(REL, "logs", "review-run.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(LINES) + "\n")
    print("review-run.txt: %s" % LINES[-1])
    return 1 if PROBLEMS else 0


if __name__ == "__main__":
    sys.exit(main())
