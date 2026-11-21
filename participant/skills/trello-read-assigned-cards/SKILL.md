# Trello: cards assigned to the signed-in member

Written by an AI assistant (Claude) at the participant's direction.

## 1. Purpose

This skill finds every Trello card assigned to the member a connection belongs to, on every board that
connection can reach, and keeps a local index of them. It can be run again and again. A second run adds
nothing that is already held, a card that is no longer the member's is flagged and kept, and the person's own
notes are never written to.

It only reads Trello. Every request is a GET. There is no code in it that creates, moves, updates, archives or
comments on anything.

    python3 participant/skills/trello-read-assigned-cards/sync.py --source fake
    python3 participant/skills/trello-read-assigned-cards/sync.py --source live --out FOLDER

`--source fake` reads the made-up Trello in `fake_trello.py`, beside this file. `--source live` reads Trello.
The sync uses the Python standard library only.

## 2. Credentials

A live run needs two environment variables, `TRELLO_API_KEY` and `TRELLO_API_TOKEN`. Set them in your own
terminal, for example with `read -s`, and export them. A read-only token is enough.

The key and token are sent in a request header. They are never put in an address, printed, or written to a
file. A fake run needs none.

## 3. Who the member is

The first request asks Trello "who am I?" (`/members/me`). The member is whoever the token belongs to. No
member id or name is written in the skill, and none can be given to it.

## 4. Which boards

Every board the connection can reach is searched, closed boards included. For each board the sync reads its
lists and all of its cards, archived ones included, and keeps the cards the member is on. Other members' cards
are counted and not kept.

`--only-boards ID,ID` searches only the boards named. The output and the index then say RESTRICTED, and how
many boards the connection can reach. Use it to keep a live run to a sandbox board.

If any board cannot be read, the run stops and writes nothing.

## 5. More cards than one request returns

Trello returns at most 1000 cards for one request. The sync asks for a board's cards a page at a time, each
time asking for the cards older than the oldest it holds, until a page comes back short. It prints, for each
board, how many requests it took and how many cards each returned.

Three checks guard this:

- A full page that holds nothing new stops the run. It would mean asking for older cards did not work.
- After the search, the sync asks Trello for its own list of the member's cards and compares. A card on a
  searched board that Trello lists and the search did not find stops the run. Trello's own list stops at 1000
  cards, so it is used as a check and not as the source.
- After writing, the sync counts the card rows in the index and prints that count beside the count retrieved.

## 6. Archived cards

An archived card that is still assigned to the member is **included**, in its own section of the index,
"Assigned and archived", and is not counted as open work. A card is archived when the card itself is archived,
when its list is archived, or when its board is closed. The index says which.

## 7. What is written

In the output folder, by default `participant/context/trello/assigned/`:

| File | What it is |
|---|---|
| `index.md` | The index. Generated. Do not edit it: the next sync replaces it. |
| `assigned.json` | The sync's memory of what it held last time. Generated. |
| `notes/<card id>.md` | **Yours.** The sync never writes here. See section 9. |

The index has one row for each card, with its name, card id, board, list and last activity, in these sections:
boards searched; assigned and open; assigned and archived; no longer assigned; assigned to several members; no
activity for 30 days or more (`--quiet-days N` changes the 30).

One folder holds one member's cards from one source. A folder that holds a fake run refuses a live one, and a
folder that holds one member's cards refuses another's.

## 8. Syncing again

A card is matched on its Trello card id and nothing else, so a renamed or moved card is the same card. Each
run prints how many cards are new, changed, unchanged, newly flagged and assigned again. A run on unchanged
data reports 0 new and 0 changed.

When a card that was held is not among the member's cards any more, the sync looks that one card up and flags
it with why:

| Reason | What Trello said |
|---|---|
| reassigned | the card exists, the member is not on it, and it names who is |
| unassigned | the card exists and nobody is on it |
| deleted | there is no such card |
| not reachable | the connection may no longer see it, for example because the member left the board |
| board not searched | the card is still the member's, on a board this run did not search |

A flagged card moves to "No longer assigned" in the index, with the reason and the time of the sync that
noticed. Its row keeps what was last known of it. **Nothing is deleted**, from the index, the memory or the
notes. If the card is assigned to the member again, it goes back.

## 9. Your notes

Write notes on a card in `notes/<card id>.md`. The index shows which cards have one.

The sync opens notes files for reading only, to take their SHA-256. It prints each file's checksum before and
after every run. Its one function that writes files refuses any path in the notes folder. It does not create
the folder, and it does not move or remove a notes file whose card is gone: that file is listed under "Notes
files with no card here".

Note text is never copied into the index or the memory.

## 10. All or nothing

Everything is read before anything is written. If Trello rate-limits the run it waits as Trello asks, at most
three times for one request and at most 15 seconds each. After that, or on any other failure, it writes
nothing, and the files from the last successful sync stay as they were. A run that could not read everything
never flags a card.

Exit codes: 0 synchronized. 1 stopped, nothing written. 2 incomplete because of a rate limit, nothing written.

## 11. Card text is other people's writing

Only the fields needed are asked for: name, short link, board, list, members, archived or not, last activity.
Descriptions, comments and checklists are not requested. Card and board names are written into the index as
names, on one line, with characters that could break a table or start a link replaced. Nothing in them is
acted on. The screen output shows ids and counts, not names.

## 12. Tests

    python3 -m unittest discover -s participant/skills/trello-read-assigned-cards/tests -v

Every test runs against `fake_trello.py`. None contacts Trello.

## 13. What it does not do

- It does not change anything in Trello.
- It does not find the member's cards on a board the member is not on, such as a public board. If Trello's own
  list holds such cards, the output says how many are on boards not searched.
- It does not look a flagged card up again at later syncs. The reason is as it was when first noticed.
- It does not read descriptions, comments or checklists. The `trello-read-card` skill does that for one card.
- It does not resolve member ids to names.
- It does not remove anything, ever. Clearing out old flagged rows means removing them from `assigned.json` by
  hand.
