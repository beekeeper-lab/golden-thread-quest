#!/usr/bin/env python3
"""Checks a findings file against the requirements it reviews, and prints the review.

    check.py [--requirements FILE] [--findings FILE]

A review of what words mean is a person's judgment, or an assistant's. This
script does not make that judgment and cannot. What it does is hold the
written review to its own rules, so that a finding cannot be loose in the
ways the quest forbids:

  1  every finding names exactly one of the four types: vague, incomplete,
     contradictory, untestable;
  2  the words a finding quotes are really in the requirement it names,
     character for character;
  3  every finding says what a tester could not decide, and what would go
     wrong if its question went unanswered;
  4  a contradiction names two requirements and quotes words from both;
  5  every requirement is accounted for exactly once: it has at least one
     finding, or it is listed as unflagged with a reason, and never both;
  6  a finding asks a question and offers no replacement wording;
  7  the findings file carries the definitions and the order they are applied
     in, so that the types can be reproduced from the file alone.

It then prints each finding in one line, and each unflagged requirement with
the reason it was left alone.

The requirements file is read for identifiers written as REQ-01 or NFR-01 at
the start of a line, optionally in bold. A requirement's text runs to the
next identifier or heading.

The findings file has one section for each finding:

    ## F-01
    - Requirement: REQ-03
    - Type: vague
    - Words: "quickly"
    - A tester could not decide: ...
    - If unanswered: ...
    - Question: ...?

For a contradiction the Requirement line names two, joined by "and", and
there is a Words line for each:

    - Requirement: REQ-04 and NFR-02
    - Words in REQ-04: "..."
    - Words in NFR-02: "..."

Under "## Unflagged" is one line for each requirement left alone:

    - REQ-01: the reason it is sound

It reads two local files and writes none.

Exit codes: 0 the review keeps all its rules; 1 it breaks one, named in the output; 2 a file could not be read.
"""
import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
DEFAULT_REQUIREMENTS = os.path.join(ROOT, "participant", "context", "ambiguity", "requirements.md")
DEFAULT_FINDINGS = os.path.join(ROOT, "participant", "context", "ambiguity", "findings.md")
TYPES = ("contradictory", "untestable", "incomplete", "vague")
ID = r"(?:REQ|NFR)-\d+"
REWRITES = ("should read", "should say", "should be reworded", "reword", "rewrite", "replace with", "change to", "suggested wording",
            "better wording", "instead say", "for example:")


class Stop(Exception):
    """A file could not be used. The message says why."""


def place(path):
    relative = os.path.relpath(path, ROOT)
    return path if relative.startswith("..") else relative


def squeeze(text):
    return " ".join(text.split())


def read_requirements(path):
    """{identifier: text} in the order they appear."""
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.read().split("\n")
    except OSError:
        raise Stop("the requirements file could not be read: %s" % place(path))
    found, current = {}, None
    for line in lines:
        start = re.match(r"\s*(?:[-*]\s+)?(?:\*\*)?(%s)(?:\*\*)?[.:)]?\s*(?:\*\*)?\s*(.*)" % ID, line)
        if start and not line.lstrip().startswith(("#", "|")):
            current = start.group(1)
            if current in found:
                raise Stop("the requirements file has two requirements called %s" % current)
            found[current] = start.group(2)
        elif line.startswith("#") or not line.strip():
            current = None if line.startswith("#") else current
        elif current:
            found[current] += " " + line.strip()
    if not found:
        raise Stop("no requirement identifiers such as REQ-01 were found in %s" % place(path))
    return {key: squeeze(value.replace("**", "")) for key, value in found.items()}


def quoted(text):
    """The text inside the first pair of straight double quotes, or None."""
    match = re.match(r'\s*"(.*)"\s*$', text)
    return match.group(1) if match else None


def read_findings(path):
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        raise Stop("the findings file could not be read: %s" % place(path))
    findings, unflagged, section, current = [], [], None, None
    for line in text.split("\n"):
        if line.startswith("## "):
            title = line[3:].strip()
            current = None
            if re.fullmatch(r"F-\d+\b.*", title):
                section, current = "finding", {"name": title.split()[0], "lines": {}, "words": {}, "extra": []}
                findings.append(current)
            else:
                section = "unflagged" if title.lower().startswith("unflagged") else "other"
        elif section == "finding" and line.startswith("- "):
            label, colon, value = line[2:].partition(": ")
            words = re.fullmatch(r"Words(?: in (%s))?" % ID, label)
            if not colon:
                current["extra"].append(line)
            elif words:
                current["words"].setdefault(words.group(1) or "", []).append(value)
            else:
                current["lines"][label] = value.strip()
        elif section == "unflagged" and line.startswith("- "):
            match = re.match(r"- (%s): (.+)" % ID, line)
            unflagged.append((match.group(1), match.group(2).strip()) if match else (None, line))
    return text, findings, unflagged


