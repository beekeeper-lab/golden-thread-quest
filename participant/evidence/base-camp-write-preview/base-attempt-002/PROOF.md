# Proof · base-camp-write-preview

Attempt: `base-attempt-002`

## In plain words

An agent asked to "create the follow-up stories" shouldn't just create them. I built a fake story
tracker (a stand-in for Jira) where every write takes two separate steps: a **preview** that shows
exactly what would be written and changes nothing, and a **confirmation** where a person types the
preview's fingerprint. The tracker writes only if that exact preview is still fresh and still
matches the change, and it records who approved the write. I used it to create three Tixly
follow-up stories, and recorded it refusing two bad confirmations first.

| | Result |
|---|---|
| Stories created | 3 (TIX-1 to TIX-3), all or none, confirmed by me under preview 22E3-E1CD-4D07 |
| Refused, nothing written | A confirmation after the stories file changed, and one for a preview older than 15 minutes |
| Reviewer check | PASSED; prints the same result on every run, so it can be re-run and compared |
| Sent anywhere real | Nothing: the tracker is a local folder Git ignores |

## What was built

- **The tracker**, `participant/tools/fake-story-tracker.py` (version 1.11.0), with three commands:
  `preview` shows the target, the action and every field of every story, says nothing was written,
  and ends with a fingerprint; `confirm` asks a person to type that fingerprint and writes only if
  every check passes; `list` shows every stored story with who confirmed it, when, and under which
  preview.
- **The rules**, `participant/context/write-preview-rules.md`: what a preview must contain, how a
  confirmation is tied to it, when it expires, what a write records, and what happens when the
  tracker's own files can't be trusted.
- **The proposed change**, `participant/context/write-preview/follow-up-stories.yaml`: three
  follow-up stories, each the work that follows one of my clarification questions from the
  previous quest, with an invented answer.
- **The reviewer check**, `participant/tools/check-write-preview.py` (version 1.5.1): it runs every
  acceptance criterion in a temporary folder with a fixed clock, so a reviewer gets the identical
  output each time. My recorded runs use the real clock, so their fingerprints and times can't
  repeat; this check is the part that can be re-run and compared word for word.

My decisions:
- **Tixly follow-up stories in a fake story tracker**, continuing my Tixly work, matching the
  quest's scenario.
- **Three stories in one preview, confirmed all or none**: the scenario's danger is a batch, and
  one approval should cover exactly what was shown.
  - From Q-02, "never selling the same seat twice": lock each seat while it's held (High).
  - From Q-03, "refunds until the doors open": keep refunds open until doors-open time (High).
  - From Q-07, "the buyer can try again": let the buyer retry a declined payment (Medium), keeping
    the edge case that the seats are still released when CHK-03's 10-minute hold ends.
- **Confirm by typing the fingerprint**, not "yes": typing it shows the person had this preview in
  front of them. There is no option that skips the preview or the typing.
- **A 15-minute limit**: long enough to read three stories, short enough that a preview left open
  over lunch can't be approved later.
- **Recording the reviewer check as a fourth log**, so the reviewer has an exact result to compare
  with.

I built this with Claude (Claude Code). Claude drafted the stories from my decisions, the tracker,
the check, the rules and this proof, and explained each step. The decisions above, the stories'
priorities and the reflection are mine.

## Where the important artifacts are

| Artifact | Path |
|---|---|
| The rules | `participant/context/write-preview-rules.md` |
| The proposed change | `participant/context/write-preview/follow-up-stories.yaml` |
| The tracker | `participant/tools/fake-story-tracker.py` |
| The reviewer check | `participant/tools/check-write-preview.py` |
| Preview, then the tracker unchanged | `participant/evidence/base-camp-write-preview/base-attempt-002/logs/preview.txt` |
| Two refused confirmations | `participant/evidence/base-camp-write-preview/base-attempt-002/logs/refused.txt` |
| The confirmed write | `participant/evidence/base-camp-write-preview/base-attempt-002/logs/confirmed.txt` |
| The reviewer check's run | `participant/evidence/base-camp-write-preview/base-attempt-002/logs/check.txt` |

## How to reproduce the behavior

From the repository root. **The reviewer check** gives the same output every time, so it can be
compared with `logs/check.txt` word for word. It works only in a temporary folder:

