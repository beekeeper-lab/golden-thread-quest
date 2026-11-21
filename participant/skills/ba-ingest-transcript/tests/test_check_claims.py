"""Self-test for check_claims.py. Standard library only, no network, temporary folders only.

check_claims.py checks the claims SKILL.md and PROOF.md make about the tests against the saved
planted-bug log. Each test here builds a small made-up repository in a temporary folder, laid
out the way check_claims.py finds its files: a copy of the check_claims.py under test in
participant/skills/ba-ingest-transcript/tests/, next to a made-up planted_bugs.py (a bare PLANTED
list, which check_claims.py loads) and test_ingest.py (parsed, never run), the skill's SKILL.md,
and PROOF.md and logs/planted-bugs.txt in participant/evidence/ba-ingest-transcript/ba-attempt-001/.
It runs the copy in a separate Python process and checks the PROBLEM lines it prints, its summary
lines and its exit code.
Expected results come from the rules SKILL.md section 11 states for the claims check, the claim
wordings and citation forms check_claims.py's opening comment lists, the line formats
planted_bugs.py prints, and the summary format of the saved logs/claims-check.txt; each test's
docstring names its source. Run from the repository root:
  .venv/bin/python participant/skills/ba-ingest-transcript/tests/test_check_claims.py
Exit code 0 means every test passed. Set CHECK_CLAIMS_UNDER_TEST to the path of another copy of
check_claims.py to test that copy. With --planted, it instead breaks one behavior at a time in a
temporary copy of check_claims.py (the PLANTED list below), runs this self-test against each
copy, and exits with code 0 only when every planted bug turned the self-test red.
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True  # nothing here may leave __pycache__ in participant/

HERE = Path(__file__).resolve().parent
CHECKER = Path(os.environ.get("CHECK_CLAIMS_UNDER_TEST", HERE / "check_claims.py"))
LIMIT = 60  # seconds for one run of check_claims.py; a normal run takes well under one
TESTS = []


def test(function):
    TESTS.append(function)
    return function


def expect(condition, message):
    if not condition:
        raise AssertionError(message)


class Outcome:
    """What one run of check_claims.py printed and returned."""

    def __init__(self, result):
        self.code = result.returncode
        self.lines = result.stdout.splitlines()
        self.stderr = result.stderr
        self.problems = [line[len("PROBLEM  "):] for line in self.lines if line.startswith("PROBLEM  ")]


class Repo:
    """A made-up repository in a temporary folder, laid out the way check_claims.py expects."""

    def __init__(self, root):
        self.root = Path(root)
        self.skill = self.root / "participant" / "skills" / "ba-ingest-transcript"
        self.package = self.root / "participant" / "evidence" / "ba-ingest-transcript" / "ba-attempt-001"
        (self.skill / "tests").mkdir(parents=True)
        (self.package / "logs").mkdir(parents=True)
        shutil.copyfile(CHECKER, self.skill / "tests" / "check_claims.py")

    def write(self, planted, tests, log, skill=(), proof=(), helpers=()):
        """planted: the names in planted_bugs.py; tests: the functions test_ingest.py marks @test;
        helpers: functions it defines without the mark; log: the lines planted_bugs.py printed;
        skill and proof: the lines of SKILL.md and PROOF.md."""
        entries = "".join(f"    ({ascii(name)}, 'old text', 'new text'),\n" for name in planted)
        (self.skill / "tests" / "planted_bugs.py").write_text(f"PLANTED = [\n{entries}]\n", encoding="utf-8")
        functions = [f"@test\ndef {name}(ws):\n    pass\n" for name in tests]
        functions += [f"def {name}(ws):\n    pass\n" for name in helpers]
        (self.skill / "tests" / "test_ingest.py").write_text(
            "def test(function):\n    return function\n\n\n" + "\n\n".join(functions), encoding="utf-8")
        caught = sum(line.startswith("KILLED") for line in log)
        text = ["# Planted bugs: proof that the tests can fail", "",
                "$ .venv/bin/python participant/skills/ba-ingest-transcript/tests/planted_bugs.py",
                *log, "", f"{caught} of {len(planted)} planted bugs caught", "[exit code: 0]"]
        (self.package / "logs" / "planted-bugs.txt").write_text("\n".join(text) + "\n", encoding="utf-8")
        (self.skill / "SKILL.md").write_text("\n".join(skill) + "\n", encoding="utf-8")
        (self.package / "PROOF.md").write_text("\n".join(proof) + "\n", encoding="utf-8")

    def check(self):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        try:
            result = subprocess.run([sys.executable, "-B", str(self.skill / "tests" / "check_claims.py")],
                                    cwd=self.root, env=env, capture_output=True, text=True, timeout=LIMIT)
        except subprocess.TimeoutExpired:
            raise AssertionError(f"check_claims.py did not finish within {LIMIT} seconds, so it was stopped") from None
        return Outcome(result)


def run(function):
    with tempfile.TemporaryDirectory() as root:
        function(Repo(root))


# The lines planted_bugs.py prints (its main()), which check_claims.py reads back.
def killed(name, *tests):
    return f"KILLED    {name}: {', '.join(tests)}"


def hung(name):
    return f"KILLED    {name}: the suite hung and was stopped after 120 seconds"


def survived(name):
    return f"SURVIVED  {name}"


def not_found(name):
    return f"ERROR     {name}: the code to break was not found exactly once"


class Like:
    """An expected PROBLEM line whose wording no rule fixes: it must start with start and hold
    each of parts."""

    def __init__(self, start, *parts):
        self.start, self.parts = start, parts

    def matches(self, line):
        return line.startswith(self.start) and all(part in line for part in self.parts)

    def __repr__(self):
        return f"Like({', '.join(ascii(part) for part in (self.start, *self.parts))})"


def expect_problems(outcome, expected, label):
    """The run printed exactly the expected PROBLEM lines, each once, in any order, printed nothing
    on stderr, and exited with code 1 when there were problems and 0 when there were none (the
    exit code rule in SKILL.md section 11). A str is an exact line, in the format check_claims.py
    printed before this round; a Like is a pattern."""
    left, missing = list(outcome.problems), []
    for item in sorted(expected, key=lambda item: isinstance(item, Like)):  # exact lines first
        found = next((line for line in left if (item.matches(line) if isinstance(item, Like) else line == item)), None)
        if found is None:
            missing.append(item)
        else:
            left.remove(found)
    expect(not missing and not left, f"{label}: expected the problems {ascii(list(expected))}, "
                                     f"but these were missing: {ascii(missing)}, and these were not expected: {ascii(left)}")
    code = 1 if expected else 0
    expect(outcome.code == code, f"{label}: expected exit code {code}, got {outcome.code}; "
                                 f"stderr ends {ascii(outcome.stderr[-2000:])}")
    expect(outcome.stderr == "", f"{label}: expected nothing on stderr, got {ascii(outcome.stderr[-2000:])}")


def expect_summary(outcome, claims, cited, caught, failing, tests, problems, label):
    """The last line keeps the format of the saved logs/claims-check.txt, so the log stays
    comparable (brief for this round; SKILL.md section 11)."""
    expected = (f"{claims} line(s) claiming a test, {cited} planted-bug reference(s), {caught} planted bugs "
                f"caught in the log, {failing} of {tests} tests made to fail by at least one planted bug, "
                f"{problems} problem(s)")
    actual = outcome.lines[-1] if outcome.lines else ""
    expect(actual == expected, f"{label}: expected the last line {ascii(expected)}, got {ascii(actual)}")


def expect_count(outcome, lines, references, label):
    """SKILL.md section 11 (this round): just before its summary line, the run prints how many lines
    and planted-bug references the fourth check covered. No rule fixes the rest of the wording."""
    start, part = f"{lines} line(s) ", f" {references} planted-bug reference(s) "
    actual = outcome.lines[-2] if len(outcome.lines) > 1 else ""
    expect(actual.startswith(start) and part in actual,
           f"{label}: expected the line before the summary to start {ascii(start)} and hold {ascii(part)}, "
           f"got {ascii(actual)}")


@test
def documents_whose_claims_are_all_backed_pass(repo):
    """SKILL.md section 11: with every claim line naming a planted bug, each named planted bug in
    planted_bugs.py and caught, every test made to fail, and each planted bug in a list with tests
    named before it making one of those tests fail, there is no problem and the exit code is 0. The
    test file has 120 tests, more than the 105 test names the old suite and this round's area
    tests hold together (counted 2026-10-29). A line that mentions tests without a claim wording, a
    planted bug that hung the suite in a list with no test named before it, and a backticked word
    that is not a test are all right. The fourth check covered the three lines that name tests
    before a list, and their five planted-bug references."""
    tests = [f"case_{n:02d}_holds" for n in range(1, 121)]
    bugs = [f"behavior {n:02d} broken" for n in range(1, 121)]
    log = [killed(bug, case) for bug, case in zip(bugs, tests)]
    log[1] = killed(bugs[1], tests[0], tests[1])  # case_02_holds fails only here, second in the list
    log.append(hung("a pattern that backtracks (the round-2 code)"))
    skill = ["# Made-up skill",
             "",
             "The tests need the application's Python, and each test names its source.",
             "Speaker labels are checked by a test (planted bug: behavior 01 broken).",
             "Tests: `case_02_holds`, `case_03_holds` (planted bugs: behavior 02 broken; behavior 03 broken).",
             "Crafted text cannot stall it (planted bug: a pattern that backtracks (the round-2 code)).",
             "`case_04_holds` and `ingest.py` cover this (planted bug: behavior 04 broken)."]
    proof = ["| 1 | Verbatim | Tests: `case_05_holds`, `case_01_holds` (planted bugs: behavior 05 broken; behavior 01 broken) |",
             "The read-back is tested (planted bugs: behavior 06 broken; behavior 07 broken).",
             "A failure while writing leaves nothing behind, with a test (planted bug: behavior 02 broken)."]
    bugs_listed = bugs + ["a pattern that backtracks (the round-2 code)"]
    repo.write(bugs_listed, tests, log, skill, proof, helpers=["make_transcript"])
    outcome = repo.check()
    expect_problems(outcome, [], "fully backed documents")
    expect_count(outcome, lines=3, references=5, label="fully backed documents")
    expect_summary(outcome, claims=5, cited=10, caught=121, failing=120, tests=120, problems=0,
                   label="fully backed documents")


@test
def each_claim_wording_without_a_planted_bug_is_reported(repo):
    """check_claims.py's opening comment: a line claims a test when it says "with a test", "with
    tests", "tests added", "is tested", "are tested", "now tested", "now checked", "checked by",
    "Test:", "Tests:", "test checks" or "tests check"; SKILL.md section 11: such a line in either
    file must name a planted bug. Each line below holds one wording only. Lines that mention tests
    in other words are not claims."""
    wordings = ["Fixed with a test.", "Fixed with tests.", "Tests added after the review.", "The reader is tested.",
                "Both forms are tested.", "Labels are now tested.", "Labels are now checked.",
                "It is checked by the suite.", "Test: the round trip.", "Tests: the round trip.",
                "The rendering test checks it.", "The rendering tests check it."]
    skill = ["# Made-up skill", "",
             "The tests need the application's Python.", "Each test names its source.",
             "A test run takes several minutes.",
             "Fixed with a test (planted bug: alpha broken).", *wordings]
    proof = ["| 3 | Timestamps | Tests: `case_a_holds` |"]
    repo.write(["alpha broken"], ["case_a_holds"], [killed("alpha broken", "case_a_holds")], skill, proof)
    outcome = repo.check()
    first = skill.index(wordings[0]) + 1
    expected = [f"SKILL.md:{first + n}: claims a test but names no planted bug" for n in range(len(wordings))]
    expected.append("PROOF.md:1: claims a test but names no planted bug")
    expect_problems(outcome, expected, "claim wordings")
    expect_summary(outcome, claims=14, cited=1, caught=1, failing=1, tests=1, problems=13, label="claim wordings")


@test
def a_named_planted_bug_must_be_listed_and_shown_caught(repo):
    """SKILL.md section 11: each planted bug named in either file is in planted_bugs.py and is shown
    as caught, that is, marked KILLED in the log. A SURVIVED line, an ERROR line or no line at all
    is not caught; a KILLED line for a name planted_bugs.py does not hold does not make it listed.
    An unlisted name with paired parentheses is reported whole, and the name after it is still read,
    even when a listed name is the start of it. check_claims.py's opening comment: a semicolon
    inside a name's own parentheses does not end the name, and spaces around a name are ignored."""
    planted = ["alpha broken", "beta broken", "gamma broken", "delta broken"]
    log = [killed("alpha broken", "case_a_holds"), survived("beta broken"), not_found("gamma broken"),
           killed("epsilon broken", "case_b_holds")]
    skill = ["Covered (planted bug: alpha broken).",
             "Fixed with a test (planted bugs: beta broken; gamma broken; delta broken).",
             "Covered (planted bug: epsilon broken).",
             "Covered (planted bugs: alpha broken (the round-9 code); beta broken).",
             "Covered (planted bugs: alpha broken (see a; b); beta broken).",
             "Covered (planted bug: alpha broken )."]
    proof = ["Covered (planted bug: alpha brokn)."]
    repo.write(planted, ["case_a_holds", "case_b_holds"], log, skill, proof)
    outcome = repo.check()
    expect_problems(outcome, [
        "SKILL.md:2: planted bug 'beta broken' is not marked KILLED in logs/planted-bugs.txt",
        "SKILL.md:2: planted bug 'gamma broken' is not marked KILLED in logs/planted-bugs.txt",
        "SKILL.md:2: planted bug 'delta broken' is not marked KILLED in logs/planted-bugs.txt",
        "SKILL.md:3: planted bug 'epsilon broken' is not in planted_bugs.py",
        "SKILL.md:4: planted bug 'alpha broken (the round-9 code)' is not in planted_bugs.py",
        "SKILL.md:4: planted bug 'beta broken' is not marked KILLED in logs/planted-bugs.txt",
        "SKILL.md:5: planted bug 'alpha broken (see a; b)' is not in planted_bugs.py",
        "SKILL.md:5: planted bug 'beta broken' is not marked KILLED in logs/planted-bugs.txt",
        "PROOF.md:1: planted bug 'alpha brokn' is not in planted_bugs.py"], "listed and caught")
    expect_summary(outcome, claims=1, cited=11, caught=2, failing=2, tests=2, problems=9, label="listed and caught")


