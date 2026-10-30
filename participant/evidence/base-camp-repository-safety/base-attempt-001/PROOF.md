# Proof · base-camp-repository-safety

Attempt: `base-attempt-001`

## In plain words

I mapped who owns what in my quest repository, and built a small **fake bug tracker** that
files made-up defects the way a safe Jira integration should. Then I tested it like a QA
test pass:

| Test | What it proves | Result |
|---|---|---|
| File BUG-101 | A write is previewed and needs my "yes" | Previewed, I typed yes, filed |
| File BUG-101 again | A rerun creates no duplicate | "already filed", nothing written, still 1 defect |
| File BUG-102 with a simulated crash right after the write | An interrupted run can be recovered | The next run spotted the crash, filed nothing twice, cleaned up; 2 defects |
| List the defects | Reads are audited too | 3 read rows in the audit log |

The sections below give the detail for the reviewer, criterion by criterion.

## What was built

- **An ownership document**, `participant/context/repository-ownership.md`. It maps the five
  zones of the repository (program, mine, generated, private runtime data, credentials), who
  may change each, and whether each goes into Git. It also lists the four actors (me, an AI
  agent working for me, the quest app, my reviewer) and what each may read and write.
- **A fake bug tracker**, `participant/tools/fake-bug-tracker.py` (Python standard library
  only), standing in for an outside system like Jira. Its "outside system" is a file in
  `local-data/fake-bug-tracker/`, which Git ignores, so nothing real is ever touched. It:
  - takes its credential only from the environment (`FAKE_BUG_TRACKER_TOKEN`), and never
    prints, logs or stores it;
  - previews every write and only writes after the person types exactly `yes` at a terminal
    (a `yes` piped or redirected in is refused; this stops the simple way of confirming
    without anyone at the keyboard, though a determined program could still fake a terminal);
  - refuses to file a defect whose key is already filed, so a rerun never duplicates;
  - notes each write in `local-data/fake-bug-tracker/pending.json` before doing it, so the
    next run can settle a run that was cut off;
  - writes every file through a temporary file and renames it into place, so a file is never
    half-replaced; if a write fails with an error, the temporary file is removed (an abrupt
    stop, such as a power cut, can still leave one behind; see the limitations);
  - adds a row to the audit log for every read, preview, write, skip, cancellation, refusal
    and recovery.
- **An audit log**, `participant/context/audit-log.md`, written by the tracker: 9 rows from my
  runs, each with time, action, target, actor, outcome and whether the write was confirmed.
- The two defects are invented, but based on real Seatwise history: a Firefox autofill bug I
  found in my own testing, and a name-rule gap still in my backlog.

I built this with Claude (Claude Code). Claude drafted the ownership document, the tracker and
this proof, and I decided how I appear in the audit log, what the fake defects are, and to do
the optional interruption demonstration. I ran every command myself and checked each output.
I did not look at anyone else's solution to this quest.

