# Proof · trello-delta-sync

Attempt: `trello-attempt-008`

## How this was made

An AI assistant (Claude) wrote the sync, the made-up Trello, the tests, the recording scripts, the three
stand-in notes files and this file, at the participant's direction. The work was done in small steps, each
shown to the participant before the next.

What the participant did themself:

- Chose the design from options before anything was written: a made-up Trello for every criterion plus real
  runs with one card moved by hand; a cursor taken from the newest activity entry Trello returned; and a sync
  that is all or nothing, with the cursor written last.
- Ran the sync three times against real Trello, in their own terminal, with credentials only they hold, and
  between the first two runs dragged one card to another list in Trello by hand. The assistant did not run
  those, did not see or handle the key or token, and changed nothing in Trello. It read the saved output.

Statements below are marked **recorded** (a log shows it, against the made-up Trello), **tested** (a passing
test shows it, with the output in `logs/tests.txt`), **observed** (the real runs show it, in
`logs/live-runs.txt`) or **not assessed**.

## What was built

A read-only delta sync, `participant/skills/trello-delta-sync/sync.py`. Its first run reads a board whole.
Every later run asks Trello for the board's activity since the last successful sync, fetches only the cards
that activity names, and updates a local copy. It keeps a cursor, and it never writes to the person's notes.

A made-up Trello, `fake_trello.py`, stands in for Trello in every recorded run and every test. It holds one
board whose every change adds an entry to an activity log, as Trello's do. The board changes in steps:

| Step | What happens on the made-up board |
|---|---|
| 0 | 12 cards in 4 lists, each with its "created" entry |
| 1 | a card moved from Doing to Done; a card archived; a comment; a rename; a new card; a card's label changed, with no activity entry; a list renamed |
| 2 | two more moves; one of those cards archived; a card deleted; a card moved to another board; the archived card restored; a new card |

The local copy in the repository, `participant/context/trello/delta/`, is as the last recorded sync left it,
at step 2. Every card and member in it is made up.

## What the cursor is taken from

The cursor is **the newest entry of the board's activity that the last successful sync read from Trello**
(criterion 4). Every entry in a Trello board's activity has an id and a time, both given by Trello. The cursor
is that id, kept in `state.json` with the entry's time, and described in
`participant/context/trello/sync-state.md`.

It is a position in Trello's own record. Three things it is not:

- **Not this machine's clock.** A clock a few seconds off, or a change landing while a sync runs, would leave
  a gap that no later sync asks about. **tested**: `test_the_cursor_does_not_come_from_this_machines_clock`
  runs a sync with the clock set five years ahead, and the cursor is still Trello's entry and Trello's time.
- **Not worked out from card fields** (criterion 1). The newest "last activity" time among the cards cannot
  see a card that was deleted, and it is the approach the scenario warns about.
- **Not moved until the end.** The activity is read first, and the cursor a sync will set is the newest entry
  of that read. It is written only after every card has been fetched, as the last of the state.

How it advances, as the sync does it:

1. Read the activity after the cursor, then fetch every card it names. Hold all of it in memory.
2. If any request fails, stop. No file is written. The cursor is where it was (criterion 4).
3. Otherwise write `cards.md`, then `state.json` with the new cursor, then the description.
4. A sync with no new activity succeeds and leaves the cursor on the same entry.

So the sync after a failed one asks Trello for the same stretch of activity and gets every card the failed one
would have (criterion 5). And a change made while a sync is running has an entry newer than the cursor that
sync sets, so the next sync reads it. **tested**:
`test_a_change_made_while_the_sync_is_running_is_read_by_the_next_one`.

The first sync has no cursor. It reads the newest activity entry, then the whole board, and sets the cursor
to that entry.

## One addition to the plan: the cross-check

Trello keeps no activity entry when a card's labels change. A sync that followed activity alone would never
fetch that card, and a full resync would then disagree with the deltas (criterion 7).

So each delta also makes one light request: the id and last-activity time of every card on the board. A card
whose time moved with no activity entry naming it is fetched too, and the output marks it as found that way.
The activity stays the main source, and it is what says a card was moved or archived (criterion 1). The
cross-check is a net under it. This was added by the assistant during the build and told to the participant.

