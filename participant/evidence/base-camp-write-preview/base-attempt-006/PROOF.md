# Proof · base-camp-write-preview

Attempt: `base-attempt-006`

## How this was made

An AI assistant (Claude) wrote the rules, the simulated board, the workflow, the recording script and this
file, at Beau Brown's direction. The work was done in small steps, each shown to Beau before the next.

Beau read the preview of the three-change sample before the confirm step was built, and said it was clear to
him. He decided that the confirmation made 14 minutes on should have a log of its own, so that
`logs/refused.txt` holds refusals only. The 15-minute limit, what goes into the fingerprint, and the
use-once rule were proposed by the assistant and shown to Beau as his to change.

In every recorded run the confirmation carries the name `Beau Brown`. That name was typed by the recording
script, not by Beau at a keyboard.

Statements below are marked **observed** (a run recorded in `logs/` shows it) or **not assessed**.

## How a confirmation is bound to its preview (criteria 3 and 4)

Every preview ends with a fingerprint, a 12-character code. A confirmation must give that code. There is no
way to confirm without one.

The code is worked out from three things together: every change in the preview (target, action, field and
value), the whole board as it was when the preview was made, and the time the preview was made. It is the first
12 characters of a SHA-256 hash of those three. The preview is saved beside the board in a file named by the
code.

At the moment of confirming, the workflow does not trust the code alone. It does four checks, and writes only
if all four pass:

1. A saved preview with that code exists.
2. The saved preview still hashes to its own code. If the file was edited after it was made, it does not.
3. The preview is not older than 15 minutes, and has not been used.
4. The change is worked out again, from the change file and the board as they are now, and compared with the
   saved preview, step by step and field by field. The board's fingerprint is compared too.

So the confirmation is bound twice over: by the code, which names one saved preview, and by check 4, which
holds the current change against what that preview showed.

- Criterion 3, a confirmation names or fingerprints the exact preview. **Observed** in `logs/preview.txt` and
  `logs/confirmed.txt`: the fingerprint printed at the end of the preview is the one given to `confirm`, and the
  result line names it. Also **observed** in `logs/preview.txt`, step 4: a confirmation with no fingerprint is
  refused, and so is one with a code that no preview has.
- Criterion 4, a change that differs is refused. **Observed** in `logs/refused.txt`, refusal 1: one word in
  one field of the change file is altered after the preview (`doing` to `done`). The confirmation names the
  preview that was read and is refused with `change 2 (UPDATE DEMO-5): status differs from the preview`. The
  board's fingerprint is the same before and after.
- "This preview", not "the last preview". **Observed** in `logs/refused.txt`: refusals 1 and 2 preview the same
  change against the same board one second apart, and the two previews have different fingerprints.

What this does not do: the code is 12 characters of the hash, and it only picks out which saved preview is
meant. The check that the change matches is done on the full contents, not on the code. Whether a person could
build two different previews with the same 12 characters was **not assessed**.

## What happens to a preview that goes stale (criterion 5)

It cannot be confirmed, nothing is written, and the person is told to make a new preview and read it. A stale
preview is never brought back. It is only replaced.

A preview goes stale in three ways.

| How | What the workflow says | Shown by |
|---|---|---|
| **Too old.** More than 15 minutes have passed since it was made. | `REFUSED: this preview has expired. It was made 16 minutes ago and the limit is 15.` | **Observed**: `logs/refused.txt`, refusal 2. The change file and the board are exactly as previewed. Only the time differs. Board unchanged. |
| **Overtaken.** The change file, or the board, is no longer what the preview showed. | `REFUSED: the change is not the one that was previewed`, with what differs. | **Observed**: `logs/refused.txt`, refusal 1 (the change file) and refusal 3 (the board). Board unchanged by both. |
| **Used.** Its changes have been written. | `REFUSED: the preview ... has already been confirmed and written. A fingerprint is used once.` | **Observed**: `logs/confirmed.txt`, step 5. Board unchanged. |

The time limit is 15 minutes, and each preview prints when it was made and when it expires. Age is counted
from the time saved in the preview. That time is part of what the fingerprint is worked out from, so editing
the saved file to make a preview look newer breaks its fingerprint and it is refused as altered. **Observed** in
`logs/refused.txt`, refusal 4.

The refusal for age is for age alone. **Observed** in `logs/within-limit.txt`: one preview is refused at 16
minutes and confirmed at 14, with the change file and the board the same both times.

How the age was shown without waiting: the workflow has a test option, `--pretend-minutes-later N`, which
moves its clock forward by N minutes, and each run that uses it prints `TEST CLOCK`. It takes only a whole
number from 0 up, so it can make a preview look older and cannot make one look newer. No run waited a real 15
minutes, so expiry by the real clock is **not assessed**.

A stale preview stays on disk as a record of what was shown. Old previews are not cleaned up, so the folder
grows.

## Reflection: what a tired reviewer would skim past

Two parts.

