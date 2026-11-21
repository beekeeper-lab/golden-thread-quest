# Proof · trello-duplicate-search

Attempt: `trello-attempt-004`

## How this was made

An AI assistant (Claude) wrote the search, the two made-up boards, the tests, the recording scripts and this
file, at the participant's direction. The work was done in small steps, each shown to the participant before
the next.

What the participant did themself:

- Chose the design from options before anything was written: five weighted signals beyond the name with a
  three-signal rule; one index for each board with the search reading several; and a recommendation in which
  the board decides between link and archive-as-duplicate.
- Decided the outcome for the proposed card in the report: **link**. They ran the search in their own
  terminal with `--decision link`, which wrote `report.md`. The assistant did not choose or record the decision.

Statements below are marked **recorded** (the log `logs/duplicate-run.txt` shows it, against made-up records),
**tested** (a passing test shows it, with the output in `logs/tests.txt`) or **not assessed**. Nothing here
was run against a real Trello board. The quest asks for a local search and says no Trello call is needed.

## What was built

A search, `participant/skills/trello-duplicate-search/search.py`, that takes a proposed card and looks through
the index of every board it is given for cards that are probably the same work.

The fixture is two made-up boards, a platform team's with 6 cards and a support team's with 4. Each card
record was written by the card reader approved in the `trello-read-card` quest, handed a made-up Trello answer.
Each board's index was built by the generator approved in the `trello-build-index` quest. Neither skill was
changed. `fixture.md` puts both indexes side by side and marks the planted cards:

| Planted | Card | Board |
|---|---|---|
| True duplicate of proposal 1, under a different name | …201, "Let admins download their contacts in a spreadsheet" | Support |
| Near duplicate of proposal 1: a one-off export of the same list, not the feature | …101 | Platform |
| An archived earlier card for the work in proposal 1 | …102 | Platform |
| Same name as proposal 2, unrelated work | …103, "Update the onboarding checklist" | Platform |

One more card, …105, has a name and a description worded as orders to the search tool.

## The confidence scale

Six things are compared. Five are signals beyond the name. Each has points for how far it is trusted.

| Signal | Points | Why that many |
|---|---|---|
| Description | 4 | The most text, so the hardest to match by chance. |
| Checklist | 3 | The steps of the work. Two cards with the same steps are rarely different work. |
| Labels | 2 | Says the area, not the task. Many cards share a label. |
| Members | 2 | The same person is often on many cards. |
| Due date | 1 | Weak alone: many cards are due in the same week. |
| Name | 1 | The weakest, as the quest's hint says. It never counts towards the three. |

A card is a candidate only when at least three of the five signals beyond the name match. The score is the
points of everything that matched, out of 13.

| Confidence | Score | What it means |
|---|---|---|
| high | 10 to 13 | Needs the description or the checklist, and usually both. Treat as the same work unless a look says otherwise. |
| medium | 7 to 9 | Strong overlap with something missing. Look before creating. |
| low | 5 or 6 | The three weakest signals, or those and the name. Same area, same person, same week: possibly the same work. |

5 is the least three signals can add up to (labels, members, due date). The cut-offs are the assistant's
judgement, agreed by the participant as a design. They were not tuned on real cards.

What the weights change (the first stretch goal, in part): in the recorded run the archived card …102 and the
near duplicate …101 each match on three signals beyond the name. Counting signals would tie them. The points
put …102 at 10, high, because it shares the checklist, and …101 at 9, medium, because it shares a member
instead. **recorded**, part 2.

## The acceptance criteria, one by one

**1. The search uses at least three signals beyond the name.** It compares five: description, checklist,
labels, members and due date. A candidate needs three of them. **tested**: `ThreeBeyondTheName` (the same name
alone, the same name with two other signals, and two signals beyond the name are each not a candidate; three
are), and `EachSignal`, 17 tests on the thresholds. **recorded**: part 2, the duplicate matched on all five.

