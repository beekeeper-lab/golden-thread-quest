# Proof · trello-read-assigned-cards

Attempt: `trello-attempt-007`

## How this was made

An AI assistant (Claude) wrote the sync, the made-up Trello, the tests, the recording scripts, the three
stand-in notes files and this file, at the participant's direction. The work was done in small steps, each
shown to the participant before the next.

What the participant did themself:

- Chose the design from options before anything was written: a made-up Trello for every criterion plus one
  real read-only run; archived cards included in their own section; notes in their own files that the sync
  never writes to, with a card that is no longer theirs flagged with the reason.
- Ran the sync once against real Trello, in their own terminal, with credentials only they hold. The assistant
  did not run it, and did not see or handle the key or token. It read the saved output afterwards.

Statements below are marked **recorded** (a log shows it, against the made-up Trello), **tested** (a passing
test shows it, with the output in `logs/tests.txt`), **observed** (the one real run shows it, in
`logs/live-run.txt`) or **not assessed**.

## What was built

A read-only sync, `participant/skills/trello-read-assigned-cards/sync.py`. It asks Trello who the connection
belongs to, searches every board that member can reach, keeps the cards assigned to them, and writes an index.
Run again, it updates the index without duplicating a card, flags a card that is no longer the member's, and
never writes to the person's notes.

A made-up Trello, `fake_trello.py`, stands in for Trello in every recorded run and every test:

| Board | State | The member is on it | Cards | Assigned to the member |
|---|---|---|---|---|
| Platform | open | yes | 130 | 65 |
| Support | open | yes | 24 | 12 |
| Design | open | yes | 12 | 6 |
| Hiring | open | yes | 6 | 3 |
| Old launch 2025 | closed | yes | 9 | 4 |
| Finance | open | no | 15 | 0 |

It returns at most 50 cards for one request, where Trello returns at most 1000, so that the Platform board
needs three requests. One card's name is worded as an order to the sync tool, and one holds a vertical bar and
brackets.

The index in the repository, `participant/context/trello/assigned/index.md`, is the one the last recorded sync
left: 89 cards assigned (78 open, 11 archived) and 1 no longer assigned. Every board, card and member in it is
made up.

## How archived cards are treated

The rule, which the sync prints at every run and writes into the index (criterion 4):

> An archived card that is still assigned to the member is **included**, in its own section, and is not counted
> as open work. A card is archived when the card, its list or its board is archived or closed.

So there are three ways, and the index says which for each card:

| Archived by | Meaning | In the made-up Trello |
|---|---|---|
| card | the card itself was archived | 4 of the member's cards |
| list | the card sits in an archived list | 3 |
| board | the card's board is closed | 4 |

Why included and not dropped: an archived card can be brought back, and a person may have notes on it. If the
sync dropped it, the card would vanish from the index on the day someone else archived it. Why in its own
section: the count of open work should not be padded with finished cards. "Assigned and open" is 78 and
"Assigned and archived" is 11, and they are never added together as work to do.

Archived is not the same as no longer assigned (criterion 6). An archived card is still the member's and stays
in the assigned part of the index. A card moves to "No longer assigned" only when the member is not on it any
more, or it cannot be found.

## The acceptance criteria, one by one

**1. The member is read from the connection.** The first request of every run is `/members/me`. The member id
is whatever Trello answers. **recorded**: `assigned-run.txt` part 2, and no 24-character id is written anywhere
in `sync.py`. **tested**: `TheMember`, 6 tests, including that a connection belonging to another member gets
that member's cards, and that a folder holding one member's cards refuses another's. **observed**: the real run
read the participant's member id from Trello. It is shown as `[member id]` in the saved log.

**2. Cards are retrieved across every board the connection can reach.** The sync asks for the member's boards,
closed ones included, and reads each. **recorded**: part 2. All 5 boards the member is on were searched, one of
them closed, and cards are held from all 5. The board the member is not on was not asked for. **tested**:
`EveryBoard`, 8 tests, including that a board that cannot be read stops the run with nothing written, so a
missing board is never mistaken for cards having gone. **observed**, in part: the real connection reaches 19
boards, 10 open and 9 closed. The real run was restricted to one of them, the sandbox, with `--only-boards`,
and its output and index say so. Searching all 19 real boards was **not assessed**: the quest says to use a
sandbox board.

**3. A result set larger than one page is retrieved completely, and the counts are reported.** **recorded**:
part 2. The Platform board's 130 cards took 3 requests of 50 + 50 + 30. The 90 cards held are exactly the
member's 90 in the made-up Trello, by id, as counted by the recording script from the made-up data. The sync
reported "retrieved 90 ... Rows saved in the index: 90. The counts agree", and the script counted 90 rows
itself. Part 5: with the limit set to Trello's real 1000 and 1500 more cards, a board of 1524 was read in
2 requests and all 1590 of the member's cards were held. Part 6: two ways paging could fail were each stopped
with nothing written. **tested**: `MoreThanOnePage`, 10 tests. Paging against real Trello was **not
assessed**: the sandbox board holds 8 cards.

