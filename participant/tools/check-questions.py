#!/usr/bin/env python3
"""Checks a clarification-question list: that every question is traceable and changes the work.

Part of the ba-clarification-questions quest. The judgment -- which questions are worth asking,
what the answers could be and what each would lead to -- is a person's, written in questions.md
and dropped.md. This program checks that judgment is complete and traceable:
  - every question cites a finding that exists in the verified findings.md;
  - every question lists at least two answers, each followed by the work it leads to;
  - no two answers to one question are the same text, and no two lead to the same work text;
  - every question reads as one sentence ending in '?' and is at most 25 words;
  - questions are numbered Q-01, Q-02, ... in order, with no gaps, and each says why it sits where
    it does (the order is by how much of the work depends on the answer);
  - every dropped question cites a finding that exists and says why its answer changes nothing;
  - every finding is accounted for: asked, dropped, or both (a question rewritten into a better one).

It accepts only what it recognises, and reports everything else. The list section holds only entry
headings and one-line fields, and a field holds plain text: no Markdown or web formatting, which
could hide content or make two identical lines look different. The introduction above the list is
prose: it may not mention an entry or a field, or contain a code block, comment or web markup that
could hide one. So the result is only PASSED when every check really passed.

It can tell that two work lines are different text, not that they are really different work;
that judgment stays with the person, who reads every line.

Read-only: it writes nothing and sends nothing.

    .venv/bin/python participant/tools/check-questions.py \\
        --findings participant/context/ambiguity/findings.md \\
        --questions participant/context/clarification/questions.md \\
        --dropped participant/context/clarification/dropped.md
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import sys
import unicodedata
from pathlib import Path

VERSION = "2.2.0"
MAX_QUESTION_WORDS = 25
MIN_ANSWERS = 2

FINDING_ID = re.compile(r"^F-\d+$")
FIELD = re.compile(r"^- \*\*([^*]+?):\*\*\s*(.*)$")
FIELD_NAMES = ("Finding", "Question", "Answer", "Work", "Why this position", "Why it changes nothing")

# A field holds plain text. These characters are Markdown or web formatting, which can hide text,
# turn a line into a link or a tag, or make two identical lines look different.
FORMATTING = re.compile(r"[*_`<>\[\]\\|&~]")
# Characters a reader can't see: any space other than an ordinary one, and every control, format
# (soft hyphen, zero-width space), private-use, unassigned or separator character, by its Unicode
# category, so the rule covers the whole class rather than a hand-picked list.
INVISIBLE_CATEGORIES = {"Cc", "Cf", "Co", "Cn", "Zl", "Zp"}
# Unicode's own list of characters that should be invisible (the Default_Ignorable_Code_Point
# property, which Python's unicodedata doesn't expose). Some sit in ordinary categories -- the
# Hangul fillers are "letters" -- so the categories above don't catch them on their own.
DEFAULT_IGNORABLE = (
    (0x00AD, 0x00AD), (0x034F, 0x034F), (0x061C, 0x061C), (0x115F, 0x1160), (0x17B4, 0x17B5),
    (0x180B, 0x180F), (0x200B, 0x200F), (0x202A, 0x202E), (0x2060, 0x206F), (0x3164, 0x3164),
    (0xFE00, 0xFE0F), (0xFEFF, 0xFEFF), (0xFFA0, 0xFFA0), (0xFFF0, 0xFFF8), (0x1BCA0, 0x1BCA3),
    (0x1D173, 0x1D17A), (0xE0000, 0xE0FFF),
)

# The introduction above the list is prose. These are reported there, however they are written:
# a field label (bold or not, colon anywhere after it), and anything that hides or styles text.
LABEL_MENTION = re.compile(
    r"(?<![A-Za-z])(?:" + "|".join(re.escape(f) for f in FIELD_NAMES) + r")[\s*_`\\]*:",
    re.IGNORECASE,
)
HIDING = re.compile(r"^\s*(?:```|~~~)|<[A-Za-z/!?]")

# A question reads as one sentence: no '.', '!' or '?' followed (perhaps after closing brackets or
# quote marks) by more text. Quoted text, common abbreviations and dotted initialisms ("U.S.") are
# set aside first so they don't count as breaks.
QUOTED_TEXT = re.compile(r'"[^"]*"|\u201c[^\u201d]*\u201d')
ABBREVIATIONS = re.compile(r"(?<!\w)(?:e\.g|i\.e|etc|vs|approx|a\.m|p\.m)\.", re.IGNORECASE)
INITIALISMS = re.compile(r"(?<!\w)(?:[A-Za-z]\.){2,}")
SENTENCE_BREAK = re.compile(r"[.!?][)\"'\u201d\u2019]*(?:\s+\S|[A-Z])")
WORD = re.compile(r"[\w'\u2019-]+")
HAS_LETTER_OR_DIGIT = re.compile(r"[^\W_]")

# Each list file: its section heading, its entry id prefix, and which fields an entry has.
# 'pairs' fields come as Answer then Work, repeated; every other field appears exactly once.
QUESTIONS = {
    "name": "questions",
    "section": "Questions",
    "prefix": "Q",
    "single": ("Finding", "Question", "Why this position"),
    "pairs": True,
}
DROPPED = {
    "name": "dropped",
    "section": "Dropped",
    "prefix": "D",
    "single": ("Finding", "Question", "Why it changes nothing"),
    "pairs": False,
}


def norm(text: str) -> str:
    """Text compared as a reader sees it: one form per character, runs of spaces as one space."""
    return " ".join(unicodedata.normalize("NFC", text).split())


def has_invisible(text: str) -> bool:
    """True when the text holds a character a reader can't see, or a space that isn't ordinary."""
    return any(
        unicodedata.category(c) in INVISIBLE_CATEGORIES
        or (c.isspace() and c != " ")
        or any(low <= ord(c) <= high for low, high in DEFAULT_IGNORABLE)
        for c in text
    )


def has_content(text: str) -> bool:
    """True when a field says something: at least one letter or digit."""
    return bool(HAS_LETTER_OR_DIGIT.search(text))


def same_text(a: str, b: str) -> bool:
    """True when two lines say the same thing word for word, ignoring case and end punctuation."""
    return norm(a).casefold().rstrip(" .!?;:") == norm(b).casefold().rstrip(" .!?;:")


def read_lines(path: Path) -> list[str]:
    """The file's lines. Exits with status 2 if it can't be read as UTF-8 text."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        print(f"Can't read {path}: {exc}", file=sys.stderr)
        sys.exit(2)
    # Only a real line ending starts a new line. (Python's splitlines() also splits on Unicode
    # separators that a Markdown viewer shows inside the line, which could invent a field.)
    return text.split("\n")


