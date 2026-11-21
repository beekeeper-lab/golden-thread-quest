# Proof · trello-create-card-preview

Attempt: `trello-attempt-005`

## How this was made

An AI assistant (Claude) wrote the preview, the made-up Trello, the drafts, the tests, the recording scripts
and this file, at the participant's direction. The work was done in small steps, each shown to the participant
before the next.

What the participant did themself:

- Chose what the preview is checked against: a made-up board for the required evidence, plus one real,
  read-only run on their own sandbox board.
- Chose what happens when a check finds a problem: a draft that points at something that is not there is
  refused with no payload, and a valid draft that should not be written yet is shown in full with a verdict
  of NOT READY.
- Ran the real run in their own terminal. The assistant did not contact Trello and did not see or handle the
  key or the token. It read the saved log afterwards.

Statements below are marked **recorded** (a log shows it, against the made-up Trello), **observed** (the
participant's real run shows it, in `logs/live-preview-run.txt`), **tested** (a passing test shows it, with
the output in `logs/tests.txt`) or **not assessed**.

**Nothing was written to Trello in this quest.** No card was created, on the made-up board or the real one.

## What was built

`participant/skills/trello-create-card-preview/preview.py` reads a card draft, asks Trello about the board and
list it names, and shows the whole request a later create would send. It ends in one of three outcomes.

| Outcome | When | What is shown |
|---|---|---|
| REFUSED | The draft points at something that is not there or not allowed. | The reason only. No payload. |
| NOT READY TO WRITE | The draft is valid, and the write should not go ahead yet. | The whole preview, with each reason. Nothing saved for a write. |
| READY TO WRITE | Every check passed. | The whole preview. The payload and its SHA-256 are saved for a later write. |

The made-up Trello, `fake_trello.py`, holds two boards. On the platform board the first list by position is
archived, which is the quest's scenario. The local indexes the duplicate search reads are a copy of that fake,
made by the approved card reader and the approved index generator, neither changed.

Smaller choices the assistant made, each of which the participant can overrule:

- A draft must say its position. There is no default, so a card never lands somewhere nobody chose.
- A board must be on a sandbox allowlist before Trello is asked anything.
- A label must match one label on the board by exact name. Two labels with one name are refused.
- A due time in the past is refused.
- A recorded duplicate decision covers only the cards it names.

## How I know the payload equals what a later write would send (criterion 5)

Plainly: the write does not exist yet, so this cannot be shown end to end. What is established is narrower.

1. **One place makes the payload and one place makes the bytes.** `build_payload` is the only code that puts
   fields into a payload, and `body_bytes` is the only code that turns a payload into the bytes of a request
   body. **tested**: `test_the_payload_is_built_once`.
2. **What is printed is that payload.** The preview prints the payload whole and the SHA-256 of
   `body_bytes(payload)`. The recording script parsed the payload back out of the printed text, made the bytes
   with its own code, and got the same size and SHA-256: 442 bytes, `9c84dc5b…`. **recorded**:
   `logs/preview-run.txt` part 3.
3. **What is saved for the write is that payload.** The saved preview in the state folder holds the same
   payload and the same SHA-256, and `payload.md` holds the same payload. **recorded**: part 3. **tested**:
   `test_the_printed_payload_the_saved_payload_and_the_payload_file_are_the_same`.
4. **Bugs that would break this are caught.** Five were planted: the position shown and left out of the
   payload, a saved payload differing from the one shown, a SHA-256 of the wrong bytes, bytes with no fixed
   order of names, and a description losing its line breaks. Each made a test fail. **recorded**:
   `logs/planted-bugs.txt`, bugs K to O.

What a later write has to do for the claim to hold: import `body_bytes`, read the saved preview by its
fingerprint, check the SHA-256 and the expiry, and send those bytes without building a payload of its own.
That is a requirement on the next quest. **Not assessed** here.

Also **not assessed**: whether Trello accepts this payload. The field names and the comma-joined lists of ids
are taken from Trello's public documentation. Trello has no way to try a create without making one.

## The acceptance criteria, one by one

**1. The list is chosen by identifier and belongs to the stated board.** The draft gives the board and the
list by Trello id, and a name is refused. The preview asks Trello for that list and compares the board Trello
says it is on with the board the draft states. **recorded**: `preview-run.txt` part 2, "Chosen by id. Trello
says it belongs to board …, the stated board: yes." The first list by position, "Old ideas", is archived and
is not the list used. **observed** on the real board: list "Backlog", by id, on the stated board. **tested**:
`TheTarget`, 11 tests.

