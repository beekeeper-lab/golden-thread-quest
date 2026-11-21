# Write preview rules

What the write-preview workflow shows before it changes anything, and what it needs before it will change
anything. Written by an AI assistant (Claude) at Beau Brown's direction.

The workflow is `participant/evidence/base-camp-write-preview/base-attempt-006/scripts/writer.py`. The system it
writes to is a simulated story board, `board.py` beside it, which is one local file. Recorded runs are in
`logs/` in the same attempt folder.

## 1. What a preview must contain

A preview is the full list of what would be written, shown before anything is written. It has these parts, in
this order.

| Part | What it says | Why |
|---|---|---|
| **How many changes** | One line at the top, for example `3 changes: 2 new stories, 1 story updated`. | A reader should know the size before reading the detail. Twelve is a different job from one. |
| **The target** | Which system and which board the changes go to. For each change, which story: an existing one by its ID, or `a new story`. | The same change is harmless in one place and costly in another. |
| **The action** | For each change, one word: `CREATE` or `UPDATE`. | So nobody has to work out from the fields what kind of change it is. |
| **Every field that would be written** | For each change, each field by name with its whole value. For an update, the value now and the value after. | This is the change. Anything not shown here is not written. |
| **What is left alone** | How many stories on the board are not touched. | So the reader can see the change has edges. |
| **A plain statement** | `Nothing has been written.` | So a preview cannot be read as a result. |

Three things a preview must not do:

- **It does not shorten a value.** A long description is shown whole. A value cut to fit a line would hide part
  of what gets written.
- **It does not leave a field out.** If a field would be written and is not in the preview, that is a fault in
  the workflow, not a tidy preview.
- **It holds no credential.** The workflow needs none, because the system is simulated. A change with a field
  named like a secret (`password`, `token`, `secret`, `api_key` and the like) is refused before a preview is
  made, so one cannot be shown, saved or passed around by mistake.

## 2. How a confirmation is tied to its preview

Every preview ends with a **fingerprint**: a short code worked out from what the preview contains. For example
`3f9a1c04b7e2`.

The fingerprint is worked out from three things together:

1. **The changes**: every target, action, field and value in the preview.
2. **The board as it was** when the preview was made.
3. **The time** the preview was made.

Change any one of them and the code comes out different. A different title gives a different code. So does the
same change against a board that has moved on, and so does the same change previewed a second time.

To confirm, a person gives two things:

- **the fingerprint** of the preview they read, and
- **their name**.

There is no other way to make the workflow write. In particular:

- **There is no `--yes`, `--force` or "confirm the latest".** A confirmation that does not name a fingerprint is
  refused.
- **Preview and write are separate runs.** One run never shows a preview and then writes it.
- **The workflow checks again at the moment of writing.** It works out the change afresh from the change file
  and the board as they are now, and compares that with the preview the fingerprint names. If anything differs,
  the confirmation is refused, nothing is written, and the person is told to make a new preview and read it.
- **A fingerprint is used once.** After its change is written, the same fingerprint is refused. Confirming twice
  does not write twice.

The reason for all of this is the difference between "yes, go ahead" and "yes, this". A bare yes approves
whatever the change has become by the time it is given. A fingerprint approves only what was read.

## 3. When a preview expires

A preview can be confirmed for **15 minutes** from the moment it was made. The preview shows both times: when
it was made and when it expires.

After that, a confirmation naming its fingerprint is refused and nothing is written. The message gives the
preview's age and the limit, and says to make a new preview and read it. This holds even when the change file
and the board are exactly as they were. An expired preview is not brought back to life. It can only be replaced.

Why a time limit as well as the check in rule 2: rule 2 catches a change that differs. It does not catch a
person who read the preview a long time ago and no longer remembers what it said. Fifteen minutes is long
enough to read a preview with care, and short enough that the person confirming is the person who just read it.

A preview can go stale in two ways, and both end the same way:

| How it went stale | What the workflow says | What is written |
|---|---|---|
| **Too old**: more than 15 minutes since it was made. | `REFUSED: this preview has expired`, with its age. | Nothing. |
| **Overtaken**: the change file or the board is no longer what the preview showed. | `REFUSED: the change is not the one that was previewed`, with what differs. | Nothing. |

A stale preview is kept on disk as a record of what was shown. It is not deleted and it cannot be confirmed.

The time comes from the clock of the machine the workflow runs on. To show the limit working without waiting 15
minutes, the workflow has one option for tests, `--pretend-minutes-later N`. It can only move the workflow's
idea of "now" forward. So it can make a preview look older and be refused. It cannot make an old preview look
new.
