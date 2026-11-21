# Proof · trello-build-index

Attempt: `trello-attempt-003`

## How this was made

An AI assistant (Claude) wrote the generator, the made-up board, the tests, the recording scripts and this
file, at the participant's direction. The work was done in small steps, each shown to the participant before
the next.

What the participant did themself:

- Chose what to index: a made-up fixture board for the required evidence, plus one real, read-only run on
  their own sandbox board.
- Agreed the design before anything was written: where list order comes from, what happens to archived lists
  and cards, what counts as a gap, and that no build time is stored in the index.
- Ran the real run in their own terminal, twice. The assistant did not contact Trello and did not see or
  handle the key or the token. It read the saved logs afterwards.

Statements below are marked **recorded** (the log `logs/index-run.txt` shows it, against made-up records),
**observed** (the participant's real run shows it, in `logs/live-index-run.txt`), **tested** (a passing test
shows it, with the output in `logs/tests.txt`) or **not assessed**.

## Where the records came from

The index needs two kinds of record, kept together in one records folder.

- **Card records.** Each was written by the card reader approved in the `trello-read-card` quest, called
  unchanged by `scripts/make_fixture.py` and handed a made-up Trello answer for each card. So each record is
  in the format that reader writes, `trello-card/1`, and none was typed by hand.
- **A board record,** `board.json`, in the shape the board reader of the `trello-read-board` quest writes: the
  board and its lists, each with id, name, position and whether it is archived.

The made-up board is awkward on purpose. Its open lists are To do, Doing, In review and Done, in that order by
position, which is not their order by name. A fifth list is archived. Among its 12 cards are one archived
card, one on the archived list, one on a list the board record does not have, one whose record has no position
and no members field, one whose name is full of table characters, and one whose name is worded as an
instruction to the index tool.

## How list order is kept (criterion 2)

A card record names its list by the list's id and says nothing else about the list. So the order of lists
cannot come from the cards. It comes from the board record.

- **Lists** are sorted by Trello's position number, `pos`, smallest first. If two lists share a position, the
  list id decides. This is the quest's hint. Names take no part: **tested** with a board whose record holds
  the lists in another order and whose names sort differently, and with two lists at one position.
- **Cards in a list** are sorted the same way, by the card's `pos` and then its id. Positions are compared as
  numbers, so 100.5 comes after 20. **Tested.**
- **Archived lists** come after the open lists, under their own heading, still in position order. Trello does
  not show them on the board, so placing them between the open lists would show a board nobody sees. Leaving
  them out would lose their cards, which criterion 3 forbids. **Recorded**, part 2: Abandoned, at position
  2500, is list 5 under "Archived lists" and keeps its card.
- **An archived card** stays in its list, after the open cards. **Recorded**, part 2.
- **A card with no position** goes after the open cards that have one, and is a gap. **A card on a list the
  board record does not have** goes in its own section and is a gap. Neither is placed by guess.
  **Recorded**, part 2.
- **If order cannot be kept, the build stops.** With no board record, or a list with no id or no position, it
  writes nothing. **Tested.**

**Recorded**, part 2: the headings come out as To do, Doing, In review, Done, and each list's cards are in
position order. **Observed** on the real sandbox board: Backlog, Doing, Review, Done, by positions 16384,
32768, 49152 and 65536, which is not their order by name.

One limit: the index has the list order the board record had when it was saved. If lists are reordered in
Trello afterwards, the index keeps the old order until the board is read again.

## The acceptance criteria, one by one

1. **The index is generated, never hand-edited.** `index.md` and `index.json` are written only by
   `index.py build`. The header of `index.md` says so. The `check` command compares the files on disk, byte
   for byte, with what a build from the records would write now, so a hand edit is found. **Recorded**, part
   7: a card was changed by hand from open to archived in the index, the check failed and named the file, and
   the next build put back what the record says.
2. **Lists appear in the order they have on the board.** See the section above.
3. **Every local card appears once.** Four ways, each independent of the one before.
   - The generator puts every file in `cards/` in exactly one of three places: a row, a repeat of a card
     already indexed, or not indexed with a reason. It adds the three and stops if they do not equal the files
     found. **Recorded**, part 1: `accounted for: 12 of 12`.
   - After the index text is made, the generator counts the card rows in it and stops if that is not the
     number indexed. **Tested.**
   - `index.md` shows the sum: `12 + 0 + 0 = 12`.
   - The recording script counts separately and shares no code with the generator. It lists the record files,
     reads the card id out of each, reads the rows out of `index.md`, and checks 12 records, 12 rows, 12
     different ids, the same ids. **Recorded**, part 1.

   "Once" is by card id. **Recorded**, part 6: with a second copy of one card's record, a card of another
   board and a file of notes added, 17 files give 14 rows, 1 repeat and 2 not indexed, and each of the three
   is named with the reason. **Observed**: 7 real records, 7 rows, 7 different ids.
