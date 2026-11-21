#!/usr/bin/env python3
"""Checks a requirements review: that every finding is well formed and traceable to the text.

Part of the ba-detect-ambiguity quest. The judgment -- which requirements have which defects -- is
a person's, written in findings.md. This program checks that judgment can be reproduced from the
two files alone:
  - every finding names exactly one of the four defect types;
  - every quoted phrase appears, word for word, in the requirement it cites;
  - a contradiction cites two requirements and quotes both; other findings cite one;
  - every finding says what a tester couldn't decide;
  - every finding asks at least one question, and each is phrased as a question, not a rewrite;
  - every requirement is either flagged or listed as unflagged with a reason, never both;
  - the set as a whole has at least 8 requirements, some sound, and every defect type.
Anything it can't read or doesn't recognise is a problem, never skipped: a check that can't be
made counts as failed, so the result is only PASSED when every check really passed.

Read-only: it writes nothing.

    .venv/bin/python participant/tools/check-findings.py \\
        --requirements participant/context/ambiguity/requirements.md \\
        --findings participant/context/ambiguity/findings.md
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path

VERSION = "1.8.0"
TYPES = ("Vague", "Incomplete", "Contradictory", "Untestable")
MIN_REQUIREMENTS = 8

# A question ends with '?' and opens the way a question does: with a question word ("What ...?"),
# a verb that starts a yes/no question ("Is the fee taxed?"), a preposition and a question word
# ("Under what conditions ...?"), or a lead-in phrase and then a question after its comma ("After
# the message, what ...?"). A statement with a question mark -- "The page must load in 2 seconds
# when checkout starts?" -- is a rewrite, not a question, even though it contains "when". Each
# Question field holds one question; a finding with several questions uses several fields.
WH_WORDS = ("what", "which", "how", "when", "where", "who", "whom", "whose", "why")
YES_NO_STARTS = (
    "is", "are", "was", "were", "can", "could", "does", "do", "did",
    "shall", "should", "will", "would", "may", "might", "must", "has", "have",
)
LEAD_INS = (
    "about", "after", "at", "before", "between", "by", "during", "for", "from", "if", "in", "into",
    "of", "on", "once", "over", "through", "to", "under", "until", "with", "within", "without",
)

QUOTED_TEXT = re.compile(r'"[^"]*"|\u201c[^\u201d]*\u201d')
ABBREVIATIONS = re.compile(r"(?<!\w)(?:e\.g|i\.e|etc|vs|approx|a\.m|p\.m)\.", re.IGNORECASE)
# A negative contraction opens a question like its verb does: "Doesn't ...?" like "Does ...?".
IRREGULAR_CONTRACTIONS = {"can't": "can", "won't": "will", "shan't": "shall"}
# A question word with a contracted verb counts as both words: "What's ...?" like "What is ...?".
# Only question words are split, so a possessive ("the buyer's card") never reads as "is".
WH_CONTRACTIONS = {"'s": "is", "'re": "are", "'ll": "will", "'d": "did", "'ve": "have"}

REQ_ID = r"[A-Z][A-Z0-9]*-\d+"
REQ_START = re.compile(rf"^\*\*({REQ_ID})\.\*\*\s+(.*)$")
# Anything that looks like the start of a requirement or a finding, well formed or not. A line
# like this that isn't exactly in the right form is reported, never read as ordinary text.
REQ_LIKE = re.compile(rf"^(?:\*\*\s*{REQ_ID}\b|{REQ_ID}[.:])")
# The introduction above '## Findings' is prose. A list item with a bold label, or a line that
# opens with a bold requirement id or finding field, is review content in the wrong place, in any
# list style ("-", "*", "+", "1.", "1)").
PREAMBLE_CONTENT = re.compile(
    rf"^(?:(?:[-*+]|\d+[.)])\s+\*\*|\*\*\s*(?:{REQ_ID}|Requirement|Type|Words in|Question|A tester))"
)
REQ_HEADING_LIKE = re.compile(rf"^#{{1,6}}\s*(?:\*\*)?\s*{REQ_ID}\b")
FINDING_LIKE = re.compile(r"^#{1,6}\s*(?:\*\*)?\s*F-\d+\b")
FINDING_HEADING = re.compile(r"^### (F-\d+)\s*$")
FIELD = re.compile(r"^- \*\*([^*]+?):\*\*\s*(.*)$")
UNFLAGGED_ITEM = re.compile(rf"^- \*\*({REQ_ID}):\*\*\s*(.*)$")
QUOTED = re.compile(r'^["“](.+)["”]$')
SINGLE_FIELDS = ("Requirement", "Type", "A tester couldn't decide")


def norm(text: str) -> str:
    """Text compared as a reader sees it: one form per character, runs of spaces as one space."""
    return " ".join(unicodedata.normalize("NFC", text).split())


def read_lines(path: Path) -> list[str]:
    """The file's lines. Exits with status 2 if it can't be read as UTF-8 text."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        print(f"Can't read {path}: {exc}", file=sys.stderr)
        sys.exit(2)
    return text.splitlines()


