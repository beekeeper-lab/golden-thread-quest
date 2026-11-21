# Requirements review

Written by an AI assistant (Claude) at the participant's direction.

## 1. Purpose

This skill is a way of reviewing a requirements set for four kinds of defect, and a checker that holds the
written review to its own rules.

The review is a judgment. A person or an assistant reads the requirements and decides which words fail and
why. `check.py`, beside this file, does not make that judgment and cannot. It checks the form of what was
written, so that a finding cannot be loose in the ways that make a review useless.

    python3 participant/skills/requirements-review/check.py

It reads `participant/context/ambiguity/requirements.md` and `findings.md`, or the files given with
`--requirements` and `--findings`. It writes nothing.

## 2. How a requirement is judged

One question decides whether there is a defect at all: would two competent testers, reading only this text,
write the same test? If they would, the requirement is sound. A word that a glossary or another requirement
defines is read with that definition.

If they would not, four questions are asked in this order, and the first answered yes gives the type.

| Order | Type | The question |
|---|---|---|
| 1 | contradictory | Is there another requirement such that no system could satisfy both, on every reasonable reading of both? |
| 2 | untestable | Is there no observation that could show the requirement is met, however its words are read? One that can be shown broken and never shown met counts. |
| 3 | incomplete | Is the fact the finding's question asks for absent, with no word in the requirement speaking of it at all? |
| 4 | vague | Does a word speak of it, in a way that has more than one reasonable reading? |

The full wording, and what it still leaves to judgment, is at the top of the findings file, which is where a
reader of the findings needs it.

## 3. How a review is made

1. Agree the definitions before reading the requirements.
2. First pass. Write down every finding raised.
3. Second look. Hold each finding to three tests: do the quoted words cause the problem; would two testers
   write different tests; what goes wrong if the question is never answered. Withdraw what does not survive,
   and say why.
4. List every requirement left alone, with the reason it is sound.
5. Run the checker.

A finding asks a question. It does not offer wording for the requirement, because what the requirement should
say is for whoever owns it. A finding is about words, and never about whoever wrote them.

Something no requirement says is a gap in the set and not a finding against a requirement. It is noted
separately.

## 4. What the checker holds a review to

| Rule | What it checks |
|---|---|
| 1 | Every finding names exactly one of the four types. Only a contradiction names two requirements. |
| 2 | The words a finding quotes are in the requirement it names, character for character. |
| 3 | Every finding says what a tester could not decide, and what goes wrong if its question is unanswered. |
| 4 | A contradiction names two requirements and quotes words from both. |
| 5 | Every requirement is accounted for once: it has a finding, or it is listed as unflagged with a reason. |
| 6 | Every finding asks a question, offers no replacement wording, and is not about a person. |
| 7 | The findings file carries the four definitions, in the order they are applied. |

It prints each finding, each unflagged requirement with its reason, and the count that shows every requirement
is accounted for.

Exit codes: 0 the review keeps all its rules. 1 it breaks one, which is named. 2 a file could not be read.

## 5. The findings file

One section for each finding:

    ## F-01
    - Requirement: REQ-03
    - Type: vague
    - Words: "quickly"
    - A tester could not decide: ...
    - If unanswered: ...
    - Question: ...?

A contradiction names two requirements joined by "and", with a `Words in REQ-…` line for each. Under
`## Unflagged` is one line for each requirement left alone: `- REQ-01: the reason it is sound`.

## 6. Tests

    cd participant/skills/requirements-review && python3 -m unittest discover -s tests -v

## 7. What it does not do

- It does not find defects. It cannot tell a sound requirement from a defective one.
- It does not check that a finding is right, that its type is the right one, or that a reason given for
  leaving a requirement alone is true.
- Its check for replacement wording is a list of phrases. Wording offered in other words would pass.
- It reads requirements identified as `REQ-` or `NFR-` and a number.
