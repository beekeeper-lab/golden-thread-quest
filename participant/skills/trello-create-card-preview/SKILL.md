# Trello create-card preview

Written by an AI assistant (Claude) at the participant's direction.

## 1. Purpose

This skill shows exactly what creating one Trello card would send, before anything is sent, including which
list the card would land in and where in that list. It reads a local draft, asks Trello about the board and
the list the draft names, checks permission, searches the local indexes for duplicates, and prints the whole
request. Then it stops.

**It writes nothing to Trello.** `preview.py` has no code of its own that sends anything. For a live run it
uses the request function of the approved `trello-read-card` skill, which sends GET and nothing else.

Run it from the repository root:

    python3 participant/skills/trello-create-card-preview/preview.py --source live --draft DRAFT.md \
        --allowlist participant/context/trello/new-card/sandbox-allowlist.json --boards FOLDER --state FOLDER

`--source fake` runs against the made-up Trello in `fake_trello.py`, with no network and no credentials.

## 2. Configuration

A live run reads two environment variables, set in the local shell and never stored in a file.

| Variable | What it holds |
|---|---|
| `TRELLO_API_KEY` | The Trello app's API key. |
| `TRELLO_API_TOKEN` | A token made through that key. |

Trello's request for a token's own record has the token in its path. That path is never written down: the
list of requests shows it as `/tokens/[the token]`. Everything that would be shown or saved, the output, the
payload file and the saved preview, is searched for the key and the token first. If either is found, nothing
is shown or saved.

| Option | What it is |
|---|---|
| `--draft FILE` | The card draft. |
| `--allowlist FILE` | The sandbox allowlist: the ids of the boards a card may be previewed for. |
| `--boards FOLDER` | The local board indexes to search for duplicates, one folder for each board, as the `trello-duplicate-search` skill reads them. |
| `--state FOLDER` | Where a READY preview is saved for a later write. |
| `--payload-out FILE` | Also write the payload, field by field, as Markdown. |
| `--log FILE` | Also save the output. |
| `--now TIME` | The time a due date is checked against, like `2026-11-20T09:00:00Z`. The default is the clock. |

## 3. The draft

A Markdown file. Between two lines of three dashes are the card's fields, one per line: a name, a colon and a
JSON value.

    format: "trello-card-draft/1"
    board: "<board id>"                  the board, by its Trello id
    list: "<list id>"                    the list, by its Trello id
    position: "bottom"                   "top", "bottom" or a number above zero
    name: "..."
    labels: ["export"]                   optional, by name
    members: ["<member id>"]             optional
    due: "2026-12-04T17:00:00.000Z"      optional
    duplicate_decision: "link"           optional. See section 8
    duplicate_candidates: ["<card id>"]  the cards that decision was made about

Under `## Description` is the description. It is sent as written, line breaks included.

- **The board and the list are given by id.** A name is refused, because two lists can share one.
- **The position has no default.** A draft that does not say where the card goes is refused.
- Any other field name in the draft is refused.

## 4. Citations

Under `## Sources` is one line for each citation:

    - name: sources/notes.md line 7: "the words quoted"
    - description: sources/notes.md lines 8-9: "more words"

Every piece of content in the draft needs at least one: the name, the description, and the labels, members
and due time if the draft sets them. Each citation is checked. The file must be under `participant/context/`,
and the quoted words must be on the lines named. A source that was changed after the draft was written fails
that check.

## 5. Two kinds of problem, three outcomes

| Outcome | When | What is shown and saved | Exit code |
|---|---|---|---|
| **REFUSED** | The draft points at something that is not there or is not allowed. | The reason only. No payload is shown, saved or written. | 1 |
| **NOT READY TO WRITE** | The draft is valid, and the write should not go ahead yet. | The whole preview, with each reason. Nothing is saved for a write. | 3 |
| **READY TO WRITE** | Every check passed. | The whole preview. The payload, its SHA-256 and a fingerprint are saved in the state folder. | 0 |

Refused:

- the board is not on the sandbox allowlist, is closed or cannot be seen;
- the list does not exist, belongs to another board, or is archived;
- a label does not exist on the board, or two labels on the board have that name;
- a member is not a member of the board;
- a citation is missing or not true;
- the due time is not a real time, or is before now;
- the duplicate search could not run, for example because an index does not match its records;
- the board's lists or cards changed while the preview was being made.

A refusal for a list, a label or a member names what does exist, so the draft can be put right.

Not ready:

- the token may not write to boards, or Trello did not say what the token may do;
- the token's member is an observer of the board, or is not an active member;
- the duplicate search found a likely duplicate that no recorded decision covers.

## 6. What the preview does

In order.

1. Reads the draft and checks its citations and its due time.
2. Checks the board is on the sandbox allowlist. Trello has not been contacted before this.
3. Asks Trello which member the token belongs to, and for the board.
4. Takes a snapshot of the board: its lists and cards.
5. Asks Trello for the list by its id, and checks it is on the stated board and not archived.
6. Asks Trello for the board's labels and members, and finds each one the draft names.
7. Builds the payload, once.
8. Asks Trello for the member's role on the board and for the token's own permissions.
9. Searches the local indexes for likely duplicates, with the `trello-duplicate-search` skill.
10. Takes the snapshot again, and refuses if it differs.
11. Shows everything, with the verdict.

## 7. The payload

The payload is made in one function, `build_payload`, and turned into bytes in one function, `body_bytes`. The
preview prints the payload whole, with its length in bytes and its SHA-256.

| Field | From |
|---|---|
| `idList` | the draft's list id |
| `pos` | the draft's position |
| `name` | the draft's name |
| `desc` | the draft's description, if it has one |
| `due` | the draft's due time, if it has one |
| `idLabels` | the board's id for each label the draft names, joined with commas |
| `idMembers` | the draft's member ids, joined with commas |

Only what the draft sets is sent. The request would be `POST https://api.trello.com/1/cards`. The bytes are
the payload as JSON with no spaces or line breaks and its names in alphabetical order. The preview prints it
indented, which is the same data.

The preview also says where in the list the card would sit: its number among the open cards, and the ids of
the cards before and after it. No card's name is printed.

A READY preview is saved in the state folder under a fingerprint, with a 15-minute expiry, for a later write
to check before it sends those bytes.

## 8. The duplicate search

The result is shown with each candidate's card id, board, confidence, matched signals and recommendation. The
preview also compares the number of the board's cards in the local index with the number Trello holds, and
warns when Trello holds more.

A candidate whose recommendation is link or archive-as-duplicate makes the preview NOT READY until the draft
records a person's decision:

    duplicate_decision: "link"
    duplicate_candidates: ["<the candidate's card id>"]

The decision covers only the cards it names. A candidate it does not name makes the preview NOT READY again.
A decision of `archive-as-duplicate` means the card is not to be created, so the preview stays NOT READY.

## 9. Tests

    python3 -m unittest discover -s participant/skills/trello-create-card-preview/tests -v

## 10. What it does not do

- It does not create anything. A later quest does the write.
- It cannot promise that Trello would accept the payload. Trello has no way to try a create without making one.
- Its "unchanged" check covers the board's lists and cards: which exist, each card's list, position, archived
  state and last activity. It does not look at labels, members, comments or other boards. It reads at most
  999 cards.
- Its permission check asks about the member's role and the token's scope. It does not know about limits or
  rules set elsewhere, such as a workspace's settings or the board's automation.
- It does not show how Trello will display the description.
- It checks a due time is not in the past. It does not know the board's own conventions for due dates.
- It cannot know that a decision recorded in a draft was made by a person.