@test
def a_test_never_made_to_fail_is_reported(repo):
    """SKILL.md section 11: each test is made to fail by at least one planted bug, as the KILLED
    lines of the log show. A test named second on a KILLED line counts; a function test_ingest.py
    defines without the @test mark is not a test."""
    planted = ["alpha broken", "beta broken", "gamma broken", "delta broken"]
    log = [killed("alpha broken", "case_a_holds", "case_b_holds"), survived("beta broken"),
           not_found("gamma broken"), hung("delta broken")]
    repo.write(planted, ["case_a_holds", "case_b_holds", "case_c_holds", "case_d_holds"], log,
               ["Nothing is claimed here."], ["Nothing is claimed here either."], helpers=["make_transcript"])
    outcome = repo.check()
    expect_problems(outcome, [
        "test_ingest.py: case_c_holds is never made to fail by a planted bug in logs/planted-bugs.txt",
        "test_ingest.py: case_d_holds is never made to fail by a planted bug in logs/planted-bugs.txt"],
        "tests made to fail")
    expect_summary(outcome, claims=0, cited=0, caught=2, failing=2, tests=4, problems=2, label="tests made to fail")


# The made-up planted bugs, tests and log of the two pairing tests below. The log shows "reader
# skips escaping" making only beta_case fail, "notice removed" alpha_case and gamma_case, and "order
# lost" alpha_case; "pattern backtracks" hung the suite and "label check removed" survived.
PAIRING_PLANTED = ["reader skips escaping", "notice removed", "pattern backtracks (the round-2 code)", "order lost",
                   "label check removed"]