**The descriptions of new stories, in the middle of the list.** Each `CREATE` block has the same shape: an id,
a title, a description, a status. After the first one the eye learns the shape and reads the titles only. The
description is the longest field and the one most likely to be wrong, and it is the one that gets skipped. In a
list of twelve, the blocks in the middle get the least attention of all.

**A change of one word.** In `logs/refused.txt`, refusal 1, the whole difference is `doing` against `done`. The
two words start the same and sit in the same place on the line. The workflow caught it because it compares
every character. A person reading the second preview would have had to catch it by eye.

What the preview already does about this:

- The number of changes is the first thing it says, so twelve does not read as one.
- An update shows only the fields that change, as the value now and the value after, so there is less to read
  and the before and after sit together.
- Nothing is shortened, so the part that is wrong is at least on the page.

What would make it harder to skim, and is not built:

- **Ask for something that can only be got by reading.** The fingerprint can be copied without reading a line.
  If the confirmation also had to give the number of changes, or the id of each story to be updated, copying
  would not be enough.
- **Refuse a preview that is too long to read with care.** A limit of, say, five changes to a preview would
  turn the twelve stories in the scenario into three previews, each short enough to read.
- **Mark the single word that differs** inside a value, so `doing` and `done` do not look alike.

None of these makes a person read. They raise the cost of not reading.

## What was built

Three things, in this attempt folder or `participant/context/`.

- **The rules**, `participant/context/write-preview-rules.md`: what a preview must contain, how a confirmation
  is tied to it, and when it expires.
- **A simulated story board**, `scripts/board.py`. The "external system" is one local JSON file of made-up
  stories. Each story has an id, a title, a description and a status. There is no network, no account and no
  login. `board.py show` lists the stories and prints a fingerprint of the whole board, which is how each log
  shows whether the board changed.
- **A workflow**, `scripts/writer.py`, with two commands that are always separate runs.
  - `preview` reads a change file, shows everything it would write, saves that preview beside the board, and
    stops. It has no code path that writes to the board.
  - `confirm` writes the changes of one preview, named by its fingerprint, after the four checks described
    above. Each write leaves a record beside the board.

A change file can create stories and update stories. It cannot delete one: the workflow has no delete.

The first stretch goal is done as part of the basic design: an update is shown as the value now and the value
after. The second, editing a preview, is not done as a feature. Its effect is covered: a change file edited
after its preview no longer matches, and the old confirmation is refused (`logs/refused.txt`, refusal 1).

## Where the important artifacts are

| What | Path |
|---|---|
| The rules | `participant/context/write-preview-rules.md` |
| A preview that stops, and the board unchanged | `participant/evidence/base-camp-write-preview/base-attempt-006/logs/preview.txt` |
| The same preview confirmed, and the board after | `participant/evidence/base-camp-write-preview/base-attempt-006/logs/confirmed.txt` |
| Refused confirmations, and the board unchanged | `participant/evidence/base-camp-write-preview/base-attempt-006/logs/refused.txt` |
| One preview refused at 16 minutes, confirmed at 14 | `.../base-attempt-006/logs/within-limit.txt` |
| The simulated board | `.../base-attempt-006/scripts/board.py` |
| The workflow | `.../base-attempt-006/scripts/writer.py` |
| The script that records the logs | `.../base-attempt-006/scripts/record_evidence.py` |
| The change files the runs use | `.../base-attempt-006/scripts/sample/` |
| The board, saved previews and write records the runs left | `.../base-attempt-006/work/` |

## How to reproduce the behavior

Needs Python 3.9 or later and nothing else. From the repository root:

    cd participant/evidence/base-camp-write-preview/base-attempt-006
    python3 scripts/record_evidence.py

This empties `work/`, makes a fresh board, and rewrites the four logs. It takes a few seconds. The fingerprints
and times in the logs will differ from the ones committed here, because the time a preview is made is part of
its fingerprint. Everything else should be the same.

To try it by hand:

    python3 scripts/board.py init work/try.json
    python3 scripts/writer.py preview --board work/try.json --change scripts/sample/follow-ups.json
    python3 scripts/writer.py confirm --board work/try.json --change scripts/sample/follow-ups.json --fingerprint CODE --confirmed-by "Your name"

with `CODE` replaced by the fingerprint the preview printed.

## What was tested or validated

Each line names the recorded run that shows it. In every log, the board is listed with its fingerprint before
and after, and the recording script writes `The board is UNCHANGED` or `The board is CHANGED` from comparing
the two.