**2. Labels and members are chosen from those that exist.** Each label name is looked up among the board's
labels and sent as that board's id for it. Each member id is checked against the board's members.
**recorded**: part 2, "each found on the board before being put in the payload: 1 label, 1 member".
**tested**: `LabelsAndMembers`, 9 tests. **Not assessed** on the real board: the sandbox draft names no label
and no member.

**3. A missing list or unknown label stops the preview with a reason.** **recorded**:
`logs/invalid-target-run.txt`, five drafts, each the main draft with one line changed: a list on another
board, a list id nothing has, the archived list, an unknown label, and a member not on the board. Each is
refused with exit code 1, a reason naming what does exist, no payload shown, none saved and no payload file
written. **observed**: on the real board a list id that nothing has was refused; Trello answered 404, and the
reason listed the board's four open lists.

**4. The duplicate result and the permission check appear in the preview.**

- *Permission.* Asked of Trello, not assumed: the role of the token's member on the board, and the token's
  own permissions. **recorded**: part 2 (may add cards, read yes, write yes) and part 5 (a token with read and
  not write: NOT READY, payload still shown). **observed**: the participant's token is read-only, and the real
  preview said so: role admin, "read yes, write NO", verdict NOT READY with that one reason. **tested**:
  `Permission`, 9 tests, including that writing is not assumed when Trello does not give the token's
  permissions.
- *Duplicates.* The `trello-duplicate-search` skill, approved in the last quest, searches the local indexes.
  **recorded**: part 2 (none, PROCEED) and part 4 (a card on another board for the same work: MEDIUM, LINK,
  NOT READY until the draft records a decision about that card, then READY). **observed**: none on the real
  board, with the index and Trello both holding 7 cards. **tested**: `Duplicates`, 12 tests.

**5. The preview contains the exact payload including list and position.** See the section above.
**recorded**: part 2, `idList` and `pos` in the payload; and where in the list: number 4 of 4 open cards,
after card …103. **observed**: number 3 of 3 in "Backlog". **tested**: `ThePayload`, 12 tests, and
`WhereInTheList`, 6.

**6. Running the preview changes nothing in Trello.** Four separate grounds:

- The preview has no code of its own that sends anything, and the approved reader it uses for a live run
  sends GET only. **tested**: `NothingIsWritten`.
- Every request sent is listed, and all were GET: 11 against the fake, 9 against real Trello. **recorded**
  and **observed**.
- The preview's own snapshot of the board's lists and cards is the same before and after. **recorded**: "4
  lists, 6 cards, 92852d0d…" twice. **observed**: "4 lists, 7 cards, 6cdcd14c…" twice.
- The recording script held a fake Trello itself, copied all of it before a preview, and found every board,
  list, card, label, membership and the token record exactly as before. **recorded**: part 6, which is the
  last part before the real run.

**7. Source citations are included.** Every piece of content in the draft has a citation to a file and line,
and each is checked against the file before the preview is made. **recorded**: part 2, six citations.
`payload.md` gives the source beside each field. **tested**: `Sources`, 7 tests: missing, untrue, on the
wrong line, outside `participant/context/`, and for content the draft does not have.

## Where the important artifacts are

| What | Path |
|---|---|
| The card draft | `participant/context/trello/new-card/draft.md` |
| The payload, field by field | `participant/context/trello/new-card/payload.md` |
| The notes the draft cites | `participant/context/trello/new-card/sources/notes.md` |
| The sandbox allowlist | `participant/context/trello/new-card/sandbox-allowlist.json` |
| The refused, not-ready and decided drafts | `participant/context/trello/new-card/refused/`, `not-ready/`, `decided/` |
| The local indexes of the made-up boards | `participant/context/trello/new-card/fixture/boards/` |
| The draft for the real sandbox board | `participant/context/trello/new-card/draft-sandbox.md` |
| The preview, the made-up Trello and how to use them | `participant/skills/trello-create-card-preview/` |
| The preview run | `logs/preview-run.txt` |
| The refused previews | `logs/invalid-target-run.txt` |
| The real run, also copied into the end of `preview-run.txt` | `logs/live-preview-run.txt` |
| The test output and the planted-bugs log | `logs/tests.txt`, `logs/planted-bugs.txt` |
| The scripts that made the fixture and the logs | `scripts/` |

The quest names `participant/evidence/trello-create-card-preview/attempt-001/`. The application created this
attempt as `trello-attempt-005`. Copies of this file, `logs/preview-run.txt` and `logs/invalid-target-run.txt`
are in `attempt-001/`, with a note saying so.

## How to reproduce the behavior