def parse_requirements(lines: list[str], problems: list[str]) -> dict[str, str]:
    """Requirement id -> its text, from the paragraphs under '## Requirements'.

    Each requirement is a paragraph that starts '**ID.**'. Any other paragraph in that section
    is a problem, since it may be a requirement whose id is mistyped.
    """
    reqs: dict[str, str] = {}
    in_section = False
    current: str | None = None
    for n, raw in enumerate(lines, 1):
        line = raw.strip()
        if REQ_HEADING_LIKE.match(line):
            problems.append(f"requirements line {n}: a requirement written as a heading isn't checked: {line[:60]!r}")
            continue
        if line.startswith("## "):
            in_section = line == "## Requirements"
            current = None
            continue
        if not in_section:
            if REQ_LIKE.match(line):
                problems.append(f"requirements line {n}: a requirement outside '## Requirements' isn't checked")
            continue
        if not line:
            current = None
            continue
        m = REQ_START.match(line)
        if not m and REQ_LIKE.match(line):
            problems.append(f"requirements line {n}: a requirement must start '**ID.** text': {line[:60]!r}")
            current = None
            continue
        if m:
            rid, text = m.groups()
            if rid in reqs:
                problems.append(f"requirements line {n}: {rid} appears twice")
                current = None
                continue
            reqs[rid] = text
            current = rid
        elif current is not None:
            reqs[current] += " " + line
        else:
            problems.append(f"requirements line {n}: text that doesn't start with a requirement id: {line[:60]!r}")
    for rid in reqs:
        reqs[rid] = norm(reqs[rid])
        if not reqs[rid]:
            problems.append(f"{rid} has no text")
    if not reqs:
        problems.append("no requirements found under '## Requirements'")
    return reqs


def field_name(raw: str) -> str:
    """A field's name as compared: trimmed, with a curly apostrophe read as a straight one."""
    return raw.strip().replace("’", "'")


