"""Checks four things about the tests' evidence, against the latest planted-bug log.

1. Every line of SKILL.md and PROOF.md that this checker recognizes as claiming a test names at
   least one planted bug. A line claims a test when it says "with a test", "with tests",
   "tests added", "is tested", "are tested", "now tested", "now checked", "checked by", "Test:",
   "Tests:", "test checks" or "tests check".
2. Every planted bug either file names is in planted_bugs.py and the log shows it as KILLED.
   Planted bugs are written "(planted bug: NAME)" or "(planted bugs: NAME; NAME)", and a line may
   hold several such lists. Names are separated by "; " and may contain parentheses, commas,
   apostrophes, quotes and colons. Spaces around a name are ignored. A name written exactly as in
   planted_bugs.py is read whole, even when its parentheses do not pair up, when nothing but spaces
   comes between it and the next "; ", ")" or the end of the line. Any other name runs to the next
   "; " or ")" outside its own parentheses, or to the end of the line, so a semicolon inside a
   name's own parentheses does not end the name, and a list that does not close on the line where
   it opens is read to the end of that line.
3. Every test in test_ingest.py (a function marked @test) is named as failing by at least one
   KILLED planted bug in the log, so no test is claimed without being shown to fail.
4. Each planted bug the log shows as KILLED, in a list that has a test named before it, is shown
   making at least one of those tests fail. A test is named when its function name is written in
   backticks, such as `command_line_exit_codes`. The tests named before a list are the ones on its
   line that come before it and after any earlier list on that line, as in a table row that names
   its tests and then cites its planted bugs. A list with no test named before it gets checks 1
   and 2 only.

Check 4 is narrower, on purpose, than pairing a list with every test on its line. A test named
after a list, or before an earlier list, is often there for another reason: as the exception to a
sentence about the other tests, or in an earlier sentence about another planted bug. On PROOF.md as
of 2026-10-28, pairing every test on the line reported five right citations as problems (three on
line 15, which names `command_line_exit_codes` after its list as the one test that does not check
the reason, and two on line 213, whose second list follows a sentence about that test). The cost:
a list followed by the test it is about is not paired with that test. The self-test
a_test_named_after_a_list_or_before_an_earlier_list_is_not_paired_with_it shows both sides.

It prints a PROBLEM line for each problem, then a line counting the lines and planted-bug
references check 4 covered, then the summary line in the same format as earlier runs. It cannot
tell whether a claim is worded in a way its patterns miss, or whether a named planted bug is the
right one; that is a reviewer's job. A test named after a list, or on another line, is not paired
with that list. When several tests are named before a list, each planted bug in it is checked
against all of them, not against the test its sentence is about. A planted bug that hung the suite
is shown making no test fail. A name not in planted_bugs.py whose parentheses do not pair up is
reported, but may be cut short or run on to the end of the line, and the names after it in its
list are not read. Run from the repository root after planted_bugs.py has been run and its output
saved to logs/planted-bugs.txt:
  .venv/bin/python participant/skills/ba-ingest-transcript/tests/check_claims.py
Exit code 0 means no problem was found. tests/test_check_claims.py is this checker's self-test.
"""
import ast
import importlib.util
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # loading planted_bugs.py must not leave __pycache__ in participant/

TESTS = Path(__file__).resolve().parent
SKILL_DIR = TESTS.parent
REPO = SKILL_DIR.parents[2]
PACKAGE = REPO / "participant" / "evidence" / "ba-ingest-transcript" / "ba-attempt-001"
DOCS = [SKILL_DIR / "SKILL.md", PACKAGE / "PROOF.md"]
LOG = PACKAGE / "logs" / "planted-bugs.txt"
CLAIM = re.compile(r"\bwith (?:a )?tests?\b|\btests? added\b|\b(?:is|are|now) tested\b|\bnow checked\b"
                   r"|\bchecked by\b|\bTests?:|\btests? checks?\b", re.I)
REFERENCE_START = re.compile(r"\(planted bugs?: ")
CODE_SPAN = re.compile(r"`([^`\n]+)`")
KILLED = "KILLED    "


def listed_name_end(line, start, known):
    """Where the separator after a name in known that starts at start begins: the "; " or ")" or
    the end of the line that follows the name, past any spaces. The longest such name wins. None
    when no name in known starts there with only spaces before such a separator."""
    for name in known:
        if line.startswith(name, start):
            at = start + len(name)
            while at < len(line) and line[at] == " ":
                at += 1
            if at == len(line) or line[at] == ")" or line.startswith("; ", at):
                return at
    return None