From the repository root. None of these contacts anything.

    python3 participant/evidence/trello-create-card-preview/trello-attempt-005/scripts/make_fixture.py
    python3 participant/skills/trello-create-card-preview/preview.py --source fake \
        --draft participant/context/trello/new-card/draft.md \
        --allowlist participant/context/trello/new-card/sandbox-allowlist.json \
        --boards participant/context/trello/new-card/fixture/boards --state SOME/EMPTY/FOLDER --now 2026-11-20T09:00:00Z
    python3 -m unittest discover -s participant/skills/trello-create-card-preview/tests -v
    python3 participant/evidence/trello-create-card-preview/trello-attempt-005/scripts/planted_bugs.py
    python3 participant/evidence/trello-create-card-preview/trello-attempt-005/scripts/record_evidence.py

The real run needs `TRELLO_API_KEY` and `TRELLO_API_TOKEN` set in the terminal, and the participant's own
sandbox board:

    python3 participant/evidence/trello-create-card-preview/trello-attempt-005/scripts/live_run.py

## What was tested or validated

| Check | Result | Where |
|---|---|---|
| Unit tests | 84 pass | `logs/tests.txt` |
| Planted bugs: 31 faults put into `preview.py` one at a time | all 31 caught by at least one test; the file restored byte for byte | `logs/planted-bugs.txt` |
| Recorded preview run, parts 1 to 6 | 35 checks pass | `logs/preview-run.txt` |
| Recorded refused previews, five drafts | 23 checks pass | `logs/invalid-target-run.txt` |
| The real read-only run | 15 checks pass | `logs/live-preview-run.txt` |

`preview-run.txt` ends "50 checks": the 35 and the real run's 15.

Three tests were wrong when first run and were corrected. In each the test was at fault, not the preview: one
looked for the word "environ" and found it in "environment" in the description at the top of the file, one
expected a backslash in a file name that has none, and one ran two identical previews in one second into one
state folder, which the preview refuses by design.

## Remaining limitations

- **The payload has never been sent.** Whether Trello accepts it is not assessed, and cannot be without
  creating a card.
- **Only one refusal was observed on real Trello:** a list id that nothing has. The others, a list on another
  board, an archived list, an unknown label and a member not on the board, are recorded against the fake only.
  The fake was built from Trello's public documentation and is not checked against Trello field by field.
- **Only a read-only token was observed.** The preview read the real token's record correctly as read yes,
  write no. What Trello returns for a token that may write has not been seen.
- **"Unchanged" is narrow.** The snapshot covers the board's lists and cards: which exist, and each card's
  list, position, archived state and last activity. It does not cover labels, members, comments or other
  boards, and it reads at most 999 cards.
- **The preview is a moment.** The position, the duplicate result and the permission check are as of the
  preview. A READY preview expires after 15 minutes, and the board can change inside that time.
- **The duplicate search reads a local copy.** A card created in Trello since the records were saved is not
  searched. The preview warns when Trello holds more cards than the index, and says nothing when a card was
  swapped for another and the counts still agree.
- **The permission check is two questions.** The member's role and the token's scope. A limit set elsewhere,
  such as a workspace setting, is not asked about.
- **A recorded decision is taken on trust.** The preview cannot know a person wrote it. The decided draft in
  the fixture carries a made-up decision, as an example. It is not a decision the participant made.
- **Stretch goals.** Where in the list the card will sit is shown. Checking the due date against the board's
  conventions is not done: only a due time in the past is refused.

## Reflection

*What could the reader of your preview still not predict?*

Four things, and the preview says the first two itself.

What Trello decides: the card's id, its short link, its number on the board and, for "bottom", the actual
position number. And whether Trello accepts the request at all, because there is no way to ask without
creating the card.

What happens between the preview and the write. The preview shows the list as it is now: third of three in
Backlog. If someone adds, moves or archives a card in the next few minutes, "bottom" lands somewhere else, and
if the list itself is archived the card goes where nobody looks, which is the scenario this quest began with.
The 15-minute expiry narrows that gap and does not close it.

What the card sets off once it exists. Members put on the card are notified, people watching the list are
notified, and any automation on the board that fires on a new card runs. None of that is in the payload and
none of it is asked about.

And what was never in the local copy. The duplicate result is true of the cards saved locally. A card someone
created in Trello an hour ago is not among them.

So the preview makes the request predictable. It does not make the board's reaction to it predictable.

## Sensitive values

The key and the token were supplied by the participant through environment variables in their own terminal.
They are in no file, log or saved address. The one request whose path holds the token is listed as
`/tokens/[the token]`, and the preview's output and every file it writes are searched for both before anything
is shown or saved.

The real run's log holds the sandbox board's name and id, its lists' names and ids, card ids, counts,
fingerprints, the token's expiry time and the made-up draft. It holds no card name, no card text and no member
id. The real cards' text stayed in a scratch folder outside the repository, shown as SCRATCH. Everything else
in the evidence is made up. No personal name, email address or home-folder path is in the evidence.