def parse_findings(lines: list[str], problems: list[str]):
    """The findings (in file order) and the unflagged list from findings.md.

    Findings are '### F-NN' headings under '## Findings', each followed only by '- **Field:** value'
    lines. Unflagged requirements are '- **ID:** reason' lines under '## Unflagged requirements'.
    Lines before '## Findings' (the introduction and definitions) are prose and aren't checked,
    except that review content there -- a finding heading, a list item with a bold label, or a
    bold requirement id or field name -- is a problem, since it would otherwise go unchecked. Any
    line after it that isn't in one of these forms is a problem too, so nothing is silently ignored.
    """
    findings: list[dict] = []
    unflagged: dict[str, str] = {}
    section = None  # None (before Findings), "findings" or "unflagged"
    seen_sections: set[str] = set()
    current: dict | None = None
    for n, raw in enumerate(lines, 1):
        line = raw.strip()
        if FINDING_LIKE.match(line) and not FINDING_HEADING.match(line):
            problems.append(f"findings line {n}: a finding heading must be '### F-NN' alone: {line[:60]!r}")
            continue
        if line.startswith("## "):
            name = {"## Findings": "findings", "## Unflagged requirements": "unflagged"}.get(line)
            if name is None:
                if section is not None:
                    problems.append(f"findings line {n}: unexpected section {line!r}")
                    section = "unknown"
                continue
            if name in seen_sections:
                problems.append(f"findings line {n}: section {line!r} appears twice")
            seen_sections.add(name)
            section, current = name, None
            continue
        if section is None:
            if FINDING_LIKE.match(line) or PREAMBLE_CONTENT.match(line):
                problems.append(f"findings line {n}: finding content before '## Findings' isn't checked: {line[:60]!r}")
            continue
        if not line:
            continue
        if section == "unknown":
            continue
        if section == "findings":
            m = FINDING_HEADING.match(line)
            if m:
                current = {"id": m.group(1), "line": n, "fields": []}
                findings.append(current)
                continue
            m = FIELD.match(line)
            if m and current is not None:
                current["fields"].append((field_name(m.group(1)), m.group(2).strip(), n))
                continue
            problems.append(f"findings line {n}: not a finding heading or field: {line[:60]!r}")
        else:
            m = UNFLAGGED_ITEM.match(line)
            if m:
                rid, reason = m.group(1), m.group(2).strip()
                if rid in unflagged:
                    problems.append(f"findings line {n}: {rid} is listed as unflagged twice")
                    continue
                unflagged[rid] = reason
                continue
            problems.append(f"findings line {n}: not an unflagged-requirement line: {line[:60]!r}")
    for name, heading in (("findings", "## Findings"), ("unflagged", "## Unflagged requirements")):
        if name not in seen_sections:
            problems.append(f"findings.md has no {heading!r} section")
    return findings, unflagged


def contains_phrase(text: str, phrase: str) -> bool:
    """Whether phrase appears in text word for word, not as part of a longer word."""
    left = r"(?<!\w)" if phrase[0].isalnum() or phrase[0] == "_" else ""
    right = r"(?!\w)" if phrase[-1].isalnum() or phrase[-1] == "_" else ""
    return re.search(left + re.escape(phrase) + right, text) is not None


def verb_of(word: str) -> str:
    """A lower-case word with any negative contraction undone: "doesn't" -> "does"."""
    if word in IRREGULAR_CONTRACTIONS:
        return IRREGULAR_CONTRACTIONS[word]
    return word[:-3] if word.endswith("n't") else word


def word_list(text: str) -> list[str]:
    """The words of text, lower case, with contractions undone: "doesn't" -> "does",
    "what's" -> "what", "is"."""
    words: list[str] = []
    for w in re.findall(r"[A-Za-z']+", text):
        w = w.casefold()
        head, sep, tail = w.partition("'")
        if head in WH_WORDS and sep and "'" + tail in WH_CONTRACTIONS:
            words += [head, WH_CONTRACTIONS["'" + tail]]
        else:
            words.append(verb_of(w))
    return words


