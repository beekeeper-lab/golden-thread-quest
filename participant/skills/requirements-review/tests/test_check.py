"""Tests for the findings checker, check.py. Local files only, in temporary folders.

Run from the repository root:
    python3 -m unittest discover -s participant/skills/requirements-review/tests -v
"""
import contextlib
import hashlib
import io
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import check  # noqa: E402

REQUIREMENTS = """# A made-up set

## Document A

**REQ-01** The system shall let a member sign in with a card number and a 6-digit PIN.

**REQ-02** The page shall load quickly for every member.

**REQ-03** A member shall be able to cancel at any time before the start.

**REQ-04** The system shall not accept a cancellation less than two hours
before the start.

## Document B

**NFR-01** The system shall be pleasant to use.
"""

FINDINGS = """# Findings

1. **Contradictory.** No system could satisfy both.
2. **Untestable.** No observation could show it is met.
3. **Incomplete.** A fact a tester needs is absent.
4. **Vague.** A word has more than one reading.

## F-01
- Requirement: REQ-03 and REQ-04
- Type: contradictory
- Words in REQ-03: "at any time before the start"
- Words in REQ-04: "shall not accept a cancellation less than two hours before the start"
- A tester could not decide: whether a cancellation one hour before the start is accepted.
- If unanswered: one of the two requirements fails whatever is built.
- Question: In the last two hours, may a member cancel?

## F-02
- Requirement: REQ-02
- Type: vague
- Words: "quickly"
- A tester could not decide: what load time to pass or fail.
- If unanswered: the developer and the tester each pick a different number.
- Question: Within how many seconds must the page load, and measured where?

## F-03
- Requirement: NFR-01
- Type: untestable
- Words: "pleasant to use"
- A tester could not decide: what to observe at all.
- If unanswered: nothing can show the requirement is met.
- Question: What that can be observed would show the system is pleasant to use?

## Unflagged

- REQ-01: the credentials are stated exactly, so there is one expected result.
"""


