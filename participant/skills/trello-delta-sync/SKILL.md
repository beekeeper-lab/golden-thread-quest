# Trello delta sync

Written by an AI assistant (Claude) at the participant's direction.

## 1. Purpose

This skill keeps a local copy of one Trello board up to date by fetching only the cards that changed since
the last successful sync. It finds them from the board's own activity, so a move, an archive or a comment is
caught as well as an edit. It keeps a cursor, moves it only when a whole sync has succeeded, and never writes
to the person's notes.

It only reads Trello. Every request is a GET. There is no code in it that creates, moves, updates, archives or
comments on anything.

    python3 participant/skills/trello-delta-sync/sync.py --source fake [--fake-step N]
    python3 participant/skills/trello-delta-sync/sync.py --source live --board BOARD_ID --out FOLDER
    python3 participant/skills/trello-delta-sync/sync.py --status [--out FOLDER]

`--source fake` reads the made-up board in `fake_trello.py`, beside this file, as it is at step 0, 1 or 2.
`--source live` reads Trello. The sync uses the Python standard library only.

## 2. Credentials

A live run needs two environment variables, `TRELLO_API_KEY` and `TRELLO_API_TOKEN`. Set them in your own
terminal, for example with `read -s`, and export them. A read-only token is enough. They are sent in a request
header. They are never put in an address, printed, or written to a file. A fake run and `--status` need none.

## 3. The cursor

The cursor is the newest entry of the board's activity that the last successful sync read from Trello. Every
entry in a board's activity has an id and a time, both given by Trello. The cursor is that id, kept in
`state.json` with the entry's time.

It is a position in Trello's own record. It is not a time read from this machine's clock, and it is not worked
out from any card's fields.

## 4. The first sync

With no cursor, the sync reads the newest activity entry first, then the board's lists and every card on the
board, archived ones included, and sets the cursor to that entry. The entry is read before the cards so that a
change made while the cards are being read is picked up by the next sync.

## 5. A delta sync

With a cursor, in this order:

1. **The activity.** The sync asks Trello for the board's activity after the cursor (`since`), a page at a
   time until a page comes back short. Any entry at or before the cursor is dropped, in case more came back
   than was asked for. Each card an entry names is noted with what happened to it: moved from one list to
   another, archived, restored, created, commented on, deleted, moved to another board, or changed.
2. **The lists.** One request. A renamed or archived list changes how its cards are shown without any card
   being fetched.
3. **A cross-check.** One light request for the id and last-activity time of every card on the board. A card
   whose time moved with no activity entry naming it is fetched too. This is needed because Trello keeps no
   activity entry for some changes, a card's labels among them. A held card that is no longer listed is looked
   up as well.
4. **The cards.** Each card found in step 1 or 3 is fetched in full, one request each. No other card is.

The output gives the number of activity entries, the cards they name, how many cards were fetched and how many
were not, and counts of new, changed and unchanged cards. A card found only by the cross-check is marked as
such.

## 6. All or nothing

Everything in section 5 is held in memory. If any request fails, the run stops and writes nothing: the cards,
the cursor and the state description are exactly as the last successful sync left them. The next sync asks for
the same stretch of activity again and fetches every card the failed one would have.

Only when every card has been fetched are the files written: `cards.md`, then `state.json`, which holds the
cursor, then the state description. The new cursor is the newest entry read in step 1. A sync that finds no new
activity succeeds and leaves the cursor on the same entry.

If Trello rate-limits the run it waits as Trello asks, at most three times for one request and at most 15
seconds each, and after that stops with nothing written.

Exit codes: 0 synchronized. 1 stopped, nothing written. 2 incomplete because of a rate limit, nothing written.

## 7. What is written

In the output folder, by default `participant/context/trello/delta/`:

| File | What it is |
|---|---|
| `cards.md` | The cards, list by list, then archived cards, then cards no longer on the board. Generated. |
| `state.json` | The sync's memory: the cursor, the lists and what is held of each card. Generated. |
| `sync-state.md` | The cursor and the last sync in words. Generated from `state.json`. With the default folder it is written one level up, as `participant/context/trello/sync-state.md`. |
| `notes/<card id>.md` | **Yours.** The sync never writes here. See section 9. |

One folder holds one board from one source. A folder that holds a fake run refuses a live one.

## 8. Archived, moved and gone

- **Moved.** The card's row moves to its new list. The output says MOVED and names both lists by id.
- **Archived.** The card is flagged in the output and kept under "Archived" in `cards.md`, with the list it
  was in. A card in an archived list is shown there too. A restored card goes back to its list.
- **No longer on the board.** A card that was deleted, or moved to another board, is flagged with which, and
  kept under "No longer on the board" with what was last known of it. Nothing is deleted locally.

## 9. Your notes

Write notes on a card in `notes/<card id>.md`. `cards.md` shows which cards have one, wherever the card ends
up. The sync opens notes files for reading only, to take their SHA-256, and prints each file's checksum before
and after every run. Its one function that writes files refuses any path in the notes folder. Note text is
never copied anywhere.

## 10. A full resync, and the digest

`--full` reads the whole board again, ignoring the cursor, and folds it into the same folder. Run it now and
then, or when in doubt.

Every sync prints a digest: a SHA-256 of what is held about the lists and the cards on the board, and nothing
about when it was synced. Two local copies with the same digest hold the same board. A full read into an empty
folder should print the same digest as the deltas have reached. If it does not, a delta missed something.

## 11. How stale

Every delta says how long ago the last successful sync was and how old the cursor's entry is, and says STALE
when the last successful sync is more than 24 hours old (`--stale-hours N` changes that). `--status` says the
same without contacting Trello.

## 12. Card text is other people's writing

Only the fields needed are asked for. Descriptions and checklists are not requested. Activity entries carry
text, such as a comment's, and the sync uses only an entry's type, ids and the names of changed fields: no text
from an entry is printed or kept. Card and list names are written into `cards.md` as names, on one line, with
characters that could break a table or start a link replaced. Nothing in them is acted on. The screen output
shows ids, counts and times, not names.

## 13. Tests

    python3 -m unittest discover -s participant/skills/trello-delta-sync/tests -v

Every test runs against `fake_trello.py`. None contacts Trello.

## 14. What it does not do

- It does not change anything in Trello.
- It does not keep descriptions, comments or checklists. A comment is seen as activity on its card and the
  card is fetched, but the comment's text is not kept.
- It cannot catch a change that leaves neither an activity entry nor a new last-activity time on the card. If
  Trello has such changes, only `--full` finds them.
- It makes one request for each changed card. After a long gap with many changes, `--full` is cheaper.
- It syncs one board for each folder.
- It does not remove anything locally, ever.