**4. A closed or archived card is included or excluded by a stated rule.** The rule is above. **recorded**:
part 2, the rule is in the output and the index, and the sync's count of 11 archived (4 by card, 3 by list,
4 by board) is the recording script's own count. Part 3 shows one card of each kind with its row, all under
"Assigned and archived" and none under "Assigned and open". **tested**: `Archived`, 7 tests.

**5. A re-sync of unchanged data adds nothing.** **recorded**: `resync-run.txt` part 2. Two more syncs each
reported 0 new, 0 changed, 90 unchanged. The same 90 card ids were held, and the index and the memory were
byte for byte what the first sync wrote. Part 4 shows the same after the reassignment. **tested**: `Resync`,
7 tests, including that a renamed card is the same card, because a card is matched on its id.

**6. A card reassigned away is flagged, not deleted, and its notes are kept.** **recorded**: part 3. In the
made-up Trello, card `...004` on the Support board was taken from the member and given to another. The sync
printed "FLAGGED, not deleted ... reassigned: now assigned to member id ...003". 90 cards were still held. The
card's row is under "No longer assigned" with the reason, the time it was noticed, and a pointer to its notes.
Its notes file has the same SHA-256 as before. Part 4: at the next sync it stays flagged and is not flagged
again. **tested**: `ReassignedAway`, 13 tests: reassigned, unassigned, deleted, a board the member left, a card
assigned again, and that a rate-limited or failed run flags nothing.

**7. Local notes are byte-identical after every sync.** **recorded**: `resync-run.txt` part 1 gives the
SHA-256 of each of the 3 notes files, taken by the recording script before the first sync. The same values
appear after each of the 5 syncs, and in AFTERWARDS side by side. One of the files has Windows line endings, an
accented letter, a tab and no final newline, so a rewrite would show. **tested**: `Notes`, 8 tests, including
that the sync runs with the notes folder set read-only, that its one writing function refuses a path in the
notes folder, and that note text is not copied into the index.

## The one real run

`logs/live-run.txt`. Read-only, restricted to the sandbox board, written to a folder outside the repository.

| What | Result |
|---|---|
| Member | read from Trello |
| Boards the connection can reach | 19 (10 open, 9 closed) |
| Boards searched | 1, the sandbox, and the output says RESTRICTED |
| Cards on it | 8, in 1 request |
| Assigned to the member | 2, both open |
| Trello's own list of the member's cards | 2, both found |
| Counts | retrieved 2, rows saved 2 |
| Requests | 5, every one a GET |

This shows that the requests the sync makes are ones real Trello answers, in the shape the sync expects. It
does not show paging, archived cards, a second sync or a reassignment against real Trello.

## The stretch goals

**Cards assigned to several members.** The index has a section listing each open card the member shares, with
the other members' ids. 26 in the made-up Trello. **recorded**: `assigned-run.txt` part 4. **tested**: `Stretch`.

**Cards with no activity for a stated period.** The index lists open cards with no activity for 30 days or
more, with the number of days. `--quiet-days N` changes the period. 26 in the made-up Trello. Archived cards
are left out. **recorded**: part 4. **tested**: `Stretch`.

## Where the important artifacts are

| What | Path |
|---|---|
| The index | `participant/context/trello/assigned/index.md` |
| The sync's memory | `participant/context/trello/assigned/assigned.json` |
| The stand-in notes | `participant/context/trello/assigned/notes/` |
| The sync and how to use it | `participant/skills/trello-read-assigned-cards/sync.py`, `SKILL.md` |
| The made-up Trello | `participant/skills/trello-read-assigned-cards/fake_trello.py` |
| The tests | `participant/skills/trello-read-assigned-cards/tests/test_sync.py` |
| The sync record | `logs/assigned-run.txt` |
| The re-sync record | `logs/resync-run.txt` |
| The real run | `logs/live-run.txt` |
| The test output | `logs/tests.txt` |
| The planted-bugs log | `logs/planted-bugs.txt` |
| The scripts that made the logs | `scripts/` |

The quest names `participant/evidence/trello-read-assigned-cards/attempt-001/`. The application created this
attempt as `trello-attempt-007`. Copies of this file, `logs/assigned-run.txt` and `logs/resync-run.txt` are in
`attempt-001/`, with a note saying so.

## How to reproduce the behavior

From the repository root. None of these contacts Trello.

    python3 participant/skills/trello-read-assigned-cards/fake_trello.py
    python3 -m unittest discover -s participant/skills/trello-read-assigned-cards/tests -v
    python3 participant/evidence/trello-read-assigned-cards/trello-attempt-007/scripts/planted_bugs.py
    python3 participant/evidence/trello-read-assigned-cards/trello-attempt-007/scripts/record_evidence.py