PAIRING_TESTS = ["alpha_case", "beta_case", "gamma_case"]
PAIRING_LOG = [killed("reader skips escaping", "beta_case"), killed("notice removed", "alpha_case", "gamma_case"),
               hung("pattern backtracks (the round-2 code)"), killed("order lost", "alpha_case"),
               survived("label check removed")]


@test
def a_planted_bug_must_fail_a_test_named_before_its_list(repo):
    """SKILL.md section 11 (this round): each planted bug in a list with a test named before it (a
    test_ingest.py function name in backticks, on the list's line, before the list and after any
    earlier list on that line) is shown making at least one of those tests fail, and each mismatch
    is reported with the line, the planted bug and the tests. A planted bug that hung the suite is
    shown making no test fail. A mismatch is reported for any name in a list, not only the first,
    and for any list on a line, not only the first. Right cases: another test named before the list
    fails; a list with no test named before it; backticked words that are not tests, including a
    function without the @test mark; a test named only on an earlier line; a test name without
    backticks, or with "()" inside them. A planted bug that is not listed or not caught gets only
    its old problem. Just before the summary, the run counts the lines and the planted-bug
    references the fourth check covered: here 12 references on 8 lines. (Tests named after a list,
    or before an earlier one, are the next test's subject.)"""
    planted = PAIRING_PLANTED
    skill = ["`alpha_case` checks the escaping (planted bug: reader skips escaping).",
             "`alpha_case` and `beta_case` check it (planted bug: reader skips escaping).",
             "The reader is covered (planted bug: reader skips escaping).",
             "`build_record` in `ingest.py` builds it (planted bug: notice removed).",
             "`alpha_case` checks the notice (planted bug: notice removed). "
             "`beta_case` checks the reader (planted bug: reader skips escaping).",
             "`gamma_case` cannot stall (planted bug: pattern backtracks (the round-2 code)).",
             "`beta_case` is named here alone.",
             "`gamma_case` keeps the order (planted bug: order lost).",
             "`beta_case` covers labels (planted bug: label check removed).",
             "`beta_case` covers labels (planted bug: label check gone).",
             "gamma_case keeps the order too (planted bug: order lost).",
             "`gamma_case()` keeps the order as well (planted bug: order lost).",
             "`alpha_case` checks both (planted bugs: notice removed; reader skips escaping).",
             "`alpha_case` checks the notice (planted bug: notice removed); "
             "`alpha_case` also checks the reader (planted bug: reader skips escaping)."]
    proof = ["| 2 | Attribution | Tests: `beta_case` (planted bugs: notice removed; reader skips escaping) |"]
    repo.write(planted, PAIRING_TESTS, PAIRING_LOG, skill, proof, helpers=["build_record"])
    outcome = repo.check()
    expect_problems(outcome, [
        "SKILL.md:9: planted bug 'label check removed' is not marked KILLED in logs/planted-bugs.txt",
        "SKILL.md:10: planted bug 'label check gone' is not in planted_bugs.py",
        Like("SKILL.md:1: ", "reader skips escaping", "alpha_case"),
        Like("SKILL.md:6: ", "pattern backtracks (the round-2 code)", "gamma_case"),
        Like("SKILL.md:8: ", "order lost", "gamma_case"),
        Like("SKILL.md:13: ", "reader skips escaping", "alpha_case"),
        Like("SKILL.md:14: ", "reader skips escaping", "alpha_case"),
        Like("PROOF.md:1: ", "notice removed", "beta_case")], "pairing")
    expect_count(outcome, lines=8, references=12, label="pairing")
    expect_summary(outcome, claims=1, cited=18, caught=4, failing=3, tests=3, problems=8, label="pairing")