4. **Lookup by list, label and member works from the index.** Two ways. By reading `index.md`, which has each
   list's table and the views "By label" and "By member". And by `index.py lookup`, which answers from
   `index.json`. **Recorded**, part 3: list "In review" (3 cards, in board order), label "bug" (3), one member
   id (4), and a label no card has (nothing, exit code 1). **Observed**: one lookup for each of the four real
   lists, which together return every card once. Members are Trello member ids, because the records hold no
   names.
5. **A card with a missing field is listed as a gap.** The card keeps its row, with `(missing)` in the cell,
   and is listed under "Gaps" with the fields it lacks. Nothing is guessed. **Recorded**, part 1: two gaps
   among the 12 cards. Part 5: the reader is handed a card with no due date, labels or closed field; the build
   reports `no closed state, no labels, no due date`, and the row shows `(missing)` three times. A card whose
   record says it has no due date shows `none` and is not a gap. **Tested** for each of the seven fields.
6. **Two builds from the same records are identical, and adding a card changes the index without a hand
   edit.** No time, counter or machine path is in either file. **Recorded**, part 1: the same SHA-256 after
   both builds, and the second build did not rewrite the file. Part 4: a thirteenth record was written by the
   card reader, the build command was run, and the index had 13 rows with the new card at its position in
   Doing; every earlier row was unchanged. Only the build wrote to the index. **Observed**: a second build on
   the real records found both files unchanged.
7. **The index is stated not to be the source of truth.** The header says the card records and the board
   record are the source of truth and the index is not, and names the folder they are in and their
   fingerprint. A lookup runs the check first and gives no answer from an index that does not match the
   records. **Recorded**, part 4: between adding the record and rebuilding, the check failed and the lookup
   refused. Each lookup answer names the record file.

## What was built

- `participant/skills/trello-build-index/SKILL.md` and `index.py`: the generator, with `build`, `check` and
  `lookup`. Standard library only. No network code.
- `participant/skills/trello-build-index/tests/test_index.py`: 56 tests.
- `participant/context/trello/index.md` and `index.json`: the generated index of the made-up board.
- `participant/context/trello/index-fixture/`: the made-up board's records, `board.json` and 12 card records.
- `scripts/make_fixture.py`: makes the records by calling the approved card reader.
- `scripts/record_evidence.py`: records `logs/index-run.txt`.
- `scripts/planted_bugs.py`: puts 32 bugs into the generator one at a time and records which tests fail.
- `scripts/live_run.py`: the participant's real, read-only run.

Both stretch goals were done. Cards due this week is `lookup --due-within-days 7`, counted from the clock or
from a clock value given with `--now`, so that it can be tested. **Recorded**, part 3. The index age is
reported by each lookup, worked out at that moment from the file's modified time, so that no time has to be
stored in the index and criterion 6 still holds.

Two things were added that the quest does not ask for. `index.json`, which the lookup reads, because reading a
Markdown table back into data would be fragile; both files come from the same build and both are checked. And
the board record as a second input, because card records alone do not hold list names or list order.

The index of the made-up board is at `participant/context/trello/index.md`, the path the quest names. The
older `board-index.md` beside it belongs to the `trello-read-board` quest and was not touched.

## The real run

The participant ran `scripts/live_run.py` in their own terminal. The approved card reader read each card of
their sandbox board from Trello, with GET requests only, into a scratch folder outside the repository. The
index was built there. The log holds counts, list names, card ids and fingerprints, and no card names.

The first run failed one of its eight checks, and the fault was in the run script, not the generator. The
saved board record holds eight cards and marks one as `not_returned`: Trello stopped returning it for this
board on an earlier sync. The script asked for it anyway and the reader stopped. The script did not record
the reader's message, so what Trello answered for that card is **not assessed**. The script now leaves out
any card the board record marks that way and says so in the log. The first log is kept unchanged as
`logs/live-index-run-first.txt`. The second run read 7 cards and passed all 8 checks.

## Where the important artifacts are

| What | Path |
|---|---|
| The generator | `participant/skills/trello-build-index/SKILL.md`, `participant/skills/trello-build-index/index.py` |
| The index | `participant/context/trello/index.md` |
| The index as data | `participant/context/trello/index.json` |
| The records | `participant/context/trello/index-fixture/` |
| The run record | `participant/evidence/trello-build-index/trello-attempt-003/logs/index-run.txt` |
| The real run | `participant/evidence/trello-build-index/trello-attempt-003/logs/live-index-run.txt`, also copied to the end of the run record |
| The real run that failed a check | `participant/evidence/trello-build-index/trello-attempt-003/logs/live-index-run-first.txt` |
| Test output | `participant/evidence/trello-build-index/trello-attempt-003/logs/tests.txt` |
| Planted bugs | `participant/evidence/trello-build-index/trello-attempt-003/logs/planted-bugs.txt` |
| Copies at the paths the quest names | `participant/evidence/trello-build-index/attempt-001/` |

The quest names `attempt-001`. The application created the attempt as `trello-attempt-003`. The run record and
this file are copied to `attempt-001`, with a note there saying so.