def load_findings_reader(root: Path):
    """The verified quest's own findings parser, so 'a finding exists' means what it meant there."""
    path = root / "participant/tools/check-findings.py"
    spec = importlib.util.spec_from_file_location("check_findings", path)
    if spec is None or spec.loader is None:
        print(f"Can't load {path}", file=sys.stderr)
        sys.exit(2)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except (OSError, SyntaxError) as exc:
        print(f"Can't load {path}: {exc}", file=sys.stderr)
        sys.exit(2)
    return module


def parse_list(lines: list[str], kind: dict, problems: list[str]) -> list[dict]:
    """The entries under '## <section>', in file order. Only exact entry headings and one-line
    fields are accepted inside the list; any other line there is reported, never skipped."""
    name, prefix, section = kind["name"], kind["prefix"], f"## {kind['section']}"
    entry_heading = re.compile(rf"^### ({prefix}-\d+)$")
    id_mention = re.compile(rf"(?<![A-Za-z0-9]){prefix}-\d+")
    entries: list[dict] = []
    current: dict | None = None
    in_section = False

    for n, raw in enumerate(lines, 1):
        line = raw.rstrip()
        where = f"{name} line {n}"
        if not in_section:
            if line == section:
                in_section = True
                continue
            # The introduction is prose. An entry or field up here would never be checked, and a
            # code block, comment or tag could hide one, so all of these are reported.
            if id_mention.search(line) or LABEL_MENTION.search(line) or HIDING.search(line):
                problems.append(f"{where}: list content or hidden text before '{section}': {line.strip()[:60]!r}")
            continue

        if not line:
            continue
        m = entry_heading.match(line)
        if m:
            current = {"id": m.group(1), "line": n, "fields": []}
            entries.append(current)
            continue
        field = FIELD.match(line)
        if field:
            if current is None:
                problems.append(f"{where}: field outside any entry: {line[:60]!r}")
                continue
            value = field.group(2).strip()
            if FORMATTING.search(value):
                problems.append(f"{where}: formatting isn't allowed in a field; write plain text: {value[:60]!r}")
            if has_invisible(raw):  # the whole line, so nothing hides in the spaces that strip() drops
                problems.append(f"{where}: an unusual space or invisible character in a field")
            current["fields"].append((field.group(1).strip(), value, n))
            continue
        problems.append(
            f"{where}: not an entry heading ('### {prefix}-NN') or a field ('- **Name:** value' "
            f"on one line): {line.strip()[:60]!r}"
        )

    if not in_section:
        problems.append(f"{name}: no '{section}' section")
    return entries