| # | Criterion | Shown by |
|---|---|---|
| 1 | A preview lists the target, the action and every field that would be written. | **Observed**: `logs/preview.txt`, step 2. The target is the board, its file, and for each change `a new story` with the id it will get, or the story's id and present title. The action is `CREATE` or `UPDATE`. Each field is listed by name with its whole value, and a two-line description keeps both lines. That every field was shown: in `logs/confirmed.txt`, step 4, the record of what was written holds the same fields and values as the preview, and nothing else. |
| 2 | Running without confirmation changes nothing, and the output says so. | **Observed**: `logs/preview.txt`. The preview begins `PREVIEW. Nothing has been written.` and ends `Nothing has been written. The board is as it was.` (step 2). The board's fingerprint is the same after it (step 3). A confirmation with no fingerprint, `--yes` on either command, and a fingerprint no preview has, are each refused, and the board's fingerprint is still the same (step 4). |
| 3 | A confirmation names or fingerprints the exact preview it approves. | **Observed**: the fingerprint that ends the preview in `logs/preview.txt` is the one given to `confirm` in `logs/confirmed.txt`, step 2, and the result names it. |
| 4 | If the proposed change differs from the one previewed, the confirmation is refused and nothing is written. | **Observed**: `logs/refused.txt`, refusal 1. One word differs. Refused, naming the change and the field. Board unchanged. |
| 5 | A preview older than the stated time limit cannot be confirmed. | **Observed**: `logs/refused.txt`, refusal 2, by the test clock. Each preview states its limit: `Expires: ... (15 minutes after it was made)`. Refused at 16 minutes with the age and the limit. Board unchanged. `logs/within-limit.txt` shows the same preview confirmed at 14. |
| 6 | The result records what was written and that a person confirmed it. | **Observed**: `logs/confirmed.txt`. Step 2 prints each change written, `Confirmed by`, `Confirmed at` and the preview's fingerprint. Step 4 prints the saved record: the name, the time, the board's fingerprint before and after, and every field written. What is recorded is the name given with the confirmation. See "Remaining limitations". |
| 7 | A person with no knowledge of the code can read a preview and say what will happen. | One reader. Beau, who has not read `writer.py`, read the three-change preview in `logs/preview.txt` before the confirm step existed and said it was clear to him. He is the participant, not an outside reader, and he was not asked to say back what would happen. Beyond that, **not assessed**. |

The safety constraints:

- **Use only a simulated system.** The board is a local file. `board.py` and `writer.py` import nothing that
  can use a network, and take no address, account or login. They read and write only the board file given and
  the two folders beside it.
- **Do not let a flag such as `--yes` skip the preview.** **Observed**: `logs/preview.txt`, step 4. `--yes` is
  not an option of either command, and a confirmation with no fingerprint is refused. `confirm` has one extra
  option, `--pretend-minutes-later`. It only moves the clock forward, and every other check still runs.
- **Do not store a credential in the preview.** The workflow reads none. **Observed**: `logs/preview.txt`,
  step 5. A change with a field named `auth_header` is refused before a preview is made, and the folder of
  saved previews holds the same one file before and after.

## Remaining limitations

Known so far. There may be others.

About "a person confirmed it":

- **The workflow records the name it is given.** It cannot tell a person from a script that supplies a name
  and a fingerprint. In every recorded run the confirmation came from the recording script. What the design
  does ensure is that whoever confirms must supply the fingerprint of one particular preview.
- **It cannot tell a preview that was shown from a saved file written by hand.** A saved preview is checked
  against its own fingerprint, which catches an edit. A person who wrote a whole new preview file, with a
  fingerprint worked out to match, could confirm it without anyone having been shown it. The saved previews are
  not signed.

About time:

- **No run waited a real 15 minutes.** Expiry was shown with the test clock only.
- **The test clock option is part of the workflow, not a separate test build.** Anyone can pass it. It can only
  make a preview older.
- **The machine's clock is trusted.** A preview dated in the future is refused. If the clock were set back to
  inside the 15 minutes, an old preview would be accepted. **Not assessed.**

About what a preview shows:

- **Criterion 7 rests on one reader**, who is the participant.
- **A credential is looked for by field name only.** A secret typed into a description would be shown in the
  preview and saved with it.
- **Characters that look alike, and spaces at the end of a value, are shown as they are** and are easy to miss.
  Characters that cannot be shown at all are refused.
- **A long preview is still long.** Nothing marks which change deserves the most care.

About the check at the moment of writing:

- **The whole board is in the fingerprint.** Any change to the board, even to a story the preview does not
  touch, cancels the preview. That is safe, and on a busy real board it would cancel previews often.
- **Nothing locks the board.** Two confirmations at the same moment, or a board changed in the instant between
  the check and the write, are **not assessed**.
- **A crash between writing the board and writing the record** would leave the board changed with no record.
  The preview would then be refused as overtaken. **Not assessed.**
- **The 12-character code.** Whether two different previews could be made with the same code was **not
  assessed**. Two previews of the same change against the same board in the same second do get the same code,
  and the second is refused.

Other:

- The board has three writable fields and no delete.
- Saved previews are never cleaned up.
- There are no unit tests. The checks are the recording script and what it prints.
- No independent review has been run on this attempt.
- The second stretch goal, editing a preview, was not built as a feature.

## Sensitive values

None. The board and its stories are made up. The workflow uses no network, account or login, so there is no
key or password in the code, the logs, the saved previews or the write records. One sample change file,
`scripts/sample/with-auth-field.json`, has a field named `auth_header` whose value is the word `example`. It is
there to show the workflow refusing it. No customer name and no real ticket content appears. The only person
named is Beau Brown, as the participant.