def is_question(text: str) -> bool:
    """Whether text is phrased as a question for the author. It checks the shape, not the meaning."""
    text = text.replace("’", "'")
    words = word_list(text)
    # One question per field: a single '?', at the end, and no second sentence before it, so a
    # question can't carry a rewrite with it ("How many seconds? It must load in 2 seconds?"),
    # however the second sentence starts ("... load. 2 seconds is the maximum?"). The periods of
    # common abbreviations ("e.g. Tixly credit") don't end a sentence, and nor does punctuation
    # inside quoted text ('after seeing "Payment declined. Try again"?').
    plain = ABBREVIATIONS.sub("", QUOTED_TEXT.sub('""', text))
    if not text.endswith("?") or plain.count("?") != 1 or re.search(r"[.!]\s+\S", plain) or not words:
        return False
    # "when" or "where" not followed straight away by a verb ("When is ...?") is either a direct
    # question with a question verb before any comma ("When exactly should ...?", "Where on the
    # page should it appear, above or below?"), or a lead-in that must be followed by a question
    # after its comma ("When the card is worth more, what happens ...?"). So "When checkout
    # starts, the map must load in 2 seconds?" isn't accepted. This checks the shape, not the
    # grammar: a rewrite whose lead-in happens to contain such a verb ("When checkout is open,
    # the map must ...?") can still pass, so a person still reads the questions.
    if words[0] in ("when", "where") and len(words) > 1 and words[1] not in YES_NO_STARTS:
        before, _, rest = plain.partition(",")
        # A question verb before any comma makes it a direct question, even with alternatives
        # after the comma ("Where on the page should it appear, above or below the form?").
        if any(w in YES_NO_STARTS for w in word_list(before)[2:]):
            return True
        if not rest:
            return False
        after = word_list(rest)
        return bool(after) and (after[0] in WH_WORDS or after[0] in YES_NO_STARTS)
    if words[0] in WH_WORDS or words[0] in YES_NO_STARTS:
        return True
    if words[0] in LEAD_INS and len(words) > 1 and words[1] in WH_WORDS:
        return True
    if words[0] in LEAD_INS and "," in plain:
        after = word_list(plain.split(",", 1)[1])
        return bool(after) and (after[0] in WH_WORDS or after[0] in YES_NO_STARTS)
    return False


def shown(path: Path, root: Path) -> str:
    """The path as printed: relative to the repository, so no home folder appears in a log."""
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return path.name


def check_finding(f: dict, reqs: dict[str, str]) -> tuple[dict, list[str]]:
    """The finding's parts, and every problem with it."""
    fid = f["id"]
    problems: list[str] = []
    single: dict[str, str] = {}
    words: list[tuple[str, str, int]] = []
    questions: list[str] = []
    for name, value, n in f["fields"]:
        if name in SINGLE_FIELDS:
            if name in single:
                problems.append(f"{fid}: '{name}' is given twice (line {n})")
            else:
                single[name] = value
        elif name.startswith("Words in "):
            words.append((name[len("Words in "):].strip(), value, n))
        elif name == "Question":
            questions.append(value)
        else:
            problems.append(f"{fid}: unknown field '{name}' (line {n})")

    cited_raw = single.get("Requirement", "")
    cited = [c.strip() for c in cited_raw.split(",") if c.strip()]
    if not cited:
        problems.append(f"{fid}: no requirement cited")
    if len(set(cited)) != len(cited):
        problems.append(f"{fid}: cites the same requirement twice")
    for rid in cited:
        if rid not in reqs:
            problems.append(f"{fid}: cites {rid}, which isn't in the requirements")

    ftype = single.get("Type", "")
    if ftype not in TYPES:
        given = repr(ftype) if ftype else "none"
        problems.append(f"{fid}: type {given} is not one of {', '.join(TYPES)}")
    elif ftype == "Contradictory" and len(set(cited)) != 2:
        problems.append(f"{fid}: a contradiction must cite exactly two requirements, not {len(set(cited))}")
    elif ftype != "Contradictory" and len(set(cited)) > 1:
        problems.append(f"{fid}: only a contradiction cites more than one requirement")

    quoted_for = set()
    for rid, value, n in words:
        m = QUOTED.match(value)
        if rid not in cited:
            problems.append(f"{fid}: quotes {rid}, which the finding doesn't cite (line {n})")
            continue
        quoted_for.add(rid)
        if not m or not norm(m.group(1)):
            problems.append(f"{fid}: the words in {rid} must be one phrase in double quotes (line {n})")
            continue
        if rid in reqs and not contains_phrase(reqs[rid], norm(m.group(1))):
            problems.append(f"{fid}: \"{norm(m.group(1))}\" does not appear word for word in {rid}")
    for rid in cited:
        if rid not in quoted_for:
            problems.append(f"{fid}: no words quoted from {rid}")

    if not single.get("A tester couldn't decide"):
        problems.append(f"{fid}: doesn't say what a tester couldn't decide")
    if not questions:
        problems.append(f"{fid}: asks no question")
    for q in questions:
        if not is_question(q):
            problems.append(f"{fid}: not phrased as a question (it must end with '?' and open as a question): {q[:60]!r}")

    parts = {"id": fid, "type": ftype, "cited": cited, "questions": len(questions)}
    return parts, problems