**2. Each match lists the signals and a confidence.** Every candidate shows all six lines, each as MATCHED
with its points, no, or not comparable, with what was found, then the confidence and the score out of 13.
**recorded**: part 2, "every candidate lists all six signals and a confidence". **tested**: `Confidence`
checks the boundaries 5, 6, 7, 9, 10 and 13, and `Report` checks every candidate in the Markdown report.

**3. Cards on other boards are searched.** Every board folder is read. **recorded**: part 2, card …201 is
found on another board than the proposal's; part 4, "all 10 cards on both boards were compared"; part 8, with
the support board removed from a copy, …201 is not found. **tested**: `AcrossBoards`, including that a label is
matched by name because its id differs on each board, and that a folder that is not a board stops the search
rather than being skipped.

**4. A same-name unrelated card is not reported as a duplicate.** **recorded**: part 3. The proposal "Update
the onboarding checklist" returns RESULT: NONE, and card …103, with exactly that name, is listed as looked at
and not reported: "matched on name only. The name is alike and nothing else is." In the same run card …203
matched on two signals and is not reported either. **tested**: `TheFixture` and `ThreeBeyondTheName`.

**5. A true duplicate with a different name is found.** **recorded**: part 2. Card …201 shares no meaningful
word of its name with the proposal, the name line says no, and it is the first candidate: HIGH, 12 of 13.
**tested**: `test_the_duplicate_with_a_different_name_on_another_board_is_found`.

**6. A proposal with no match reports none.** **recorded**: part 4. "RESULT: NONE. No card on any board
searched matches this proposal on three or more signals beyond the name", with no candidate and no near miss
listed, and exit code 0. **tested**: `test_a_proposal_with_no_match_reports_none`.

**7. The recommendation is link, archive-as-duplicate or proceed, a person decides, and the search does not
change the index.**

- *The three words.* **recorded**: part 5 shows all three in one run. **tested**: `Confidence` and `Finished`.
  The same card …201 is LINK when the new card is for the platform board and ARCHIVE-AS-DUPLICATE when it is
  for the support board, where …201 is. An archived card is PROCEED.
- *A person decides.* The search prints that it has created, linked, archived and changed nothing. A report
  written with no `--decision` says "Not yet decided". **recorded**: part 7. **tested**: `Report`, including
  that a decision does not change anything above it in the report. The participant's decision, link, is in
  `report.md`. **recorded**: AFTERWARDS.
- *The index is unchanged.* The recording script took the SHA-256 of all 16 files in the boards folder before
  the first search and after the last, and they are the same. Each index still passes the generator's check.
  **recorded**: part 6. A stale index is refused and is not rebuilt by the search. **recorded**: part 7.
  **tested**: `NothingChanges` and `StaleIndex`.

## Where the important artifacts are

| What | Path |
|---|---|
| The fixture overview | `participant/context/trello/duplicates/fixture.md` |
| The two boards, records and indexes | `participant/context/trello/duplicates/boards/` |
| The four proposals | `participant/context/trello/duplicates/proposals/` |
| The report, with the decision | `participant/context/trello/duplicates/report.md` |
| The search and how to use it | `participant/skills/trello-duplicate-search/search.py`, `SKILL.md` |
| The tests | `participant/skills/trello-duplicate-search/tests/test_search.py` |
| The run log | `logs/duplicate-run.txt` |
| The test output | `logs/tests.txt` |
| The planted-bugs log | `logs/planted-bugs.txt` |
| The scripts that made the fixture and the logs | `scripts/` |

The quest names `participant/evidence/trello-duplicate-search/attempt-001/`. The application created this
attempt as `trello-attempt-004`. Copies of this file and of `logs/duplicate-run.txt` are in `attempt-001/`,
with a note saying so.

## How to reproduce the behavior