Before handing in, I had GitHub Copilot review the work on a practice pull request in my own
copy (Hoosiertom50/golden-thread-quest#2). It found no High findings and 10 Medium ones. I
fixed the three where my documents claimed more than was true (credentials can't be
committed "even by mistake"; the app "never commits"; temporary files are "always" removed)
and four small code issues: a piped `yes` could confirm a write without anyone at the
keyboard, a `list` right after a crash didn't settle it, the "filed" audit row came after the
pending note was removed, and a key with a hidden line break was accepted. That was version
1.1.0. The other three are listed under Remaining limitations.

A second Copilot review confirmed those 10 resolved, found no High, and raised 5 new Medium
findings. My bar was no High and at most 3 Mediums, so I fixed two claims that overstated
things (the terminal check, and how far the secret scan reached) and two code issues I judged
worth it: pressing Ctrl-C at the prompt cancelled without an audit row, and a damaged data
file wasn't checked entry by entry. A third review found no High and three Mediums: the run
records were missing (I had cleared them to redo the runs), a data file of garbled bytes
crashed the tool instead of being refused (fixed, as part of the same damaged-file fix), and a
mistyped command isn't audited (listed under Remaining limitations). That is version 1.2.0, and every run in this hand-in was
redone with it. The fifth, about power-loss durability, is listed under Remaining limitations.

## Where the important artifacts are

| Artifact | Path |
|---|---|
| Ownership document | `participant/context/repository-ownership.md` |
| Audit log | `participant/context/audit-log.md` |
| The fake bug tracker | `participant/tools/fake-bug-tracker.py` |
| First read (0 defects) | `participant/evidence/base-camp-repository-safety/base-attempt-001/logs/read.txt` |
| First run: BUG-101 previewed, confirmed, filed | `.../base-attempt-001/logs/first-run.txt` |
| Second run: no duplicate, then a list showing 1 defect | `.../base-attempt-001/logs/second-run.txt` |
| Interrupted run: BUG-102 crash, and the pending note left behind | `.../base-attempt-001/logs/interrupted-run.txt` |
| Recovery run: crash settled, nothing repeated, 2 defects, note cleaned up | `.../base-attempt-001/logs/recovery-run.txt` |

Not handed in, on purpose: `local-data/fake-bug-tracker/defects.json` (the fake outside
system's data, private runtime data) and the token, which only ever lived in my terminal.

## How to reproduce the behavior

From the repository root, in one terminal window:

```bash
read -rs FAKE_BUG_TRACKER_TOKEN && export FAKE_BUG_TRACKER_TOKEN   # type any made-up value
T=participant/tools/fake-bug-tracker.py
.venv/bin/python $T list                                              # a read
.venv/bin/python $T file --key BUG-201 --severity Low --title "Demo defect"   # type yes
.venv/bin/python $T file --key BUG-201 --severity Low --title "Demo defect"   # "already filed"
FAKE_BUG_TRACKER_SIMULATE_CRASH=after-write .venv/bin/python $T file --key BUG-202 --severity Low --title "Crash demo"   # type yes
ls local-data/fake-bug-tracker                                        # pending.json is there
.venv/bin/python $T file --key BUG-202 --severity Low --title "Crash demo"    # "recovery: ...", nothing repeated
.venv/bin/python $T list                                              # no duplicates
```

Without the token, every command is refused and writes nothing but a "refused" audit row.
These commands add rows to the audit log in whichever copy they are run in.

## How I tested interruption and rerun behavior

- **Rerun:** I ran the exact same `file` command for BUG-101 twice. The second run found the
  key already filed, asked nothing and wrote nothing, and a list afterwards showed 1 defect
  (`logs/second-run.txt`).
- **Interruption:** I set `FAKE_BUG_TRACKER_SIMULATE_CRASH=after-write`, which stops the
  program the instant the defect is written, before it can clear its pending note or write
  its "filed" audit row: the same state a power cut or a killed terminal would leave.
  `logs/interrupted-run.txt` shows the run stopping with no exit status, then `pending.json`
  still present.
- **Recovery:** I ran the same command normally. It found the pending note, saw BUG-102 was
  already in the tracker, recorded a `recover` row, cleared the note and filed nothing again.
  A list showed exactly 2 defects and the folder held only `defects.json`
  (`logs/recovery-run.txt`).
- **What the audit log shows for the crash:** there is no "filed" row for BUG-102, because
  the crashed run never got to write one. The `recover` row at 15:07:50Z records that the
  write had happened. I left it that way rather than inventing a row afterwards.

## What was tested or validated

Against the acceptance criteria:

1. **Program, participant and generated areas documented:** the zones table in
   `repository-ownership.md`, with the exact folders in each.
2. **Credentials from the environment:** the tracker reads `FAKE_BUG_TRACKER_TOKEN` only from
   the environment, set with `read -rs` so it never showed on screen, and never writes it
   anywhere. GitHub access uses the GitHub CLI's own login, kept in the macOS keychain.
3. **Generated output and private runtime data ignored by Git:** `.gitignore` ignores
   `/generated/` and `/local-data/` (and `.env`, `*.key`, `credentials.json`, `**/secrets/`
   and more). `git check-ignore -v` confirms each, and `git status` shows changes only under
   `participant/`.
4. **External writes previewed and confirmed:** every `file` shows the exact defect first
   and needs a typed `yes` (`logs/first-run.txt`); anything else cancels with nothing written.
5. **Audit log fields:** every row has time (UTC), action, target, actor ("Tom Carter via
   fake-bug-tracker.py"), outcome, and whether the write was confirmed.
6. **No duplicate on rerun:** `logs/second-run.txt` and `logs/recovery-run.txt`.
7. **Understandable without asking the AI:** the ownership document is written for a person,
   with tables and a "How to check this is true" section of commands anyone can run.

The registered validator, `validate-repository-foundation`, is run from the evidence page as
the last step before submitting. The app saves its result in this attempt's `validation/`
folder, so it is in the hand-in but not in earlier drafts.

Claude ran the application's secret-scanning function for me over every file under `participant/`, not
just the evidence files the app's own scan covers. It found nothing.

**Reflection** (the quest's question): code enforces the confirmation prompt, the no-duplicate
rule, the pending-note recovery and the credential coming from the environment. Repository
structure enforces what reaches Git, through `.gitignore` and keeping private data in
`local-data/`. Human judgment still decides whether a previewed write is right before typing
`yes`, and whether anything personal slipped into a title or a log before committing.

## Remaining limitations

- The "outside system" is a local file. A real tracker would add network failures, rate
  limits and permissions, which this does not exercise.
- Recovery covers one interrupted write at a time (one pending note).
- Two runs at the same moment are not prevented, and are worse than a duplicate: if one run
  waits at its prompt while another files a defect, confirming the first would overwrite the
  file without the second defect. A real integration would lock the tracker for the whole
  operation.
- The tool writes to fixed paths and follows folder shortcuts (symlinks). If someone replaced
  `local-data/fake-bug-tracker` or `participant/context` with a link, writes would follow it
  outside the repository. The quest app itself guards against this; this small tool does not.
- A mistyped command (for example an unknown severity) is refused by Python's own option
  parser before the tool starts, so it writes nothing but also adds no "refused" audit row.
- After a write the tool forces the file onto the disk but not the folder's record of it, so a
  power cut in that split second could lose the last save (it could not duplicate it).
- A temporary file left by an abrupt stop (power cut, killed process) is not cleaned up
  automatically. One left under `participant/` would be committed by `gtq hand-in`, so
  `git status --short participant` is worth a look first.
- The terminal check refuses ordinary piped or redirected input. It does not prove a person
  typed the answer: a program can create a fake terminal and send `yes`, and it says nothing
  about who was at the keyboard. Human approval still depends on the person running it.
- The crash is simulated at one point, right after the write. A crash before the write is
  also handled (the pending note is cleared and nothing was filed), but I did not record a
  run of it.
- Defect titles are written to the audit log as typed. They are made up here; with real data
  a person would need to check them before committing.
- The actor name comes from the repository's Git setting (`user.name`), which anyone can set.
  It records who ran the tool, not a verified identity.

## Sensitive values

No real secret, token, customer name or private ticket content is in this hand-in. The token
was a made-up value typed in my terminal and is not in any file. The two defects are invented
from my own testing notes and contain no personal data. The tracker's data file stays in
`local-data/`, which Git ignores.
