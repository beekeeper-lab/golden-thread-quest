# Proof · trello-create-card

Attempt: `trello-attempt-006`

## How this was made

An AI assistant (Claude) wrote the workflow, the made-up Trello, the draft, the tests, the recording scripts
and this file, at the participant's direction. The work was done in small steps, each shown to the participant
before the next.

What the participant did themself:

- Chose how a second run is kept safe: a link file written before the create is sent, and a `reconcile`
  command that finds a card made by a lost create without putting any marker in the card.
- Chose the card: a made-up card with a name, a description and a due date, for their own sandbox board.
- Made a token with write scope, valid for one day, in their own browser and terminal.
- **Made the write.** They ran the preview, read it, typed its fingerprint into their own terminal and ran the
  confirmation. Then they ran the workflow a second time, and the verify.

The assistant did not contact Trello, did not run any command against the real board, did not supply the
confirmation, and did not see or handle the key or the token. It read the saved logs afterwards.

Statements below are marked **observed** (the participant's real run shows it, in a `logs/live-*.txt` file),
**recorded** (a log shows it, against the made-up Trello), **tested** (a passing test shows it, with the
output in `logs/tests.txt`) or **not assessed**.

## What was written to Trello

**One card**, on the participant's own sandbox board, "GTQ Sandbox", which is on the sandbox allowlist.

| | |
|---|---|
| Board id | `6afdf376f8b9111df7e27f99` |
| List | "Backlog", list id `6afdf3911014b50669965df7` |
| Card id | `6b00b32ea6e47268f6721469` |
| Made by Trello at | 2026-11-20 20:53:02 UTC |
| Confirmed by | the participant, at 2026-11-20 20:53:00 UTC |
| Preview | fingerprint `847183421875` |

One POST was sent. Nothing else was written, then or since. The card is still on the board. Its text is made up
and it can be deleted by hand: the workflow has no way to delete.

## How I verified the card equals the preview (criterion 1)

Three separate comparisons, and they agree.

1. **The bytes.** The preview showed the payload and the SHA-256 of the bytes that would be sent,
   `c7eac8df…`. Before writing, the confirmation worked the payload out again from the draft and from Trello,
   and checked it has that SHA-256. **observed**: `live-confirmation.txt`, "the payload worked out again now
   has the SHA-256 of the previewed one … ok". The payload is built by the functions of the approved preview
   skill, `build_payload` and `body_bytes`, not by code of this workflow's own. **tested**:
   `test_the_bytes_sent_are_the_bytes_whose_sha_the_preview_showed` captures the bytes handed to the made-up
   Trello and hashes them.
2. **The read-back at the create.** The card was fetched from Trello by the card id it returned, and each
   field the payload sent was compared. **observed**:

   | Field | Sent | Read back | Verdict |
   |---|---|---|---|
   | list | `6afdf391…` | `6afdf391…` | the same |
   | position | "bottom" | number 3 of 3 open cards in the list | the same: last in the list |
   | name | "Made-up card to check the create workflow" | the same text | the same |
   | description | 97 characters | 97 characters | the same, character for character |
   | due | 2026-12-18T17:00:00.000Z | 2026-12-18T17:00:00.000Z | the same |
   | board | not sent: it follows from the list | `6afdf376…` | the board that was previewed |

3. **The read-back again, nine minutes later.** `verify` fetched the card by its id and compared it again:
   every field the same, and still 3 of 3 in the list. **observed**: `live-verify.txt`.

The comparison is not a formality. Four tests have the made-up Trello create a card that differs from what was
sent, in its due time, list, description or labels, and each is caught. Seven more test the comparison
directly. **tested**: `WhenTrelloAnswersOtherwise` and `Compare`. Eight planted bugs that send other bytes or
weaken the comparison are each caught. **recorded**: `logs/planted-bugs.txt`, bugs H and Q to W.

What this does not show: labels and members. The real card has neither. Those are compared against the
made-up Trello only. See limitations.

## The acceptance criteria, one by one

**1. The card created matches the previewed payload field for field.** See above. **observed**, **recorded**
in `confirmation.txt` part 1, where the recording script reads the card out of the made-up Trello's own file.

**2. The returned identifiers are written to the local file.** `participant/context/trello/new-card/linked.md`
holds `card_id`, `list_id`, `board_id` and the short link Trello returned. **observed**: "Written to the link
file: the card id 6b00b32e…, the list id … and the board id …". **tested**:
`test_the_returned_identifiers_are_written_to_the_link_file`.

**3. The local file is matched to the Trello card by identifier afterwards.** `verify` reads the card id from
the link file and fetches that card. **observed**: "Matched to Trello by card id 6b00b32e…: found." **tested**:
`Verify`, including a card that was renamed and moved to another list: it is still found, by its id, and the
changes are reported.

**4. A preview shows the board, the list and the exact changes, and nothing is written before the human
confirms it.** **observed**: `live-preview.txt` shows board "GTQ Sandbox", list "Backlog", the one request, the
payload, and "10 requests, every one a GET", with the board snapshot the same before and after: 4 lists, 7
cards. The preview command has no way to write. **tested**: `test_a_preview_has_no_way_to_write`. Two
confirmations that were not proper were refused on the real board before the proper one: see criterion 7.

**5. The preview records the permission check and the duplicate check, or states where Trello cannot perform
one.** **observed**: the token's scope, "read yes, write yes", and its expiry, 2026-11-21T20:29:55Z; the
member's role, admin, which may add cards; three duplicate checks, all clear; and the statement "Where Trello
cannot check: it has no way to refuse a second create of the same card, and no way to try a create without
making one." **recorded**: `preview.txt` part 2, a token that may not write gets no fingerprint.

**6. The workflow writes only to a board on an explicit sandbox allowlist and refuses any other.**
**recorded**: `confirmation.txt` part 5, twice: a draft for a board the allowlist leaves out is refused at the
preview, and a board taken off the allowlist after a preview is refused at the confirmation. **tested**. The
allowlist is `participant/context/trello/new-card/sandbox-allowlist.json`. **Not assessed** on real Trello: it
would mean pointing the workflow at a board that is not a sandbox.

**7. The confirmation is tied to a fingerprint of the exact preview, is refused when missing or when the
change differs, and expires after a stated time.**

- *Tied to the fingerprint, in the same run as the write.* **observed**: "CONFIRMATION for preview
  847183421875, given by: the participant", then one POST, in one run of one command.
- *Refused when missing.* **observed**, and not planned. The participant's first two attempts at the
  confirmation went wrong: the first was run with the placeholder word still where the fingerprint goes, the
  second with an empty fingerprint. Both were refused with nothing written: "a fingerprint is 12 characters"
  and "no confirmation was given". They are kept as `live-confirmation-refused.txt` and
  `live-confirmation-missing.txt`. **recorded** too: `confirmation.txt` part 2.
- *Refused when the change differs.* **recorded**: part 3, the draft's position edited after the preview: "the
  payload now differs in pos". **tested**, including a draft edited without changing the payload.
- *Expires.* The limit is 15 minutes, stated in every preview. **recorded**: part 4, refused at 16 minutes.
  **observed**: the real confirmation was given 2 minutes after its preview.
- *Used once.* **observed**: `live-rerun-confirm.txt`.

**8. A result record holds the board, list and card identifiers, the identifier of what was created, the
timestamp and the confirmer.** `participant/context/trello/results/create-card.md`. **observed**. What was
created is the card itself, so its identifier is the card id. The time is given twice: by this workflow's
clock, and by Trello's, read from the card id.

**9. Running the approved workflow again creates no duplicate, or the quest states the limit.** **observed**:
the preview again is refused, naming the card (`live-rerun.txt`); the same confirmation again is refused
(`live-rerun-confirm.txt`); and `verify` afterwards shows the card still 3 of 3 in its list, so no second card
was added there. **recorded**: `rerun.txt`, where the script checks the made-up Trello's own file. The limit,
stated: Trello cannot prevent a repeat. The protection is the link file, which is local. On a machine without
it, a card with exactly the same name on the board makes the preview NOT READY (`rerun.txt` part 5), and a card
under a different name would not be stopped. A person would notice it on the board.

## The lost answer (the second stretch goal)

This cannot be made to happen on real Trello on purpose, so it is **recorded** against the made-up Trello only,
in `logs/recovery.txt`, and **tested** in `WhenTheAnswerIsLost`, 9 tests.

- The card is created and the answer never arrives: exit code 2, "NOT KNOWN whether Trello created the card",
  one POST, not sent again. The link file already says a create was sent.
- After that, a new preview and the old confirmation are both refused.
- `reconcile` finds exactly one card that was not on the board before and holds what was sent, links it and
  compares it, writing nothing to Trello.
- If the create never reached Trello, `reconcile` says NOT FOUND and creates nothing.
- If Trello refuses the create outright, the workflow reads the board before believing it.

## Where the important artifacts are

| What | Path |
|---|---|
| The local link, with the read-back | `participant/context/trello/new-card/linked.md` |
| The result record | `participant/context/trello/results/create-card.md` |
| The draft that was created, and its sources | `participant/context/trello/new-card/draft-create.md`, `sources/create-notes.md` |
| The workflow, the made-up Trello and how to use them | `participant/skills/trello-create-card/` |
| The preview | `logs/preview.txt` |
| The approved run and the four refusals | `logs/confirmation.txt` |
| The second run | `logs/rerun.txt` |
| The lost answer | `logs/recovery.txt` |
| The real run, each also copied into the end of the log it belongs to | `logs/live-preview.txt`, `live-confirmation-refused.txt`, `live-confirmation-missing.txt`, `live-confirmation.txt`, `live-rerun.txt`, `live-rerun-confirm.txt`, `live-verify.txt` |
| The test output and the planted-bugs log | `logs/tests.txt`, `logs/planted-bugs.txt` |

The quest names `participant/evidence/trello-create-card/attempt-001/`. The application created this attempt
as `trello-attempt-006`. Copies of this file, `logs/preview.txt`, `logs/confirmation.txt` and `logs/rerun.txt`
are in `attempt-001/`, with a note saying so.

## How to reproduce the behavior

From the repository root. None of these contacts anything.

    python3 -m unittest discover -s participant/skills/trello-create-card/tests -v
    python3 participant/evidence/trello-create-card/trello-attempt-006/scripts/planted_bugs.py
    python3 participant/evidence/trello-create-card/trello-attempt-006/scripts/record_evidence.py

The real run cannot be reproduced as it was: the draft is linked now, so the workflow refuses to create it
again. That refusal is itself reproducible, with the key and token set, as is the verify:

    python3 participant/skills/trello-create-card/create.py verify --source live --link participant/context/trello/new-card/linked.md

## What was tested or validated

| Check | Result | Where |
|---|---|---|
| Unit tests | 69 pass | `logs/tests.txt` |
| Planted bugs: 31 faults put into `create.py` one at a time | all 31 caught by at least one test; the file restored byte for byte | `logs/planted-bugs.txt` |
| Recorded preview | 15 checks pass | `logs/preview.txt` |
| Recorded approved run and refusals | 28 checks pass | `logs/confirmation.txt` |
| Recorded second run | 9 checks pass | `logs/rerun.txt` |
| Recorded lost answer | 13 checks pass | `logs/recovery.txt` |
| The real run | one card created; read back the same twice; second run refused | `logs/live-*.txt` |

The tests passed when first run. Two faults were in the recording script and were corrected: a draft it made
for one refusal kept citations for fields it had removed, and it counted requests in output that did not list
them. For the second, the workflow was changed to list its requests when a create's outcome is uncertain,
which is when a person most needs to see them. That change was made before the real run.

## Remaining limitations

- **Only part of this was seen on real Trello.** Observed: the preview, two unplanned refusals, the create,
  the read-back, the second run and the verify. Recorded against the made-up Trello only: the refusals for a
  changed draft, an expired preview and a board off the allowlist, and everything about a lost answer. The
  made-up Trello was built from Trello's public documentation and is not checked against Trello field by field.
- **Labels and members were not created on real Trello.** The real card has neither, by the participant's
  choice. Creating a card with its label in one request, the first stretch goal, is shown against the made-up
  Trello only. Whether real Trello takes the comma-joined ids the payload uses for them is not assessed.
- **The protection against a second card is local.** It is the link file. Another machine, another tool or a
  person is stopped only by the same-name check, and only for exactly the same name.
- **`reconcile` matches on what was sent.** If someone edits or moves the new card before `reconcile` runs, it
  is not matched, and is reported only as one more card that was not there before. If someone creates an
  identical card in the same moment, two match and nothing is linked.
- **There is a gap between the last check and the create.** A second or two. A card added by someone else then
  is not seen before the write. The read-back would show the new card is no longer last.
- **"Confirmed by" is a typed name.** The workflow cannot know who typed it. Trello's own record of the card's
  creator is the token's member.
- **`verify` reads the card twice.** A harmless extra GET, visible in `live-verify.txt`. Left as it is, so that
  the workflow is the one the real run used.
- **The card stays on the board.** The workflow cannot delete or archive. The participant removes it by hand.
- **The token is valid until 2026-11-21 20:29 UTC.** It can write to any board its member can. The participant
  can revoke it sooner in Trello's account settings.

## Reflection

*What happens locally if the write succeeds but recording the identifier fails?*

Without care, the worst thing: Trello holds a card that nothing local knows about, and the next run, seeing no
record, makes it again. That is the scenario this quest starts from.

Here, the local side is told before the write, not after. The link file is written first, saying a create is
being sent and listing every card on the board at that moment. So if the write succeeds and recording the card
id fails, whether because the answer was lost or because the file could not be written, what is left locally
is a link file that says "sent, result not recorded". Every later preview and confirmation stops on it. If
the id did come back, it is printed with the instruction to write it down. And `reconcile` can find the card
without the id: it is the one card on the board that was not in the list and holds what was sent.

That was tested by making the second write of the link file fail: the card exists, the id is shown, nothing
creates again, and `reconcile` links it.

What it does not cover is the first write failing, which is harmless because nothing has been sent yet, and
the link file being lost altogether. Then Trello has the card and this machine has nothing. Only the same-name
check stands between that and a second card, and it needs the name not to have changed.

## Sensitive values

The key and the token were supplied by the participant through environment variables in their own terminal.
They are in no file, log or saved address. The one request whose path holds the token is listed as
`/tokens/[the token]`, and the output and every file written are searched for both before anything is shown or
saved. Each real log ends with that search's result.

The real logs hold the sandbox board's name and id, its lists' names and ids, card ids, the made-up card's own
text, the token's expiry time and the name "the participant". They hold no other card's name or text and no
member id. The other cards' text stayed in a scratch folder outside the repository. Everything else in the
evidence is made up. No personal name, email address or home-folder path is in the evidence.