That Trello keeps no entry for a label change is stated from the assistant's knowledge of Trello and built
into the made-up Trello. It was **not assessed** against real Trello in this attempt.

## The acceptance criteria, one by one

**1. Changed cards are found from board activity, not from card fields alone.** **recorded**: `delta-run.txt`
part 3. The delta read 6 entries after the cursor, naming 5 cards, the same numbers the recording script
worked out from the made-up board. It fetched 6 cards of 13: those 5 and the label card. Part 4 lists every
request that delta made: one for the activity with `since` set to the cursor, one for the lists, one for ids
and last-activity times, and 6 card fetches. The board's cards were not read in full again. **tested**:
`FromActivity`, 13 tests. **observed**: run 2 read 1 entry after the cursor, fetched 1 card and did not fetch
the other 7.

**2. A card moved between lists is detected.** **recorded**: part 3. Card `...003` moved from Doing to Done
with nothing else changed. The sync printed the move from the activity, with both list ids, then "MOVED to
list ...004", and the card is held in Done and no longer in Doing. **tested**: `Moved`, 5 tests, including a
card moved twice between syncs and one moved and moved back. **observed**: the participant dragged one card
from one list to another on the real board. Run 2 printed "moved from list ... to list ..." from Trello's
activity, and "MOVED to list ...".

**3. An archived card is detected and flagged.** **recorded**: part 3. Card `...005` was archived. The sync
printed "ARCHIVED in Trello. Flagged, and kept with its notes". Its row is under "Archived" in `cards.md` with
the list it was in and a pointer to its notes, and no longer under Doing. `failed-sync-run.txt` part 3: a card
moved and then archived shows both, and the first card, restored, went back to its list. **tested**:
`Archived`, 5 tests. Not run against real Trello: **not assessed** there.

**4. The cursor advances only after the whole sync succeeds, and a failed sync leaves it where it was.**
**recorded**: `failed-sync-run.txt` part 2. The made-up Trello answered the third card fetched with an error.
The sync stopped with exit code 1. The cursor in `state.json` was the same entry as before, and the SHA-256 of
`cards.md`, `state.json` and `sync-state.md`, taken by the recording script before and after, did not change.
Part 3: once a whole sync succeeded, the cursor advanced to the newest entry read. **tested**: `TheCursor`,
14 tests: a failure at the activity, the lists, the listing or a card; a rate limit; and that the cursor is
written last.

**5. The next sync recovers what a failed one missed.** **recorded**: part 3. The next sync started from the
same cursor, read the same 7 entries, and fetched all 6 cards: the two the failed sync had reached and the
four it had not. **tested**: `test_the_next_sync_recovers_everything_the_failed_one_missed`, and
`test_the_recovered_state_is_what_a_sync_with_no_failure_reaches`.

**6. Local notes are byte-identical after every sync.** **recorded**: `notes-intact.txt` parts 1 and 4. The
SHA-256 of each of the 3 notes files, taken by the recording script before the first sync, is the same after
6 syncs into that folder, one of which failed. The notes are for the card that moved, the card that was
archived and restored, and the card that was deleted from the board, and that last file is still there. One
file has Windows line endings, an accented letter, a tab and no final newline, so a rewrite would show.
**tested**: `Notes`, 7 tests, including that the sync runs with the notes folder set read-only.

**7. A full resync reaches the same local state as the deltas.** **recorded**: `notes-intact.txt` part 2. The
board at step 2 was read whole into an empty folder. Its digest is the digest of the copy built by one full
read and two deltas. The recording script also compared them itself, without the digest: the same 12 cards,
108 fields and 4 lists, all equal, and the same cursor. Part 3: a full read in place, over the deltas, found
0 new and 0 changed. **tested**: `FullResync`, 8 tests. **observed**: run 3 read the real board whole into a
second empty folder and printed the digest run 2 had printed after first sync plus delta: `3593bdce...`.

One difference between the two is meant. The deltas also keep the 2 cards that are no longer on the board,
flagged. A read from nothing cannot know they existed. The digest covers the cards on the board.

