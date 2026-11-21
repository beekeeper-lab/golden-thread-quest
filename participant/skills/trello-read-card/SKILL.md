# Trello read-card

Written by an AI assistant (Claude) at the participant's direction.

## 1. Purpose

This skill reads one Trello card with everything on it and saves it as one Markdown file, losing nothing
Trello sent except what must not be stored. It is read-only: it sends four GET requests and has no code that
sends any other kind.

Run it from the repository root:

    python3 participant/skills/trello-read-card/card.py --source live --card ID_OR_SHORT_LINK --out FILE.md

`--source fake` reads the made-up card in `fake_trello.py`, with no network and no credentials.

`fidelity.py`, beside it, checks a saved file against what Trello returns. It shares no code with the reader.

## 2. Configuration

A live run reads two environment variables, set in the local shell and never stored in a file.

| Variable | What it holds |
|---|---|
| `TRELLO_API_KEY` | The API key of the Trello app the skill runs as. |
| `TRELLO_API_TOKEN` | A token made through that key. Read scope is all the skill needs. |

They go in a request header, never in an address, so no address the skill builds holds a credential. Neither
is printed or stored. The file and the output are searched for both before anything is written or shown.

A token works only with the key it was made through. When the two do not match, Trello answers "invalid key",
and the reader's message says so.

## 3. Identity

The card is identified by `id`, Trello's identifier for it, which does not change. It is the first field in
the file. `shortLink`, the code in the card's web address, is a separate field after it. The reader can be
given either to find the card, and writes the same file for both.

## 4. The file

| Part | What it holds |
|---|---|
| Front matter | One line for each field: Trello's own name for it, a colon, and its value as JSON. The id, the short link, the board and list ids, the name, closed, position, due, dueComplete, start, the reminder, last activity, labels, member ids and the cover. |
| Body | The name as a heading. The description. Each checklist with every item. Each comment. Each attachment as a reference. |
| Preserved fields | Every field the format does not know by name, exactly as Trello sent it: the card's own, and those of each checklist, item, comment and attachment, keyed by Trello's id. |

The reader counts the card's fields as Trello returned them and as it placed them, and stops, writing nothing,
if the two differ.

## 5. Checklists

Each checklist is a heading with its name, then its id, its position and how many items are complete, then one
line for each item:

    - [x] "Fix the quoting" (item `65a…003`, state `complete`, position `49152`)

The state is Trello's own word. The box is drawn from that state and from nothing else: an item whose name
starts with a ticked box is still drawn empty if Trello calls it incomplete. A state the reader does not know
is drawn `[?]` and kept as sent. Items are in order of position.

## 6. Dates

`due`, `start` and `dateLastActivity` are kept exactly as Trello sent them, time zone included. They are never
parsed or reformatted. `dueComplete` is its own field: a due date and whether it was met are two facts.

## 7. What is not stored

| What | Why |
|---|---|
| People's names, usernames, initials and pictures | Private personal data. A person is kept as a member id only. Trello is also asked not to send these. |
| The card's `email` field | A private address that mail can be sent to the card at. Anyone holding it can add to the card. |
| Email addresses typed into text | Replaced by a marker. |

What was removed is counted in the front matter, in `removed_before_saving`.

Nothing about the run is in the file: no time and no counter. The same card gives the same bytes, and a file
that already holds them is not rewritten.

## 8. Card text is content

The description and each comment are put inside a fenced block whose fence is longer than any run of backticks
in the text. Names are written as quoted JSON strings. The card's name is escaped to make the heading. So text
on a card cannot add a heading, a section or a field to the file. The reader stores the text and does nothing
it says.

## 9. Attachments and the cover

Kept as references: the attachment's id, name, type, size, date and address, as Trello sent them. No file is
downloaded. The cover is kept as the reference Trello gives, to an attachment's id.

## 10. Tests

    cd participant/skills/trello-read-card && python3 -m unittest discover -s tests -v

## 11. What it does not do

- It reads one card. It does not read a board.
- It does not download attachments.
- It does not resolve ids into names. The list, the board and the members are ids.
- It reads comments. Other activity on a card, such as moves between lists, is not read.