```bash
.venv/bin/python participant/tools/check-write-preview.py \
    --stories participant/context/write-preview/follow-up-stories.yaml
```

**The real commands**, as recorded. They use the real clock, so a re-run gives a new fingerprint
and new times but the same behavior. Before `confirm`, set `FAKE_STORY_TRACKER_TOKEN` in the
terminal (with `export`) to any made-up value; the tracker only checks that one is set:

```bash
.venv/bin/python participant/tools/fake-story-tracker.py preview --stories participant/context/write-preview/follow-up-stories.yaml
.venv/bin/python participant/tools/fake-story-tracker.py confirm --stories participant/context/write-preview/follow-up-stories.yaml
.venv/bin/python participant/tools/fake-story-tracker.py list
```

The tracker lives in `local-data/fake-story-tracker/`, which Git ignores. Delete that folder to
start from an empty tracker.

## How a confirmation is bound to its preview

The **fingerprint** is a code made from three things: the exact change (the target, the action and
every field of every story), the tracker's contents when the preview was made, and the time it was
made. Change any of them and the code changes (criterion 3).

To confirm, a person types the fingerprint at the keyboard. Before writing, the tracker re-reads
the stories file and checks that it still holds **exactly** the change that was previewed; checks
that the tracker hasn't changed since; and checks that the saved preview hasn't been edited, used
before, or gone stale. Any difference is refused, named, and nothing is written (criterion 4). In
`refused.txt`, I changed one word of story 1's title after the preview ("can't" to "cannot") and
typed the preview's fingerprint: "Refused: The stories file no longer holds the change that was
previewed: story 1: title changed. Nothing was written." (The line meant to show that edit came out
empty, because Git wasn't tracking the stories file yet, so it had nothing to compare; the refusal
names the change itself.) A preview approves **one** write: once it's used, the same fingerprint
is refused, and two people confirming at the same moment can't both write.

## What happens to a preview that goes stale

A preview can be confirmed for **15 minutes** after it was made (criterion 5). The time is checked
when the fingerprint is typed, not when `confirm` was started, so leaving the prompt open doesn't
stretch it, and a clock set back can't make an old preview look new. In `refused.txt`, a preview dated 20 minutes earlier was refused: "The preview expired
at 10-29-2026 12:01:30 PM EDT (made 10-29-2026 11:46:30 AM EDT; the limit is 15 minutes). Nothing
was written." The person previews again and reads the change as it is now. A preview can be dated
earlier (to show this) but never later, so its life can only be shortened.

## What was tested or validated

Against the acceptance criteria:

1. **A preview lists the target, the action and every field that would be written:** see
   `preview.txt`. The reviewer check reads all 26 labeled values back and compares each one whole
   with the stories file.
2. **Running without confirmation changes nothing, and the output says so:** the preview ends
   "Nothing was written. The tracker still has 0 stories.", and `list` right after shows 0 stories.
   I predicted this run before first recording it (3 stories, TIX-1 to TIX-3, 0 stories, nothing
   written), and it matched. After later review fixes I re-recorded all four logs on the final code,
   so every log shows the same version; the stories file and what the runs show were unchanged.
3. **A confirmation names or fingerprints the exact preview it approves:** I typed 22E3-E1CD-4D07;
   each story in `confirmed.txt` records "under preview 22E3-E1CD-4D07".
4. **A change that differs from the preview is refused and nothing is written:** the first refusal
   in `refused.txt`, followed by `list` showing 0 stories.
5. **A preview older than the time limit can't be confirmed:** the second refusal in
   `refused.txt`.
6. **The result records what was written and that a person confirmed it:** in `confirmed.txt`,
   `list` shows TIX-1 to TIX-3 with every field as previewed, and "Confirmed: by Tom Carter at
   10-29-2026 12:07:46 PM EDT, under preview 22E3-E1CD-4D07" on each.
7. **A person with no knowledge of the code can read a preview and say what will happen:** the
   preview is plain labeled text: the target, "create 3 stories, all or none", each story's key,
   fields and criteria, and when it expires. This is judged by a person; my reflection below is
   about where it could still be skimmed.

The reviewer check (`check.txt`) also confirms the safety constraints: an answer piped in is
refused (a person must type); no token means no write, and the token is never stored or shown;
two simultaneous confirmations write once; a tracker folder that is a link is refused; and the
real commands work end to end.