class Case(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.requirements = os.path.join(tmp.name, "requirements.md")
        self.findings = os.path.join(tmp.name, "findings.md")
        self.write(REQUIREMENTS, FINDINGS)

    def write(self, requirements=None, findings=None):
        for path, text in ((self.requirements, requirements), (self.findings, findings)):
            if text is not None:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(text)

    def run_check(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = check.main(["--requirements", self.requirements, "--findings", self.findings])
        return code, out.getvalue()

    def broken(self, old, new, rule, phrase):
        self.assertIn(old, FINDINGS)
        self.write(findings=FINDINGS.replace(old, new))
        code, text = self.run_check()
        self.assertEqual(code, 1, text)
        self.assertIn("RESULT: NOT ACCEPTED.", text)
        self.assertIn("rule %d: " % rule, text)
        self.assertIn(phrase, text)


class AGoodReview(Case):
    def test_it_is_accepted_and_printed(self):
        code, text = self.run_check()
        self.assertEqual(code, 0, text)
        for phrase in ("FINDINGS, 3, on 4 requirements:", "By type: contradictory 1, untestable 1, incomplete 0, vague 1.",
                       "UNFLAGGED, 1 requirements left alone", "REQ-01  the credentials are stated exactly",
                       "ACCOUNTED FOR: 4 with a finding + 1 unflagged = 5 of 5 requirements.", "RESULT: THE REVIEW KEEPS ALL ITS RULES."):
            self.assertIn(phrase, text)

    def test_it_says_what_it_cannot_check(self):
        self.assertIn("Whether each judgment is right is not something it can check.", self.run_check()[1])

    def test_it_writes_nothing(self):
        def state():
            found = []
            for path in (self.requirements, self.findings):
                with open(path, "rb") as f:
                    found.append(hashlib.sha256(f.read()).hexdigest())
            return found + \
                sorted(os.listdir(os.path.dirname(self.findings)))
        before = state()
        self.run_check()
        self.assertEqual(state(), before)

    def test_a_requirement_that_runs_over_two_lines_is_read_whole(self):
        self.assertEqual(check.read_requirements(self.requirements)["REQ-04"],
                         "The system shall not accept a cancellation less than two hours before the start.")

    def test_a_requirement_may_have_more_than_one_finding(self):
        extra = FINDINGS.replace("## Unflagged", "## F-04\n- Requirement: REQ-02\n- Type: incomplete\n- Words: \"every member\"\n"
                                 "- A tester could not decide: which connection a member is on.\n- If unanswered: the test passes on a fast line only.\n"
                                 "- Question: On what connection is the load time measured?\n\n## Unflagged")
        self.write(findings=extra)
        self.assertEqual(self.run_check()[0], 0)

    def test_the_review_in_the_repository_keeps_its_rules(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = check.main([])
        self.assertEqual(code, 0, out.getvalue())


class Rule1Type(Case):
    def test_a_type_outside_the_four_is_refused(self):
        for value in ("ambiguous", "vague or incomplete", "Vague", ""):
            self.broken("- Type: vague", "- Type: %s" % value, 1, "F-02 does not name one of the four types")

    def test_a_missing_type_line_is_refused(self):
        self.broken("- Type: vague\n", "", 1, "F-02 does not name one of the four types")

    def test_two_findings_with_one_name_are_refused(self):
        self.broken("## F-03", "## F-02", 1, "F-02 appears twice")

    def test_no_findings_at_all_is_refused(self):
        self.write(findings=FINDINGS.split("## F-01")[0] + "## Unflagged\n\n" + "".join(
            "- %s: there is one expected result for this requirement.\n" % r for r in ("REQ-01", "REQ-02", "REQ-03", "REQ-04", "NFR-01")))
        code, text = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("the findings file holds no findings", text)


class Rule2Words(Case):
    def test_words_that_are_not_in_the_requirement_are_refused(self):
        self.broken('- Words: "quickly"', '- Words: "fast"', 2, 'F-02 quotes words that are not in REQ-02: "fast"')
        self.broken('- Words: "quickly"', '- Words: "Quickly"', 2, "F-02 quotes words that are not in REQ-02")
        self.broken('- Words: "pleasant to use"', '- Words: "pleasant to  use!"', 2, "F-03 quotes words that are not in NFR-01")

    def test_words_from_another_requirement_are_refused(self):
        self.broken('- Words: "quickly"', '- Words: "6-digit PIN"', 2, "F-02 quotes words that are not in REQ-02")

    def test_words_not_in_quotes_or_missing_are_refused(self):
        self.broken('- Words: "quickly"', "- Words: quickly", 2, "F-02 has a Words line that is not text inside double quotes")
        self.broken('- Words: "quickly"\n', "", 2, "F-02 quotes no words")

    def test_a_requirement_that_does_not_exist_is_refused(self):
        self.broken("- Requirement: REQ-02", "- Requirement: REQ-99", 2, "F-02 names REQ-99, which is not in the requirements file")

    def test_a_quote_split_over_a_line_break_in_the_requirement_still_matches(self):
        self.assertEqual(self.run_check()[0], 0, "F-01 quotes words that span two lines of REQ-04")


class Rule3Tester(Case):
    def test_what_a_tester_could_not_decide_must_be_said(self):
        self.broken("- A tester could not decide: what load time to pass or fail.\n", "", 3, "F-02 does not say: A tester could not decide")
        self.broken("- A tester could not decide: what load time to pass or fail.", "- A tester could not decide: n/a", 3, "F-02 does not say")

    def test_what_goes_wrong_if_unanswered_must_be_said(self):
        self.broken("- If unanswered: nothing can show the requirement is met.\n", "", 3, "F-03 does not say: If unanswered")


class Rule4Contradiction(Case):
    def test_a_contradiction_must_name_two_requirements(self):
        self.broken("- Requirement: REQ-03 and REQ-04", "- Requirement: REQ-03", 4, "F-01 is a contradiction and names 1 requirement, where it must name two")

    def test_a_contradiction_must_quote_both(self):
        self.broken('- Words in REQ-04: "shall not accept a cancellation less than two hours before the start"\n', "", 4,
                    "F-01 is a contradiction and quotes no words from REQ-04")

    def test_each_quote_must_be_in_its_own_requirement(self):
        self.broken('- Words in REQ-03: "at any time before the start"', '- Words in REQ-03: "less than two hours"', 2,
                    "F-01 quotes words that are not in REQ-03")

    def test_only_a_contradiction_may_name_two(self):
        self.broken("- Requirement: REQ-02", "- Requirement: REQ-02 and REQ-01", 1, "F-02 names more than one requirement and is not a contradiction")


class Rule5Accounted(Case):
    def test_a_requirement_with_no_finding_and_not_unflagged_is_refused(self):
        self.broken("- REQ-01: the credentials are stated exactly, so there is one expected result.\n", "", 5,
                    "REQ-01 has no finding and is not listed as unflagged, so it is not accounted for")

    def test_a_requirement_both_flagged_and_unflagged_is_refused(self):
        self.broken("## Unflagged\n", "## Unflagged\n\n- REQ-02: it reads well enough for a tester to proceed with.", 5,
                    "REQ-02 has a finding (F-02) and is also listed as unflagged")

    def test_an_unflagged_requirement_needs_a_reason(self):
        self.broken("- REQ-01: the credentials are stated exactly, so there is one expected result.", "- REQ-01: fine", 5,
                    "REQ-01 is listed as unflagged with no reason to speak of")
        self.broken("- REQ-01: the credentials are stated exactly, so there is one expected result.", "- REQ-01", 5, "could not be read")

    def test_unflagged_lines_must_be_real_and_single(self):
        line = "- REQ-01: the credentials are stated exactly, so there is one expected result."
        self.broken(line, line + "\n" + line, 5, "REQ-01 is listed as unflagged twice")
        self.broken(line, line + "\n- REQ-77: this one is clear and measurable in every respect.", 5, "REQ-77 is listed as unflagged and is not in the requirements file")


class Rule6AsksAndDoesNotRewrite(Case):
    def test_a_finding_must_ask_a_question(self):
        self.broken("- Question: Within how many seconds must the page load, and measured where?", "- Question: State the number of seconds.", 6,
                    "F-02 does not ask a question")
        self.broken("- Question: Within how many seconds must the page load, and measured where?\n", "", 6, "F-02 does not ask a question")

    def test_a_finding_that_offers_wording_is_refused(self):
        for phrase in ("It should read: within 2 seconds. Agreed?", "Could this be changed to 'within 2 seconds'? Change to that?",
                       "Suggested wording: within 2 seconds?", "Replace with 'within 2 seconds'?"):
            self.write(findings=FINDINGS.replace("- Question: Within how many seconds must the page load, and measured where?", "- Question: " + phrase))
            code, text = self.run_check()
            self.assertEqual(code, 1, phrase)
            self.assertIn("F-02 offers wording in place of a question", text)

    def test_a_finding_about_a_person_is_refused(self):
        self.broken("- If unanswered: the developer and the tester each pick a different number.",
                    "- If unanswered: the author did not think about what the tester needs here.", 6, "F-02 is about a person and not about the words")


class Rule7Definitions(Case):
    def test_each_type_must_be_defined_in_the_file(self):
        self.broken("4. **Vague.** A word has more than one reading.\n", "", 7, "the findings file does not define the type 'vague'")

    def test_the_definitions_must_be_in_the_order_they_are_applied(self):
        swapped = FINDINGS.replace("1. **Contradictory.** No system could satisfy both.\n", "").replace(
            "4. **Vague.** A word has more than one reading.\n", "4. **Vague.** A word has more than one reading.\n5. **Contradictory.** No system could satisfy both.\n")
        self.write(findings=swapped)
        code, text = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("rule 7: the definitions are not given in the order they are applied", text)


class Files(Case):
    def test_a_missing_or_unusable_file_stops_the_check(self):
        self.write(requirements="# Nothing here\n\nSome prose with no identifiers.\n")
        code, text = self.run_check()
        self.assertEqual(code, 2)
        self.assertIn("STOPPED: no requirement identifiers", text)
        self.write(requirements=REQUIREMENTS + "\n**REQ-01** A second requirement with the same name.\n")
        self.assertIn("two requirements called REQ-01", self.run_check()[1])
        os.remove(self.findings)
        self.assertEqual(self.run_check()[0], 2)

    def test_the_checker_reads_and_does_nothing_else(self):
        with open(check.__file__, encoding="utf-8") as f:
            source = f.read()
        for word in ('"w"', "os.remove", "urllib", "socket", "subprocess", "os.system", "eval(", "exec("):
            self.assertNotIn(word, source)


if __name__ == "__main__":
    unittest.main()