@test
def a_test_named_after_a_list_or_before_an_earlier_list_is_not_paired_with_it(repo):
    """SKILL.md section 11 (this round) states that the fourth check pairs a list only with the
    tests named before it and after any earlier list on its line, not with every test on the line,
    and why: a test named after a list, or before an earlier list, is often there for another
    reason. This shows that narrowing in both directions. Not reported: a list followed by a test
    named as the exception (the shape of PROOF.md line 15 on 2026-10-28); a second list whose only
    test comes before the first list (the shape of PROOF.md line 213); and the stated known miss, a
    list followed by the test it is about, even though that test does not fail under it. Reported:
    a list whose test named before it does not fail, although a test named after the list does;
    and a second list whose test does not fail, although the test before the first list does. The
    fourth check covered 4 references on 3 lines."""
    skill = ["Each refusal checks its reason (planted bug: reader skips escaping), "
             "except `alpha_case`, which checks exit codes.",
             "`gamma_case` checks the notice (planted bug: notice removed); "
             "and the reader was renamed (planted bug: reader skips escaping).",
             "The reader is covered (planted bug: reader skips escaping) by `alpha_case`.",
             "`alpha_case` checks it (planted bug: reader skips escaping), as `beta_case` does too.",
             "`beta_case` checks the reader (planted bug: reader skips escaping); "
             "`alpha_case` checks it too (planted bug: reader skips escaping)."]
    repo.write(PAIRING_PLANTED, PAIRING_TESTS, PAIRING_LOG, skill, ["Nothing here."])
    outcome = repo.check()
    expect_problems(outcome, [Like("SKILL.md:4: ", "reader skips escaping", "alpha_case"),
                              Like("SKILL.md:5: ", "reader skips escaping", "alpha_case")], "narrowed pairing")
    expect_count(outcome, lines=3, references=4, label="narrowed pairing")
    expect_summary(outcome, claims=0, cited=7, caught=4, failing=3, tests=3, problems=2, label="narrowed pairing")