def check_question_text(text: str, where: str, limit: int | None) -> list[str]:
    """A question reads as one sentence ending in '?', and is short enough to answer without a
    meeting."""
    found = []
    if not text:
        return [f"{where}: the question is empty"]
    plain = INITIALISMS.sub("abbr", ABBREVIATIONS.sub("abbr", QUOTED_TEXT.sub('"q"', norm(text))))
    if not plain.endswith("?"):
        found.append(f"{where}: the question doesn't end with '?'")
    if plain.count("?") > 1 or SENTENCE_BREAK.search(plain):
        found.append(f"{where}: the question is more than one sentence")
    words = len([w for w in WORD.findall(norm(text)) if HAS_LETTER_OR_DIGIT.search(w)])
    if words == 0:
        found.append(f"{where}: the question has no words")
    if limit is not None and words > limit:
        found.append(f"{where}: the question is {words} words; the limit is {limit}")
    return found


def check_entry(entry: dict, kind: dict, finding_ids: set[str]) -> tuple[dict, list[str]]:
    """One entry's parts and its problems."""
    eid = entry["id"]
    found: list[str] = []
    single: dict[str, str] = {}
    pairs: list[tuple[str, str]] = []
    pending_answer: str | None = None

    for fname, value, n in entry["fields"]:
        where = f"{eid} ({kind['name']} line {n})"
        if kind["pairs"] and fname == "Answer":
            if pending_answer is not None:
                found.append(f"{where}: an Answer with no Work line after it")
            pending_answer = value
            if not has_content(value):
                found.append(f"{where}: an Answer with nothing in it")
            continue
        if kind["pairs"] and fname == "Work":
            if pending_answer is None:
                found.append(f"{where}: a Work line with no Answer before it")
            else:
                pairs.append((pending_answer, value))
            pending_answer = None
            if not has_content(value):
                found.append(f"{where}: a Work line with nothing in it")
            continue
        if pending_answer is not None:
            found.append(f"{where}: an Answer with no Work line after it")
            pending_answer = None
        if fname not in kind["single"]:
            found.append(f"{where}: unknown field {fname!r}")
            continue
        if fname in single:
            found.append(f"{where}: {fname} given twice")
            continue
        single[fname] = value
    if pending_answer is not None:
        found.append(f"{eid}: an Answer with no Work line after it")

    for fname in kind["single"]:
        if fname not in single:
            found.append(f"{eid}: no {fname} line")
        elif not has_content(single[fname]):
            found.append(f"{eid}: {fname} is empty")

    finding = single.get("Finding", "")
    if finding:
        if not FINDING_ID.match(finding):
            found.append(f"{eid}: Finding must be one finding id like F-07, not {finding!r}")
        elif finding not in finding_ids:
            found.append(f"{eid}: cites {finding}, which isn't in findings.md")

    limit = MAX_QUESTION_WORDS if kind["pairs"] else None
    if "Question" in single:
        found.extend(check_question_text(single["Question"], eid, limit))

    if kind["pairs"]:
        if len(pairs) < MIN_ANSWERS:
            found.append(f"{eid}: {len(pairs)} answer(s) with their work; at least {MIN_ANSWERS} needed")
        for i in range(len(pairs)):
            for j in range(i + 1, len(pairs)):
                if pairs[i][0] and same_text(pairs[i][0], pairs[j][0]):
                    found.append(f"{eid}: answers {i + 1} and {j + 1} are the same text")
                if pairs[i][1] and same_text(pairs[i][1], pairs[j][1]):
                    found.append(f"{eid}: answers {i + 1} and {j + 1} lead to the same work text")

    parts = {"id": eid, "finding": finding, "question": single.get("Question", ""), "answers": len(pairs)}
    return parts, found