## The real runs

`logs/live-runs.txt`. Read-only, on the sandbox board, written to folders outside the repository.

| Run | What it did | Result |
|---|---|---|
| 1 | First sync, no cursor | 8 cards read. Cursor set to the board's newest activity entry. 4 requests. |
| | The participant dragged one card to another list | |
| 2 | Delta | 1 activity entry after the cursor, naming 1 card: moved from one list to another. 1 card fetched, 7 not. Cursor advanced to that entry. 5 requests. |
| 3 | Full read into a second empty folder | 8 cards. The same digest as after run 2, and the same cursor. |

This shows that real Trello answers the activity request with `since` set to an entry's id as the sync
expects, that a real move appears in the activity in the shape the sync reads, and that deltas and a full read
agree on a real board. It does not show an archive, a deletion, a failure or a label change against real
Trello.

## The stretch goals

**Detect a card deleted from a board.** **recorded**: `failed-sync-run.txt` part 3. Card `...008` was deleted.
The activity named it, the sync found no such card, and it is flagged "deleted" and kept under "No longer on
the board" with its notes pointed to. A card moved to another board is told apart and flagged as that.
**tested**: `Gone`, 5 tests, including a card that vanishes with no activity entry at all.

**Report how stale the cursor is.** Every delta prints how long ago the last successful sync was and how old
the cursor's entry is, and says STALE past 24 hours. `--status` says the same without contacting Trello.
**recorded**: `delta-run.txt` part 3, where the made-up clock is two days on and the sync says STALE, and
`notes-intact.txt` part 5. **tested**: `Stale`, 5 tests, including that a failed sync does not make the cursor
look fresh. **observed**: run 2 reported the cursor's entry as 4.8 hours old.

## Where the important artifacts are

| What | Path |
|---|---|
| The sync state | `participant/context/trello/sync-state.md` |
| The local copy | `participant/context/trello/delta/cards.md`, `state.json` |
| The stand-in notes | `participant/context/trello/delta/notes/` |
| The sync and how to use it | `participant/skills/trello-delta-sync/sync.py`, `SKILL.md` |
| The made-up Trello | `participant/skills/trello-delta-sync/fake_trello.py` |
| The tests | `participant/skills/trello-delta-sync/tests/test_sync.py` |
| The delta record | `logs/delta-run.txt` |
| The failed-sync record | `logs/failed-sync-run.txt` |
| The notes and full-resync record | `logs/notes-intact.txt` |
| The real runs | `logs/live-runs.txt` |
| The test output | `logs/tests.txt` |
| The planted-bugs log | `logs/planted-bugs.txt` |
| The scripts that made the logs | `scripts/` |

The quest names `participant/evidence/trello-delta-sync/attempt-001/`. The application created this attempt as
`trello-attempt-008`. Copies of this file and of the three records are in `attempt-001/`, with a note saying so.

## How to reproduce the behavior

From the repository root. None of these contacts Trello.

    python3 participant/skills/trello-delta-sync/fake_trello.py 2
    python3 -m unittest discover -s participant/skills/trello-delta-sync/tests -v
    python3 participant/evidence/trello-delta-sync/trello-attempt-008/scripts/planted_bugs.py
    python3 participant/evidence/trello-delta-sync/trello-attempt-008/scripts/record_evidence.py

The last command removes the generated files, leaves the notes alone, and runs the syncs again in order. By
hand, the same sequence is:

    python3 participant/skills/trello-delta-sync/sync.py --source fake
    python3 participant/skills/trello-delta-sync/sync.py --source fake --fake-step 1
    python3 participant/skills/trello-delta-sync/sync.py --source fake --fake-step 2 --fake-fail-card 3
    python3 participant/skills/trello-delta-sync/sync.py --source fake --fake-step 2
    python3 participant/skills/trello-delta-sync/sync.py --source fake --fake-step 2 --full

The real runs need `TRELLO_API_KEY` and `TRELLO_API_TOKEN` set in the terminal, and a folder outside the
repository:

    python3 participant/skills/trello-delta-sync/sync.py --source live --board BOARD_ID --out FOLDER