NAMES = ["NOTE, STYLE and REGION blocks skipped unchecked (the round-2 code)",
         "the skill's own reader does not undo the escaping",
         "the speaker" + chr(0x2019) + "s label read as words",
         'a "Name:" label read as words',
         "a label 'Action Item: send' read as a speaker",
         "a mistyped arrow '--)' accepted",
         "an opening '(' in a label accepted",
         "a (+44) country code, written '+(44)', not redacted"]


@test
def planted_bug_names_with_punctuation_are_read_whole(repo):
    """Brief for this round and SKILL.md section 11: a planted bug's name may hold parentheses,
    commas, apostrophes, quotes and colons, a line may cite planted bugs in several lists, and a
    name written exactly as in planted_bugs.py is read whole even when its parentheses do not pair
    up. Read whole, every name below is listed and caught, and every test is made to fail, so there
    is no problem. Names are cited as check_claims.py's opening comment gives: "(planted bug: NAME)"
    or "(planted bugs: NAME; NAME)"."""
    n1, n2, n3, n4, n5, n6, n7, n8 = NAMES
    tests = [f"case_n{n}" for n in range(1, 9)]
    skill = [f"Blocks are checked by a test (planted bugs: {n1}; {n2}; {n3}). Labels too (planted bug: {n4}).",
             f"Tests: `case_n5`, `case_n6` (planted bugs: {n5}; {n6}).",
             f"Arrows (planted bug: {n6}). Labels (planted bug: {n7}). Numbers (planted bugs: {n8}; {n1})."]
    proof = [f"| 7 | `case_n7` and `case_n8` (planted bugs: {n7}; {n8}) |"]
    repo.write(NAMES, tests, [killed(name, case) for name, case in zip(NAMES, tests)], skill, proof)
    outcome = repo.check()
    expect_problems(outcome, [], "names with punctuation")
    expect_summary(outcome, claims=2, cited=12, caught=8, failing=8, tests=8, problems=0, label="names with punctuation")