From the repository root. None of these contacts anything.

    python3 participant/evidence/trello-duplicate-search/trello-attempt-004/scripts/make_fixture.py
    python3 participant/skills/trello-duplicate-search/search.py --proposal participant/context/trello/duplicates/proposals/1-duplicate-on-another-board.json
    python3 participant/skills/trello-duplicate-search/search.py --proposal participant/context/trello/duplicates/proposals/2-same-name-unrelated.json
    python3 participant/skills/trello-duplicate-search/search.py --proposal participant/context/trello/duplicates/proposals/3-no-match.json
    python3 -m unittest discover -s participant/skills/trello-duplicate-search/tests -v
    python3 participant/evidence/trello-duplicate-search/trello-attempt-004/scripts/planted_bugs.py
    python3 participant/evidence/trello-duplicate-search/trello-attempt-004/scripts/record_evidence.py

The first command makes the boards again. They come out byte for byte the same, so the indexes still match.
The report is written by adding `--report participant/context/trello/duplicates/report.md --decision link` to
the second command.

## What was tested or validated

| Check | Result | Where |
|---|---|---|
| Unit tests | 76 pass | `logs/tests.txt` |
| Planted bugs: 26 faults put into `search.py` one at a time | all 26 caught by at least one test; the file restored byte for byte | `logs/planted-bugs.txt` |
| Recorded run, parts 1 to 8 and AFTERWARDS | 47 checks pass | `logs/duplicate-run.txt` |

The planted bugs include the two the quest turns on: the name counted as one of the three signals, and a
candidate needing its name to match. Three tests were wrong when first run and were corrected. In each case
the test was at fault, not the search: one read signals from a result that leaves out cards matching nothing,
one copied a board folder without rebuilding its index, and one counted a line of the search's own
description as an import.

## Remaining limitations

- **Made-up boards only.** Not assessed on real cards. Real descriptions are longer, messier and often empty.
- **The assistant wrote both the fixture and the search.** The planted cards fit the search's rules. A
  duplicate written by someone else, in their own words, is a harder test and has not been run.
- **Words are compared as written.** The search does not know that two different words mean the same thing.
  The true duplicate is found because its description, checklist, labels, member and due date agree, not
  because "contacts" was understood as "customers". A duplicate with a different name, different wording and
  no shared label or member would be missed.
- **A sparse card cannot be a candidate.** Three of the five fields must be filled in on both sides and
  match. A card with only a name and a description, however alike, is listed at most as looked at and not
  reported. On a board where cards are mostly bare, this search would report almost nothing.
- **The thresholds are judgement.** Half of the shorter description, three days, 10 points for high: none was
  measured against real duplicates.
- **Comments and attachments are not compared.**
- **Finished is narrow.** An archived card, an archived list or a due date marked complete. A card sitting in a
  list called "Done" with no due date counts as open.
- **One decision for the proposal,** not one for each candidate. And the search cannot know that the decision
  it is given was made by a person. It records what it is given and says who is meant to give it.
- **Nothing is carried out.** No card is created, linked or archived. That would be a write to Trello, which
  this quest does not include.
- **Stretch goals.** The signals are weighted and one effect is shown above. Clustering duplicates into groups
  is not done.

## Reflection

*What does a false duplicate cost on a shared board?*

More than a missed one looks like it should. If the search calls a card a duplicate when it is not, the likely
result is that the new card is not created, or an existing one is archived, and a piece of real work
disappears from the board without anyone deciding to drop it. On a shared board the person who loses the card
is often not the person who ran the search, so they find out late, when the work is missed. There is a second
cost: after a few false alarms people stop reading the matches, and then the true ones are ignored too.

That is why this search needs three signals beyond the name before it says anything, never recommends
archiving a card on another team's board, and stops at a recommendation. A false "link" costs someone a minute
to look. A false "archive" costs a team its card.

## Sensitive values

No credential is involved: the search reads local files and has no code that reads the environment or
contacts a network. Every board, list, card and member id in the fixture, the report and the logs is made up.
The logs show the temporary folder as COPY. No personal name, email address, site address or home-folder path
is in the evidence.
