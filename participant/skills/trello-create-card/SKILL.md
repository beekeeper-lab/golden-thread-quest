# Trello create-card

Written by an AI assistant (Claude) at the participant's direction.

## 1. Purpose

This skill creates one Trello card from a local draft, and ties the local record to the card it made. It
previews first, creates only after a person confirms that exact preview, reads the new card back to compare it
with what was sent, and writes the card's identifiers into a local link file. Once a draft is linked it is
never created again.

**It writes to Trello.** The one write it can make is the creation of one card, and only on a board on the
sandbox allowlist.

Run it from the repository root:

    python3 participant/skills/trello-create-card/create.py preview --source live --draft DRAFT.md --link LINK.md \
        --allowlist participant/context/trello/new-card/sandbox-allowlist.json --boards FOLDER --state FOLDER

`--source fake --fake-file FILE` runs against the made-up Trello in `fake_trello_write.py`, kept in that file
between commands, with no network and no credentials.

## 2. Configuration

A live run reads two environment variables, set in the local shell and never stored in a file:
`TRELLO_API_KEY` and `TRELLO_API_TOKEN`. A create needs a token made with write scope. The output, the result
record and anything else that would be shown or saved is searched for both before it is shown or saved. The one
request whose path holds the token is listed as `/tokens/[the token]`.

| Option | What it is |
|---|---|
| `--draft FILE` | The card draft, in the format of the `trello-create-card-preview` skill, with its citations. |
| `--link FILE` | The link file: the local record of the card. One draft has one link file. |
| `--allowlist FILE` | The sandbox allowlist: the ids of the boards a card may be created on. |
| `--boards FOLDER` | The local board indexes to search for duplicates. |
| `--state FOLDER` | Where a preview is kept between the preview and the confirmation. |
| `--log FILE` | Also save the output. |
| `--result FILE` | Save the result record of a create, as Markdown. |

## 3. The four commands

| Command | What it does | Writes to Trello |
|---|---|---|
| `preview` | Shows the board, the list, every field, the exact payload, the token's scope and expiry, the permission check, the duplicate checks and, if every check passes, a fingerprint. | No. It has no way to. |
| `confirm` | Creates the card of one preview, named by its fingerprint, then records and compares it. | One create |
| `verify` | Reads the linked card from Trello by its card id and compares it again with the payload that was sent. | No |
| `reconcile` | After a create whose result was never recorded: finds the card and links it. | No |

Exit codes: 0 done. 1 refused, nothing written to Trello. 2 a create was sent and a person needs to look. 3 a
preview that is not ready, or a verify that found the card changed.

## 4. The preview

The payload is built by the `trello-create-card-preview` skill's own functions, `build_payload` and
`body_bytes`, from the same draft, so a preview here and a preview there cannot mean different things.
Everything that skill checks is checked: the citations, the allowlist, that the list is on the stated board
and not archived, that each label and member exists on the board, the member's role and the token's scope.

This workflow adds two checks.

- **The link file.** A draft that is already linked is refused.
- **A same-name check asked of Trello.** Open cards on the board with exactly this name. This does not depend
  on the local index. Such a card makes the preview NOT READY unless the draft records a person's decision
  that names it.

A preview that is NOT READY is shown in full, saves nothing and has no fingerprint, so there is nothing to
confirm. A preview that is READY is saved in the state folder and shows its fingerprint and its expiry.

## 5. The confirmation

`confirm` needs `--fingerprint` and `--confirmed-by`. There is no option that creates without them. It
refuses, creating nothing, unless all of this holds at that moment:

- the saved preview is unaltered, has not been used, and is at most 15 minutes old;
- the draft file is byte for byte the one that was previewed;
- the payload, worked out again from the draft and from Trello as it is now, has the SHA-256 of the previewed one;
- the board is on the sandbox allowlist, and the list is on that board and not archived;
- Trello says the token may write, and its member may add cards to the board;
- the duplicate checks still pass;
- the draft has no link file.

Then, in this order:

1. It writes the link file, saying a create is being sent and its result is not yet recorded, with the ids of
   every card on the board at that moment.
2. It sends the create, once. The bytes sent are the bytes whose SHA-256 the preview showed.
3. It writes the card id that came back into the link file.
4. It reads the card back from Trello by its card id.
5. It compares the card with the payload, field for field, and writes the comparison and the result record.

The order matters. If anything fails after step 2, the link file already says that a create went out.

The name given with `--confirmed-by` is recorded as given. It must be short plain text and not an email
address.

## 6. Read back and compare

| Field | The same when |
|---|---|
| `idList` | the card is in the list that was sent |
| `pos` | for `bottom`, the card is last of the open cards in its list; for `top`, first; for a number, that number |
| `name`, `desc` | the text read back equals the text sent, character for character |
| `due` | the same instant |
| `idLabels`, `idMembers` | the same ids, in any order |
| `idBoard` | not sent. It must be the board that was previewed |

Something on the card that the payload did not send, such as a label, is a difference. What Trello set is
listed: the card id, short link, number on the board, position number, and when Trello made it, which is read
from the card id.

If any field differs after a create, the command says so, records it in the link file, and exits with code 2.
The card exists by then, so a person needs to look. `verify` reports a difference with exit code 3: the card
may simply have been moved or edited since.

## 7. Not creating the same card twice

Trello has no way to refuse a second create of the same card, and none to try a create without making one. The
protection is this workflow's own, in three layers.

1. **The link file.** A draft that is linked to a Trello card is refused by `preview` and by `confirm`, before
   Trello is contacted.
2. **The intent is written before the create is sent.** A link file that says a create was sent and never
   recorded also stops `preview` and `confirm`. They say to run `reconcile`.
3. **The cards that were there before.** The link file holds the ids of every card on the board just before
   the create was sent. `reconcile` reads the board and looks for a card that is not in that list and holds
   what the payload sent: the list, name, description, due time, labels and members. Exactly one: it is
   linked, read back and compared. None: it says so and creates nothing. More than one: nothing is linked and
   a person needs to look.

A create is sent once in a run and never retried. When no answer comes back, the workflow says it is not known
whether the card was created.

When Trello answers a create with a refusal, the workflow reads the board before believing it. Only if the
board holds no card that was not there before does it remove the link file and report that nothing was created.

What this does not stop: the same card being created some other way, by a person, another tool, or this
workflow on a machine that does not have the link file. There the same-name check stops a card with exactly
the same name, and nothing stops one with a different name.

## 8. The link file

The local card. It holds the card's name, description and sources; the board, list and card ids; which preview
it came from; who confirmed and when; the payload that was sent; and the read-back comparison.

The card is identified by its card id. `verify` fetches the card by that id, wherever it now is and whatever
it is now called.

## 9. Tests

    python3 -m unittest discover -s participant/skills/trello-create-card/tests -v

## 10. What it does not do

- It does not delete, edit, move or archive a card. Removing one it created is done by hand in Trello.
- It does not stop a duplicate made outside this workflow.
- `reconcile` matches on what was sent. A card that someone edited or moved before `reconcile` ran is not
  matched, and is reported only as a card that was not there before.
- It cannot know who typed the confirmation. It records the name it is given. Trello records the token's
  member as the card's creator.
- It does not close the moment between its last check and the create. A card added by someone else in that
  second or two is not seen. The read-back would report a position that is no longer last.
- It reads at most 999 cards of a board.
- It creates a card with the fields the preview skill supports: no checklist, no attachment, no start date.