**Review.** GitHub Copilot reviewed the tracker, the check, the rules and the stories on a
practice pull request in my own copy (Hoosiertom50/golden-thread-quest#6) over 13 rounds, ending
with "Approval recommended" and no open issues. Every finding was reproduced before it was fixed,
including several that Copilot only hinted at in its round summaries. It found **4 High** issues:
- two confirmations at the same moment could both write (fixed with a lock on the tracker);
- the clock was read before the person typed, so leaving the prompt open stretched the limit;
- a tracker folder that was a link let writes land in another folder's files (folders are now
  opened without following links);
- two large confirmed batches could make the tracker too big to read back (fields now have length
  limits, and a write is refused if its file would be too big).

Later rounds hardened the tracker against damaged or unusual input: a clock set back before the
preview, hand-edited tracker files, folders it can't create, a failure to show the result after a
successful write (it now says the stories were written), a confirmer's name with a tab in it, and
text that looks the same but is stored differently. One finding, a clock set back only part-way,
can't be fixed by a program that trusts the computer's clock; it is a documented limitation below.

Many Mediums made the **check** honest: it had passed while a field was missing or a value was
wrong ("Highest" for "High"), so it now compares every value whole. Before every round Claude
re-read both programs and ran its own tests (84 cases), and tested the check against 24
deliberately broken trackers to prove it catches what it claims. That testing also found mistakes
in the check itself, which were fixed before Copilot saw them. Those working tests stay in my own
folder and aren't part of the hand-in; the reviewer check is the part a reviewer can re-run.

The tracker is longer than the earlier quests' tools (about 720 lines) for that reason: most of it
is the hardening from these rounds (links, damaged files, clocks, two confirmations at once), and
each part answers a specific finding.

## Reflection: which part of the preview would a tired reviewer skim past?

Reading my own preview, I don't see anything I'd skim, but I wrote these stories, so I'd read them
closely. Someone seeing them cold might not. They would probably read story 1 carefully and give
the later ones less attention, especially story 3, because its priority is only Medium. Yet story 3
holds an edge case that matters: the seats are still released when the 10-minute hold ends, even if
the buyer is still retrying.

How I'd make it harder to skim: a short summary at the top of the preview, so the reviewer sees the
whole change before the detail, and a flag on the unusual parts (edge cases, or anything that
replaces an existing rule, like story 2 replacing CHK-05's 48-hour cutoff). If the reviewer has to
notice and acknowledge the flagged parts, it shows they read the whole thing rather than skimming
it.

## Remaining limitations

- **A typed confirmation shows someone was at a keyboard, not that a person read it.** A piped-in
  answer is refused, but a program that pretends to be a keyboard can still type the fingerprint
  (the reviewer check does exactly that, to test the real command). A real system would add an
  approval only a person can give, such as approving in the tracker's own screen.
- **The time limit trusts the computer's clock.** A clock set back to before the preview was made is
  refused, but one set back only part-way (a 30-minute-old preview made to look 5 minutes old)
  can't be told apart from a fresh one by any program that reads that clock. A real system would
  take the time from a server the person confirming can't change.
- **macOS and Linux only, one computer.** The tracker uses a Unix file lock and the reviewer check
  simulates a keyboard, so neither runs on Windows. The lock that stops two simultaneous
  confirmations works between runs on the same computer, not across a shared network folder.
- **Simulated.** The tracker is a local folder and the token is never checked against anything; a
  real integration would call a real API with a real, restricted token kept in a secret store.
- **The fingerprint is 12 characters.** Enough that two different previews won't share one by
  chance, but it isn't a security signature.
- **Stretch goals.** Partly: editing the stories after a preview invalidates the old confirmation
  (criterion 4), and the preview shows the tracker's current count and the keys each story will
  get, but it isn't a full side-by-side difference against the current state.

## Sensitive values

No real project, person, customer or credential is in this hand-in. Tixly, every story and every
answer are invented. The token used was a made-up value; the tracker never prints or stores it, and
the reviewer check confirms it appears in no saved file or output. The repository's secret scan
first flagged three places that *looked* like secrets (the setup line in this proof, and a made-up
value and a variable name in the check). None was a real secret, but a scan that flags them would
also flag a real one written the same way, so I rewrote them rather than ask for an exception.