@test
def spaces_around_a_listed_name_are_ignored_even_when_its_parentheses_do_not_pair_up(repo):
    """SKILL.md section 11 (this round): spaces around a name are ignored, and a name written
    exactly as in planted_bugs.py is read whole, even when its parentheses do not pair up, when
    nothing but spaces comes between it and the next "; ", ")" or the end of the line. So the first
    five lines below, with extra spaces around such names and one list that does not close on its
    line, have no problem. Near misses that must still be reported: such a name followed by other
    words is not that name; a semicolon with no space after it does not separate names; and any
    other name runs to the next "; " or ")" outside its own parentheses, or to the end of the line,
    so the reported names are exactly the ones below."""
    n4, n5, n6, n7 = NAMES[3:7]
    tests = ["case_n4", "case_n5", "case_n6", "case_n7"]
    skill = [f"Covered (planted bug: {n7} ).",
             f"Covered (planted bug:  {n7}).",
             f"Covered (planted bugs: {n6} ; {n4}).",
             f"Wrapped (planted bugs: {n5}; {n6}",
             f"Covered (planted bugs:  {n6}  ;  {n7}  ).",
             f"Extra (planted bug: {n7} twice).",
             f"Extra (planted bugs: {n6}, twice; {n4}).",
             f"Extra (planted bugs: {n4};{n5})."]
    repo.write([n4, n5, n6, n7], tests, [killed(name, case) for name, case in zip([n4, n5, n6, n7], tests)],
               skill, ["Nothing here."])
    outcome = repo.check()
    expect_problems(outcome, [f"SKILL.md:6: planted bug {n7 + ' twice).'!r} is not in planted_bugs.py",
                              f"SKILL.md:7: planted bug {n6[:n6.index(')')]!r} is not in planted_bugs.py",
                              f"SKILL.md:8: planted bug {n4 + ';' + n5!r} is not in planted_bugs.py"],
                    "spaces around listed names")
    expect_summary(outcome, claims=0, cited=11, caught=4, failing=4, tests=4, problems=3,
                   label="spaces around listed names")


@test
def a_cited_name_not_in_planted_bugs_py_is_reported_even_with_an_unmatched_parenthesis(repo):
    """SKILL.md section 11: each planted bug named in either file is in planted_bugs.py. A cited
    name that is not there is reported, not dropped, even when it holds a parenthesis that does
    not pair up; the lines below make no claim, so no other check would notice it. SKILL.md section
    11's known misses: such a name may be cut short at that parenthesis or run on to the end of the
    line, and the names after it in its list are not read; and a list that does not close on its
    line is read to the end of that line, every name in it included (the third line)."""
    n7 = NAMES[6]
    skill = ["Labels are covered (planted bug: an opening '(' in a labl accepted).",
             f"Labels are covered (planted bugs: a stray ')' in a label; {n7}).",
             f"Wrapped (planted bugs: {n7}; a label chek removed"]
    repo.write([n7], ["case_a_holds"], [killed(n7, "case_a_holds")], skill, ["Nothing here."])
    outcome = repo.check()
    expect_problems(outcome, [Like("SKILL.md:1: planted bug ", "in a labl accepted", "is not in planted_bugs.py"),
                              Like("SKILL.md:2: planted bug ", "a stray ", "is not in planted_bugs.py"),
                              "SKILL.md:3: planted bug 'a label chek removed' is not in planted_bugs.py"],
                    "unmatched parenthesis")
    expect_summary(outcome, claims=0, cited=4, caught=1, failing=1, tests=1, problems=3, label="unmatched parenthesis")