def main(argv: list[str] | None = None) -> int:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--requirements", type=Path,
                        default=root / "participant/context/ambiguity/requirements.md")
    parser.add_argument("--findings", type=Path,
                        default=root / "participant/context/ambiguity/findings.md")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    args = parser.parse_args(argv)

    problems: list[str] = []
    reqs = parse_requirements(read_lines(args.requirements), problems)
    raw_findings, unflagged = parse_findings(read_lines(args.findings), problems)

    findings = []
    seen_ids: set[str] = set()
    for f in raw_findings:
        if f["id"] in seen_ids:
            problems.append(f"finding id {f['id']} is used twice")
        seen_ids.add(f["id"])
        parts, found = check_finding(f, reqs)
        findings.append(parts)
        problems.extend(found)

    flagged = {rid for f in findings for rid in f["cited"] if rid in reqs}
    for rid, reason in unflagged.items():
        if rid not in reqs:
            problems.append(f"unflagged list names {rid}, which isn't in the requirements")
        elif rid in flagged:
            problems.append(f"{rid} is both flagged and listed as unflagged")
        if not reason:
            problems.append(f"unflagged {rid} gives no reason it is sound")
    for rid in reqs:
        if rid not in flagged and rid not in unflagged:
            problems.append(f"{rid} is neither flagged nor listed as unflagged")

    # The set itself must be a fair test: enough requirements, some sound, every defect type.
    if len(reqs) < MIN_REQUIREMENTS:
        problems.append(f"the set has {len(reqs)} requirements; the quest needs at least {MIN_REQUIREMENTS}")
    sound = [rid for rid in reqs if rid in unflagged and rid not in flagged]
    if not sound:
        problems.append("no requirement is left unflagged as sound")
    for t in TYPES:
        if not any(f["type"] == t for f in findings):
            problems.append(f"no finding of type {t}")

    print(f"# check-findings.py {VERSION}")
    print(f"Requirements: {shown(args.requirements, root)}")
    print(f"Findings:     {shown(args.findings, root)}")
    print()
    print(f"{len(reqs)} requirements, {len(findings)} findings, {len(sound)} unflagged.")
    print()
    print("By requirement:")
    for rid in reqs:
        mine = [f for f in findings if rid in f["cited"]]
        if mine:
            listed = ", ".join(
                f"{f['id']} {f['type'] or '?'}" + (f" (with {', '.join(c for c in f['cited'] if c != rid)})"
                                                   if len(f["cited"]) > 1 else "")
                for f in mine
            )
            print(f"  {rid}  flagged: {listed}")
        elif rid in unflagged:
            print(f"  {rid}  unflagged")
        else:
            print(f"  {rid}  NOT ACCOUNTED FOR")
    print()
    print("By type:")
    for t in TYPES:
        ids = [f["id"] for f in findings if f["type"] == t]
        print(f"  {t:<14}{len(ids):>2}  {', '.join(ids)}")
    print()
    print("Unflagged requirements, and why each is sound:")
    if sound:
        for rid in sound:
            print(f"  {rid}: {unflagged[rid]}")
    else:
        print("  (none)")
    print()
    if problems:
        print(f"Problems ({len(problems)}):")
        for p in problems:
            print(f"  - {p}")
        print()
        print("result: FAILED (exit status 1)")
        return 1
    print("Checks: every quote appears word for word in the requirement it cites; every finding has one")
    print("of the four types, what a tester couldn't decide, and a question; the contradiction cites")
    print("both requirements; every requirement is flagged or unflagged with a reason, never both.")
    print()
    print("result: PASSED (exit status 0)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