## What was tested or validated

| Check | Result | Where |
|---|---|---|
| Unit tests | 81 pass | `logs/tests.txt` |
| Planted bugs: 30 faults put into `sync.py` one at a time | all 30 caught by at least one test; the file restored byte for byte | `logs/planted-bugs.txt` |
| The delta record, parts 1 to 5 | 21 checks pass | `logs/delta-run.txt` |
| The failed-sync record, parts 1 to 4 | 17 checks pass | `logs/failed-sync-run.txt` |
| The notes and full-resync record, parts 1 to 5 | 13 checks pass | `logs/notes-intact.txt` |
| Three real runs, read-only | each exit 0; the digests of run 2 and run 3 are the same | `logs/live-runs.txt` |

The planted bugs include: the activity not read at all, the cross-check switched off, a move not recognised,
the cursor written before the cards are fetched, a card that cannot be fetched skipped, the cursor taken from
the clock, and a notes file written to while reading it.

One test was wrong when first run: it expected one card in a list that holds two at that step. The test was
at fault, not the sync, and was corrected.

## Remaining limitations

- **Which changes leave no activity entry was not measured on real Trello.** The cross-check exists for label
  changes. If some change moves neither the activity nor a card's last-activity time, a delta cannot see it,
  and only `--full` would. Comparing digests after a full read is how that would be noticed.
- **The made-up Trello is a stand-in**, written from Trello's documentation by the same assistant that wrote
  the sync. The real runs confirm the shapes of the board, lists, cards, the activity with `since`, and a move
  entry. They do not confirm an archive entry, a delete entry, a move to another board, or how Trello answers
  for a card that no longer exists.
- **Paging was not run against real Trello.** More than 1000 activity entries or cards in one sync is covered
  by tests against the made-up Trello only.
- **The three files are written one after another**, not as one step. If the machine stopped between
  `cards.md` and `state.json`, `cards.md` would be ahead of the cursor. The next sync would fetch the same
  cards again and write the same result, so nothing is lost, but for that moment the two disagree.
- **Descriptions, comments and checklists are not kept.** A comment is seen as activity and its card is
  fetched, but only the card's last-activity time changes locally.
- **One request for each changed card.** After a long gap with many changes a full read is cheaper. The sync
  does not switch by itself.
- **A flagged card's reason is as first noticed.** A deleted card and one the connection can no longer see are
  told apart by how Trello answers, which was not observed.
- **Nothing is ever removed locally.** "No longer on the board" only grows.

## Reflection

*What changes can happen to a card that leave no trace on the card itself?*

More than I expected. A move between lists changes only which list the card points at, and if I compare the
fields I care about, such as the name and the due date, the card looks untouched. The same is true of a new
position within a list. A comment is not on the card at all: it is an entry in the activity that points at the
card. Archiving a whole list changes how every card in it should be shown, and not one of those cards changes.
Renaming a list does the same. And the largest one: a deleted card leaves no card to look at, so a sync that
only reads cards cannot tell "deleted" from "never existed".

What surprised me is that it also runs the other way. A label change is on the card but leaves no entry in the
activity. So neither source is complete. The activity knows what happened and to which card. The card knows
what is true now. A sync I can trust has to read the activity to learn where to look, read the card to learn
the truth, and now and then read everything and compare, in case both missed something.

## Sensitive values

No key, token or secret is in any file here. The sync reads them from the environment and sends them in a
header, never in an address. The participant set them in their own terminal, and the assistant did not see
them.

Every card, list, board and member id in `sync-state.md`, the local copy, the notes and the three records is
made up. The real runs' local copies were written to folders outside the repository and are not included:
they hold real card names. In `logs/live-runs.txt` those folders are shown as SCRATCH and SCRATCH-FULL. That
log holds the sandbox board's id, as earlier attempts do, and the ids of one card, two lists and two activity
entries on that sandbox board. It holds no name of a card, list, board or person. The sync prints ids, counts
and times, not names. No personal name, email address, site address or home-folder path is in the evidence.