def check(requirements, text, findings, unflagged):
    """Every way the review breaks its own rules, as (rule number, what is wrong)."""
    problems = []
    flagged = {}
    lower = text.lower()
    for word in TYPES:
        if not re.search(r"\*\*%s\b" % word, lower):
            problems.append((7, "the findings file does not define the type '%s'" % word))
    order = [lower.find("**%s" % word) for word in TYPES]
    if all(position >= 0 for position in order) and order != sorted(order):
        problems.append((7, "the definitions are not given in the order they are applied: %s" % ", ".join(TYPES)))
    if not findings:
        problems.append((1, "the findings file holds no findings"))
    seen = set()
    for finding in findings:
        name, lines = finding["name"], finding["lines"]
        if name in seen:
            problems.append((1, "%s appears twice" % name))
        seen.add(name)
        kind = lines.get("Type", "")
        if kind not in TYPES:
            problems.append((1, "%s does not name one of the four types: it says %r" % (name, kind)))
        named = re.findall(ID, lines.get("Requirement", ""))
        if not named:
            problems.append((2, "%s names no requirement" % name))
        for req in named:
            if req not in requirements:
                problems.append((2, "%s names %s, which is not in the requirements file" % (name, req)))
            flagged.setdefault(req, []).append(name)
        if kind == "contradictory":
            if len(set(named)) != 2:
                problems.append((4, "%s is a contradiction and names %d requirement%s, where it must name two"
                                 % (name, len(set(named)), "" if len(set(named)) == 1 else "s")))
            for req in named:
                if req not in finding["words"]:
                    problems.append((4, "%s is a contradiction and quotes no words from %s" % (name, req)))
        elif len(named) > 1:
            problems.append((1, "%s names more than one requirement and is not a contradiction" % name))
        if not finding["words"]:
            problems.append((2, "%s quotes no words" % name))
        for req, values in finding["words"].items():
            target = req or (named[0] if named else None)
            if req and req not in named:
                problems.append((2, "%s quotes words from %s, which it does not name as its requirement" % (name, req)))
            for value in values:
                words = quoted(value)
                if words is None or not words.strip():
                    problems.append((2, "%s has a Words line that is not text inside double quotes" % name))
                elif target in requirements and squeeze(words) not in requirements[target]:
                    problems.append((2, "%s quotes words that are not in %s: \"%s\"" % (name, target, words[:60])))
        for label in ("A tester could not decide", "If unanswered"):
            if len(lines.get(label, "")) < 15:
                problems.append((3, "%s does not say: %s" % (name, label)))
        question = lines.get("Question", "")
        if not question.rstrip().endswith("?"):
            problems.append((6, "%s does not ask a question" % name))
        said = " ".join(lines.values()).lower()
        for phrase in REWRITES:
            if phrase in said:
                problems.append((6, "%s offers wording in place of a question: it says '%s'" % (name, phrase)))
        if re.search(r"\b(the author|the writer|whoever wrote)\b", said):
            problems.append((6, "%s is about a person and not about the words" % name))
    left = {}
    for req, reason in unflagged:
        if req is None:
            problems.append((5, "a line under Unflagged could not be read: %s" % reason[:50]))
        elif req in left:
            problems.append((5, "%s is listed as unflagged twice" % req))
        elif req not in requirements:
            problems.append((5, "%s is listed as unflagged and is not in the requirements file" % req))
        else:
            left[req] = reason
            if len(reason) < 20:
                problems.append((5, "%s is listed as unflagged with no reason to speak of" % req))
    for req in requirements:
        if req in flagged and req in left:
            problems.append((5, "%s has a finding (%s) and is also listed as unflagged" % (req, ", ".join(flagged[req]))))
        if req not in flagged and req not in left:
            problems.append((5, "%s has no finding and is not listed as unflagged, so it is not accounted for" % req))
    return problems, flagged, left


def main(argv=None):
    parser = argparse.ArgumentParser(description="Check a findings file against its requirements and print the review.")
    parser.add_argument("--requirements", default=DEFAULT_REQUIREMENTS)
    parser.add_argument("--findings", default=DEFAULT_FINDINGS)
    args = parser.parse_args(argv)
    try:
        requirements = read_requirements(args.requirements)
        text, findings, unflagged = read_findings(args.findings)
    except Stop as stop:
        print("STOPPED: %s." % stop)
        return 2
    problems, flagged, left = check(requirements, text, findings, unflagged)
    print("REQUIREMENTS REVIEW. Reads two local files and writes none.")
    print("Requirements: %s, %d requirements." % (place(args.requirements), len(requirements)))
    print("Findings:     %s, %d findings." % (place(args.findings), len(findings)))
    print("")
    print("FINDINGS, %d, on %d requirements:" % (len(findings), len(flagged)))
    for finding in findings:
        lines = finding["lines"]
        words = "; ".join("%s%s" % ("%s " % req if req else "", " ".join(values)) for req, values in finding["words"].items())
        print("  %-5s %-17s %-14s words: %s" % (finding["name"], lines.get("Requirement", "?"), lines.get("Type", "?"), words))
        print("        asks: %s" % lines.get("Question", "(no question)"))
    counts = {kind: sum(1 for finding in findings if finding["lines"].get("Type") == kind) for kind in TYPES}
    print("By type: %s." % ", ".join("%s %d" % (kind, counts[kind]) for kind in TYPES))
    print("")
    print("UNFLAGGED, %d requirements left alone, each with the reason it is sound:" % len(left))
    for req in requirements:
        if req in left:
            print("  %-7s %s" % (req, left[req]))
    print("")
    print("ACCOUNTED FOR: %d with a finding + %d unflagged = %d of %d requirements."
          % (len([r for r in requirements if r in flagged]), len(left), len([r for r in requirements if r in flagged or r in left]), len(requirements)))
    print("")
    if problems:
        print("THE REVIEW BREAKS ITS OWN RULES, %d time%s:" % (len(problems), "" if len(problems) == 1 else "s"))
        for rule, what in problems:
            print("  rule %d: %s" % (rule, what))
        print("")
        print("RESULT: NOT ACCEPTED.")
        return 1
    print("Rules checked: one type from four for each finding; quoted words found in the requirement named, character for")
    print("character; what a tester could not decide and what goes wrong if unanswered both stated; a contradiction names")
    print("two requirements and quotes both; every requirement accounted for once; each finding asks a question and offers")
    print("no wording; the definitions are in the file, in the order they are applied.")
    print("This script checks the form of the review. Whether each judgment is right is not something it can check.")
    print("")
    print("RESULT: THE REVIEW KEEPS ALL ITS RULES.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
