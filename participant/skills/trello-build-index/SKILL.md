# Trello build-index

Written by an AI assistant (Claude) at the participant's direction.

## 1. Purpose

This skill builds an index of one Trello board from the card records saved locally, in the shape Trello uses:
the board, then its lists in board order, then the cards in each list. A person or an agent can then find what
is in a list, under a label or with a member without opening every card file.

It reads local files only. It never contacts Trello and needs no credentials.

Run it from the repository root:

    python3 participant/skills/trello-build-index/index.py build

The generator is `index.py`, beside this file. It uses the Python standard library only.

## 2. What is the source of truth

The records are. There are two kinds, in one records folder:

| Record | What it is |
|---|---|
| `cards/*.md` | Card records in the format `trello-card/1`, written by the `trello-read-card` skill. |
| `board.json` | The board record: the board, and its lists with each list's id, name, position and whether it is archived. It is in the shape the `trello-read-board` skill writes. |

The index is a view of them and nothing more. It is two generated files:

| File | For |
|---|---|
| `index.md` | People. Each list in board order with its cards, views by label and by member, gaps, and what could not be indexed. |
| `index.json` | Lookups. The same content as data. |

Rules that follow from that:

- **Never edit either index file by hand.** If the index is wrong, fix the record or the generator and build
  again. A hand edit is overwritten by the next build and is found by `check` before that.
- **To learn what a card holds, read its record.** Use the index to find the record.
- **Either file can be deleted.** A build makes it again, byte for byte.

By default the records folder is `participant/context/trello/index-fixture/`, a made-up board, and the index is
written to `participant/context/trello/`. `--records FOLDER` and `--out FOLDER` point any command elsewhere.

## 3. How list order is kept

A card record says which list the card is in by the list's id, and holds nothing else about the list. The
list's name and its place on the board come from the board record.

- Lists are ordered by Trello's position number, `pos`, smallest first. If two lists have the same position,
  the list id decides. Names are never used to order anything.
- Cards in a list are ordered the same way: by the card's `pos`, then by its id.
- Open lists come first. Archived lists follow under their own heading, "Archived lists", still in position
  order, so that their cards are not lost. Trello does not show an archived list on the board.
- An archived card stays in its list, after the open cards, with its state shown as `archived`.
- A card whose record has no position goes after the open cards that have one, and is listed as a gap.
- A card on a list the board record does not have, or with no list, goes in its own section, "Cards whose list
  is not known", and is listed as a gap. It is not put in a list by guess.

The build stops if the board record is absent, or if a list in it has no id or no position, because list order
could not then be kept.

## 4. The three commands

    python3 participant/skills/trello-build-index/index.py build
    python3 participant/skills/trello-build-index/index.py check
    python3 participant/skills/trello-build-index/index.py lookup --list "In review"

`build` reads the board record and every `.md` file in `cards/`, and writes both index files. A file that
already holds exactly the bytes a build would write is left alone.

`check` says whether the index on disk is exactly what a build from the records, as they are now, would write.
It fails when a card record or the board record was added, removed or changed since the last build, and when
either index file was edited by hand. It writes nothing.

`lookup` answers one question from `index.json`:

| Option | Finds |
|---|---|
| `--list NAME_OR_ID` | The cards in that list, in board order. The whole name, in any letter case, or the list id. |
| `--label NAME` | Cards carrying a label of that name. The whole name, in any letter case. |
| `--member ID` | Cards that Trello member id is on. The whole id. |
| `--due-within-days N` | Open cards, not yet complete, due from now to N days on, soonest first. `--now 2026-11-20T09:00:00Z` sets the clock; without it the computer's clock is used and the answer says so. |

A lookup runs the check first. If the index does not match the records, it gives no answer and says to
rebuild. When it does answer, it also says how long ago the index file was last written.

Exit codes: 0 done, and for a lookup, something was found. 1 nothing was found, or the index does not match
the records. 2 the run could not go on.

## 5. Every card once

A card is identified by its Trello id, from the `id` line of its record. Every `.md` file found in `cards/`
ends in exactly one of three places:

| Place | What it means |
|---|---|
| Indexed | One row. A card with a field missing is still a row. |
| A repeat | A second file holding a card id that is already a row. Reported with both file names. |
| Not indexed | Not a `trello-card/1` record, no usable card id, or a card of another board. Listed with the reason. |

The build adds the three counts and stops, writing nothing, if they do not equal the number of files found.
After the index text is made it counts the card rows in it and stops if that is not the number indexed.
`index.md` shows the sum.

## 6. Gaps

A field the record does not have is shown as `(missing)` in the row, and the card is listed under "Gaps" with
the fields it lacks. Nothing is guessed. The fields are name, list, position, closed state, labels, members,
due date and board.

`none` is not a gap. It means the record says the card has no label, no member or no due date.

## 7. Names are other people's writing

Card, list and label names are shown as text. They are escaped so that a name cannot split a table row, start
a heading or become a link, and cut at 90 characters in `index.md`. Nothing in a name is acted on. The index
holds no card description, comment or checklist text.

Members are Trello member ids. The records hold no names.

## 8. Same records, same index

Neither file holds a time, a counter or a machine path. In place of a build time the index holds a fingerprint
of the records: a SHA-256 over the board record and every card record. The index age is worked out at lookup
time from the file's modified time, so that it does not have to be stored.

## 9. Tests

    python3 -m unittest discover -s participant/skills/trello-build-index/tests -v

## 10. What it does not do

- It does not read Trello. If a record is out of date with Trello, the index agrees with the record.
- It indexes one board: the one in the board record. Cards of another board are listed as not indexed.
- It does not protect a person who opens `index.md` directly. The file cannot know it is stale. A lookup checks.
- It reads only `.md` files directly in `cards/`.
- It does not judge a repeat. The file first in name order is the row, and a person decides about the other.
- It does not find labels or members by part of a name.