PLANTED = [
    # A line that claims a test names a planted bug
    ("a claim line that names no planted bug not reported",
     '                if not named:\n',
     '                if False:\n'),
    ("the 'checked by' wording not read as a claim",
     r'''r"|\bchecked by\b|\bTests?:|\btests? checks?\b", re.I)''',
     r'''r"|\bTests?:|\btests? checks?\b", re.I)'''),
    ("any line that mentions a test read as a claim",
     r'''CLAIM = re.compile(r"\bwith (?:a )?tests?\b|\btests? added\b|\b(?:is|are|now) tested\b|\bnow checked\b"
                   r"|\bchecked by\b|\bTests?:|\btests? checks?\b", re.I)''',
     r'''CLAIM = re.compile(r"\btests?\b", re.I)'''),
    ("PROOF.md left out of the documents checked",
     'DOCS = [SKILL_DIR / "SKILL.md", PACKAGE / "PROOF.md"]',
     'DOCS = [SKILL_DIR / "SKILL.md"]'),

    # Each named planted bug is in planted_bugs.py and is caught
    ("a cited planted bug missing from planted_bugs.py not reported",
     '                    if name not in names:\n',
     '                    if False:\n'),
    ("a planted bug counted as caught when the log names it at all",
     '                    elif name not in killed:\n',
     '                    elif name not in LOG.read_text(encoding="utf-8"):\n'),
    ("log lines split at the first colon (the old code)",
     '            name, colon, tests = line[len(KILLED):].rpartition(": ")',
     '            name, colon, tests = line[len(KILLED):].partition(": ")'),
    ("an unmatched parenthesis in a listed name ends the list (the old code)",
     '    known = sorted(known, key=len, reverse=True)\n',
     '    known = []\n'),
    ("a listed name read as the start of a longer cited name",
     '''            if at == len(line) or line[at] == ")" or line.startswith("; ", at):''',
     '''            if True:'''),
    ("spaces before a listed name not skipped",
     '''            while start < len(line) and line[start] == " ":
                start += 1
''',
     ''),
    ("spaces after a listed name not skipped",
     '''            while at < len(line) and line[at] == " ":
                at += 1
''',
     ''),
    ("a semicolon with no space after it read as the end of a listed name",
     '''            if at == len(line) or line[at] == ")" or line.startswith("; ", at):''',
     '''            if at == len(line) or line[at] in ");":'''),
    ("a listed name at the end of an unclosed list not read whole",
     '''            if at == len(line) or line[at] == ")" or line.startswith("; ", at):''',
     '''            if line[at:at + 1] == ")" or line.startswith("; ", at):'''),
    ("only the first name of an unclosed list read",
     '''                stop = min(end + 1, len(line))
''',
     '''                stop = min(end + 1, len(line))
                names = names[:1] if end >= len(line) else names
'''),
    ("parentheses inside an unlisted name not paired",
     '''                    depth += {"(": 1, ")": -1}.get(line[end], 0)''',
     '''                    depth += 0'''),
    ("a semicolon inside a name's own parentheses ends the name",
     '''                while end < len(line) and not (depth == 0 and (line[end] == ")" or line.startswith("; ", end))):''',
     '''                while end < len(line) and not ((depth == 0 and line[end] == ")") or line.startswith("; ", end)):'''),
    ("spaces around a cited name kept",
     '''                names.append(line[position:end].strip())''',
     '''                names.append(line[position:end])'''),
    ("an unclosed planted-bug list dropped (the old code)",
     '''            if line[position:end].strip():''',
     '''            if line[position:end].strip() and end < len(line):'''),

    # Each test is made to fail
    ("a test never made to fail not reported",
     '        if test not in failing:\n',
     '        if False:\n'),
    ("functions without the @test mark counted as tests",
     '''    return [node.name for node in tree.body if isinstance(node, ast.FunctionDef)
            and any(getattr(decorator, "id", "") == "test" for decorator in node.decorator_list)]''',
     '''    return [node.name for node in tree.body if isinstance(node, ast.FunctionDef)]'''),
    ("only the first test on a log line counted as failing",
     '''tests.split(", ") if test.strip())''',
     '''tests.split(", ")[:1] if test.strip())'''),

    # Each planted bug in a list fails a test named before that list
    ("the pairing check removed",
     '                        if not set(before) & set(shown[name]):',
     '                        if False:'),
    ("pairing checked against every test any planted bug makes fail",
     '                        if not set(before) & set(shown[name]):',
     '                        if not set(before) & failing:'),
    ("only the first test named before a list paired",
     '                        if not set(before) & set(shown[name]):',
     '                        if not set(before[:1]) & set(shown[name]):'),
    ("a list with no test named before it checked against an empty list of tests",
     '                    elif before:\n',
     '                    elif True:\n'),
    ("only the first planted bug in a list paired",
     '                    elif before:\n',
     '                    elif before and name == listed[0]:\n'),
    ("every test on a line paired with every list on it (the line rule)",
     '                before = list(dict.fromkeys(test for at, test in spans if after <= at < start))',
     '                before = list(dict.fromkeys(test for at, test in spans))'),
    ("tests named after a list paired with it",
     '                before = list(dict.fromkeys(test for at, test in spans if after <= at < start))',
     '                before = list(dict.fromkeys(test for at, test in spans if after <= at))'),
    ("tests named before an earlier list paired with a later one",
     '                after = stop\n',
     ''),
    ("only the first list on a line paired",
     '                after = stop\n',
     '                after = len(line)\n'),
    ("tests found in the whole document, not on the line",
     'CODE_SPAN.finditer(line)',
     'CODE_SPAN.finditer(doc.read_text(encoding="utf-8"))'),
    ("any backticked word counted as a test",
     ' for span in CODE_SPAN.finditer(line) if span.group(1) in known_tests]',
     ' for span in CODE_SPAN.finditer(line)]'),
    ("test names found on a line without backticks",
     '            spans = [(span.start(), span.group(1)) for span in CODE_SPAN.finditer(line) if span.group(1) in known_tests]',
     '            spans = [(line.find(test), test) for test in tests if test in line]'),
    ("the pairing problem leaves out the tests named before the list",
     '''f"named before its list fail ({', '.join(before)}); "''',
     '''f"named before its list fail; "'''),

    # Output and exit code
    ("the exit code 0 even when problems are found",
     '    return 1 if problems else 0',
     '    return 0'),
    ("a new count added to the old summary line",
     '''          f"planted bug, {len(problems)} problem(s)")''',
     '''          f"planted bug, {paired_lines} line(s) with a test named before a list, {len(problems)} problem(s)")'''),
    ("the count of lines with a test named before a list not printed",
     '''    print(f"{paired_lines} line(s) with a test named before a planted-bug list, {paired} planted-bug reference(s) "
          f"checked against the tests named before their list")
''',
     ''),
    ("each checked reference counted as a line",
     '                paired_lines += 1\n',
     '                paired_lines += checked\n'),
]