## How to reproduce the behavior

From the repository root. None of these uses the network.

```bash
python3 participant/skills/trello-build-index/index.py build
python3 participant/skills/trello-build-index/index.py check
python3 participant/skills/trello-build-index/index.py lookup --list "In review"
python3 participant/skills/trello-build-index/index.py lookup --label bug
python3 participant/skills/trello-build-index/index.py lookup --member 5f0000000000000000000002
python3 -m unittest discover -s participant/skills/trello-build-index/tests -v
python3 participant/evidence/trello-build-index/trello-attempt-003/scripts/record_evidence.py
python3 participant/evidence/trello-build-index/trello-attempt-003/scripts/planted_bugs.py
```

The recorded log comes out the same each time, except the lines saying how long ago the index was written.
The real run needs the participant's own sandbox board and credentials, and is not reproducible by a reviewer.

## What was tested or validated

| What | How | Result |
|---|---|---|
| The generator | 56 unit tests, `logs/tests.txt` | all pass |
| Whether the tests notice a broken generator | 32 planted bugs, `logs/planted-bugs.txt` | all 32 caught |
| The behaviours the quest names | `scripts/record_evidence.py`, 46 checks inside `logs/index-run.txt` | all passed |
| The same on real records | `scripts/live_run.py`, 8 checks, `logs/live-index-run.txt` | first run 7 of 8, second run all passed |

One test was wrong when first written, not the generator: its pattern for "a build time in the file" matched
the words "rebuilt at any time" in the header. The pattern now requires a digit after the words.

## Remaining limitations

- **The index can only be as right as the records.** It never reads Trello. If a record is out of date, the
  index agrees with the record and both are wrong.
- **List order is the board record's.** Lists reordered, renamed or added in Trello since the board was read
  are not seen. A card moved to a list made since then lands under "Cards whose list is not known".
- **The two kinds of record can be of different ages.** The index does not compare when the board record and
  each card record were saved. The fixture's card records hold no save time.
- **A person reading `index.md` directly is not protected by the check.** The file cannot know it is stale.
  Its header says how to check, and a lookup always does.
- **The check uses the generator.** It asks whether the index is what the generator writes now. A mistake in
  the generator would be in both. The count by the recording script is the only check that shares none of
  the generator's code, and it covers the number of rows and the ids, not the content of each row.
- **One board.** Cards of any other board are listed as not indexed. The quest's title speaks of boards; an
  index of several boards was not built.
- **Only `.md` files directly in `cards/` are records.** **Tested** as the intended behaviour.
- **A repeat is not judged.** The file first in name order is the row. The other is reported.
- **Members are ids, and labels are matched by whole name.** Two labels with the same name and different
  colours are found together by a lookup, and shown apart in "By label".
- **Names are cut at 90 characters in `index.md`.** The whole name is in `index.json` and in the record.
- **The real run's records are not in the repository,** and its log leaves out card names, so a reviewer
  cannot check its rows against its records. The real board has no archived list and its records had no gap,
  so those behaviours were **not assessed** on real records.
- **Not assessed**: large boards. Every record is read on each build, check and lookup.

## Reflection: what could make the index disagree with the records unnoticed?

Anything that changes one side while nobody runs the comparison, and a few things the comparison cannot see.

The plain case is a record changing after the build. The generator can detect that, but only when asked.
Someone who opens `index.md` to see what is in review, which is the use it was made for, is asking nothing. A
stale index looks exactly as trustworthy as a fresh one.

This quest added a case the Jira index did not have: there are two kinds of record, and they can disagree with
each other. The cards say which list they are in; the board record says what the lists are and their order.
If the board is read on Monday and a card on Wednesday, the index is built from two different moments and the
check still passes, because the index does match the records. The real run showed a small version of this. The
board record still held a card that Trello had stopped returning, and the run script trusted it.

The quieter cases, where the comparison is run and says yes:

- **A record the generator never looks at,** in a subfolder or with another extension. It is in no count.
- **A file reported at the bottom of the index** as a repeat or not indexed. The tool noticed. Whether a
  person reads that far is another matter.
- **A fault in the generator.** The check compares the index with the generator's own answer.
- **A name that is cut or escaped.** Two cards that differ only after the ninetieth character look the same.

A count can agree while the content does not. Counting records and rows shows nothing was lost. It does not
show that what was kept is right, or that the records are still true of Trello. So the header says what it
says: use the index to find a card, then read the card's record.

## Sensitive values

- No credential is in any file. The generator has no network code. The real run's script never reads the key
  or the token; the approved card reader reads them from the environment.
- No real card text is in the repository. Every board, list, card and member in the index, the fixture and
  parts 1 to 7 of the log is made up. The real run's log holds the sandbox board's list names and card ids,
  counts and fingerprints, and no card names, descriptions or member ids.
- No personal name, email address or site address is in any file here.
- The logs hold no home-folder path. Temporary folders are shown as `COPY` and `SCRATCH`.