def references(line, known=()):
    """The planted-bug lists a line cites, each as (start, stop, names). A list opens at start with
    "(planted bug: " or "(planted bugs: " and ends at stop, just after the parenthesis that closes
    it, or at the end of the line. Its names are separated by "; ", and spaces around a name are
    ignored. A name in known (the names in planted_bugs.py) is read whole wherever only spaces come
    between it and "; ", ")" or the end of the line. Any other name runs to the next "; " or ")"
    outside its own parentheses, or to the end of the line."""
    known = sorted(known, key=len, reverse=True)
    lists = []
    for match in REFERENCE_START.finditer(line):
        position, stop, names = match.end(), len(line), []
        while position < len(line):
            start = position
            while start < len(line) and line[start] == " ":
                start += 1
            end = listed_name_end(line, start, known)
            if end is None:
                depth, end = 0, position
                while end < len(line) and not (depth == 0 and (line[end] == ")" or line.startswith("; ", end))):
                    depth += {"(": 1, ")": -1}.get(line[end], 0)
                    end += 1
            if line[position:end].strip():
                names.append(line[position:end].strip())
            if end >= len(line) or line[end] == ")":
                stop = min(end + 1, len(line))
                break
            position = end + 2
        lists.append((match.start(), stop, names))
    return lists


def read_log():
    """What the log shows each KILLED planted bug failing: test names, or the text the log gives
    instead, such as a hung suite. The name is all before the line's last ": ", because a test
    name never holds one and a planted-bug name can."""
    shown = {}
    for line in LOG.read_text(encoding="utf-8").splitlines():
        if line.startswith(KILLED):
            name, colon, tests = line[len(KILLED):].rpartition(": ")
            if not colon:
                name, tests = tests, ""
            shown.setdefault(name, []).extend(test.strip() for test in tests.split(", ") if test.strip())
    return shown


def test_names():
    tree = ast.parse((TESTS / "test_ingest.py").read_text(encoding="utf-8"))
    return [node.name for node in tree.body if isinstance(node, ast.FunctionDef)
            and any(getattr(decorator, "id", "") == "test" for decorator in node.decorator_list)]


def main():
    spec = importlib.util.spec_from_file_location("planted_bugs", TESTS / "planted_bugs.py")
    planted = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(planted)
    names = {name for name, _, _ in planted.PLANTED}
    shown = read_log()
    killed = set(shown)
    failing = {test for tests in shown.values() for test in tests}
    tests = test_names()
    known_tests = set(tests)
    problems, claims, cited, paired_lines, paired = [], 0, 0, 0, 0
    for doc in DOCS:
        for number, line in enumerate(doc.read_text(encoding="utf-8").splitlines(), start=1):
            lists = references(line, names)
            named = [name for _, _, listed in lists for name in listed]
            cited += len(named)
            if CLAIM.search(line):
                claims += 1
                if not named:
                    problems.append(f"{doc.name}:{number}: claims a test but names no planted bug")
            spans = [(span.start(), span.group(1)) for span in CODE_SPAN.finditer(line) if span.group(1) in known_tests]
            after, checked = 0, 0  # after: where the previous list on this line ended
            for start, stop, listed in lists:
                before = list(dict.fromkeys(test for at, test in spans if after <= at < start))
                after = stop
                for name in listed:
                    if name not in names:
                        problems.append(f"{doc.name}:{number}: planted bug {name!r} is not in planted_bugs.py")
                    elif name not in killed:
                        problems.append(f"{doc.name}:{number}: planted bug {name!r} is not marked KILLED in logs/planted-bugs.txt")
                    elif before:
                        checked += 1
                        if not set(before) & set(shown[name]):
                            problems.append(f"{doc.name}:{number}: planted bug {name!r} is not shown making any test "
                                            f"named before its list fail ({', '.join(before)}); "
                                            f"logs/planted-bugs.txt shows: {', '.join(shown[name]) or 'nothing'}")
            if checked:
                paired_lines += 1
                paired += checked
    for test in tests:
        if test not in failing:
            problems.append(f"test_ingest.py: {test} is never made to fail by a planted bug in logs/planted-bugs.txt")
    for problem in problems:
        print(f"PROBLEM  {problem}")
    print(f"{paired_lines} line(s) with a test named before a planted-bug list, {paired} planted-bug reference(s) "
          f"checked against the tests named before their list")
    print(f"{claims} line(s) claiming a test, {cited} planted-bug reference(s), {len(killed)} planted bugs caught "
          f"in the log, {sum(test in failing for test in tests)} of {len(tests)} tests made to fail by at least one "
          f"planted bug, {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