def check_numbering(entries: list[dict], prefix: str, name: str) -> list[str]:
    """Entries are numbered 01, 02, ... in file order: the order on the page is the order asked."""
    found = []
    seen: set[str] = set()
    for i, e in enumerate(entries, 1):
        if e["id"] in seen:
            found.append(f"{name}: {e['id']} is used twice")
        seen.add(e["id"])
        expected = f"{prefix}-{i:02d}"
        if e["id"] != expected:
            found.append(f"{name}: entry {i} is {e['id']}; expected {expected} (numbered in order, no gaps)")
    return found


def shown(path: Path, root: Path) -> str:
    """The path as printed: relative to the repository, so no home folder appears in a log."""
    try:
        return path.resolve().relative_to(root).as_posix()
    except ValueError:
        return path.name


def main(argv: list[str] | None = None) -> int:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--findings", type=Path,
                        default=root / "participant/context/ambiguity/findings.md")
    parser.add_argument("--questions", type=Path,
                        default=root / "participant/context/clarification/questions.md")
    parser.add_argument("--dropped", type=Path,
                        default=root / "participant/context/clarification/dropped.md")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    args = parser.parse_args(argv)

    problems: list[str] = []
    findings_reader = load_findings_reader(root)
    finding_problems: list[str] = []
    raw_findings, _unflagged = findings_reader.parse_findings(read_lines(args.findings), finding_problems)
    problems.extend(f"findings.md: {p}" for p in finding_problems)
    finding_ids: list[str] = []
    for f in raw_findings:
        if f["id"] in finding_ids:
            problems.append(f"findings.md: finding id {f['id']} is used twice")
        else:
            finding_ids.append(f["id"])
    if not finding_ids:
        problems.append("findings.md: no findings to link questions to")

    q_entries = parse_list(read_lines(args.questions), QUESTIONS, problems)
    d_entries = parse_list(read_lines(args.dropped), DROPPED, problems)
    problems.extend(check_numbering(q_entries, "Q", "questions"))
    problems.extend(check_numbering(d_entries, "D", "dropped"))
    if not q_entries:
        problems.append("questions: no questions")

    questions, dropped = [], []
    for e in q_entries:
        parts, found = check_entry(e, QUESTIONS, set(finding_ids))
        questions.append(parts)
        problems.extend(found)
    for e in d_entries:
        parts, found = check_entry(e, DROPPED, set(finding_ids))
        dropped.append(parts)
        problems.extend(found)

    asked = {q["finding"] for q in questions}
    set_aside = {d["finding"] for d in dropped}
    for fid in finding_ids:
        if fid not in asked and fid not in set_aside:
            problems.append(f"{fid} is neither asked nor dropped")

    print(f"# check-questions.py {VERSION}")
    print(f"Findings:  {shown(args.findings, root)}")
    print(f"Questions: {shown(args.questions, root)}")
    print(f"Dropped:   {shown(args.dropped, root)}")
    print()
    print(f"{len(finding_ids)} findings, {len(questions)} questions, {len(dropped)} dropped.")
    print()
    print("Questions, in the order asked:")
    for q in questions:
        print(f"  {q['id']}  {q['finding'] or '?':<5} {q['answers']} answers  {q['question']}")
    print()
    print("Dropped:")
    if dropped:
        for d in dropped:
            print(f"  {d['id']}  {d['finding'] or '?':<5} {d['question']}")
    else:
        print("  (none)")
    print()
    print("By finding:")
    for fid in finding_ids:
        q_ids = [q["id"] for q in questions if q["finding"] == fid]
        d_ids = [d["id"] for d in dropped if d["finding"] == fid]
        parts = []
        if q_ids:
            parts.append("asked " + ", ".join(q_ids))
        if d_ids:
            parts.append("dropped " + ", ".join(d_ids))
        print(f"  {fid:<5} {'; '.join(parts) if parts else 'NOT ACCOUNTED FOR'}")
    print()
    if problems:
        print(f"Problems ({len(problems)}):")
        for p in problems:
            print(f"  - {p}")
        print()
        print("result: FAILED (exit status 1)")
        return 1
    print("Checks: every question and dropped question cites a finding in findings.md; every question")
    print(f"has at least {MIN_ANSWERS} answers, each with different work text; every question reads as one")
    print(f"sentence of at most {MAX_QUESTION_WORDS} words ending in '?'; questions are numbered in order with a")
    print("reason for each position; every dropped question says why it changes nothing; every finding")
    print("is asked or dropped; every field is plain text.")
    print()
    print("result: PASSED (exit status 0)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