The last command removes the generated index and memory, then runs the five syncs again: one from nothing, two
unchanged, one after the made-up reassignment, and one more. It leaves the notes alone. A single sync is:

    python3 participant/skills/trello-read-assigned-cards/sync.py --source fake
    python3 participant/skills/trello-read-assigned-cards/sync.py --source fake --fake-after reassignment

The real run needs `TRELLO_API_KEY` and `TRELLO_API_TOKEN` set in the terminal, and a folder outside the
repository:

    python3 participant/skills/trello-read-assigned-cards/sync.py --source live --out FOLDER --only-boards BOARD_ID

## What was tested or validated

| Check | Result | Where |
|---|---|---|
| Unit tests | 77 pass | `logs/tests.txt` |
| Planted bugs: 30 faults put into `sync.py` one at a time | all 30 caught by at least one test; the file restored byte for byte | `logs/planted-bugs.txt` |
| The sync record, parts 1 to 7 | 27 checks pass | `logs/assigned-run.txt` |
| The re-sync record, parts 1 to 4 and AFTERWARDS | 21 checks pass | `logs/resync-run.txt` |
| One real run, read-only | exit 0, counts agree | `logs/live-run.txt` |

The planted bugs include: the member written into the skill, only the first board searched, reading stopped
after the first page, archived cards counted as open, a card no longer assigned deleted from the memory, and a
notes file written to while reading it.

Two faults were found while building, both in the assistant's own checking code and not in the sync. One test
asserted the wrong outcome and was removed, because the test beside it already covered the case. And the
recording script ran one sync without telling it the made-up page limit, so a check failed for the wrong
reason. It was corrected and both records were made again.

## Remaining limitations

- **Paging was not run against real Trello.** The sync asks for older cards with `before`, as Trello's
  documentation describes. The sandbox board has 8 cards, so the real run never needed a second page. If
  `before` did not work as documented, the sync would stop on a full page with nothing new, or the comparison
  with Trello's own list would catch a missed card, but only among the first 1000 cards that list holds.
- **The made-up Trello is a stand-in.** It was written from Trello's documentation by the same assistant that
  wrote the sync. In particular, how real Trello answers for a deleted card and for a card on a board the
  member has left was not observed. The sync treats "no such card" as deleted and "not allowed" as not
  reachable. If Trello answers both the same way, the reason shown would be wrong, though the card would still
  be flagged and kept.
- **Boards the member is not on are not searched.** A card assigned to the member on a public board they have
  not joined would be missed. The output says how many cards in Trello's own list are on boards not searched.
- **A reassignment was not run against real Trello.** That would mean changing a card, and this quest only
  reads. Nor was a second real sync run.
- **A flagged card is looked up once.** If it is reassigned again later, to a third person, the reason shown
  stays as first noticed.
- **Every card on every board is downloaded** to find the member's, with seven fields each and no descriptions.
  Other members' cards are counted and discarded, never saved. On an account with many large boards this is
  slow and reads more than it keeps.
- **Nothing is ever removed.** The "No longer assigned" section only grows. Clearing it is done by hand.
- **Notes are matched to cards by file name.** A notes file named with anything other than a held card's id is
  listed as having no card, and left.
- **Member ids are not turned into names.** The index shows who else is on a card by Trello member id.

## Reflection

*What should happen to a card that was assigned to you last week?*

It should not silently disappear, and it should not stay in my list as if it were still mine. Both are wrong in
different ways. If it disappears, I lose whatever I wrote about it, and I cannot tell the difference between
"someone took this off me" and "the sync broke". If it stays, I plan around work that is no longer mine, which
is the same mistake as the scenario, in the other direction.

So it should move out of my open work into a place of its own, with three things attached: that it is no
longer mine, why (given to someone else, deleted, or out of my reach), and when that was noticed. My notes on
it should stay exactly as I left them, because the person who has it now may need what I learned. After that
it is my decision whether to hand the notes over, keep them or clear the row. The sync should never make that
decision for me.

## Sensitive values

No key, token or secret is in any file here. The sync reads them from the environment and sends them in a
header, never in an address. The participant set them in their own terminal, and the assistant did not see
them.

Every board, card and member id in the index, the memory, the notes and the two records is made up. The real
run's index and memory were written to a folder outside the repository and are not included: they hold real
card names. In `logs/live-run.txt` the output folder is shown as SCRATCH and the member's Trello id as
`[member id]`. The sandbox board's id appears there, as it does in earlier attempts. The number of boards the
real connection can reach appears as a count, with no board named. The sync prints ids and counts, not names.
No personal name, email address, site address or home-folder path is in the evidence.