def run_planted():
    """Break one behavior at a time in a temporary copy of check_claims.py and run this self-test
    against the copy. Each planted bug must turn the self-test red (KILLED)."""
    source = CHECKER.read_text(encoding="utf-8")
    survived_count = 0
    for name, old, new in PLANTED:
        if source.count(old) != 1:
            print(f"ERROR     {name}: the code to break was not found exactly once")
            survived_count += 1
            continue
        with tempfile.TemporaryDirectory() as root:
            copy = Path(root) / "check_claims.py"
            copy.write_text(source.replace(old, new), encoding="utf-8")
            env = dict(os.environ, CHECK_CLAIMS_UNDER_TEST=str(copy), PYTHONDONTWRITEBYTECODE="1")
            try:
                result = subprocess.run([sys.executable, "-B", str(Path(__file__).resolve())], env=env,
                                        capture_output=True, text=True, timeout=LIMIT * 10)
            except subprocess.TimeoutExpired:
                print(f"KILLED    {name}: the self-test hung and was stopped after {LIMIT * 10} seconds")
                continue
        failed = [line.split(":")[0][6:] for line in result.stdout.splitlines() if line.startswith("FAIL")]
        if result.returncode:
            print(f"KILLED    {name}: {', '.join(failed) or 'exit code ' + str(result.returncode)}")
        else:
            print(f"SURVIVED  {name}")
            survived_count += 1
    print(f"\n{len(PLANTED) - survived_count} of {len(PLANTED)} planted bugs caught")
    return 1 if survived_count else 0


def main():
    if sys.argv[1:] == ["--planted"]:
        return run_planted()
    failures = 0
    for function in TESTS:
        try:
            run(function)
            print(f"PASS  {function.__name__}")
        except Exception as error:  # report every failure, then exit non-zero
            failures += 1
            print(f"FAIL  {function.__name__}: {type(error).__name__}: {error}")
    print(f"\n{len(TESTS) - failures} passed, {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
